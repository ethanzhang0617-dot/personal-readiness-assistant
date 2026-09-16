"""Training orchestration. Session selection stays in the recommendation engine."""

from __future__ import annotations

from typing import Any, Mapping

import ai_facts
from training_recommendation_engine import recommend_training

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
    alternatives = [{"name": item.get("name"), "training_type": item.get("training_type"),
                     "focus": item.get("focus"), "muscle_groups": list(item.get("muscle_groups") or []),
                     "intensity": item.get("intensity"), "duration": item.get("duration"),
                     "reason": item.get("reason")}
                    for item in (recommendation.get("alternatives") or [])]
    return {
        "primary_name": primary.get("name"),
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
        "source": "training_recommendation_engine.recommend_training",
    }


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
