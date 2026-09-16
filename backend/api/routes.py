"""Thin HTTP surface over the existing engines.

Each handler resolves a profile, calls one service, and returns JSON. No
threshold, formula or recommendation rule is implemented in this file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import ai_engine
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.models import (
    CheckInRequest,
    CoachMessageRequest,
    CoachMessageResponse,
    DecisionTraceStep,
    HealthResponse,
    ProfileSummary,
    ReadinessSummary,
    RecentSession,
    ScienceReferencesResponse,
    TodayResponse,
    TrainingRecommendationSummary,
    WeeklyExposure,
)
from backend.services import coach_service, demo_service, readiness_service, science_service, training_service

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


@router.get("/today", response_model=TodayResponse)
def today(profile_id: str | None = Query(default=None),
          scenario: str | None = Query(default=None)) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    check_in = readiness_service.build_check_in(profile, scenario=scenario) if scenario else None
    assessment = readiness_service.assess(profile, check_in)
    rec = training_service.recommend(profile, assessment)
    readiness_payload = readiness_service.summary(profile, assessment)
    return {
        "profile": _profile_summary(profile),
        "readiness": readiness_payload,
        "training": {
            "recommendation": training_service.summary(rec),
            "decision_trace": training_service.decision_trace(rec),
        },
        "why": {
            "headline": readiness_payload.get("explanation") or "Readiness and recent training drive today's session.",
            "rationale": list(rec.get("rationale") or []),
            "decision_factors": list(rec.get("decision_factors") or []),
            "note": "Decision Trace is a deterministic explanation, not model chain-of-thought.",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "backend.services.readiness_service + training_service",
    }


@router.post("/check-in", response_model=TodayResponse)
def check_in(payload: CheckInRequest) -> dict[str, Any]:
    profile = _profile_or_404(payload.profile_id)
    check_in_values = payload.model_dump(exclude_none=True, exclude={"profile_id", "scenario"})
    check_in = readiness_service.build_check_in(profile, check_in_values, payload.scenario)
    assessment = readiness_service.assess(profile, check_in)
    rec = training_service.recommend(profile, assessment)
    readiness_payload = readiness_service.summary(profile, assessment)
    return {
        "profile": _profile_summary(profile),
        "readiness": readiness_payload,
        "training": {"recommendation": training_service.summary(rec),
                     "decision_trace": training_service.decision_trace(rec)},
        "why": {"headline": readiness_payload.get("explanation") or "Readiness and recent training drive today's session.",
                "rationale": list(rec.get("rationale") or []),
                "decision_factors": list(rec.get("decision_factors") or []),
                "note": "Decision Trace is a deterministic explanation, not model chain-of-thought."},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "backend.services.readiness_service + training_service",
    }


@router.post("/coach/message", response_model=CoachMessageResponse)
def coach_message(payload: CoachMessageRequest) -> dict[str, Any]:
    profile, assessment, rec = _context(payload.profile_id)
    history = [{"role": turn.role, "content": turn.content} for turn in payload.history]
    return coach_service.answer(payload.question, profile, assessment, rec, history)
