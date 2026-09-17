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


def test_upward_tier_raise_is_not_a_reachable_product_path() -> None:
    """Phase 2 removed the unreachable "raise the demand tier" rule.

    The engine's demand already *is* the band readiness permits, so no amount of
    good tolerance can produce a tier increase through the real product path. The
    honest replacement is within-tier guidance (see the Phase 2 tests below); the
    product must never claim an upward adaptation it cannot perform.
    """
    days = _days(30)
    sessions = [_session(index, days[2 + index * 3], "Normal", feedback=_good()) for index in range(6)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    summary = ar.summarise(ar.build_episodes(profile))
    assert summary["bands"][2]["observations"] == 6 and summary["bands"][2]["evidence"] == "Established"

    for demand in ("Normal", "Reduced / autoregulated", "Rest or lower-demand"):
        decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": demand})
        assert decision["adjustment"] == 0, demand
        assert decision["direction"] != "raise", demand
        assert decision["final_demand"] == demand
        assert "raised today's session" not in str(decision.get("reason") or "").casefold(), demand


def test_upward_ignores_tolerance_of_the_current_band_only() -> None:
    """Good Moderate tolerance alone must not raise a Moderate session to High."""
    days = _days(30)
    sessions = [_session(index, days[2 + index * 3], "Reduced / autoregulated", feedback=_good()) for index in range(6)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    decision = ar.evaluate(profile, {"overall_readiness": GREEN}, {"intensity": "Reduced / autoregulated"})
    assert decision["adjustment"] == 0, decision["reason"]


def test_within_tier_guidance_is_blocked_outside_green_readiness() -> None:
    days = _days(30)
    sessions = [_session(index, days[2 + index * 3], "Normal", feedback=_good()) for index in range(6)]
    profile = _profile(sessions, daily=[{"date": day, "fatigue": 2, "soreness": 2} for day in days])
    for status in (AMBER, RED, STOP):
        decision = ar.evaluate(profile, {"overall_readiness": status}, {"intensity": "Normal"})
        assert decision["adjustment"] == 0, status
        # Extra effort is never suggested when readiness is not Green, and the
        # refusal is explained with plain product language instead of silence.
        assert decision["within_tier"]["available"] is False, status
        assert decision["no_increase_reason"], status


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


@pytest.mark.parametrize("case,expected_evidence,expected_confidence", [
    ("insufficient", "Insufficient", "Limited"),
    ("emerging", "Emerging", "Developing"),
    ("poor_high_tolerance", "Emerging", "Developing"),
    ("established_good", "Established", "Strong"),
])
def test_demo_response_cases(case: str, expected_evidence: str, expected_confidence: str) -> None:
    """The four documented demo states, evaluated through the real product path."""
    from backend.services import readiness_service, state_service, training_service

    _, state = state_service.base_state("demo-ethan", "Well Recovered Day")
    seeded = state_service.seed_demo_responses(state_service.UserState(**state), case)
    full = state_service.materialise(seeded)
    assessment = readiness_service.assess(full, state_service.check_in_draft(seeded, full))
    recommendation = training_service.recommend(full, assessment)
    decision = ar.evaluate(full, assessment, recommendation)

    assert decision["base_band"] == "High", case
    assert decision["evidence"] == expected_evidence, case
    assert decision["confidence"]["state"] == expected_confidence, case
    if case == "poor_high_tolerance":
        # The portfolio demo: base High demand becomes Moderate.
        assert decision["final_band"] == "Moderate"
        assert decision["adjustment"] == -1
    elif case == "established_good":
        # Good tolerance never raises the tier; it offers bounded extra effort
        # inside the demand readiness already permits.
        assert decision["adjustment"] == 0
        assert decision["within_tier"]["available"] is True
    else:
        assert decision["adjustment"] == 0, case


# --------------------------------------------------------------------------- #
# V1.3 — Adaptive Decision Loop Phase 2: profile, confidence, evidence
# --------------------------------------------------------------------------- #


def _series(count: int, demand: str, feedback: dict, *, end: date | None = None, end_offset: int = 2,
            spacing: int = 3, start_index: int = 0, offset: int = 0) -> tuple[list[dict], list[dict]]:
    """``count`` complete episodes at one demand, each followed by its own check-in."""
    anchor = end or date.today()
    sessions: list[dict] = []
    daily: list[dict] = []
    for step in range(count):
        session_date = anchor - timedelta(days=end_offset + offset + step * spacing)
        sessions.append(_session(start_index + step, session_date.isoformat(), demand, feedback=feedback))
        daily.append({
            "date": (session_date + timedelta(days=1)).isoformat(),
            "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4,
            "sleep_hours": 8.0, "sleep_quality": 4, "rmssd_ms": 50.0, "resting_hr_bpm": 55.0,
        })
    return sessions, daily


def _evaluate(sessions: list[dict], daily: list[dict], demand: str = "Normal") -> dict:
    return ar.evaluate(_profile(sessions, daily=daily), {"overall_readiness": GREEN}, {"intensity": demand})


def test_recommendation_confidence_is_limited_developing_or_strong() -> None:
    for count, expected in ((0, "Limited"), (1, "Limited"), (2, "Limited"), (3, "Developing"),
                            (5, "Developing"), (6, "Strong"), (9, "Strong")):
        sessions, daily = _series(count, "Normal", _good())
        confidence = _evaluate(sessions, daily)["confidence"]
        assert confidence["state"] == expected, count
        assert confidence["state"] in ar.CONFIDENCE_STATES
        assert confidence["relevant_episodes"] == count, count
        # Qualitative only: never a percentage or a physiological-sounding score.
        assert "%" not in confidence["label"]
        assert confidence["label"] == f"{expected} evidence"


def test_confidence_describes_evidence_not_readiness() -> None:
    sessions, daily = _series(6, "Normal", _good())
    for status in (GREEN, AMBER, RED):
        decision = ar.evaluate(_profile(sessions, daily=daily), {"overall_readiness": status},
                               {"intensity": "Normal"})
        # The confidence state follows the personalisation evidence, never the
        # readiness colour, and the note always states what it is not.
        assert decision["confidence"]["state"] == "Strong", status
        assert decision["confidence"]["note"].endswith("a claim about recovery.")
        assert decision["consistency"]["consistent"] is True


def test_pattern_consistency_summarises_the_dominant_direction() -> None:
    def episodes(*verdicts: str) -> list[dict]:
        return [{"response": {"verdict": verdict}, "complete": True, "band": "High"} for verdict in verdicts]

    empty = ar.pattern_consistency([])
    assert empty["episodes"] == 0 and empty["consistent"] is False and empty["direction"] is None

    # Four of five pointing the same way is a consistent pattern.
    consistent = ar.pattern_consistency(episodes(*(["poorer_than_usual"] * 4 + ["better_than_usual"])))
    assert consistent["consistent"] is True and consistent["direction"] == "poorer_than_usual"
    assert consistent["label"] == "Consistent" and consistent["ratio"] == 0.8

    # 2 poorer / 2 expected / 1 good is a mixed pattern, never a probability.
    mixed = ar.pattern_consistency(episodes("poorer_than_usual", "poorer_than_usual",
                                            "as_usual", "as_usual", "better_than_usual"))
    assert mixed["consistent"] is False and mixed["direction"] == "mixed"
    assert mixed["label"] == "Mixed" and mixed["ratio"] == 0.4

    # Under three episodes there is not enough evidence to call a pattern.
    thin = ar.pattern_consistency(episodes("better_than_usual", "better_than_usual"))
    assert thin["label"] == "Not enough evidence" and thin["consistent"] is False


def test_relevant_episodes_only_count_todays_demand() -> None:
    high_sessions, high_daily = _series(3, "Normal", _good(), start_index=0)
    moderate_sessions, moderate_daily = _series(4, "Reduced / autoregulated", _good(), start_index=10, offset=1)
    sessions = high_sessions + moderate_sessions
    daily = high_daily + moderate_daily

    high = _evaluate(sessions, daily, "Normal")
    assert high["relevant"]["band"] == "High" and high["relevant"]["count"] == 3
    assert high["confidence"]["state"] == "Developing"

    moderate = _evaluate(sessions, daily, "Reduced / autoregulated")
    assert moderate["relevant"]["band"] == "Moderate" and moderate["relevant"]["count"] == 4
    assert moderate["confidence"]["state"] == "Developing"

    # A demand band with no history is honestly reported as Limited, never zero-filled.
    low = _evaluate(sessions, daily, "Rest or lower-demand")
    assert low["relevant"]["count"] == 0 and low["confidence"]["state"] == "Limited"


def test_recency_window_stops_old_episodes_driving_today() -> None:
    old_sessions, old_daily = _series(4, "Normal", _good(), end=date.today() - timedelta(days=90))
    recent_sessions, recent_daily = _series(3, "Normal", _good(), start_index=20)
    sessions = old_sessions + recent_sessions
    daily = old_daily + recent_daily

    decision = _evaluate(sessions, daily)
    # All seven stay in the profile and in the history…
    assert decision["summary"]["episodes_complete"] == 7
    assert decision["profile"]["bands"][2]["observations"] == 7
    assert len(decision["episodes"]) == 7
    # …but only the three inside the recent window can drive personalisation.
    assert decision["relevant"]["count"] == 3
    assert decision["relevant"]["window_days"] == ar.RECENT_WINDOW_DAYS
    assert decision["confidence"]["state"] == "Developing"


def test_recency_boundary_uses_the_documented_window() -> None:
    inside = date.today() - timedelta(days=ar.RECENT_WINDOW_DAYS - 1)
    outside = date.today() - timedelta(days=ar.RECENT_WINDOW_DAYS + 1)
    episodes = [
        {"session_id": "in", "date": inside.isoformat(), "band": "High", "complete": True,
         "response": {"verdict": "better_than_usual"}},
        {"session_id": "out", "date": outside.isoformat(), "band": "High", "complete": True,
         "response": {"verdict": "poorer_than_usual"}},
    ]
    assert [row["session_id"] for row in ar.relevant_episodes(episodes, "High")] == ["in"]


def test_evidence_coverage_describes_what_actually_exists() -> None:
    sessions, daily = _series(4, "Normal", _good())
    coverage = _evaluate(sessions, daily)["coverage"]
    assert coverage["episodes_complete"] == 4 and coverage["episodes_total"] >= 4
    assert coverage["last_complete_days_ago"] is not None and coverage["last_complete_days_ago"] >= 0
    assert {row["band"] for row in coverage["bands"]} == {"Low", "Moderate", "High"}
    assert next(row for row in coverage["bands"] if row["band"] == "High")["observations"] == 4


def test_a_session_without_a_following_check_in_stays_pending() -> None:
    sessions, daily = _series(3, "Normal", _poor())
    pending = _session(99, (date.today() - timedelta(days=1)).isoformat(), "Normal", feedback=_poor())
    decision = _evaluate(sessions + [pending], daily)
    assert decision["coverage"]["episodes_pending"] == 1
    assert decision["coverage"]["episodes_complete"] == 3
    # Pending episodes never contribute to the personalisation evidence.
    assert decision["relevant"]["count"] == 3


def test_response_profile_reports_counts_status_and_recent_pattern() -> None:
    sessions, daily = _series(6, "Normal", _good())
    high = next(row for row in _evaluate(sessions, daily)["profile"]["bands"] if row["band"] == "High")
    assert high["observations"] == 6 and high["better"] == 6 and high["poorer"] == 0
    assert high["evidence"] == "Established"
    assert high["pattern"] == "Generally tolerated better than expected"
    assert high["recent_observations"] == 6
    assert high["recent_pattern"] == "Generally tolerated better than expected"


def test_focus_patterns_are_hidden_until_the_data_supports_them() -> None:
    thin_sessions, thin_daily = _series(2, "Normal", _good())
    assert _evaluate(thin_sessions, thin_daily)["profile"]["focus"] == []

    enough_sessions, enough_daily = _series(3, "Normal", _good())
    focus = _evaluate(enough_sessions, enough_daily)["profile"]["focus"]
    assert len(focus) == 1 and focus[0]["focus"] == "Back + Biceps" and focus[0]["observations"] == 3


def test_good_tolerance_is_expressed_within_the_prescribed_demand() -> None:
    sessions, daily = _series(6, "Normal", _good())
    decision = _evaluate(sessions, daily)
    assert decision["base_band"] == "High" and decision["final_band"] == "High"
    assert decision["adjustment"] == 0 and decision["direction"] == "within_tier"
    assert decision["confidence"]["state"] == "Strong"
    within = decision["within_tier"]
    assert within["available"] is True
    assert within["scope"].startswith("Within the demand already prescribed")
    assert "RIR" in within["guidance"] and "No extra sets" in within["guidance"]
    assert decision["no_increase_reason"] is None

    # The engine's own demand and effort wording are both preserved.
    summary = response_service.apply_to_summary({"session_demand": "Normal", "rir_guidance": "1–3 RIR"},
                                                decision, "1–3 RIR")
    assert summary["base_session_demand"] == "Normal"
    assert summary["session_demand"] == "Normal"
    assert summary["rir_guidance"] == "1–3 RIR"
    assert summary["adaptation"]["label"] == "Personalized from recent response"
    assert summary["adaptation"]["scope"].startswith("Within the demand already prescribed")
    # Base and final never collapse into one opaque output.
    assert summary["personal_response"]["base_demand"] == "Normal"
    assert summary["personal_response"]["final_demand"] == "Normal"


def test_within_tier_guidance_respects_readiness_soreness_and_scope() -> None:
    strong = {"confidence": {"state": "Strong"}, "consistency": {"counts": {"poorer_than_usual": 0}},
              "_relevant_episodes": [{"response": {"verdict": "better_than_usual"}}] * 4}

    assert ar.within_tier_guidance(strong, {"overall_readiness": GREEN}, "High", GREEN)["available"] is True

    not_green = ar.within_tier_guidance(strong, {"overall_readiness": AMBER}, "High", AMBER)
    assert not_green["available"] is False and "not Green" in not_green["reason"]

    sore = ar.within_tier_guidance(
        strong, {"overall_readiness": GREEN, "today_data": {"local_soreness": {"Quads": 5}}}, "High", GREEN)
    assert sore["available"] is False and "soreness" in sore["reason"]

    flagged = ar.within_tier_guidance(
        strong, {"overall_readiness": GREEN, "safety_flags": ["Chest pain"]}, "High", GREEN)
    assert flagged["available"] is False and "safety" in flagged["reason"]

    # When no safe in-range option exists the product says so instead of inventing one.
    ceiling = ar.within_tier_guidance(strong, {"overall_readiness": GREEN}, "Low", GREEN)
    assert ceiling["available"] is False and ceiling["reason"] == ar.CEILING_MESSAGE

    weak = {"confidence": {"state": "Developing"}, "consistency": {"counts": {"poorer_than_usual": 0}},
            "_relevant_episodes": [{"response": {"verdict": "better_than_usual"}}] * 4}
    assert ar.within_tier_guidance(weak, {"overall_readiness": GREEN}, "High", GREEN)["available"] is False


def test_adaptation_history_records_one_meaningful_event_per_day() -> None:
    from backend.services import state_service

    sessions, daily = _series(3, "Normal", _poor())
    event = ar.adaptation_event(_evaluate(sessions, daily), date(2026, 1, 5))
    assert event["result"] == "reduced" and event["adjustment"] == -1
    assert event["base_band"] == "High" and event["final_band"] == "Moderate"
    assert event["confidence"] == "Developing" and event["relevant_episodes"] == 3
    assert event["reason"]

    state = state_service.UserState(profile_id="demo-ethan", scenario="Well Recovered Day")
    state = state_service.record_adaptation(state, event)
    assert len(state.adaptation_log) == 1
    # Recomputing the same day replaces the entry instead of duplicating it.
    again = state_service.record_adaptation(state, {**event, "reason": "updated"})
    assert len(again.adaptation_log) == 1 and again.adaptation_log[0]["reason"] == "updated"

    quiet = ar.adaptation_event({"adjustment": 0, "base_demand": "Normal", "base_band": "High",
                                 "final_demand": "Normal", "final_band": "High",
                                 "confidence": {"state": "Limited"}, "evidence": "Insufficient",
                                 "detail": "Not enough history yet"}, date(2026, 1, 6))
    assert quiet["result"] == "no_change" and quiet["reason"] == "Not enough history yet"
