"""V1.3 Adaptive Decision Loop — Phase 1 regression tests.

These cover the deterministic Personal Response layer only: episodes, evidence
states, the bounded one-step adjustment and its safety precedence. The engines
themselves are covered by test_app.py and must stay untouched.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

import adaptive_response as ar
from backend.services import response_service
from demo_data import build_demo_profiles
from readiness_engine import AMBER, GREEN, RED, STOP


def _days(count: int, end: date | None = None) -> list[str]:
    anchor = end or date.today()
    return [(anchor - timedelta(days=count - index - 1)).isoformat() for index in range(count)]


def _profile(sessions: list[dict], daily: list[dict] | None = None) -> dict:
    profile = json.loads(json.dumps(build_demo_profiles()[0], default=str))
    profile["training_history"] = sessions
    profile["history"] = daily if daily is not None else [
        {"date": day, "rmssd_ms": 50, "resting_hr_bpm": 55, "sleep_hours": 8, "sleep_quality": 4,
         "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4}
        for day in _days(30)
    ]
    return profile


def _session(index: int, session_date: str, demand: str, *, feedback: dict | None = None,
             completed: bool = True) -> dict:
    return {
        "session_id": f"s-{index}",
        "date": session_date,
        "primary_focus": "Back + Biceps",
        "training_type": "Strength",
        "duration_min": 55,
        "session_rpe": 7,
        "working_sets": 12,
        "completed": completed,
        "response_context": {
            "readiness_status": GREEN, "readiness_index": 88, "readiness_confidence": "NORMAL",
            "base_session_demand": demand, "final_session_demand": demand,
        } if demand else None,
        "response_feedback": feedback,
    }


def _poor() -> dict:
    return {"difficulty": 5, "performance": 2, "completion": "Stopped early", "note": ""}


def _good() -> dict:
    return {"difficulty": 2, "performance": 4, "completion": "Completed", "note": ""}


def test_demand_bands_match_the_engine_vocabulary() -> None:
    assert ar.band_for_demand("Normal") == "High"
    assert ar.band_for_demand("Reduced / autoregulated") == "Moderate"
    assert ar.band_for_demand("Reduced strength") == "Moderate"
    assert ar.band_for_demand("Rest or lower-demand") == "Low"
    assert ar.band_for_demand("Lower-demand") == "Low"
    # Vocabulary the adaptive layer must not classify (it never adapts those paths).
    assert ar.band_for_demand("RPE 3–4 / 10") is None
    assert ar.band_for_demand("Recovery") is None
    assert ar.band_for_demand(None) is None


def test_evidence_states_use_the_documented_thresholds() -> None:
    assert ar.evidence_state(0) == "Insufficient"
    assert ar.evidence_state(2) == "Insufficient"
    assert ar.evidence_state(3) == "Emerging"
    assert ar.evidence_state(5) == "Emerging"
    assert ar.evidence_state(6) == "Established"


def test_response_episode_links_the_next_check_in() -> None:
    days = _days(10)
    profile = _profile(
        [_session(1, days[4], "Normal", feedback=_poor()), _session(2, days[7], "Normal", feedback=_good())],
        daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days],
    )
    episodes = ar.build_episodes(profile)
    newest = episodes[0]
    assert newest["session_id"] == "s-2"
    assert newest["link"] == "linked" and newest["complete"] is True
    assert newest["after"]["date"] == days[8]
    assert newest["before"]["readiness_status"] == GREEN
    assert newest["performed"]["duration_min"] == 55
    assert newest["recommendation"]["base_demand"] == "Normal"


def test_episode_is_pending_without_a_following_check_in() -> None:
    days = _days(6)
    profile = _profile([_session(1, days[-1], "Normal", feedback=_poor())],
                       daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    episode = ar.build_episodes(profile)[0]
    assert episode["link"] == "pending" and episode["complete"] is False


def test_sessions_without_a_snapshot_are_not_classified() -> None:
    days = _days(6)
    profile = _profile([_session(1, days[3], None, feedback=_poor())],
                       daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    episode = ar.build_episodes(profile)[0]
    assert episode["band"] is None and episode["complete"] is False


def test_insufficient_evidence_never_adapts() -> None:
    days = _days(10)
    profile = _profile([_session(1, days[3], "Normal", feedback=_poor())],
                       daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Normal"})
    assert decision["evidence"] == "Insufficient"
    assert decision["adjustment"] == 0
    assert decision["detail"] == "Not enough history yet"


def test_repeated_poor_response_reduces_one_step() -> None:
    days = _days(14)
    profile = _profile(
        [_session(index, days[2 + index * 3], "Normal", feedback=_poor()) for index in range(3)],
        daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days],
    )
    decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Normal"})
    assert decision["base_band"] == "High" and decision["final_band"] == "Moderate"
    assert decision["adjustment"] == -1
    assert decision["final_demand"] == ar.BAND_DEMAND["Moderate"]
    assert "reduced today's session" in decision["reason"].casefold()


def test_adjustment_is_capped_at_one_step() -> None:
    days = _days(30)
    sessions = [_session(index, days[2 + index * 3], "Normal", feedback=_poor()) for index in range(8)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Normal"})
    assert decision["adjustment"] == -1  # never -2, even with eight poor episodes
    assert decision["final_band"] == "Moderate"


def test_upward_requires_established_evidence_and_leaves_high_alone() -> None:
    days = _days(30)
    # Evidence must come from the band we would move *into* (High), which is the
    # conservative reading: tolerating Moderate well says nothing about High.
    sessions = [_session(index, days[2 + index * 3], "Normal", feedback=_good()) for index in range(6)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    summary = ar.summarise(ar.build_episodes(profile))
    assert summary["bands"][2]["observations"] == 6 and summary["bands"][2]["evidence"] == "Established"

    # A High base has no headroom, so nothing is raised.
    high = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Normal"})
    assert high["adjustment"] == 0 and high["final_band"] == "High"

    # With a Moderate base and Green readiness the rule may raise exactly one step.
    moderate = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Reduced / autoregulated"})
    assert moderate["final_band"] == "High" and moderate["adjustment"] == 1
    assert "raised today's session" in moderate["reason"].casefold()


def test_upward_ignores_tolerance_of_the_current_band_only() -> None:
    """Good Moderate tolerance alone must not raise a Moderate session to High."""
    days = _days(30)
    sessions = [_session(index, days[2 + index * 3], "Reduced / autoregulated", feedback=_good()) for index in range(6)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Reduced / autoregulated"})
    assert decision["adjustment"] == 0, decision["reason"]


def test_upward_is_blocked_outside_green_readiness() -> None:
    days = _days(30)
    sessions = [_session(index, days[2 + index * 3], "Normal", feedback=_good()) for index in range(6)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    for status in (AMBER, RED, STOP):
        decision = ar.evaluate(profile, {"overall_readiness": status}, {"intensity": "Reduced / autoregulated"})
        assert decision["adjustment"] == 0, status


def test_red_and_stop_are_never_overridden() -> None:
    days = _days(20)
    sessions = [_session(index, days[2 + index * 3], "Normal", feedback=_poor()) for index in range(5)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    for status, demand in ((RED, "Rest or lower-demand"), (STOP, "STOP")):
        decision = ar.evaluate(profile, {"overall_readiness": status}, {"intensity": demand})
        assert decision["adjustment"] == 0
        assert decision["detail"] == "Readiness or safety routing takes precedence"
        assert decision["final_demand"] == demand


def test_summary_keeps_base_and_final_separate() -> None:
    days = _days(14)
    profile = _profile([_session(index, days[2 + index * 3], "Normal", feedback=_poor()) for index in range(3)],
                       daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Normal"})
    summary = response_service.apply_to_summary(
        {"session_demand": "Normal", "rir_guidance": "1–3 RIR"}, decision, "1–3 RIR")
    assert summary["base_session_demand"] == "Normal"
    assert summary["session_demand"] == "Reduced / autoregulated"
    assert summary["rir_guidance"] == ar.BAND_RIR["Moderate"]
    assert summary["adaptation"]["label"] == "Adjusted from your recent response"
    assert summary["personal_response"]["adjustment"] == -1


def test_decision_trace_gains_the_personal_response_step() -> None:
    base_trace = [
        {"index": index, "step": step, "value": step, "source": "deterministic"}
        for index, step in enumerate(
            ["GOAL", "PROGRAMME", "WEEKLY EXPOSURE", "RECENT TRAINING", "LOCAL SORENESS", "READINESS",
             "SESSION DEMAND", "RECOMMENDATION"], start=1)
    ]
    trace = response_service.apply_to_trace(base_trace, {"adjustment": -1, "base_band": "High",
                                                         "final_band": "Moderate", "evidence": "Emerging"})
    steps = [row["step"] for row in trace]
    assert len(trace) == 9
    assert steps[5] == "READINESS" and steps[6] == "PERSONAL RESPONSE" and steps[7] == "SESSION DEMAND"
    assert trace[6]["value"] == "Reduced one step · High → Moderate"
    assert [row["index"] for row in trace] == list(range(1, 10))

    quiet = response_service.apply_to_trace(base_trace, {"adjustment": 0, "base_band": "High", "evidence": "Emerging"})
    assert [row for row in quiet if row["step"] == "PERSONAL RESPONSE"][0]["value"] == "No adjustment"


@pytest.mark.parametrize("case,expected_evidence", [
    ("insufficient", "Insufficient"),
    ("emerging", "Emerging"),
    ("poor_high_tolerance", "Emerging"),
    ("established_good", "Established"),
])
def test_demo_response_cases(case: str, expected_evidence: str) -> None:
    from backend.services import state_service

    profile, state = state_service.base_state("demo-ethan", "Well Recovered Day")
    seeded = state_service.seed_demo_responses(state_service.UserState(**state), case)
    full = state_service.materialise(seeded)
    decision = ar.evaluate(full, {"overall_readiness": GREEN}, {"intensity": "Normal"})
    assert decision["evidence"] == expected_evidence, case
    if case == "poor_high_tolerance":
        # The portfolio demo: base High demand becomes Moderate.
        assert decision["base_band"] == "High" and decision["final_band"] == "Moderate"
        assert decision["adjustment"] == -1
    else:
        assert decision["adjustment"] == 0, case
