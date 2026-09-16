"""Training orchestration. Session selection stays in the recommendation engine."""

from __future__ import annotations

from typing import Any, Mapping

import ai_facts
from training_recommendation_engine import prescription_log_defaults, recommend_training, workout_template

from backend.services import demo_service


_EXPOSURE_NOTE = ("Weighted working sets over the last seven days including today. "
                  "Direct sets count 1.0 and mapped secondary sets 0.5; not days and not sessions.")


def _duration_range(value: Any) -> list[int] | None:
    """The engine describes the session window as a start/end pair."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        numbers = [int(item) for item in value if item is not None]
        return numbers or None
    return [int(value), int(value)]


def rir_guidance(recommendation: Mapping[str, Any]) -> str | None:
    """Reuse the Streamlit wording so both surfaces never disagree."""
    from app import rir_guidance as _rir_guidance

    return _rir_guidance(dict(recommendation.get("primary") or {}))


def recommend(profile: Mapping[str, Any], assessment: Mapping[str, Any]) -> dict[str, Any]:
    return recommend_training(dict(profile), assessment, list(profile.get("training_history") or []))


def summary(recommendation: Mapping[str, Any]) -> dict[str, Any]:
    primary = dict(recommendation.get("primary") or {})
    exercises = [{"name": item.get("name"), "sets": item.get("working_sets", item.get("sets")),
                  "reps": item.get("reps"), "rir": item.get("rir")}
                 for item in (primary.get("exercises") or [])]
    alternatives = [_session_summary(item) for item in (recommendation.get("alternatives") or [])]
    return {
        "primary_name": primary.get("name"),
        "prescription_id": primary.get("prescription_id"),
        "training_type": primary.get("training_type"),
        "focus": primary.get("focus"),
        "split": primary.get("split"),
        "muscle_groups": list(primary.get("muscle_groups") or []),
        "session_demand": recommendation.get("intensity"),
        "duration": recommendation.get("duration"),
        "estimated_duration_min_range": _duration_range(primary.get("estimated_duration_min")),
        "rir_guidance": rir_guidance(recommendation),
        "exercises": exercises,
        "alternatives": alternatives,
        "avoid": list(recommendation.get("avoid") or []),
        "rationale": list(recommendation.get("rationale") or []),
        "priority": {str(key): list(value) for key, value in (recommendation.get("priority") or {}).items()},
        "volume_modifier": recommendation.get("volume_modifier"),
        "target_source": recommendation.get("target_source"),
        "template": dict(recommendation.get("template") or {}),
        "log_defaults": _log_defaults(primary),
        "source": "training_recommendation_engine.recommend_training",
    }


def _log_defaults(prescription: Mapping[str, Any]) -> dict[str, Any]:
    """Per-exercise defaults for the completed-session form, straight from the engine."""
    if not prescription.get("prescription_id"):
        return {"exercises": [], "prescribed_sets": 0}
    defaults = prescription_log_defaults(dict(prescription))
    return {
        "exercises": [{"name": item["name"], "prescribed_sets": item["prescribed_sets"]}
                      for item in defaults.get("exercises", [])],
        "prescribed_sets": defaults.get("prescribed_sets", 0),
    }


def _session_summary(session: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": session.get("name"),
        "prescription_id": session.get("prescription_id"),
        "training_type": session.get("training_type"),
        "focus": session.get("focus"),
        "muscle_groups": list(session.get("muscle_groups") or []),
        "intensity": session.get("intensity"),
        "duration": session.get("duration"),
        "reason": session.get("reason"),
        "template": dict(workout_template(dict(session)) or {}),
        "log_defaults": _log_defaults(session),
    }


def find_session(recommendation: Mapping[str, Any], prescription_id: str | None) -> dict[str, Any]:
    """Resolve a selected prescription id to the primary or an alternative."""
    choices = [dict(recommendation.get("primary") or {}), *[dict(item) for item in (recommendation.get("alternatives") or [])]]
    for choice in choices:
        if choice.get("prescription_id") and choice.get("prescription_id") == prescription_id:
            return choice
    return choices[0]


def exposure(profile: Mapping[str, Any], assessment: Mapping[str, Any],
             recommendation: Mapping[str, Any]) -> dict[str, Any]:
    """Exposure values come from the read-only fact projection, not a new formula."""
    facts = ai_facts.build_personal_facts(dict(profile), assessment, dict(recommendation))
    entry = facts["weekly_exposure"]
    groups = [{"group": group, "value": float(item.get("value") or 0),
               "target": item.get("target"), "unit": "weighted working sets", "status": None}
              for group, item in entry["groups"].items()]
    return {
        "period": entry["period"],
        "unit": "weighted working sets",
        "target_source": entry.get("target_source"),
        "groups": groups,
        "note": _EXPOSURE_NOTE,
        "source": entry.get("source", "training_recommendation_engine.weekly_training_exposure"),
    }


def recent_sessions(profile: Mapping[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """Completed sessions, newest first. Read-only projection of stored history."""
    rows = [row for row in (profile.get("training_history") or []) if row.get("completed")]
    rows.sort(key=lambda row: str(row.get("date")), reverse=True)
    sessions = []
    for row in rows[:limit]:
        sessions.append({
            "date": row.get("date"),
            "focus": row.get("primary_focus") or row.get("training_type"),
            "training_type": row.get("training_type"),
            "session_rpe": row.get("session_rpe"),
            "duration_min": row.get("duration_min"),
            "working_sets": row.get("actual_sets") if row.get("actual_sets") is not None else row.get("working_sets"),
        })
    return sessions


def decision_trace(recommendation: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"index": index, "step": str(item.get("step")), "value": str(item.get("value")),
             "source": "deterministic"}
            for index, item in enumerate(recommendation.get("decision_trace") or [], start=1)]
