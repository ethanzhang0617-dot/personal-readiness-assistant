"""V1.3 final sprint: in-session calibration, the decision explorer, the loop.

These cover the two additions of the final sprint and the closed loop they join:
morning check-in, recommendation, session, optional checkpoint, completion,
post-session feedback, next-day check-in, Response Episode, Personal Response,
future recommendation and Coach.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import ai_engine
import decision_explorer as dx
import session_calibration as sc
from backend.main import app
from backend.services import calibration_service, explorer_service, state_service
from readiness_engine import AMBER, GREEN, RED


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _state(client: TestClient, scenario: str = "Well Recovered Day", demo: str | None = None) -> dict:
    url = f"/api/state/base?profile_id=demo-ethan&scenario={scenario}"
    if demo:
        url += f"&response_demo={demo}"
    return client.get(url).json()["state"]


def _calibrate(client: TestClient, state: dict, **observation) -> dict:
    body = {"effort": "As expected", "performance": "As expected", "actual_rir": 2}
    body.update(observation)
    response = client.post("/api/state/session/calibration", json={"state": state, "observation": body})
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Vocabulary and parsing
# --------------------------------------------------------------------------- #


def test_calibration_vocabulary_is_bounded() -> None:
    assert sc.CALIBRATION_RESULTS == ("HOLD", "EASE", "OPTIONAL PUSH")
    assert sc.SCOPE.startswith("Within the effort range already prescribed")


def test_rir_range_reads_the_products_own_effort_wording() -> None:
    assert sc.rir_range("1–3 RIR") == (1, 3)
    assert sc.rir_range("2–4 RIR; avoid unnecessary failure") == (2, 4)
    assert sc.rir_range("3 RIR") == (3, 3)
    assert sc.rir_range("RPE 3–4 / 10") is None
    assert sc.rir_range(None) is None


# --------------------------------------------------------------------------- #
# The rule
# --------------------------------------------------------------------------- #


def test_hold_when_the_checkpoint_matches_the_plan() -> None:
    result = sc.checkpoint({"effort": "As expected", "performance": "As expected", "actual_rir": 2},
                           "1–3 RIR", GREEN)
    assert result["result"] == "HOLD"
    assert "Nothing about the session changes" in result["guidance"]


def test_ease_when_the_reported_rir_is_below_the_prescribed_range() -> None:
    result = sc.checkpoint({"effort": "Harder than expected", "performance": "As expected", "actual_rir": 0},
                           "1–3 RIR", GREEN)
    assert result["result"] == "EASE"
    assert "below the prescribed 1–3 RIR range" in result["reason"]
    assert "conservative end" in result["guidance"]


def test_ease_when_performance_is_worse_than_expected() -> None:
    result = sc.checkpoint({"effort": "As expected", "performance": "Worse than expected", "actual_rir": 2},
                           "1–3 RIR", GREEN)
    assert result["result"] == "EASE"


def test_a_single_harder_than_expected_observation_holds() -> None:
    """One hard moment inside the prescribed RIR range is not a divergence."""
    result = sc.checkpoint({"effort": "Harder than expected", "performance": "As expected", "actual_rir": 2},
                           "1–3 RIR", GREEN)
    assert result["result"] == "HOLD"
    assert "one hard moment" in result["reason"]


@pytest.mark.parametrize("observation,readiness,expected", [
    ({"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": 5}, GREEN,
     "OPTIONAL PUSH"),
    ({"effort": "Easier than expected", "performance": "As expected", "actual_rir": 5}, GREEN, "OPTIONAL PUSH"),
    ({"effort": "As expected", "performance": "Better than expected", "actual_rir": 5}, GREEN, "HOLD"),
    ({"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": 2}, GREEN, "HOLD"),
    ({"effort": "Easier than expected", "performance": "Worse than expected", "actual_rir": 5}, GREEN, "EASE"),
    ({"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": None}, GREEN, "HOLD"),
    ({"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": 5}, AMBER, "HOLD"),
    ({"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": 5}, RED, "HOLD"),
])
def test_optional_push_requires_every_condition(observation: dict, readiness: str, expected: str) -> None:
    assert sc.checkpoint(observation, "1–3 RIR", readiness)["result"] == expected


def test_safety_and_soreness_always_ease() -> None:
    push_like = {"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": 5}
    flagged = sc.checkpoint(push_like, "1–3 RIR", GREEN, ["Chest pain"])
    assert flagged["result"] == "EASE" and "safety flag" in flagged["reason"]

    sore = sc.checkpoint(push_like, "1–3 RIR", GREEN, [], {"Quads": 5})
    assert sore["result"] == "EASE" and "Quads soreness is 5/5" in sore["reason"]


def test_calibration_guidance_never_raises_anything() -> None:
    for result in (
        sc.checkpoint({"effort": "As expected", "performance": "As expected", "actual_rir": 2}, "1–3 RIR", GREEN),
        sc.checkpoint({"effort": "Harder than expected", "performance": "As expected", "actual_rir": 0},
                      "1–3 RIR", GREEN),
        sc.checkpoint({"effort": "Easier than expected", "performance": "Better than expected", "actual_rir": 5},
                      "1–3 RIR", GREEN),
    ):
        guidance = result["guidance"].casefold()
        assert result["scope"] == sc.SCOPE
        assert "no tier, focus, exercise or volume change" in result["scope"].casefold()
        assert "normal demand" not in guidance
        assert "added" not in guidance
        assert result["result"] in sc.CALIBRATION_RESULTS


# --------------------------------------------------------------------------- #
# API: active session and persistence
# --------------------------------------------------------------------------- #


def test_active_session_exposes_the_starting_guidance_and_trace(client: TestClient) -> None:
    started = client.post("/api/state/session/start", json={"state": _state(client)}).json()
    active = started["active_session"]
    assert active["primary_focus"] and active["session_demand"] and active["planned_rir"]
    steps = [row["step"] for row in started["session_trace"]]
    assert steps == ["PRE-SESSION DECISION", "PERSONAL RESPONSE", "STARTING GUIDANCE",
                     "IN-SESSION OBSERVATION", "CALIBRATION", "FINAL SESSION GUIDANCE"]
    assert started["today"]["active_session"]["planned_rir"] == active["planned_rir"]


def test_calibration_is_stored_on_the_active_session_and_survives_a_round_trip(client: TestClient) -> None:
    started = client.post("/api/state/session/start", json={"state": _state(client)}).json()
    eased = _calibrate(client, started["state"], effort="Harder than expected", actual_rir=0)
    assert eased["calibration"]["result"] == "EASE"
    assert eased["state"]["active_session"]["calibration"]["result"] == "EASE"
    assert eased["summary"]["counts"]["EASE"] == 1

    # A reload replays the stored state; the checkpoint and its guidance come back.
    reloaded = client.post("/api/state/today", json={"state": eased["state"]}).json()["today"]
    assert reloaded["active_session"]["calibration"]["result"] == "EASE"
    trace = {row["step"]: row["value"] for row in reloaded["session_trace"]}
    assert trace["CALIBRATION"] == "EASE"
    assert "conservative end" in trace["FINAL SESSION GUIDANCE"]
    assert "0 RIR" in trace["IN-SESSION OBSERVATION"]


def test_calibration_never_changes_the_demand_or_the_focus(client: TestClient) -> None:
    started = client.post("/api/state/session/start", json={"state": _state(client)}).json()
    before = started["today"]["training"]["recommendation"]
    calibrated = _calibrate(client, started["state"], effort="Harder than expected", actual_rir=0)
    after = client.post("/api/state/today", json={"state": calibrated["state"]}).json()["today"]
    recommendation = after["training"]["recommendation"]
    assert recommendation["session_demand"] == before["session_demand"]
    assert recommendation["base_session_demand"] == before["base_session_demand"]
    assert recommendation["primary_name"] == before["primary_name"]
    assert recommendation["rir_guidance"] == before["rir_guidance"]
    assert [row["step"] for row in after["training"]["decision_trace"]] == \
        [row["step"] for row in started["today"]["training"]["decision_trace"]]


def test_discarding_an_active_session_clears_it_without_logging(client: TestClient) -> None:
    started = client.post("/api/state/session/start", json={"state": _state(client)}).json()
    sessions_before = len(started["state"]["training_history"])
    cancelled = client.post("/api/state/session/cancel", json={"state": started["state"]}).json()
    assert cancelled["state"]["active_session"] is None
    assert len(cancelled["state"]["training_history"]) == sessions_before


# --------------------------------------------------------------------------- #
# Response Episode integration
# --------------------------------------------------------------------------- #


def test_the_checkpoint_travels_into_the_response_episode(client: TestClient) -> None:
    started = client.post("/api/state/session/start", json={"state": _state(client)}).json()
    calibrated = _calibrate(client, started["state"], effort="Harder than expected", actual_rir=0)
    logged = client.post("/api/state/session",
                         json={"state": calibrated["state"], "duration_min": 55, "session_rpe": 8}).json()

    session_id = logged["session"]["session_id"]
    row = next(item for item in logged["state"]["training_history"] if item["session_id"] == session_id)
    assert row["response_calibration"]["result"] == "EASE"
    assert logged["state"]["active_session"] is None

    episode = next(item for item in logged["today"]["personal_response"]["episodes"]
                   if item["session_id"] == session_id)
    assert episode["calibrated"]["result"] == "EASE"
    assert episode["calibrated"]["actual_rir"] == 0


def test_legacy_sessions_without_a_checkpoint_stay_valid() -> None:
    import adaptive_response as ar
    from demo_data import build_demo_profiles

    profile = json.loads(json.dumps(build_demo_profiles()[0], default=str))
    episodes = ar.build_episodes(profile)
    assert episodes, "the demo profile has sessions"
    assert all(episode["calibrated"] is None for episode in episodes)

    state = state_service.UserState(profile_id="demo-ethan", scenario="Well Recovered Day")
    assert calibration_service.history(state) == []
    assert calibration_service.summary(state)["total"] == 0


def test_calibration_history_summarises_what_was_recorded(client: TestClient) -> None:
    state = _state(client)
    for observation in (
        {"effort": "As expected", "performance": "As expected", "actual_rir": 2},
        {"effort": "Harder than expected", "performance": "As expected", "actual_rir": 0},
    ):
        state = client.post("/api/state/session/start", json={"state": state}).json()["state"]
        calibrated = _calibrate(client, state, **observation)
        state = client.post("/api/state/session",
                            json={"state": calibrated["state"], "duration_min": 50,
                                  "session_rpe": 7}).json()["state"]
    summary = calibration_service.summary(state_service.UserState(**state))
    assert summary["total"] == 2
    assert summary["counts"] == {"HOLD": 1, "EASE": 1, "OPTIONAL PUSH": 0}
    assert summary["eased"] == 1
    assert summary["trend"]


# --------------------------------------------------------------------------- #
# Coach: calibration facts, zero provider calls
# --------------------------------------------------------------------------- #


def _calibrated_state(client: TestClient) -> dict:
    started = client.post("/api/state/session/start", json={"state": _state(client)}).json()
    return _calibrate(client, started["state"], effort="Harder than expected", actual_rir=0)["state"]


def test_coach_answers_calibration_questions_with_zero_provider_calls(client: TestClient, monkeypatch) -> None:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):
        calls.append(str(url))
        raise AssertionError("calibration questions must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    state = _calibrated_state(client)
    for question in ("What is my calibration today?",
                     "Have I often needed to ease off recently?",
                     "What RIR did I just record?",
                     "Why did you tell me to ease off?"):
        payload = client.post("/api/state/coach", json={"state": state, "question": question, "history": []}).json()
        assert payload["kind"] == "verified_data", question
        assert payload["ai_used"] is False, question
        assert payload["answer"], question
    assert calls == []


def test_coach_answers_the_chinese_phrasings_of_the_same_questions() -> None:
    """The product copy is English, but the documented phrasings still route."""
    for question in ("我今天的 calibration 是什么？",
                     "我最近经常需要在训练中降低强度吗？",
                     "刚才记录的 RIR 是多少？",
                     "刚才为什么让我降低一点强度？"):
        assert sc.answer_question(question, []) is not None, question


def test_coach_calibration_answer_reports_the_recorded_values(client: TestClient) -> None:
    state = _calibrated_state(client)
    payload = client.post("/api/state/coach",
                          json={"state": state, "question": "What RIR did I just record?", "history": []}).json()
    assert "0 RIR" in payload["answer"]
    assert "1–3 RIR" in payload["answer"]
    assert "EASE" in payload["answer"]


def test_coach_does_not_treat_unrelated_questions_as_calibration() -> None:
    """A substring match would read "increase" as "ease"."""
    assert sc.answer_question("Why didn't you increase today's training if I usually recover well?", []) is None
    assert sc.answer_question("Why this workout?", []) is None


# --------------------------------------------------------------------------- #
# What-if / Decision Explorer
# --------------------------------------------------------------------------- #


def test_explorer_publishes_its_levers_and_read_only_note(client: TestClient) -> None:
    payload = client.get("/api/decision-explorer").json()
    assert [lever["key"] for lever in payload["levers"]] == ["soreness", "recovery", "personal_response"]
    assert payload["read_only"] is True
    assert "not a prediction" in payload["note"]


def test_what_if_uses_the_same_engine_as_today(client: TestClient) -> None:
    state = _state(client)
    today = client.post("/api/state/today", json={"state": state}).json()["today"]
    recommendation = today["training"]["recommendation"]
    result = client.post("/api/state/what-if", json={"state": state, "lever": "recovery"}).json()

    current = result["current"]
    assert current["session_demand"] == recommendation["session_demand"]
    assert current["base_session_demand"] == recommendation["base_session_demand"]
    assert current["primary_focus"] == recommendation["primary_name"]
    assert current["rir_guidance"] == recommendation["rir_guidance"]
    assert current["readiness_status"] == today["readiness"]["status"]
    assert current["readiness_index"] == today["readiness"]["index"]


def test_what_if_changes_one_input_and_shows_both_results(client: TestClient) -> None:
    result = client.post("/api/state/what-if", json={"state": _state(client), "lever": "recovery"}).json()
    assert result["changed"] is True
    assert result["changed_input"]
    assert result["current"] and result["alternative"]
    keys = {row["key"] for row in result["differences"]}
    assert keys and keys <= {key for key, _ in dx.COMPARED_FIELDS}
    assert "How hard (final demand)" in {row["label"] for row in result["differences"]}
    assert result["conclusion"]
    assert result["why"], "the alternative keeps the engine's own rationale"


def test_what_if_soreness_keeps_the_demand_and_offers_a_safer_session(client: TestClient) -> None:
    """Portfolio demo 1: the decision holds, the session offered is safer."""
    state = _state(client)
    today = client.post("/api/state/today", json={"state": state}).json()["today"]
    group = today["training"]["recommendation"]["muscle_groups"][0]
    result = client.post("/api/state/what-if",
                         json={"state": state, "lever": "soreness", "group": group, "level": 4}).json()
    assert result["current"]["primary_focus"] != result["alternative"]["primary_focus"]
    assert result["alternative"]["primary_focus"]
    assert "soreness set to 4/5" in result["changed_input"]


def test_what_if_without_the_poorer_history_shows_the_base_decision(client: TestClient) -> None:
    """Portfolio demo 2: a personalised MODERATE would be the base HIGH."""
    state = _state(client, demo="poor_high_tolerance")
    today = client.post("/api/state/today", json={"state": state}).json()["today"]
    assert today["personal_response"]["adjustment"] == -1

    result = client.post("/api/state/what-if", json={"state": state, "lever": "personal_response"}).json()
    assert result["current"]["session_demand"] == "Reduced / autoregulated"
    assert result["alternative"]["session_demand"] == "Normal"
    assert result["alternative"]["base_session_demand"] == "Normal"
    assert result["alternative"]["personal_response_adjustment"] == "No adjustment"
    assert result["changed"] is True
    # Only the personal-response layer moved: readiness itself is untouched.
    assert result["current"]["readiness_status"] == result["alternative"]["readiness_status"]
    assert result["current"]["readiness_index"] == result["alternative"]["readiness_index"]


def test_what_if_returns_no_state_so_it_cannot_mutate_saved_data(client: TestClient) -> None:
    state = _state(client, demo="poor_high_tolerance")
    before = json.dumps(state, sort_keys=True, default=str)
    payload = client.post("/api/state/what-if", json={"state": state, "lever": "personal_response"}).json()
    assert "state" not in payload
    assert "adaptation_log" not in payload
    assert json.dumps(state, sort_keys=True, default=str) == before
    assert payload["read_only_note"].startswith("Simulation only")


def test_what_if_never_touches_personal_response_evidence(client: TestClient) -> None:
    """Stripping the history happens on a copy, never on the saved episodes."""
    state = _state(client, demo="poor_high_tolerance")
    before = client.post("/api/state/personal-response", json={"state": state}).json()
    client.post("/api/state/what-if", json={"state": state, "lever": "personal_response"})
    after = client.post("/api/state/personal-response", json={"state": state}).json()
    assert len(before["episodes"]) == len(after["episodes"])
    assert any(row.get("response_feedback") for row in state["training_history"])
    assert before["adjustment"] == after["adjustment"] == -1


def test_what_if_matches_the_engine_when_recomputed_directly(client: TestClient) -> None:
    """The explorer is not a second model: the same engines produce the alternative."""
    state = _state(client)
    api_result = client.post("/api/state/what-if", json={"state": state, "lever": "recovery"}).json()
    direct = explorer_service.explore(state_service.UserState(**state), {"key": "recovery"})
    assert api_result["alternative"] == direct["alternative"]
    assert {row["key"] for row in api_result["differences"]} == {row["key"] for row in direct["differences"]}


def test_what_if_rejects_an_unknown_lever(client: TestClient) -> None:
    response = client.post("/api/state/what-if", json={"state": _state(client), "lever": "wearable"})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# The closed loop, end to end
# --------------------------------------------------------------------------- #


def test_the_full_v13_loop_closes(client: TestClient) -> None:
    # 1. A poorer-response history is loaded, so today is already personalised.
    state = _state(client, demo="poor_high_tolerance")
    envelope = client.post("/api/state/today", json={"state": state}).json()
    state = envelope["state"]
    assert envelope["today"]["personal_response"]["adjustment"] == -1
    assert envelope["today"]["personal_response"]["confidence"]["state"] == "Developing"

    # 2. Start the session with the guidance the product now prescribes.
    started = client.post("/api/state/session/start", json={"state": state}).json()
    state = started["state"]
    assert started["active_session"]["session_demand"] == "Reduced / autoregulated"

    # 3. One checkpoint during the session.
    calibrated = _calibrate(client, state, effort="Harder than expected", performance="As expected", actual_rir=1)
    state = calibrated["state"]
    assert calibrated["calibration"]["result"] in sc.CALIBRATION_RESULTS

    # 4. Complete the session, then give post-session feedback. The session is
    #    dated yesterday because a *next-day* check-in is what closes the loop.
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    logged = client.post("/api/state/session",
                         json={"state": state, "duration_min": 45, "session_rpe": 6,
                               "date": yesterday}).json()
    state = logged["state"]
    session_id = logged["session"]["session_id"]
    assert state["active_session"] is None
    stored = next(row for row in state["training_history"] if row["session_id"] == session_id)
    assert stored["response_calibration"]["result"]

    feedback = client.post("/api/state/feedback",
                           json={"state": state, "session_id": session_id, "difficulty": 4, "performance": 3,
                                 "completion": "Completed", "note": "Loop check"}).json()
    state = feedback["state"]
    episode = next(item for item in feedback["today"]["personal_response"]["episodes"]
                   if item["session_id"] == session_id)
    assert episode["calibrated"] is not None

    # 5. This morning's check-in completes the episode.
    next_day = date.today().isoformat()
    closed = client.post("/api/state/check-in",
                         json={"state": state,
                               "check_in": {"date": next_day, "rmssd_ms": 40.0, "resting_hr_bpm": 60.0,
                                            "sleep_hours": 6.2, "sleep_quality": 2, "fatigue": 4, "soreness": 4,
                                            "stress": 3, "motivation": 2}}).json()
    state = closed["state"]
    response_payload = client.post("/api/state/personal-response", json={"state": state}).json()
    updated = next(item for item in response_payload["episodes"] if item["session_id"] == session_id)
    assert updated["complete"] is True
    assert updated["calibrated"] is not None

    # 6. The learning layer still evaluates, and the Coach explains the facts.
    import adaptive_response as ar

    assert response_payload["confidence"]["state"] in ar.CONFIDENCE_STATES
    assert response_payload["adaptation_history"]
    coach = client.post("/api/state/coach",
                        json={"state": state, "question": "Have I often needed to ease off recently?",
                              "history": []}).json()
    assert coach["ai_used"] is False and coach["kind"] == "verified_data"
    assert "checkpoint" in coach["answer"].casefold()

    # 7. And the next decision is still produced by the same engines.
    after = client.post("/api/state/today", json={"state": state}).json()["today"]
    assert after["training"]["recommendation"]["session_demand"]
    assert after["personal_response"]["base_demand"]
