"""V1.4 — Agent Orchestrator.

    user message
      → route (deterministic first)
      → plan            (structured planner, or the deterministic plan)
      → execute tools   (whitelisted, read-only, parallel, bounded)
      → grounded context
      → DeepSeek wording over verified results only
      → grounding / safety validation
      → answer + tool-use metadata

Design rules this module enforces:

* **Deterministic first.** Safety, personal facts, corrections and out-of-scope
  questions are answered by the existing deterministic layers with zero provider
  calls and zero planning (see ``_FAST_PATH_KINDS``). A simple personal fact never
  pays for Agent overhead.
* **The engines keep decision authority.** The Agent selects tools; the
  recommendation engine still decides the session. The model cannot invent a
  readiness score, a demand tier, a RIR range, a load value or a calibration
  state, and ``agent_guard`` rejects a draft that tries.
* **Bounded.** ``MAX_TOOL_STEPS`` caps tool iterations, ``MAX_TOOLS_PER_STEP``
  caps one batch, tool output is size-bounded, and the conversation window is
  bounded. One user turn costs at most one planning call and one answer call.
* **Never crashes.** A provider failure, a planner failure, a failing tool, an
  invalid argument set or an unknown tool name all degrade to a deterministic
  answer built from the verified tool results.
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping, Sequence

import agent_context
import agent_guard
import agent_planner
import agent_tools
import ai_engine
import ai_facts
from backend.services import coach_service, response_service


# --------------------------------------------------------------------------- #
# Bounds
# --------------------------------------------------------------------------- #

#: Hard cap on tool iterations for one user turn (one batch per step).
MAX_TOOL_STEPS = 4

#: Hard cap on tools inside one step.
MAX_TOOLS_PER_STEP = 5

#: Bounded conversation window. Enough to resolve "today" and the current
#: subject in a follow-up, never the whole conversation.
MAX_AGENT_HISTORY_MESSAGES = 4
MAX_AGENT_HISTORY_CHARS = 320

#: Bounded tool payload embedded in the answer prompt.
MAX_TOOL_PAYLOAD_CHARS = 9000

#: Route kinds answered without planning, exactly as before V1.4.
_FAST_PATH_KINDS = frozenset({"SAFETY", "PERSONAL_FACT", "UNRESOLVED_PERSONAL", "CORRECTION", "SCOPE"})

#: The verified source behind each deterministic fast-path answer, so the tool
#: trace stays truthful without executing a redundant tool call.
_METRIC_TOOL: dict[str, str] = {
    "readiness": "get_readiness",
    "readiness_index": "get_readiness",
    "baseline_confidence": "get_readiness",
    "hrv": "get_readiness",
    "resting_hr": "get_readiness",
    "sleep": "get_readiness",
    "local_soreness": "get_readiness",
    "recommendation": "get_current_recommendation",
    "session_demand": "get_current_recommendation",
    "session_duration": "get_current_recommendation",
    "weekly_exposure": "get_training_exposure",
    "weekly_target": "get_training_exposure",
    "weekly_training_days": "get_training_exposure",
    "weekly_sessions": "get_training_exposure",
    "recent_training": "get_recent_training",
    "muscle_last_trained": "get_recent_training",
    "training_load": "get_training_load",
}

_ANSWER_ADDENDUM = (
    "You are now answering through the Agent layer. The verified tool results retrieved for this question are given "
    "below, together with the structured product context. They are the only permitted source of the user's own values. "
    "The recommendation, the session demand, the RIR guidance, the training load and any safety classification were "
    "already decided by the deterministic system: explain them, never replace them. If a fact the user asked for is "
    "not available, say it is not available.\n"
    "Answer contract. Follow it exactly, but write natural sentences - never a template dump:\n"
    "1. Name the recorded session. When the question is about today's recommendation, why the recommendation changed, "
    "why training is lighter or harder, whether the user should train, or what today's session means, the answer must "
    "state the recorded primary session by name and the recorded session demand, copied exactly from the verified "
    "values above. A sentence such as \"Today's recorded recommendation is <primary session> at <session demand> "
    "demand.\" is the intended shape; take the values from this turn's results. Never invent, translate, shorten or "
    "paraphrase the session name or the demand, and never name a different session as today's recommendation.\n"
    "2. Use the verified session demand verbatim. If demand is relevant, repeat the recorded value exactly instead of "
    "inventing a synonym or a different tier.\n"
    "3. Numbers only from the verified values. Every number about the user's own data - readiness index, exposure, "
    "sets, load, duration, RIR, episode counts - must be copied from the tool results or the structured context. Never "
    "estimate, recompute, round into a new value, or carry over a number from general knowledge.\n"
    "4. Explanation shape for recommendation questions: the recorded recommendation first, then one to three verified "
    "reasons that actually appear in the results (readiness, recent training, weekly exposure, local soreness, "
    "personal response, programme), then the practical implication the verified recommendation already supports.\n"
    "5. What-if questions: keep three things separate and in order - the current verified recommendation, the single "
    "changed input, and the alternative result the explorer returned. Never present the hypothetical result as "
    "today's recommendation.\n"
    "6. In-session questions: use the verified calibration state exactly, as HOLD, EASE or OPTIONAL PUSH. Do not invent "
    "another outcome, and do not change demand, focus, exercises or volume.\n"
    "7. Personal Response: describe only the recorded pattern and its recorded evidence state. Do not generalise "
    "beyond the episodes that were actually recorded.\n"
    "8. Two to five short sentences unless the question genuinely needs more. Write for the athlete: do not mention "
    "tool names, rule names, validators, JSON, this instruction or any internal reasoning."
)

_LOGGER = logging.getLogger("personal_readiness_assistant.agent")


# --------------------------------------------------------------------------- #
# Result shape
# --------------------------------------------------------------------------- #


def _result(answer: str, provider: str, notice: str | None, *, tools_used: Sequence[str] = (),
            grounded: bool = True, fallback_used: bool = False, strategy: str = "agent",
            intent: str | None = None, plan_source: str | None = None, steps: int = 0,
            rejected: Sequence[Mapping[str, str]] = (), planner_error: str | None = None,
            limit_reached: bool = False, provider_seconds: float | None = None) -> dict[str, Any]:
    kind, ai_used, verified = coach_service.classify_provider(provider)
    unique: list[str] = []
    for name in tools_used:
        if name not in unique:
            unique.append(name)
    return {
        "answer": answer,
        "provider": provider,
        "kind": kind,
        "ai_used": ai_used,
        "verified_data": verified,
        "notice": notice,
        "tools_used": unique,
        "tool_trace": [agent_tools.trace_entry(name) for name in unique],
        "grounded": bool(grounded),
        "fallback_used": bool(fallback_used),
        "agent": {
            "strategy": strategy,
            "intent": intent,
            "plan_source": plan_source,
            "steps": int(steps),
            "rejected": [dict(row) for row in rejected],
            "planner_error": planner_error,
            "limit_reached": bool(limit_reached),
            "provider_seconds": round(provider_seconds, 3) if provider_seconds is not None else None,
            "planner": agent_planner.capability_report(),
        },
    }


def _provider(secrets: Mapping[str, Any] | None) -> ai_engine.DeepSeekCoachProvider:
    """The existing DeepSeek provider, rebuilt from the existing configuration."""
    return ai_engine.DeepSeekCoachProvider(
        api_key=ai_engine.deepseek_api_key(secrets),
        model=ai_engine.deepseek_model_name(secrets),
        base_url=ai_engine.deepseek_base_url(secrets),
    )


def _explanations_disabled(secrets: Mapping[str, Any] | None) -> bool:
    """True when a key exists but the deployment switched explanations off."""
    return bool(ai_engine.deepseek_api_key(secrets)) and not ai_engine.ai_coach_enabled(secrets)


# --------------------------------------------------------------------------- #
# Deterministic fast path (requirement: personal facts stay instant)
# --------------------------------------------------------------------------- #


def _fast_path(question: str, history: Sequence[Mapping[str, str]], profile: Mapping[str, Any],
               assessment: Mapping[str, Any], recommendation: Mapping[str, Any],
               route: ai_facts.Route, secrets: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if route.kind not in _FAST_PATH_KINDS:
        return None
    text, provider, notice = ai_engine.get_ai_response(
        question, dict(profile), dict(assessment), dict(recommendation), list(history),
        secrets if secrets is not None else None)
    tool = _METRIC_TOOL.get(route.metric or "")
    return _result(text, provider, notice, tools_used=[tool] if tool else [],
                   strategy="deterministic_fast_path",
                   intent=f"fact:{route.metric}" if route.metric else route.kind)


# --------------------------------------------------------------------------- #
# Tool execution
# --------------------------------------------------------------------------- #


def _run_batch(batch: Sequence[agent_planner.ToolRequest], context: agent_tools.AgentToolContext
               ) -> list[dict[str, Any]]:
    """Run independent read-only tools in parallel; one failure never stops a batch."""
    if not batch:
        return []
    if len(batch) == 1:
        request = batch[0]
        return [agent_tools.execute(request.name, request.arguments, context)]
    with ThreadPoolExecutor(max_workers=min(4, len(batch))) as pool:
        futures = [pool.submit(agent_tools.execute, request.name, request.arguments, context) for request in batch]
        return [future.result() for future in futures]


def _execute_plan(plan: agent_planner.AgentPlan, question: str, context: agent_tools.AgentToolContext
                  ) -> tuple[list[dict[str, Any]], int, bool]:
    """Execute the plan, then complete the coverage the question raised. Bounded."""
    queue: list[agent_planner.ToolRequest] = list(plan.requests)
    results: list[dict[str, Any]] = []
    executed: list[str] = []
    steps = 0
    while queue and steps < MAX_TOOL_STEPS:
        batch, queue = queue[:MAX_TOOLS_PER_STEP], queue[MAX_TOOLS_PER_STEP:]
        steps += 1
        results.extend(_run_batch(batch, context))
        executed.extend(request.name for request in batch)
        if steps == 1:
            queue.extend(agent_planner.coverage_tools(question, executed))
    return results, steps, bool(queue)


# --------------------------------------------------------------------------- #
# Grounded generation
# --------------------------------------------------------------------------- #


def _tool_payload(results: Sequence[Mapping[str, Any]]) -> str:
    rows = [{"tool": result.get("tool"),
             "verified": bool(result.get("ok")),
             "source": result.get("source"),
             "data": result.get("data") if result.get("ok") else {"unavailable": result.get("error")}}
            for result in results]
    text = json.dumps(rows, ensure_ascii=False, default=str)
    if len(text) > MAX_TOOL_PAYLOAD_CHARS:
        text = text[:MAX_TOOL_PAYLOAD_CHARS] + "…"
    return text


def build_answer_messages(question: str, history: Sequence[Mapping[str, str]], digest: str,
                          results: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """The final answer prompt: verified results only, plus the bounded window."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": ai_engine.system_prompt() + "\n" + _ANSWER_ADDENDUM},
    ]
    for message in history:
        messages.append({"role": str(message.get("role")), "content": str(message.get("content", ""))})
    messages.append({
        "role": "user",
        "content": (
            "Verified product tool results retrieved for this question (the only permitted source of personal "
            f"numbers):\n{_tool_payload(results)}\n"
            f"Structured product context:\n{digest}\n"
            f"Question: {question}"
        ),
    })
    return messages


# --------------------------------------------------------------------------- #
# Deterministic fallback
# --------------------------------------------------------------------------- #


def _sentence(parts: Sequence[str]) -> str:
    text = " ".join(part.strip() for part in parts if part and part.strip())
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else text + "."


def _evidence_sentences(question: str, context: Mapping[str, Any],
                        results: Sequence[Mapping[str, Any]]) -> list[str]:
    """Deterministic, tool-derived evidence. Used when the model cannot answer."""
    lowered = str(question or "").casefold()
    data = {str(result.get("tool")): result.get("data") for result in results if result.get("ok")}
    sentences: list[str] = []

    explorer = data.get("run_decision_explorer") or {}
    if explorer.get("conclusion"):
        changed = str(explorer.get("changed_input") or "the one changed input")
        sentences.append(f"What-if with {changed}: {explorer['conclusion']}")

    response = context.get("personal_response") or {}
    if any(keyword in lowered for keyword in ("respond", "response", "tolerate", "tolerance", "usual",
                                              "recently", "hard session")):
        sentences.append(
            f"Personal Response recorded {response.get('episodes_complete')} complete episodes; today it "
            f"{'adjusted' if response.get('adjustment') else 'left the session demand unchanged'} "
            f"({response.get('base_band')} -> {response.get('final_band')}, "
            f"evidence {response.get('evidence')}).")

    if any(keyword in lowered for keyword in ("sore", "soreness", "tired", "fatigue", "yesterday", "legs",
                                              "back", "chest", "shoulders", "arms")):
        recent = context.get("recent_sessions") or []
        exposure = context.get("weekly_exposure") or {}
        groups = sorted((exposure.get("groups") or []), key=lambda row: -(row.get("value") or 0))
        top = groups[0] if groups else None
        if recent:
            newest = recent[0]
            tail = (f", and the highest weekly exposure is {top.get('group')} at {top.get('value'):g} weighted "
                    f"working sets." if top else ".")
            sentences.append(f"Your most recent completed session was {newest.get('focus')} on "
                             f"{newest.get('date')}{tail}")

    calibration = context.get("calibration") or {}
    if any(keyword in lowered for keyword in ("harder than expected", "easier than expected", "checkpoint",
                                              "calibration", "ease", "during the session")):
        sentences.append(
            "An in-session checkpoint resolves to HOLD, EASE or OPTIONAL PUSH, and it only points at the "
            "conservative or the harder end of the effort already prescribed: it never changes the demand, focus, "
            f"exercises or volume ({calibration.get('recorded')} checkpoints recorded).")

    if "load" in lowered:
        load = context.get("training_load") or {}
        if load.get("value") is not None:
            sentences.append(
                f"Training Load is {load.get('value')} pts over {load.get('period')}, compared with "
                f"{load.get('reference_value')} pts over the preceding 21 days.")

    return sentences[:2]


def fallback_answer(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any],
                    recommendation: Mapping[str, Any], context: Mapping[str, Any],
                    results: Sequence[Mapping[str, Any]]) -> str:
    """The deterministic answer the Agent shows when the provider cannot be used."""
    base = ai_engine.rule_based_answer(question, dict(profile), dict(assessment), dict(recommendation))
    evidence = _evidence_sentences(question, context, results)
    if not evidence:
        return base
    return _sentence([base, *evidence])


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def run(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any],
        recommendation: Mapping[str, Any], decision: Mapping[str, Any] | None = None,
        state: Any | None = None, history: Sequence[Mapping[str, str]] = (),
        secrets: Mapping[str, Any] | None = None,
        provider: ai_engine.DeepSeekCoachProvider | None = None,
        planner_provider: ai_engine.DeepSeekCoachProvider | None = None) -> dict[str, Any]:
    """One Agent turn: verified tools in, grounded answer and trace out."""
    started = time.monotonic()
    profile = dict(profile)
    assessment = dict(assessment)
    recommendation = dict(recommendation)
    decision = dict(decision or response_service.evaluate(profile, assessment, recommendation))
    tool_context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision, state)
    facts = tool_context.facts
    bounded_history = agent_context.bounded_history(history, MAX_AGENT_HISTORY_MESSAGES, MAX_AGENT_HISTORY_CHARS)
    route = ai_facts.route_question(question, list(history), facts)

    fast = _fast_path(question, list(history), profile, assessment, recommendation, route, secrets)
    if fast is not None:
        _log({"event": "agent_request", "strategy": fast["agent"]["strategy"], "tools": fast["tools_used"],
              "steps": 0, "fallback_used": False, "latency_ms": _ms(started)})
        return fast

    context = agent_context.build_agent_context(profile, assessment, recommendation, decision, state)
    digest = agent_context.context_digest(context)
    # One provider for the whole turn: the planner and the answer both use the
    # existing DeepSeek client, so one question costs at most two calls.
    answer_provider = provider if provider is not None else _provider(secrets)
    planner = planner_provider if planner_provider is not None else answer_provider
    plan = agent_planner.plan(question, digest, bounded_history, planner)
    results, steps, limit_reached = _execute_plan(plan, question, tool_context)
    failures = [str(result.get("tool")) for result in results if not result.get("ok")]
    tools_used = [str(result.get("tool")) for result in results if result.get("ok")] or \
                 [request.name for request in plan.requests]

    use_provider = bool(answer_provider.configured) and not _explanations_disabled(secrets)
    provider_seconds: float | None = None
    notice: str | None = None
    if use_provider:
        messages = build_answer_messages(question, bounded_history, digest, results)
        attempt = time.monotonic()
        try:
            draft = answer_provider.complete(messages)
            provider_seconds = time.monotonic() - attempt
            accepted, reason = agent_guard.guard_agent_answer(
                draft, question, facts, results, assessment, decision, route, recommendation)
            if accepted:
                _log({"event": "agent_request", "strategy": agent_planner.PLANNER_STRATEGY, "intent": plan.intent,
                      "plan_source": plan.source, "tools": tools_used, "tool_failures": failures, "steps": steps,
                      "fallback_used": False, "provider_seconds": round(provider_seconds, 3),
                      "latency_ms": _ms(started)})
                return _result(draft, ai_engine.AI_PROVIDER_LABEL, None, tools_used=tools_used,
                               strategy=agent_planner.PLANNER_STRATEGY, intent=plan.intent,
                               plan_source=plan.source, steps=steps, rejected=plan.rejected,
                               planner_error=plan.error, limit_reached=limit_reached,
                               provider_seconds=provider_seconds)
            notice = ai_engine.AI_REJECTED_NOTICE
            _log({"event": "agent_request", "strategy": agent_planner.PLANNER_STRATEGY, "intent": plan.intent,
                  "tools": tools_used, "steps": steps, "validation_rejected": reason,
                  "fallback_used": True, "latency_ms": _ms(started)})
        except Exception as exc:  # noqa: BLE001 - the Agent never crashes the Coach
            provider_seconds = time.monotonic() - attempt
            notice = ai_engine.AI_UNAVAILABLE_NOTICE
            _log({"event": "agent_request", "strategy": agent_planner.PLANNER_STRATEGY, "intent": plan.intent,
                  "tools": tools_used, "steps": steps, "provider_error": type(exc).__name__,
                  "fallback_used": True, "latency_ms": _ms(started)})
    else:
        notice = (ai_engine.AI_UNAVAILABLE_NOTICE if not answer_provider.configured
                  else "AI explanations are disabled for this deployment, so the deterministic answer is shown.")

    answer = fallback_answer(question, profile, assessment, recommendation, context, results)
    return _result(answer, ai_engine.PROVIDER_INSTANT, notice, tools_used=tools_used,
                   strategy="deterministic_fallback", intent=plan.intent, plan_source=plan.source,
                   steps=steps, rejected=plan.rejected, planner_error=plan.error,
                   limit_reached=limit_reached, provider_seconds=provider_seconds, fallback_used=True)


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _log(record: Mapping[str, Any]) -> None:
    """Lightweight structured logging: tool names, counts and timings only."""
    try:
        _LOGGER.info("agent %s", json.dumps(dict(record), default=str))
    except Exception:  # noqa: BLE001 - logging must never affect the answer
        return
