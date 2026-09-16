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
    assert payload["api_version"].startswith("1.2.0")
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
    assert len(computed["training"]["decision_trace"]) == 8
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
