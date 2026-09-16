"""Thin HTTP surface over the existing engines.

Each handler resolves a profile, calls one service, and returns JSON. No
threshold, formula or recommendation rule is implemented in this file.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

import ai_engine
from fastapi import APIRouter, HTTPException, Query
from training_recommendation_engine import prescription_log_defaults

from backend.schemas.models import (
    BaseStateResponse,
    CheckInRequest,
    CheckInRequest2,
    CoachMessageRequest,
    CoachMessageResponse,
    CoachStateRequest,
    DecisionTraceStep,
    HealthResponse,
    InsightsRequest,
    InsightsResponse,
    PersonalResponseRequest,
    PersonalResponseResponse,
    ProfileSummary,
    ProfileEditRequest,
    ProfileOptionsResponse,
    ReadinessSummary,
    RecentSession,
    ScienceReferencesResponse,
    ScienceLogicResponse,
    ScenarioListResponse,
    SessionLogRequest,
    SessionLogResponse,
    SessionFeedbackRequest,
    StateEnvelope,
    StateRequest,
    TodayResponse,
    TrainingRecommendationSummary,
    WeeklyExposure,
)
from backend.services import (coach_service, demo_service, insights_service, readiness_service, response_service,
                              science_service, state_service, training_service)

router = APIRouter(prefix="/api")

API_VERSION = "1.2.0-phase1"
REFERENCE_IMPLEMENTATION = "Streamlit V1.1 (app.py) — untouched and still runnable"
ENGINES = [
    "readiness_engine.assess_readiness",
    "training_recommendation_engine.recommend_training",
    "training_recommendation_engine.weekly_training_exposure",
    "ai_facts.build_personal_facts",
    "ai_engine.get_ai_response",
]


def _profile_or_404(profile_id: str | None) -> dict[str, Any]:
    try:
        return demo_service.get_profile(profile_id)
    except demo_service.UnknownProfileError:
        raise HTTPException(status_code=404, detail=f"Unknown profile id: {profile_id}") from None


def _context(profile_id: str | None, check_in: dict[str, Any] | None = None):
    profile = _profile_or_404(profile_id)
    assessment = readiness_service.assess(profile, check_in)
    recommendation = training_service.recommend(profile, assessment)
    return profile, assessment, recommendation


def _today_payload(profile: dict[str, Any], assessment: dict[str, Any],
                   recommendation: dict[str, Any]) -> dict[str, Any]:
    """One Today payload shape, shared by the demo and state endpoints.

    V1.3 adds the bounded Personal Response layer on top of the engine's base
    decision: the base recommendation is preserved, the final one is what the
    product presents, and the Decision Trace shows the extra step.
    """
    decision = response_service.evaluate(profile, assessment, recommendation)
    base_summary = training_service.summary(recommendation)
    summary = response_service.apply_to_summary(base_summary, decision, base_summary.get("rir_guidance"))
    trace = response_service.apply_to_trace(training_service.decision_trace(recommendation), decision)
    readiness_payload = readiness_service.summary(profile, assessment)
    return {
        "profile": _profile_summary(profile),
        "readiness": readiness_payload,
        "training": {
            "recommendation": summary,
            "decision_trace": trace,
            "exposure": training_service.exposure(profile, assessment, recommendation),
            "history": training_service.recent_sessions(profile, 8),
        },
        "personal_response": response_service.payload(decision),
        "why": {
            "headline": readiness_payload.get("explanation") or "Readiness and recent training drive today's session.",
            "rationale": list(recommendation.get("rationale") or []),
            "decision_factors": list(recommendation.get("decision_factors") or []),
            "note": "Decision Trace is a deterministic explanation, not model chain-of-thought.",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "backend.services.readiness_service + training_service",
    }


def _state_context(state) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Materialise a client-owned state into profile + assessment + recommendation + draft."""
    profile = state_service.materialise(state)
    draft = state_service.check_in_draft(state, profile)
    assessment = readiness_service.assess(profile, draft)
    recommendation = training_service.recommend(profile, assessment)
    return profile, assessment, recommendation, draft


def _response_decision(profile: dict[str, Any], assessment: dict[str, Any],
                       recommendation: dict[str, Any]) -> dict[str, Any]:
    return response_service.evaluate(profile, assessment, recommendation)


def _snapshot(profile: dict[str, Any], assessment: dict[str, Any], recommendation: dict[str, Any],
              decision: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compact pre-session snapshot captured when a session is logged."""
    recommendation_summary = dict((payload.get("training") or {}).get("recommendation") or {})
    exposure = recommendation.get("weekly_exposure") or {}
    groups = sorted(((str(key), float(value)) for key, value in exposure.items()), key=lambda item: -item[1])
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "readiness_status": assessment.get("overall_readiness"),
        "readiness_index": assessment.get("readiness_index"),
        "readiness_confidence": assessment.get("assessment_confidence"),
        "base_session_demand": decision.get("base_demand"),
        "final_session_demand": decision.get("final_demand"),
        "adjustment": decision.get("adjustment", 0),
        "recommended_focus": recommendation_summary.get("primary_name"),
        "recommended_duration": recommendation_summary.get("duration"),
        "recommended_rir": recommendation_summary.get("rir_guidance"),
        "local_soreness": dict((assessment.get("today_data") or {}).get("local_soreness") or {}),
        "exposure_note": (f"{groups[0][0]} {groups[0][1]:g} / "
                          f"{(recommendation.get('weekly_targets') or {}).get(groups[0][0], 0):g} sets") if groups else None,
    }


def _profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": profile.get("user_id"),
        "name": profile.get("name"),
        "is_demo": bool(profile.get("is_demo")),
        "age": profile.get("age"),
        "sex": profile.get("sex"),
        "primary_activity": profile.get("primary_activity"),
        "training_goal": profile.get("training_goal"),
        "training_level": profile.get("training_level"),
        "training_split_preference": profile.get("training_split_preference"),
        "personal_sleep_need": profile.get("personal_sleep_need"),
        "target_sessions_per_week": profile.get("target_sessions_per_week"),
        "weekly_set_targets": dict(profile.get("weekly_set_targets") or {}),
        "default_scenario": profile.get("default_scenario"),
        "scenarios": list(demo_service.scenarios()),
    }


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    secrets = coach_service.server_secrets()
    return {
        "status": "ok",
        "service": "personal-readiness-assistant-api",
        "api_version": API_VERSION,
        "reference_implementation": REFERENCE_IMPLEMENTATION,
        "ai_provider": ai_engine.AI_PROVIDER_LABEL,
        "ai_explanations_enabled": ai_engine.ai_coach_enabled(secrets),
        "ai_credential_configured": coach_service.credential_configured(),
        "engines": ENGINES,
    }


@router.get("/profiles", response_model=list[ProfileSummary])
def profiles() -> list[dict[str, Any]]:
    return [_profile_summary(profile) for profile in demo_service.demo_profiles()]


@router.get("/profile", response_model=ProfileSummary)
def profile(profile_id: str | None = Query(default=None)) -> dict[str, Any]:
    return _profile_summary(_profile_or_404(profile_id))


@router.get("/readiness", response_model=ReadinessSummary)
def readiness(profile_id: str | None = Query(default=None)) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    _, summary = readiness_service.assess_and_summarise(profile)
    return summary


@router.get("/training/recommendation", response_model=TrainingRecommendationSummary)
def recommendation(profile_id: str | None = Query(default=None)) -> dict[str, Any]:
    _, _, rec = _context(profile_id)
    return training_service.summary(rec)


@router.get("/training/exposure", response_model=WeeklyExposure)
def exposure(profile_id: str | None = Query(default=None)) -> dict[str, Any]:
    profile, assessment, rec = _context(profile_id)
    return training_service.exposure(profile, assessment, rec)


@router.get("/training/history", response_model=list[RecentSession])
def history(profile_id: str | None = Query(default=None),
            limit: int = Query(default=8, ge=1, le=30)) -> list[dict[str, Any]]:
    return training_service.recent_sessions(_profile_or_404(profile_id), limit)


@router.get("/decision-trace", response_model=list[DecisionTraceStep])
def decision_trace(profile_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    _, _, rec = _context(profile_id)
    return training_service.decision_trace(rec)


@router.get("/science/references", response_model=ScienceReferencesResponse)
def references() -> dict[str, Any]:
    return science_service.references()


@router.get("/science/logic", response_model=ScienceLogicResponse)
def science_logic() -> dict[str, Any]:
    return science_service.logic()


@router.get("/today", response_model=TodayResponse)
def today(profile_id: str | None = Query(default=None),
          scenario: str | None = Query(default=None)) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    check_in = readiness_service.build_check_in(profile, scenario=scenario) if scenario else None
    assessment = readiness_service.assess(profile, check_in)
    rec = training_service.recommend(profile, assessment)
    return _today_payload(profile, assessment, rec)


@router.post("/check-in", response_model=TodayResponse)
def check_in(payload: CheckInRequest) -> dict[str, Any]:
    profile = _profile_or_404(payload.profile_id)
    check_in_values = payload.model_dump(exclude_none=True, exclude={"profile_id", "scenario"})
    check_in = readiness_service.build_check_in(profile, check_in_values, payload.scenario)
    assessment = readiness_service.assess(profile, check_in)
    rec = training_service.recommend(profile, assessment)
    return _today_payload(profile, assessment, rec)


@router.post("/coach/message", response_model=CoachMessageResponse)
def coach_message(payload: CoachMessageRequest) -> dict[str, Any]:
    profile, assessment, rec = _context(payload.profile_id)
    history = [{"role": turn.role, "content": turn.content} for turn in payload.history]
    return coach_service.answer(payload.question, profile, assessment, rec, history)


# --------------------------------------------------------------------------- #
# Phase 2 — stateless compute over the client-owned state
# --------------------------------------------------------------------------- #


@router.get("/scenarios", response_model=ScenarioListResponse)
def scenarios() -> dict[str, Any]:
    return {
        "scenarios": state_service.scenario_list(),
        "fields": list(state_service.SCENARIO_FIELDS),
        "safety_flags": list(state_service.safety_flags()),
        "muscle_groups": list(state_service.muscle_groups()),
        "note": "Demo scenarios are simulated check-ins for the fixed demo profiles. They are not predictions.",
    }


@router.get("/state/base", response_model=BaseStateResponse)
def state_base(profile_id: str | None = Query(default=None),
               scenario: str | None = Query(default=None),
               response_demo: str | None = Query(default=None)) -> dict[str, Any]:
    profile, state = state_service.base_state(profile_id, scenario)
    if response_demo:
        seeded = state_service.seed_demo_responses(state_service.UserState(**state), response_demo)
        state = seeded.model_dump()
    return {
        "state": state,
        "profile": _profile_summary(profile),
        "daily_rows": len(profile.get("history") or []),
        "training_rows": len(profile.get("training_history") or []),
        "note": "The client owns this state. The API computes from it and stores nothing.",
    }


@router.get("/profile/options", response_model=ProfileOptionsResponse)
def profile_options() -> dict[str, Any]:
    return {**state_service.profile_options(), "muscle_groups": list(state_service.muscle_groups())}


@router.post("/state/today", response_model=StateEnvelope)
def state_today(payload: StateRequest) -> dict[str, Any]:
    profile, assessment, rec, _ = _state_context(payload.state)
    return {"state": payload.state, "today": _today_payload(profile, assessment, rec)}


@router.post("/state/check-in", response_model=StateEnvelope)
def state_check_in(payload: CheckInRequest2) -> dict[str, Any]:
    new_state = state_service.apply_check_in(payload.state, payload.check_in)
    profile, assessment, rec, _ = _state_context(new_state)
    return {"state": new_state, "today": _today_payload(profile, assessment, rec)}


@router.post("/state/profile", response_model=StateEnvelope)
def state_profile(payload: ProfileEditRequest) -> dict[str, Any]:
    new_state = state_service.apply_profile_edits(payload.state, payload.edits.model_dump())
    profile, assessment, rec, _ = _state_context(new_state)
    return {"state": new_state, "today": _today_payload(profile, assessment, rec)}


@router.post("/state/session", response_model=SessionLogResponse)
def state_session(payload: SessionLogRequest) -> dict[str, Any]:
    profile, assessment, rec, _ = _state_context(payload.state)
    decision = _response_decision(profile, assessment, rec)
    snapshot_payload = _today_payload(profile, assessment, rec)
    selected = training_service.find_session(rec, payload.prescription_id)
    defaults = prescription_log_defaults(selected)
    exercises = payload.exercises or [
        {"name": item["name"], "working_sets": item["prescribed_sets"], "prescribed_sets": item["prescribed_sets"]}
        for item in defaults.get("exercises", [])
    ]
    details = {
        "date": payload.date or date.today().isoformat(),
        "training_type": selected.get("training_type"),
        "primary_focus": selected.get("name"),
        "muscle_groups": list(selected.get("muscle_groups") or []),
        "prescription_id": selected.get("prescription_id"),
        "exercises": exercises,
        "prescribed_sets": defaults.get("prescribed_sets"),
        "actual_sets": sum(float(item.get("working_sets") or 0) for item in exercises),
        "completion_status": payload.completion_status,
        "duration_min": payload.duration_min,
        "session_rpe": payload.session_rpe,
        "notes": payload.notes or "",
    }
    new_state, session = state_service.apply_session(payload.state, details)
    # Capture the compact pre-session snapshot on the logged session.
    snapshot = _snapshot(profile, assessment, rec, decision, snapshot_payload)
    session = {**session, "response_context": snapshot}
    new_state = state_service.upsert_session_overlay(new_state, str(session["session_id"]),
                                                     {"response_context": snapshot})
    updated_profile, updated_assessment, updated_rec, _ = _state_context(new_state)
    return {
        "state": new_state,
        "session": session,
        "today": _today_payload(updated_profile, updated_assessment, updated_rec),
        "exposure": training_service.exposure(updated_profile, updated_assessment, updated_rec),
        "history": training_service.recent_sessions(updated_profile, 8),
    }


@router.post("/state/coach", response_model=CoachMessageResponse)
def state_coach(payload: CoachStateRequest) -> dict[str, Any]:
    profile, assessment, rec, _ = _state_context(payload.state)
    # Personal Response facts are answered deterministically, so they never reach
    # the AI provider (the AI-01 grounding contract).
    deterministic = response_service.answer_question(payload.question, _response_decision(profile, assessment, rec))
    if deterministic:
        return coach_service.verified_answer(deterministic, "Answered from your recorded data. No model wording was used.")
    history = [{"role": turn.role, "content": turn.content} for turn in payload.history]
    return coach_service.answer(payload.question, profile, assessment, rec, history)


@router.post("/state/feedback", response_model=StateEnvelope)
def state_feedback(payload: SessionFeedbackRequest) -> dict[str, Any]:
    """Lightweight post-session feedback; adds meaning beyond session RPE."""
    new_state = state_service.upsert_session_overlay(payload.state, payload.session_id, {
        "response_feedback": {
            "difficulty": payload.difficulty,
            "performance": payload.performance,
            "completion": payload.completion,
            "note": payload.note or "",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    })
    profile, assessment, rec, _ = _state_context(new_state)
    return {"state": new_state, "today": _today_payload(profile, assessment, rec)}


@router.post("/state/personal-response", response_model=PersonalResponseResponse)
def state_personal_response(payload: PersonalResponseRequest) -> dict[str, Any]:
    profile, assessment, rec, _ = _state_context(payload.state)
    return response_service.payload(_response_decision(profile, assessment, rec))


@router.get("/personal-response", response_model=PersonalResponseResponse)
def personal_response(profile_id: str | None = Query(default=None),
                      response_demo: str | None = Query(default=None)) -> dict[str, Any]:
    """Read-only Personal Response view of a demo profile."""
    profile = _profile_or_404(profile_id)
    state = state_service.UserState(profile_id=str(profile["user_id"]),
                                    scenario=state_service.default_scenario(profile))
    if response_demo:
        state = state_service.seed_demo_responses(state, response_demo)
    full_profile, assessment, rec, _ = _state_context(state)
    return response_service.payload(_response_decision(full_profile, assessment, rec))


@router.post("/state/insights", response_model=InsightsResponse)
def state_insights(payload: InsightsRequest) -> dict[str, Any]:
    profile, assessment, rec, _ = _state_context(payload.state)
    return insights_service.build(profile, assessment, rec, payload.window)
