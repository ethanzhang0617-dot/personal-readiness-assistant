"""V1.4 — Agent layer tests.

Every test here runs without a network call: the DeepSeek client is replaced by a
fake that records the messages it was given. The suite covers the tool registry,
the planner, the orchestrator, the grounding and safety guards, the deterministic
fast path, the fallback behaviour and the six acceptance scenarios.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import agent_context
import agent_guard
import agent_orchestrator
import agent_planner
import agent_tools
import ai_engine
import ai_facts
from backend.main import app
from backend.services import demo_service, readiness_service, response_service, state_service, training_service


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class FakeProvider:
    """Stand-in for ``ai_engine.DeepSeekCoachProvider``. Never touches a network."""

    configured = True

    def __init__(self, plan: dict | None = None, answer: str = "Today's session stays as recommended.",
                 fail_planner: bool = False, fail_answer: bool = False) -> None:
        self.plan = plan if plan is not None else {
            "intent": "explain_recommendation",
            "tools": [{"name": "get_readiness", "arguments": {}},
                      {"name": "get_current_recommendation", "arguments": {}}],
        }
        self.answer = answer
        self.fail_planner = fail_planner
        self.fail_answer = fail_answer
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages) -> str:
        rows = [dict(message) for message in messages]
        self.calls.append(rows)
        is_planner = "tool planner" in str(rows[0].get("content", ""))
        if is_planner:
            if self.fail_planner:
                raise ai_engine.DeepSeekProviderError("planner unavailable")
            return json.dumps(self.plan)
        if self.fail_answer:
            raise ai_engine.DeepSeekProviderError("provider unavailable")
        return self.answer

    @property
    def planner_calls(self) -> list[list[dict[str, str]]]:
        return [call for call in self.calls if "tool planner" in str(call[0].get("content", ""))]

    @property
    def answer_calls(self) -> list[list[dict[str, str]]]:
        return [call for call in self.calls if "tool planner" not in str(call[0].get("content", ""))]


def _demo_context() -> tuple[dict, dict, dict, dict]:
    profile = demo_service.get_profile("demo-ethan")
    assessment = readiness_service.assess(profile)
    recommendation = training_service.recommend(profile, assessment)
    decision = response_service.evaluate(profile, assessment, recommendation)
    return profile, assessment, recommendation, decision


def _seeded_state(client: TestClient, case: str = "poor_high_tolerance") -> dict:
    response = client.get(f"/api/state/base?profile_id=demo-ethan&scenario=Well Recovered Day&response_demo={case}")
    assert response.status_code == 200
    return response.json()["state"]


def _use_fake_provider(monkeypatch, provider: FakeProvider) -> None:
    """Inject the fake where the orchestrator builds its provider."""
    monkeypatch.setattr(agent_orchestrator, "_provider", lambda secrets=None: provider)


def _no_provider_calls(monkeypatch) -> list[str]:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):  # pragma: no cover - only runs on a defect
        calls.append(str(url))
        raise AssertionError("this turn must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    return calls


# --------------------------------------------------------------------------- #
# Tool registry
# --------------------------------------------------------------------------- #


def test_tool_registry_exposes_only_the_whitelisted_read_only_tools() -> None:
    expected = {
        "get_readiness", "get_current_recommendation", "get_recent_training", "get_training_exposure",
        "get_personal_response", "get_recommendation_confidence", "get_decision_trace",
        "run_decision_explorer", "get_session_calibration_context", "get_training_load", "get_personal_context",
    }
    assert set(agent_tools.tool_names()) == expected
    for spec in agent_tools.tool_specs():
        assert spec.operation == agent_tools.READ_ONLY
        assert spec.source
        assert spec.input_schema["type"] == "object"
        assert spec.output_schema["type"] == "object"
        assert spec.errors
    # The planner-visible catalogue never leaks a handler, an import path or a callable.
    catalogue = agent_tools.catalogue()
    body = json.dumps(catalogue)
    assert set(catalogue[0]) == {"name", "description", "arguments", "operation"}
    assert "backend.services" not in body and "lambda" not in body and "def " not in body


def test_unknown_tool_name_is_refused_without_executing_anything() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    for name in ("os.system", "subprocess.run", "../../etc/passwd", "", None, "get_readiness "):
        result = agent_tools.execute(name, {}, context)
        assert result["ok"] is False
        assert result["error"] == "unknown_tool"
        assert "whitelist" in result["detail"]


def test_invalid_arguments_are_refused() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)

    undeclared = agent_tools.execute("get_readiness", {"limit": 3}, context)
    assert undeclared["error"] == "invalid_arguments"
    assert "Undeclared" in undeclared["detail"]

    out_of_range = agent_tools.execute("get_recent_training", {"limit": 99}, context)
    assert out_of_range["error"] == "invalid_arguments"

    wrong_type = agent_tools.execute("get_recent_training", {"limit": "many"}, context)
    assert wrong_type["error"] == "invalid_arguments"

    unknown_enum = agent_tools.execute("run_decision_explorer", {"lever": "make_it_hard"}, context)
    assert unknown_enum["error"] == "invalid_arguments"

    missing_required = agent_tools.execute("run_decision_explorer", {}, context)
    assert missing_required["error"] == "invalid_arguments"
    assert "lever" in missing_required["detail"]


def test_get_readiness_wrapper_returns_a_structured_result() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    result = agent_tools.execute("get_readiness", {}, context)
    assert result["ok"] is True
    assert result["operation"] == "read_only"
    assert result["source"] == "readiness_engine.assess_readiness"
    data = result["data"]
    json.dumps(data)  # JSON-compatible, not a raw engine object
    assert data["status"] == assessment["overall_readiness"]
    assert data["index"] == assessment["readiness_index"]
    assert data["baseline_confidence"] == assessment["assessment_confidence"]
    assert set(data["domains"]) == set(assessment["domains"])


def test_recommendation_wrapper_uses_the_existing_engine() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    data = agent_tools.execute("get_current_recommendation", {}, context)["data"]
    engine_summary = training_service.summary(recommendation)
    final_summary = response_service.apply_to_summary(
        engine_summary, decision, engine_summary.get("rir_guidance"))
    assert data["primary"] == engine_summary["primary_name"]
    assert data["session_demand"] == final_summary["session_demand"]
    assert data["base_session_demand"] == decision["base_demand"]
    assert data["rir_guidance"] == final_summary["rir_guidance"]
    assert data["primary"] == recommendation["primary"]["name"]


def test_personal_response_wrapper_uses_the_existing_logic() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    data = agent_tools.execute("get_personal_response", {}, context)["data"]
    payload = response_service.payload(decision)
    assert data["adjustment"] == payload["adjustment"]
    assert data["base_demand"] == payload["base_demand"]
    assert data["final_demand"] == payload["final_demand"]
    assert data["evidence"] == payload["evidence"]


def test_decision_explorer_wrapper_is_read_only() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    state = state_service.UserState(**state_service.base_state("demo-ethan")[1])
    before = json.dumps(state.model_dump(), sort_keys=True, default=str)
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision, state)
    results = [
        agent_tools.execute("run_decision_explorer", change, context)
        for change in ({"lever": "soreness", "group": "Back", "level": 4},
                       {"lever": "recovery"},
                       {"lever": "personal_response"})
    ]
    for result in results:
        assert result["ok"] is True
        assert result["data"]["read_only_note"]
    after = json.dumps(state.model_dump(), sort_keys=True, default=str)
    assert before == after, "the explorer must never mutate the client state"


def test_weekly_exposure_wrapper_uses_the_engine_numbers() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    data = agent_tools.execute("get_training_exposure", {"group": "back"}, context)["data"]
    facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
    assert data["unit"] == "weighted working sets"
    assert data["groups"] == [{"group": "Back",
                               "value": facts["weekly_exposure"]["groups"]["Back"]["value"],
                               "target": facts["weekly_exposure"]["groups"]["Back"]["target"]}]


# --------------------------------------------------------------------------- #
# Planner
# --------------------------------------------------------------------------- #


def test_planner_refuses_unknown_tools_and_undeclared_arguments() -> None:
    draft = json.dumps({
        "intent": "explain_recommendation",
        "tools": [
            {"name": "get_readiness", "arguments": {}},
            {"name": "delete_everything", "arguments": {}},
            {"name": "get_recent_training", "arguments": {"limit": 500}},
            {"name": "get_training_load", "arguments": {}},
        ],
    })
    plan = agent_planner.parse_plan(draft)
    assert [request.name for request in plan.requests] == ["get_readiness", "get_training_load"]
    reasons = {row["name"]: row["reason"] for row in plan.rejected}
    assert reasons["delete_everything"] == "unknown_tool"
    assert reasons["get_recent_training"].startswith("invalid_arguments")


def test_planner_is_a_structured_planner_and_does_not_claim_native_tool_calling() -> None:
    report = agent_planner.capability_report()
    assert report["strategy"] == "structured_planner"
    assert report["native_tool_calling"] is False
    assert report["reason"]


def test_planner_falls_back_to_a_deterministic_plan_without_a_provider() -> None:
    plan = agent_planner.plan("Why is today's recommendation lighter than usual?", "digest", (), None)
    assert plan.source == "heuristic"
    names = [request.name for request in plan.requests]
    assert "get_readiness" in names and "get_current_recommendation" in names
    assert "get_recent_training" in names and "get_personal_response" in names


def test_planner_failure_degrades_to_the_deterministic_plan() -> None:
    provider = FakeProvider(fail_planner=True)
    plan = agent_planner.plan("Why is my session lighter today?", "digest", (), provider)
    assert plan.source == "heuristic"
    assert plan.requests
    assert plan.error and plan.error.startswith("planner_unavailable")


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #


def test_simple_personal_fact_uses_the_deterministic_fast_path(client: TestClient, monkeypatch) -> None:
    calls = _no_provider_calls(monkeypatch)
    state = _seeded_state(client, case="established_good")
    payload = client.post("/api/state/coach",
                          json={"state": state, "question": "What is my readiness today?", "history": []}).json()
    assert payload["kind"] == "verified_data"
    assert payload["ai_used"] is False
    assert payload["agent"]["strategy"] == "deterministic_fast_path"
    assert payload["agent"]["steps"] == 0
    assert payload["tools_used"] == ["get_readiness"]
    assert payload["tool_trace"][0]["label"] == "Readiness"
    assert calls == []


def test_multi_tool_agent_request_uses_every_planned_tool(monkeypatch) -> None:
    provider = FakeProvider(
        plan={"intent": "explain_recommendation",
              "tools": [{"name": "get_readiness", "arguments": {}},
                        {"name": "get_current_recommendation", "arguments": {}},
                        {"name": "get_recent_training", "arguments": {"limit": 3}}]},
        answer="Your session demand is unchanged because readiness and recent training support the recorded plan.")
    profile, assessment, recommendation, decision = _demo_context()
    result = agent_orchestrator.run("Why is today's session what it is?", profile, assessment, recommendation,
                                    decision, history=[], provider=provider)
    assert result["kind"] == "ai_explanation"
    assert result["kind"] == "ai_explanation" and result["ai_used"] is True
    assert result["tools_used"][:3] == ["get_readiness", "get_current_recommendation", "get_recent_training"]
    assert result["agent"]["plan_source"] == "planner"
    assert result["fallback_used"] is False
    assert len(provider.planner_calls) == 1 and len(provider.answer_calls) == 1
    # The planner prompt offers the whitelist; the answer prompt carries the results.
    assert "get_recent_training" in provider.planner_calls[0][-1]["content"]
    assert '"tool": "get_recent_training"' in provider.answer_calls[0][-1]["content"]


def test_tool_iterations_are_capped(monkeypatch) -> None:
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    plan = agent_planner.AgentPlan(
        intent="explain_recommendation",
        requests=tuple(agent_planner.ToolRequest("get_readiness", {})
                       for _ in range(agent_orchestrator.MAX_TOOL_STEPS * agent_orchestrator.MAX_TOOLS_PER_STEP + 3)),
        source="planner",
    )
    results, steps, limit_reached = agent_orchestrator._execute_plan(plan, "why", context)
    assert steps == agent_orchestrator.MAX_TOOL_STEPS
    assert limit_reached is True
    assert len(results) == agent_orchestrator.MAX_TOOL_STEPS * agent_orchestrator.MAX_TOOLS_PER_STEP


def test_provider_failure_falls_back_to_a_verified_answer(monkeypatch) -> None:
    provider = FakeProvider(fail_answer=True)
    profile, assessment, recommendation, decision = _demo_context()
    result = agent_orchestrator.run("Why is today's recommendation lighter than usual?", profile, assessment,
                                    recommendation, decision, provider=provider)
    assert result["kind"] == "deterministic_fallback"
    assert result["ai_used"] is False
    assert result["fallback_used"] is True
    assert result["notice"] == ai_engine.AI_UNAVAILABLE_NOTICE
    assert result["answer"]
    assert result["tools_used"], "the fallback still reports the verified sources it used"


def test_planner_failure_still_produces_a_grounded_answer(monkeypatch) -> None:
    provider = FakeProvider(fail_planner=True,
                            answer="Your session demand is unchanged; readiness and recent training are the reason.")
    profile, assessment, recommendation, decision = _demo_context()
    result = agent_orchestrator.run("Why is today's session lighter?", profile, assessment, recommendation,
                                    decision, provider=provider)
    assert result["agent"]["plan_source"] == "heuristic"
    assert result["tools_used"]
    assert result["answer"]


def test_failing_tool_does_not_break_the_turn(monkeypatch) -> None:
    def exploding(context, arguments):
        raise RuntimeError("engine exploded")

    monkeypatch.setitem(agent_tools._HANDLERS, "get_readiness", exploding)
    provider = FakeProvider(fail_answer=True)
    profile, assessment, recommendation, decision = _demo_context()
    result = agent_orchestrator.run("Why is today's recommendation lighter than usual?", profile, assessment,
                                    recommendation, decision, provider=provider)
    assert result["answer"]
    assert result["tools_used"], "the remaining verified tools are still reported"
    assert "get_readiness" not in result["tools_used"]


def test_tool_failure_is_reported_as_a_structured_error(monkeypatch) -> None:
    def exploding(context, arguments):
        raise RuntimeError("sk-secret-value leaked")

    monkeypatch.setitem(agent_tools._HANDLERS, "get_training_load", exploding)
    profile, assessment, recommendation, decision = _demo_context()
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    result = agent_tools.execute("get_training_load", {}, context)
    assert result["ok"] is False
    assert result["error"] == "tool_failure"
    assert "sk-secret" not in json.dumps(result)


# --------------------------------------------------------------------------- #
# Grounding, safety and decision authority
# --------------------------------------------------------------------------- #


def test_the_model_cannot_invent_a_readiness_score(monkeypatch) -> None:
    provider = FakeProvider(answer="Your readiness index today is **87 out of 100**, so train normally.")
    profile, assessment, recommendation, decision = _demo_context()
    result = agent_orchestrator.run("Why is today's recommendation lighter than usual?", profile, assessment,
                                    recommendation, decision, provider=provider)
    assert result["kind"] == "deterministic_fallback"
    assert result["notice"] == ai_engine.AI_REJECTED_NOTICE
    assert "87" not in result["answer"]


def test_the_model_cannot_override_the_deterministic_recommendation(client: TestClient, monkeypatch) -> None:
    state = _seeded_state(client)  # Personal Response has already reduced the demand one band
    provider = FakeProvider(answer="Your session demand is Normal today, so a full session is fine.")
    monkeypatch.setattr(agent_orchestrator, "_provider", lambda secrets=None: provider)
    payload = client.post("/api/state/coach",
                          json={"state": state, "question": "Why is today's session lighter than usual?",
                                "history": []}).json()
    assert payload["kind"] == "deterministic_fallback"
    assert payload["notice"] == ai_engine.AI_REJECTED_NOTICE
    assert "session demand is Normal" not in payload["answer"]


def test_grounding_guard_licenses_only_verified_numbers() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
    context = agent_tools.AgentToolContext(profile, assessment, recommendation, decision)
    results = [agent_tools.execute("get_readiness", {}, context)]

    accepted, _reason = agent_guard.guard_agent_answer(
        f"Your readiness is {assessment['overall_readiness']} today and today's demand is "
        f"{decision['final_demand']}.", "why", facts, results, assessment, decision,
        ai_facts.Route("EXPLANATION"), recommendation)
    assert accepted is True

    rejected, reason = agent_guard.guard_agent_answer(
        "You completed 42 weighted working sets this week.", "why", facts, results, assessment, decision,
        ai_facts.Route("EXPLANATION"), recommendation)
    assert rejected is False
    assert "42" in reason


def test_safety_precedence_is_preserved() -> None:
    profile = demo_service.get_profile("demo-ethan")
    check_in = readiness_service.build_check_in(profile)
    check_in["safety_flags"] = ["Fever / acute illness"]
    assessment = readiness_service.assess(profile, check_in)
    recommendation = training_service.recommend(profile, assessment)
    decision = response_service.evaluate(profile, assessment, recommendation)
    facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
    assert assessment["overall_readiness"] == readiness_service.STOP

    accepted, _reason = agent_guard.guard_safety_precedence(
        "Safety mode is active: pause demanding training and seek professional review.", assessment)
    assert accepted is True
    rejected, reason = agent_guard.guard_safety_precedence(
        "Your readiness is low but a normal session is fine today.", assessment)
    assert rejected is False
    assert "safety" in reason.casefold()

    # A safety turn never reaches the model, and the answer keeps the restriction.
    provider = FakeProvider()
    result = agent_orchestrator.run("Should I train hard today?", profile, assessment, recommendation,
                                    decision, provider=provider)
    assert result["kind"] == "safety"
    assert result["ai_used"] is False
    assert provider.calls == []
    assert "safety" in result["answer"].casefold() or "professional" in result["answer"].casefold()


def test_conversation_follow_up_context_is_bounded_and_carried(monkeypatch) -> None:
    provider = FakeProvider(
        plan={"intent": "what_if", "tools": [{"name": "run_decision_explorer",
                                              "arguments": {"lever": "soreness", "group": "Back", "level": 4}}]},
        answer="Under the current rules, back soreness at 4/5 would change today's session demand.")
    profile, assessment, recommendation, decision = _demo_context()
    history = [{"role": "user", "content": "Why is today lighter?"},
               {"role": "assistant", "content": "Today's demand is reduced because of your recent response."}]
    result = agent_orchestrator.run("What if I still want to train back?", profile, assessment, recommendation,
                                    decision, history=history, provider=provider)
    assert result["tools_used"] == ["run_decision_explorer"]
    carried = provider.planner_calls[0]
    assert any("Why is today lighter?" in str(message.get("content")) for message in carried)
    assert len(carried) <= agent_orchestrator.MAX_AGENT_HISTORY_MESSAGES + 2


def test_tool_trace_metadata_is_published_without_internal_detail(client: TestClient, monkeypatch) -> None:
    provider = FakeProvider(answer="Your session demand is unchanged because readiness is the recorded reason.")
    monkeypatch.setattr(agent_orchestrator, "_provider", lambda secrets=None: provider)
    state = _seeded_state(client, case="established_good")
    payload = client.post("/api/state/coach",
                          json={"state": state, "question": "Why is today's recommendation lighter than usual?",
                                "history": []}).json()
    body = json.dumps(payload)
    assert payload["tools_used"]
    assert all({"tool", "label", "source", "operation"} == set(row) for row in payload["tool_trace"])
    assert payload["agent"]["strategy"] and payload["agent"]["steps"] >= 1
    # A tool trace, not a reasoning trace: no prompt, no chain-of-thought, no secret.
    for forbidden in ("tool planner", "system", "prompt", "chain-of-thought", "sk-", "DEEPSEEK_API_KEY"):
        assert forbidden not in body.casefold()


def test_health_publishes_the_agent_strategy_and_tool_whitelist(client: TestClient) -> None:
    payload = client.get("/api/health").json()
    agent = payload["agent"]
    assert agent["strategy"] == "structured_planner"
    assert agent["native_tool_calling"] is False
    assert agent["reason"]
    assert "get_readiness" in agent["tools"] and "run_decision_explorer" in agent["tools"]
    assert "agent_orchestrator.run" in payload["engines"]


# --------------------------------------------------------------------------- #
# Acceptance scenarios
# --------------------------------------------------------------------------- #


def test_scenario_a_explains_a_lighter_recommendation_from_verified_sources(client: TestClient) -> None:
    state = _seeded_state(client)
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "Why is today's recommendation lighter than usual?", "history": []}).json()
    tools = set(payload["tools_used"])
    assert {"get_readiness", "get_current_recommendation"} <= tools
    assert tools & {"get_recent_training", "get_personal_response"}
    assert payload["answer"]
    assert payload["grounded"] is True


def test_scenario_b_soreness_question_loads_recent_training_and_keeps_the_engine_decision(client: TestClient) -> None:
    state = _seeded_state(client, case="established_good")
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "I trained legs yesterday and still feel sore. What should I do today?",
              "history": []}).json()
    tools = set(payload["tools_used"])
    assert {"get_readiness", "get_current_recommendation", "get_recent_training"} <= tools
    # The recorded primary recommendation survives into the answer.
    today = client.post("/api/state/today", json={"state": state}).json()["today"]
    primary = today["training"]["recommendation"]["primary_name"]
    assert primary.casefold() in payload["answer"].casefold()


def test_scenario_c_what_if_uses_the_existing_decision_explorer(client: TestClient) -> None:
    state = _seeded_state(client, case="established_good")
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "I still want to train back. What would change?", "history": []}).json()
    assert "run_decision_explorer" in payload["tools_used"]
    trace = next(row for row in payload["tool_trace"] if row["tool"] == "run_decision_explorer")
    assert trace["operation"] == "read_only"
    assert "current rules" in payload["answer"] or "would change" in payload["answer"]


def test_scenario_d_response_history_questions_use_recorded_response_data(client: TestClient, monkeypatch) -> None:
    calls = _no_provider_calls(monkeypatch)
    state = _seeded_state(client)
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "How have I responded to hard sessions recently?", "history": []}).json()
    assert payload["kind"] == "verified_data"
    assert payload["ai_used"] is False
    assert "get_personal_response" in payload["tools_used"]
    assert "high demand" in payload["answer"].casefold()
    assert calls == []


def test_scenario_e_session_feeling_uses_the_calibration_rules(client: TestClient) -> None:
    state = _seeded_state(client, case="established_good")
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "What if today's session feels much harder than expected?", "history": []}).json()
    assert "get_session_calibration_context" in payload["tools_used"]
    answer = payload["answer"].casefold()
    assert "hold" in answer and "ease" in answer and "optional push" in answer
    assert "never changes the demand" in answer or "no tier" in answer


def test_scenario_f_simple_readiness_question_avoids_agent_overhead(client: TestClient, monkeypatch) -> None:
    calls = _no_provider_calls(monkeypatch)
    state = _seeded_state(client, case="established_good")
    payload = client.post("/api/state/coach",
                          json={"state": state, "question": "What is my readiness today?", "history": []}).json()
    assert payload["agent"]["steps"] == 0
    assert payload["agent"]["strategy"] == "deterministic_fast_path"
    assert payload["agent"]["provider_seconds"] is None
    assert calls == []


# --------------------------------------------------------------------------- #
# Context and memory
# --------------------------------------------------------------------------- #


def test_agent_context_and_memory_are_structured_and_evidence_backed() -> None:
    profile, assessment, recommendation, decision = _demo_context()
    state = state_service.UserState(**state_service.base_state("demo-ethan")[1])
    context = agent_context.build_agent_context(profile, assessment, recommendation, decision, state)
    json.dumps(context, default=str)
    assert context["readiness"]["status"] == assessment["overall_readiness"]
    assert context["recommendation"]["primary"] == recommendation["primary"]["name"]
    assert context["weekly_exposure"]["unit"] == "weighted working sets"
    memory = context["memory"]
    assert memory["recorded_sessions"] == len(profile["training_history"])
    assert "trait" in memory["note"]
    # Conservative memory: no free-text judgement fields exist at all.
    forbidden = {"personality", "motivation_judgement", "health_status", "recovery_judgement", "lazy"}
    assert not (forbidden & set(memory))
    digest = agent_context.context_digest(context)
    assert "weighted working sets" in digest and len(digest) < 2000
