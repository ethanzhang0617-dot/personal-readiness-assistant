"""Readiness orchestration. The formula itself stays in ``readiness_engine``."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping

from readiness_engine import STOP, assess_readiness

from backend.services import demo_service


_DOMAIN_LABELS = {
    "autonomic": "Autonomic",
    "sleep": "Sleep & Recovery",
    "subjective": "Subjective Wellness",
    "training_load": "Training Load",
}

_CONFIDENCE_NOTES = {
    "NORMAL": "Enough valid paired observations for a personal baseline.",
    "LIMITED": "Limited valid observations; the baseline is still settling.",
    "INSUFFICIENT": "Not enough valid observations for a personal comparison yet.",
}

_CHECK_IN_FIELDS = ("rmssd_ms", "resting_hr_bpm", "sleep_hours", "sleep_quality",
                    "fatigue", "soreness", "stress", "motivation", "local_soreness", "safety_flags")


def build_check_in(profile: Mapping[str, Any], overrides: Mapping[str, Any] | None = None,
                   scenario: str | None = None) -> dict[str, Any]:
    """Demo check-in with explicit overrides applied on top."""
    draft = demo_service.scenario_values(profile, scenario) if scenario else demo_service.default_check_in(profile)
    for field in _CHECK_IN_FIELDS:
        if overrides and overrides.get(field) is not None:
            draft[field] = overrides[field]
    draft["date"] = date.today().isoformat()
    return draft


def assess(profile: Mapping[str, Any], check_in: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run the existing engine. No threshold, aggregation or scoring logic lives here."""
    draft = deepcopy(check_in) if check_in else build_check_in(profile)
    draft["date"] = str(draft.get("date") or date.today().isoformat())
    return assess_readiness(draft, profile["history"], profile["personal_sleep_need"], profile["assessments"])


def summary(profile: Mapping[str, Any], assessment: Mapping[str, Any]) -> dict[str, Any]:
    domains = assessment.get("domains") or {}
    confidence = assessment.get("assessment_confidence")
    return {
        "status": assessment.get("overall_readiness"),
        "status_label": str(assessment.get("overall_readiness") or "").title(),
        "index": assessment.get("readiness_index"),
        "index_scale": {"min": 0, "max": 100},
        "confidence": confidence,
        "confidence_note": _CONFIDENCE_NOTES.get(str(confidence), None),
        "domains": [{"key": key, "label": _DOMAIN_LABELS.get(key, key.title()), "status": value}
                    for key, value in domains.items()],
        "contributors": list(assessment.get("key_contributors") or []),
        "explanation": next(iter(assessment.get("why_this_status") or []), None),
        "why_this_status": list(assessment.get("why_this_status") or []),
        "decision_support": list(assessment.get("decision_support") or []),
        "safety_active": assessment.get("overall_readiness") == STOP,
        "safety_flags": list(assessment.get("safety_flags") or []),
        "limitations": list(assessment.get("limitations") or []),
        "measurements": dict(assessment.get("measurements") or {}),
        "baseline": dict(assessment.get("baseline") or {}),
        "check_in": {key: value for key, value in (assessment.get("today_data") or {}).items()
                     if key in _CHECK_IN_FIELDS or key == "date"},
        "assessment_date": assessment.get("assessment_date"),
        "source": "readiness_engine.assess_readiness",
    }


def assess_and_summarise(profile: Mapping[str, Any], check_in: Mapping[str, Any] | None = None
                         ) -> tuple[dict[str, Any], dict[str, Any]]:
    assessment = assess(profile, check_in)
    return assessment, summary(profile, assessment)
