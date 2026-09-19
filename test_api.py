"""Focused tests for the V1.2 FastAPI adapter.

These tests only cover the transport layer. Scientific behaviour is still
asserted by the existing ``test_app.py`` suite, which stays unchanged.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import ai_engine
from backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_health_reports_engines_and_never_exposes_the_credential(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    # Service metadata: the current stack is reported, and the historical
    # Streamlit prototype is no longer described as the reference implementation.
    # V1.4 adds the Agent layer, so the published version moves with it.
    assert payload["product_version"] == "1.4"
    assert payload["api_version"] == "1.4"
    assert payload["frontend"] == "Next.js"
    assert payload["backend"] == "FastAPI"
    assert "reference_implementation" not in payload
    assert "Streamlit" not in json.dumps(payload)
    assert payload["ai_provider"] == ai_engine.AI_PROVIDER_LABEL
    assert "readiness_engine.assess_readiness" in payload["engines"]
    assert "training_recommendation_engine.recommend_training" in payload["engines"]
    assert isinstance(payload["ai_credential_configured"], bool)
    body = json.dumps(payload)
    assert "DEEPSEEK_API_KEY" not in body
    assert "sk-" not in body


def test_readiness_endpoint_matches_the_engine(client: TestClient) -> None:
    import app as streamlit_app
    from demo_data import build_demo_profiles
    from readiness_engine import assess_readiness

    payload = client.get("/api/readiness").json()

    profile = build_demo_profiles()[0]
    expected = assess_readiness(streamlit_app.get_draft(profile), profile["history"],
                                profile["personal_sleep_need"], profile["assessments"])

    assert payload["status"] == expected["overall_readiness"]
    assert payload["index"] == expected["readiness_index"]
    assert payload["confidence"] == expected["assessment_confidence"]
    assert payload["index_scale"] == {"min": 0, "max": 100}
    assert {domain["key"] for domain in payload["domains"]} == set(expected["domains"])
    assert payload["source"] == "readiness_engine.assess_readiness"


def test_recommendation_and_trace_match_the_engine(client: TestClient) -> None:
    payload = client.get("/api/training/recommendation").json()
    trace = client.get("/api/decision-trace").json()

    assert payload["primary_name"]
    assert payload["session_demand"]
    assert payload["duration"]
    assert payload["source"] == "training_recommendation_engine.recommend_training"
    assert [step["index"] for step in trace] == list(range(1, len(trace) + 1))
    assert trace[0]["step"] == "GOAL"
    assert trace[-1]["step"] == "RECOMMENDATION"
    assert trace[-1]["value"] == payload["primary_name"]
    assert all(step["source"] == "deterministic" for step in trace)


def test_today_separates_how_hard_from_duration(client: TestClient) -> None:
    payload = client.get("/api/today").json()
    recommendation = payload["training"]["recommendation"]
    assert payload["readiness"]["status"]
    assert recommendation["session_demand"] != recommendation["duration"]
    assert recommendation["duration"].endswith("min")
    assert payload["why"]["note"].startswith("Decision Trace is a deterministic explanation")


def test_exposure_uses_weighted_working_sets(client: TestClient) -> None:
    payload = client.get("/api/training/exposure").json()
    assert payload["unit"] == "weighted working sets"
    assert "Direct sets count 1.0" in payload["note"]
    assert "not days and not sessions" in payload["note"]
    assert payload["groups"]


def test_science_endpoint_serves_the_audited_reference_set(client: TestClient) -> None:
    payload = client.get("/api/science/references").json()
    assert len(payload["references"]) == 13
    assert len(payload["evidence_boundaries"]) == 3
    pmids = {reference["pmid"] for reference in payload["references"]}
    assert {"24578692", "30558493", "41343037"} <= pmids
    for reference in payload["references"]:
        assert reference["pubmed_url"].endswith(f"/{reference['pmid']}/")
        assert reference["doi_url"].startswith("https://doi.org/10.")
    joined = " ".join(payload["evidence_boundaries"])
    assert "not clinically validated" in joined
    assert "have not been prospectively validated" in joined


def test_unknown_profile_returns_404(client: TestClient) -> None:
    assert client.get("/api/today?profile_id=does-not-exist").status_code == 404


def test_coach_factual_endpoint_makes_zero_provider_calls(client: TestClient, monkeypatch) -> None:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):
        calls.append(str(url))
        raise AssertionError("a personal factual question must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    response = client.post("/api/coach/message", json={"question": "How much have I trained back this week?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "verified_data"
    assert payload["ai_used"] is False
    assert payload["verified_data"] is True
    assert "weighted working set" in payload["answer"].casefold()
    assert calls == []


def test_coach_explanation_degrades_when_the_provider_is_down(client: TestClient, monkeypatch) -> None:
    def exploding_post(url, *args, **kwargs):
        raise ai_engine.requests.exceptions.ConnectionError("provider unreachable")

    monkeypatch.setattr(ai_engine.requests, "post", exploding_post)
    response = client.post("/api/coach/message", json={"question": "Why this workout?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "deterministic_fallback"
    assert payload["ai_used"] is False
    assert payload["notice"]
    assert payload["answer"]


def test_coach_rejects_an_empty_question(client: TestClient) -> None:
    assert client.post("/api/coach/message", json={"question": ""}).status_code == 422


# --------------------------------------------------------------------------- #
# Phase 2 — stateless compute over client-owned state
# --------------------------------------------------------------------------- #


def _base_state(client: TestClient) -> dict:
    response = client.get("/api/state/base")
    assert response.status_code == 200
    return response.json()["state"]


def test_scenarios_and_profile_options_come_from_the_product_definitions(client: TestClient) -> None:
    from product_options import GOALS, SPLITS
    from readiness_engine import SAFETY_FLAGS
    from scenario_data import SCENARIOS
    from training_recommendation_engine import MUSCLE_GROUPS

    scenarios = client.get("/api/scenarios").json()
    assert [item["name"] for item in scenarios["scenarios"]] == list(SCENARIOS)
    assert scenarios["safety_flags"] == list(SAFETY_FLAGS)
    assert scenarios["muscle_groups"] == list(MUSCLE_GROUPS)

    options = client.get("/api/profile/options").json()
    assert options["goals"] == list(GOALS)
    assert options["splits"] == list(SPLITS)


def test_state_base_seeds_the_client_and_stores_nothing(client: TestClient) -> None:
    payload = client.get("/api/state/base").json()
    assert payload["state"]["profile_id"] == "demo-ethan"
    assert payload["state"]["daily_history"] == []
    assert payload["state"]["training_history"] == []
    assert payload["daily_rows"] > 0 and payload["training_rows"] > 0
    assert "stores nothing" in payload["note"]


def test_state_today_matches_the_demo_computation(client: TestClient) -> None:
    state = _base_state(client)
    demo = client.get("/api/today").json()
    computed = client.post("/api/state/today", json={"state": state}).json()["today"]
    assert computed["readiness"]["status"] == demo["readiness"]["status"]
    assert computed["readiness"]["index"] == demo["readiness"]["index"]
    assert computed["training"]["recommendation"]["primary_name"] == demo["training"]["recommendation"]["primary_name"]
    # V1.3 inserts the PERSONAL RESPONSE step between READINESS and SESSION DEMAND.
    steps = [row["step"] for row in computed["training"]["decision_trace"]]
    assert len(steps) == 9
    assert steps.index("PERSONAL RESPONSE") == steps.index("READINESS") + 1
    assert computed["training"]["exposure"]["unit"] == "weighted working sets"
    assert computed["training"]["recommendation"]["template"]["items"]
    assert computed["training"]["recommendation"]["log_defaults"]["exercises"]


def test_scenario_switch_changes_the_recommendation_context(client: TestClient) -> None:
    state = _base_state(client)
    hard = {**state, "scenario": "High Load / Poor Sleep Day"}
    easy = {**state, "scenario": "Well Recovered Day"}
    hard_today = client.post("/api/state/today", json={"state": hard}).json()["today"]
    easy_today = client.post("/api/state/today", json={"state": easy}).json()["today"]
    assert hard_today["readiness"]["status"] != easy_today["readiness"]["status"]
    assert hard_today["training"]["recommendation"]["session_demand"] != easy_today["training"]["recommendation"]["session_demand"]


def test_state_check_in_updates_readiness_and_keeps_the_row(client: TestClient) -> None:
    state = _base_state(client)
    response = client.post(
        "/api/state/check-in",
        json={
            "state": state,
            "check_in": {
                "date": "2026-09-16",
                "rmssd_ms": 38.0,
                "resting_hr_bpm": 66,
                "sleep_hours": 5.1,
                "sleep_quality": 2,
                "fatigue": 5,
                "soreness": 4,
                "stress": 4,
                "motivation": 2,
                "local_soreness": {"Quads": 4},
                "safety_flags": [],
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["check_in"]["sleep_hours"] == 5.1
    assert payload["state"]["daily_history"][0]["date"] == "2026-09-16"
    assert payload["today"]["readiness"]["check_in"]["sleep_hours"] == 5.1
    assert payload["today"]["readiness"]["status"] in {"AMBER", "RED", "GREEN", "INSUFFICIENT DATA"}
    # The submitted soreness reaches the engine's session-compatibility context.
    assert payload["today"]["training"]["decision_trace"][-1]["step"] == "RECOMMENDATION"


def test_safety_flag_routes_the_state_to_stop(client: TestClient) -> None:
    state = _base_state(client)
    flags = client.get("/api/scenarios").json()["safety_flags"]
    assert flags
    response = client.post(
        "/api/state/check-in",
        json={
            "state": state,
            "check_in": {
                "date": "2026-09-16",
                "rmssd_ms": 50.0,
                "resting_hr_bpm": 55,
                "sleep_hours": 8.0,
                "sleep_quality": 4,
                "fatigue": 2,
                "soreness": 2,
                "stress": 2,
                "motivation": 4,
                "safety_flags": [flags[0]],
            },
        },
    )
    payload = response.json()
    assert payload["today"]["readiness"]["safety_active"] is True
    assert payload["today"]["readiness"]["status"] == "STOP / PROFESSIONAL REVIEW"


def test_profile_edits_change_the_context_and_the_recommendation(client: TestClient) -> None:
    state = _base_state(client)
    response = client.post(
        "/api/state/profile",
        json={"state": state, "edits": {"training_goal": "Endurance", "training_split_preference": "Running-focused"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["edits"]["training_goal"] == "Endurance"
    assert payload["today"]["profile"]["training_goal"] == "Endurance"
    assert payload["today"]["profile"]["training_split_preference"] == "Running-focused"
    assert payload["today"]["training"]["decision_trace"][0]["value"] == "Endurance"


def test_logging_a_session_updates_load_exposure_and_history(client: TestClient) -> None:
    state = _base_state(client)
    before = client.post("/api/state/today", json={"state": state}).json()["today"]
    response = client.post(
        "/api/state/session",
        json={"state": state, "duration_min": 60, "session_rpe": 7, "completion_status": "Completed"},
    )
    assert response.status_code == 200
    payload = response.json()
    session = payload["session"]
    # The engine computes load as duration × session RPE, in AU.
    assert session["session_load"] == 420.0
    assert session["actual_sets"] > 0
    assert session["muscle_set_contributions"]
    assert len(payload["state"]["training_history"]) == 1
    assert payload["state"]["daily_history"][0]["session_load"] == 420.0
    assert payload["history"][0]["date"] == session["date"]
    # Exposure for the trained muscle group moves with the logged sets.
    trained = session["muscle_groups"][0]
    before_group = next(group for group in before["training"]["exposure"]["groups"] if group["group"] == trained)
    after_group = next(group for group in payload["exposure"]["groups"] if group["group"] == trained)
    assert after_group["value"] >= before_group["value"]


def test_session_logging_rejects_invalid_input(client: TestClient) -> None:
    state = _base_state(client)
    bad = client.post("/api/state/session", json={"state": state, "duration_min": 0, "session_rpe": 7})
    assert bad.status_code == 422
    too_hard = client.post("/api/state/session", json={"state": state, "duration_min": 60, "session_rpe": 42})
    assert too_hard.status_code == 422


def test_insights_series_keep_missing_days_missing(client: TestClient) -> None:
    state = _base_state(client)
    payload = client.post("/api/state/insights", json={"state": state, "window": 28}).json()
    assert payload["window"] == 28
    assert {series["key"] for series in payload["series"]} == {"ln_rmssd", "resting_hr_bpm", "sleep_hours", "session_load"}
    for series in payload["series"]:
        assert len(series["points"]) <= 28
        for point in series["points"]:
            assert point["value"] is None or isinstance(point["value"], (int, float))
    assert payload["exposure"]["unit"] == "weighted working sets"
    assert "gaps, not as zero" in payload["missing_data_note"]
    assert payload["load"]["calendar_days_required"] == 28


def test_state_coach_factual_question_makes_zero_provider_calls(client: TestClient, monkeypatch) -> None:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):
        calls.append(str(url))
        raise AssertionError("a personal factual question must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    state = _base_state(client)
    response = client.post(
        "/api/state/coach",
        json={"state": state, "question": "How much have I trained back this week?", "history": []},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "verified_data"
    assert payload["ai_used"] is False
    assert "weighted working set" in payload["answer"].casefold()
    assert calls == []


def test_state_coach_reflects_the_submitted_check_in(client: TestClient) -> None:
    state = _base_state(client)
    checked = client.post(
        "/api/state/check-in",
        json={
            "state": state,
            "check_in": {
                "date": "2026-09-16",
                "rmssd_ms": 50.0,
                "resting_hr_bpm": 55,
                "sleep_hours": 8.0,
                "sleep_quality": 4,
                "fatigue": 2,
                "soreness": 2,
                "stress": 2,
                "motivation": 4,
                "local_soreness": {"Back": 3},
            },
        },
    ).json()["state"]
    payload = client.post(
        "/api/state/coach",
        json={"state": checked, "question": "How sore is my back?", "history": []},
    ).json()
    assert payload["kind"] == "verified_data"
    assert "3" in payload["answer"]


# --------------------------------------------------------------------------- #
# V1.3 — Adaptive Decision Loop Phase 1
# --------------------------------------------------------------------------- #


def _seeded_state(client: TestClient, case: str = "poor_high_tolerance") -> dict:
    response = client.get(f"/api/state/base?profile_id=demo-ethan&scenario=Well Recovered Day&response_demo={case}")
    assert response.status_code == 200
    return response.json()["state"]


def test_today_exposes_base_and_final_demand_with_a_personal_response_step(client: TestClient) -> None:
    payload = client.post("/api/state/today", json={"state": _seeded_state(client)}).json()["today"]
    recommendation = payload["training"]["recommendation"]
    response = payload["personal_response"]

    assert recommendation["base_session_demand"] == "Normal"
    assert recommendation["session_demand"] == "Reduced / autoregulated"
    assert recommendation["adaptation"]["label"] == "Adjusted from your recent response"
    assert recommendation["rir_guidance"] == "2–4 RIR; avoid unnecessary failure"
    assert response["adjustment"] == -1 and response["base_band"] == "High" and response["final_band"] == "Moderate"

    steps = [row["step"] for row in payload["training"]["decision_trace"]]
    assert len(steps) == 9
    assert steps.index("PERSONAL RESPONSE") == steps.index("READINESS") + 1
    assert steps.index("PERSONAL RESPONSE") == steps.index("SESSION DEMAND") - 1
    assert "Reduced one step" in payload["training"]["decision_trace"][steps.index("PERSONAL RESPONSE")]["value"]


def test_today_without_response_history_does_not_adjust(client: TestClient) -> None:
    payload = client.post("/api/state/today", json={"state": _base_state(client)}).json()["today"]
    recommendation = payload["training"]["recommendation"]
    assert recommendation["adaptation"] is None
    assert recommendation["base_session_demand"] == recommendation["session_demand"]
    step = [row for row in payload["training"]["decision_trace"] if row["step"] == "PERSONAL RESPONSE"][0]
    assert step["value"] == "Not enough history yet"


def test_logging_a_session_captures_the_pre_session_snapshot(client: TestClient) -> None:
    response = client.post(
        "/api/state/session",
        json={"state": _seeded_state(client), "duration_min": 50, "session_rpe": 6},
    ).json()
    snapshot = response["session"]["response_context"]
    assert snapshot["base_session_demand"] and snapshot["final_session_demand"]
    assert snapshot["recommended_focus"]
    assert snapshot["recommended_duration"] and snapshot["recommended_rir"]
    assert snapshot["readiness_status"] and "captured_at" in snapshot
    # The snapshot travels back with the state so the browser can persist it.
    stored = [row for row in response["state"]["training_history"] if row["session_id"] == response["session"]["session_id"]]
    assert stored and stored[0]["response_context"]["recommended_focus"] == snapshot["recommended_focus"]


def test_post_session_feedback_is_stored_and_recomputed(client: TestClient) -> None:
    state = _seeded_state(client)
    logged = client.post("/api/state/session", json={"state": state, "duration_min": 45, "session_rpe": 6}).json()
    session_id = logged["session"]["session_id"]
    response = client.post(
        "/api/state/feedback",
        json={"state": logged["state"], "session_id": session_id, "difficulty": 4, "performance": 3,
              "completion": "Modified", "note": "Cut the session short"},
    )
    assert response.status_code == 200
    payload = response.json()
    row = [item for item in payload["state"]["training_history"] if item["session_id"] == session_id][0]
    assert row["response_feedback"]["difficulty"] == 4
    assert row["response_feedback"]["completion"] == "Modified"
    assert row["response_feedback"]["note"] == "Cut the session short"
    assert payload["today"]["personal_response"]["summary"]["episodes_total"] >= 1


def test_feedback_rejects_out_of_range_values(client: TestClient) -> None:
    state = _seeded_state(client)
    logged = client.post("/api/state/session", json={"state": state, "duration_min": 45, "session_rpe": 6}).json()
    session_id = logged["session"]["session_id"]
    for body in ({"difficulty": 9, "performance": 3}, {"difficulty": 3, "performance": 0}):
        bad = client.post("/api/state/feedback",
                          json={"state": logged["state"], "session_id": session_id, **body})
        assert bad.status_code == 422


def test_personal_response_endpoints_expose_the_demo_cases(client: TestClient) -> None:
    for case, evidence, complete in (("insufficient", "Insufficient", 1), ("emerging", "Emerging", 4),
                                     ("established_good", "Established", 6)):
        payload = client.get(f"/api/personal-response?response_demo={case}").json()
        assert payload["evidence"] == evidence
        assert payload["summary"]["episodes_complete"] == complete
    seeded = client.post("/api/state/personal-response", json={"state": _seeded_state(client)}).json()
    assert seeded["adjustment"] == -1 and seeded["episodes"]


def test_coach_answers_personal_response_questions_with_zero_provider_calls(client: TestClient, monkeypatch) -> None:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):
        calls.append(str(url))
        raise AssertionError("personal response questions must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    state = _seeded_state(client)
    for question in ("How do I usually respond to high-demand sessions?",
                     "How many response episodes do I have?",
                     "Why was today's session adjusted?",
                     "What happened after my last session?"):
        payload = client.post("/api/state/coach", json={"state": state, "question": question, "history": []}).json()
        assert payload["kind"] == "verified_data", question
        assert payload["ai_used"] is False, question
        assert payload["answer"]
    assert calls == []


def test_coach_personal_response_answer_reports_the_pattern(client: TestClient) -> None:
    state = _seeded_state(client)
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "How do I usually respond to high-demand sessions?", "history": []},
    ).json()
    assert "High demand" in payload["answer"]
    assert "harder to recover from" in payload["answer"]
    assert "not a recovery measurement" in payload["answer"]


def test_red_readiness_cannot_be_overridden_by_personal_response(client: TestClient) -> None:
    state = _seeded_state(client)
    payload = client.post(
        "/api/state/check-in",
        json={"state": state, "check_in": {"date": "2026-09-17", "rmssd_ms": 40.0, "resting_hr_bpm": 62,
                                          "sleep_hours": 5.0, "sleep_quality": 2, "fatigue": 5, "soreness": 4,
                                          "stress": 4, "motivation": 2}},
    ).json()
    recommendation = payload["today"]["training"]["recommendation"]
    response = payload["today"]["personal_response"]
    assert payload["today"]["readiness"]["status"] in {"RED", "AMBER", "STOP / PROFESSIONAL REVIEW"}
    assert response["adjustment"] <= 0
    assert recommendation["base_session_demand"] == recommendation["session_demand"] or response["adjustment"] == -1


# --------------------------------------------------------------------------- #
# V1.3 — Adaptive Decision Loop Phase 2
# --------------------------------------------------------------------------- #


def test_personal_response_exposes_confidence_coverage_and_profile(client: TestClient) -> None:
    payload = client.get("/api/personal-response?response_demo=established_good").json()

    assert payload["confidence"]["state"] == "Strong"
    assert payload["confidence_state"] == "Strong"
    assert payload["confidence"]["label"] == "Strong evidence"
    # Qualitative vocabulary only — never a percentage or a physiological score.
    assert "%" not in json.dumps(payload["confidence"])
    assert payload["relevant_episodes"] == payload["relevant"]["count"] == 6
    assert payload["relevant"]["band"] == "High"
    assert payload["coverage"]["episodes_complete"] == 6
    assert payload["consistency"]["consistent"] is True

    high = next(row for row in payload["profile"]["bands"] if row["band"] == "High")
    assert high["observations"] == 6 and high["evidence"] == "Established"
    assert payload["bands_profile"] == payload["profile"]["bands"]


def test_personal_response_profile_hides_unsupported_focus_patterns(client: TestClient) -> None:
    thin = client.get("/api/personal-response?response_demo=insufficient").json()
    assert thin["confidence"]["state"] == "Limited"
    assert thin["profile"]["focus"] == []


def test_state_personal_response_returns_the_adaptation_history(client: TestClient) -> None:
    state = _seeded_state(client)
    envelope = client.post("/api/state/today", json={"state": state}).json()
    # The evaluated decision is recorded in the client-owned state.
    assert len(envelope["state"]["adaptation_log"]) == 1

    payload = client.post("/api/state/personal-response",
                          json={"state": envelope["state"]}).json()
    history = payload["adaptation_history"]
    assert len(history) == 1
    assert history[0]["result"] == "reduced" and history[0]["adjustment"] == -1
    assert history[0]["base_band"] == "High" and history[0]["final_band"] == "Moderate"
    assert history[0]["confidence"] == "Developing"


def test_decision_trace_personal_response_step_carries_structured_detail(client: TestClient) -> None:
    payload = client.post("/api/state/today", json={"state": _seeded_state(client)}).json()["today"]
    step = next(row for row in payload["training"]["decision_trace"] if row["step"] == "PERSONAL RESPONSE")
    detail = step["detail"]
    assert detail["evidence"] == "3 relevant sessions at High demand"
    assert detail["confidence"] == "Developing evidence"
    assert detail["adjustment"] == "Reduced one step (High → Moderate)"
    assert detail["pattern"].endswith("(Consistent)")


def test_recommendation_carries_the_confidence_without_changing_the_base(client: TestClient) -> None:
    today = client.post("/api/state/today", json={"state": _seeded_state(client)}).json()["today"]
    recommendation = today["training"]["recommendation"]
    assert recommendation["recommendation_confidence"]["state"] == "Developing"
    # Base and final stay separate; the engine's own demand is never overwritten.
    assert recommendation["base_session_demand"] == "Normal"
    assert recommendation["session_demand"] == "Reduced / autoregulated"
    assert today["personal_response"]["base_demand"] == "Normal"
    assert today["personal_response"]["final_demand"] == "Reduced / autoregulated"


def test_coach_answers_confidence_and_history_questions_with_zero_provider_calls(
    client: TestClient, monkeypatch
) -> None:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):
        calls.append(str(url))
        raise AssertionError("personal response questions must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    state = _seeded_state(client)
    for question in ("How confident is today's personalized recommendation?",
                     "How many sessions support this adjustment?",
                     "Has Personal Response changed my training before?",
                     "Why didn't you increase today's training if I usually recover well?"):
        payload = client.post("/api/state/coach", json={"state": state, "question": question, "history": []}).json()
        assert payload["kind"] == "verified_data", question
        assert payload["ai_used"] is False, question
        assert payload["answer"], question
    assert calls == []


def test_coach_explains_why_todays_session_was_not_increased(client: TestClient) -> None:
    state = client.get(
        "/api/state/base?profile_id=demo-ethan&scenario=Well Recovered Day&response_demo=established_good"
    ).json()["state"]
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "Why didn't you increase today's training if I usually recover well?",
              "history": []},
    ).json()
    assert payload["kind"] == "verified_data" and payload["ai_used"] is False
    assert "readiness permits" in payload["answer"]
    assert "RIR" in payload["answer"]


def test_coach_confidence_answer_reports_the_recorded_state(client: TestClient) -> None:
    state = client.get(
        "/api/state/base?profile_id=demo-ethan&scenario=Well Recovered Day&response_demo=established_good"
    ).json()["state"]
    payload = client.post(
        "/api/state/coach",
        json={"state": state, "question": "How confident is today's personalized recommendation?", "history": []},
    ).json()
    assert "Strong" in payload["answer"]
    assert "6 recent sessions" in payload["answer"]
