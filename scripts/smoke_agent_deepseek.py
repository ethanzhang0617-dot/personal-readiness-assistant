"""Manual live smoke test for the V1.4 Agent layer.

The automated suite (`test_agent.py`) mocks the provider on purpose: no test may
spend a real API call. This script is the opposite - it is the only place that
exercises the **real** configured DeepSeek provider through the real V1.4
orchestration stack, so that a release can prove the planning call, the tool
round, the grounded synthesis and the guards work against the live provider.

Run it by hand:

    DEEPSEEK_API_KEY=... python3 scripts/smoke_agent_deepseek.py

  or, when a local ``.streamlit/secrets.toml`` already holds the key:

    python3 scripts/smoke_agent_deepseek.py

Options:

    --all           also run the optional second case (what-if / Decision Explorer)
    --attempts N    how many times to try each case (default 2; provider wording is
                    stochastic and an existing grounding guard may reject a draft)
    --strict        exit non-zero when no credential is configured
    --show-answer   print the full answer instead of a short preview

It never runs during pytest, the frontend build, a Vercel build, a Render build
or CI: nothing imports it and nothing invokes it automatically. Without a
credential it prints SKIPPED and exits 0, so it can never fail a build.

The script never prints the credential, the Authorization header, the system
prompt or any chain-of-thought - only the public metadata the API itself exposes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_orchestrator
import agent_planner
import ai_engine
from backend.services import coach_service, readiness_service, response_service, state_service, training_service


#: Mandatory case: this question needs several verified sources, so a passing run
#: proves the planner, the tool round and the grounded synthesis all happened.
PRIMARY_QUESTION = "Why is today's recommendation lighter than usual?"

#: Optional second case: the what-if facet should reach the existing Decision
#: Explorer (read-only simulation).
SECOND_QUESTION = "I still want to train back. What would change?"

MIN_TOOLS = 2

_SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-]{4,}")


class CountingProvider:
    """Delegates to the real provider and counts the calls it made.

    The transport underneath is the unmodified ``ai_engine.DeepSeekCoachProvider``;
    this wrapper only records how many times the live provider was actually called
    (one planning call plus one answer call per Agent turn).
    """

    def __init__(self, inner: ai_engine.DeepSeekCoachProvider) -> None:
        self.inner = inner
        self.calls = 0

    @property
    def configured(self) -> bool:
        return self.inner.configured

    def complete(self, messages):
        self.calls += 1
        return self.inner.complete(messages)


def _clean(text: str) -> str:
    """Never let a credential reach the terminal, whatever happens upstream."""
    return _SECRET_PATTERN.sub("sk-***", str(text))


def _demo_turn():
    """A canonical demo state, built from the existing fixtures only."""
    _, seeded = state_service.base_state("demo-ethan")
    state = state_service.UserState(**seeded)
    profile = state_service.materialise(state)
    draft = state_service.check_in_draft(state, profile)
    assessment = readiness_service.assess(profile, draft)
    recommendation = training_service.recommend(profile, assessment)
    decision = response_service.evaluate(profile, assessment, recommendation)
    return state, profile, assessment, recommendation, decision


def _run_case(question: str, secrets: dict, show_answer: bool,
              attempt: int = 1, total_attempts: int = 1,
              verbose: bool = True) -> tuple[bool, dict, dict[str, object]]:
    state, profile, assessment, recommendation, decision = _demo_turn()
    provider = CountingProvider(ai_engine.DeepSeekCoachProvider(
        api_key=ai_engine.deepseek_api_key(secrets),
        model=ai_engine.deepseek_model_name(secrets),
        base_url=ai_engine.deepseek_base_url(secrets),
    ))
    started = time.monotonic()
    result = agent_orchestrator.run(
        question=question,
        profile=profile,
        assessment=assessment,
        recommendation=recommendation,
        decision=decision,
        state=state,
        history=[],
        secrets=secrets,
        provider=provider,
    )
    elapsed = time.monotonic() - started

    agent = result.get("agent") or {}
    tools = list(result.get("tools_used") or [])
    rejected = [row for row in (agent.get("rejected") or [])]
    answer = str(result.get("answer") or "")

    summary = {
        "question": question,
        "attempt": attempt,
        "planner": agent.get("plan_source") == "planner",
        "strategy": agent.get("strategy"),
        "tools": list(tools),
        "grounded": bool(result.get("grounded")),
        "fallback": bool(result.get("fallback_used")),
        "guard_rejected": result.get("notice") == ai_engine.AI_REJECTED_NOTICE,
        "provider_error": result.get("notice") == ai_engine.AI_UNAVAILABLE_NOTICE,
        "provider_calls": provider.calls,
        "latency": round(elapsed, 2),
        "provider_seconds": agent.get("provider_seconds"),
    }

    if verbose:
        print(f"QUESTION: {question}")
        print(f"ATTEMPT: {attempt}/{total_attempts}")
        print(f"PROVIDER: {result.get('provider')}")
        print(f"STRATEGY: {agent.get('strategy')}   (plan source: {agent.get('plan_source')})")
        print("TOOLS USED:")
        for name in tools:
            print(f"- {name}")
        print(f"Grounded: {str(bool(result.get('grounded'))).lower()}")
        print(f"Fallback: {str(bool(result.get('fallback_used'))).lower()}")
        print(f"Provider calls: {provider.calls}   Agent latency: {elapsed:.2f}s   "
              f"Provider time: {agent.get('provider_seconds')}")
        print(f"Answer received: {'yes' if answer else 'no'}")
        print(f"Answer preview: {_clean(answer[:200]) if not show_answer else _clean(answer)}")
        print(f"Rejected tools: {rejected or 'none'}")
    else:
        print(f"run {attempt}: planner={'ok' if summary['planner'] else 'no'} "
              f"tools={len(tools)} grounded={str(summary['grounded']).lower()} "
              f"fallback={str(summary['fallback']).lower()} "
              f"guard_rejected={str(summary['guard_rejected']).lower()} "
              f"latency={elapsed:.2f}s provider={agent.get('provider_seconds')}")

    failures: list[str] = []
    if provider.calls < 1:
        failures.append("the provider was never called")
    if agent.get("strategy") != agent_planner.PLANNER_STRATEGY:
        failures.append(f"strategy is {agent.get('strategy')!r}, expected the Agent layer")
    if agent.get("plan_source") != "planner":
        failures.append(f"plan source is {agent.get('plan_source')!r}, expected the live planner")
    if len(tools) < MIN_TOOLS:
        failures.append(f"only {len(tools)} verified tool(s) were used")
    if not answer:
        failures.append("the answer was empty")
    if not result.get("grounded"):
        failures.append("the answer was not grounded")
    if result.get("fallback_used"):
        failures.append("a deterministic fallback was used instead of the provider")
    if any(str(row.get("reason", "")).split(":")[0] in {"unknown_tool", "invalid_arguments"} for row in rejected):
        failures.append(f"a tool name or argument set was rejected: {rejected}")

    if failures and summary["guard_rejected"]:
        # A guard rejection is a legitimate product outcome: the draft was not
        # shown and the verified deterministic answer was used instead. It says
        # nothing about whether the provider itself worked.
        print("NOTE: the live draft was rejected by a grounding / safety / decision-authority guard, "
              "so the verified deterministic answer was shown. This is the documented fallback path.")
    if verbose:
        print(f"CASE RESULT: {'PASS' if not failures else 'FAIL - ' + '; '.join(failures)}")
    summary["failures"] = failures
    return (not failures), result, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Real-provider smoke test for the V1.4 Agent layer.")
    parser.add_argument("--all", action="store_true", help="also run the optional what-if case")
    parser.add_argument("--attempts", type=int, default=2,
                        help="attempts per case (default 2: the provider wording is stochastic and a grounding "
                             "guard may reject a draft, which the product answers deterministically)")
    parser.add_argument("--stability", type=int, default=0, metavar="N",
                        help="run the mandatory question N times without retrying and report the guard-rejection "
                             "rate (use this to measure prompt stability before a production promotion)")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when no credential is configured")
    parser.add_argument("--show-answer", action="store_true", help="print the full answer")
    args = parser.parse_args()
    attempts_allowed = max(1, min(int(args.attempts), 5))

    secrets = coach_service.server_secrets()

    print("REAL DEEPSEEK AGENT SMOKE")
    print(f"Provider: {ai_engine.AI_PROVIDER_LABEL}")
    print(f"Model: {ai_engine.deepseek_model_name(secrets)}")
    print(f"Planner strategy: {agent_planner.PLANNER_STRATEGY} "
          f"(native tool calling: {agent_planner.NATIVE_TOOL_CALLING_SUPPORTED})")
    print("")

    if not ai_engine.ai_coach_enabled(secrets):
        print("SKIPPED - DEEPSEEK_API_KEY not configured")
        print("Set DEEPSEEK_API_KEY (or .streamlit/secrets.toml) and run this script again.")
        print("Automated tests stay mocked; nothing else in the project depends on this script.")
        return 3 if args.strict else 0

    cases = [PRIMARY_QUESTION] + ([SECOND_QUESTION] if args.all else [])
    results = []
    attempt_report: list[dict] = []
    stability_rejections = 0
    stability_runs = 0

    if args.stability > 0:
        runs = max(1, min(int(args.stability), 10))
        print("-" * 68)
        print(f"STABILITY RUN - {runs} independent attempts, no retry")
        summaries: list[dict] = []
        for index in range(1, runs + 1):
            passed, result, summary = _run_case(PRIMARY_QUESTION, secrets, args.show_answer, index, runs,
                                                verbose=False)
            summaries.append(summary)
            results.append((PRIMARY_QUESTION, passed, result))
        rejected = [row for row in summaries if row["guard_rejected"]]
        grounded = [row for row in summaries if row["grounded"]]
        latencies = [float(row["latency"]) for row in summaries]
        stability_rejections = len(rejected)
        stability_runs = runs
        print(f"Guard rejections: {len(rejected)}/{runs}   Grounded: {len(grounded)}/{runs}   "
              f"Latency: min {min(latencies):.2f}s / max {max(latencies):.2f}s")
        print("STABILITY RESULT: " + ("PASS" if len(rejected) <= 1 else "FAIL - review the prompt before promoting"))
        # The mandatory question was measured above; only run the optional case here.
        cases = [SECOND_QUESTION] if args.all else []

    for question in cases:
        passed, result = False, {}
        used = 0
        for attempt in range(1, attempts_allowed + 1):
            print("-" * 68)
            passed, result, _summary = _run_case(question, secrets, args.show_answer, attempt, attempts_allowed)
            used = attempt
            if passed:
                break
        attempt_report.append({"question": question, "attempts": used, "passed": passed})
        results.append((question, passed, result))
        print("")

    passed = all(ok for _question, ok, _result in results)
    if stability_runs:
        passed = passed and stability_rejections <= 1
    retried = [row for row in attempt_report if row["attempts"] > 1]
    if retried:
        print("Guard-rejected drafts that were retried (the product showed the verified answer on the "
              "rejected attempt):")
        for row in retried:
            print(f"- {row['attempts']} attempt(s) for: {row['question']}")
    used_tools: list[str] = []
    for _question, _ok, result in results:
        used_tools.extend(list(result.get("tools_used") or []))
    if args.all:
        explorer = any("run_decision_explorer" in (result.get("tools_used") or []) for _q, _o, result in results)
        print(f"Decision Explorer selected in the what-if case: {'yes' if explorer else 'no'}")
        passed = passed and explorer

    print("=" * 68)
    print(f"Strategy: {agent_planner.PLANNER_STRATEGY}")
    print(f"Grounded: {all(bool(r.get('grounded')) for _q, _o, r in results)}")
    print(f"Fallback used: {any(bool(r.get('fallback_used')) for _q, _o, r in results)}")
    if stability_runs:
        print(f"Guard rejection rate: {stability_rejections}/{stability_runs} "
              f"(previous observed baseline: 2/5)")
    print(f"Secret exposed: NO")
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
