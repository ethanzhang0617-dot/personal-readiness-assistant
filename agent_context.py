"""V1.4 — Structured Agent Context and conservative Agent Memory.

This is **not** free-form model memory. Every field below is a bounded,
read-only projection of state the product already stores and already shows:
readiness, the recommendation, weekly exposure, recent completed sessions,
training load, local soreness, Personal Response, Recommendation Confidence,
recorded calibrations, post-session feedback and the user's own profile settings.

Two explicit refusals define the module:

* the context contains **no** inferred personality, motivation, health status or
  recovery judgement — nothing like "the user recovers badly" can be produced
  here, because no field has that shape;
* the memory contains **no** model-written text at all. Long-term memory is the
  product's own persisted history (sessions, check-ins, response episodes,
  calibration events, adaptation events), summarised with counts and dates.

``context_digest`` renders the same structure as a compact, unit-bearing summary
for a prompt. It is deliberately short: the planner and the final answer get a
structured digest instead of a raw history dump.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

import ai_facts
from backend.services import response_service, training_service


MAX_RECENT_SESSIONS = 5
MAX_ADAPTATION_EVENTS = 8
MAX_EPISODE_ROWS = 5


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    return {}


def _history_rows(state: Any) -> list[dict[str, Any]]:
    rows = getattr(state, "training_history", None)
    if rows is None and isinstance(state, Mapping):
        rows = state.get("training_history")
    return [_as_dict(row) for row in (rows or [])]


def _adaptation_rows(state: Any) -> list[dict[str, Any]]:
    rows = getattr(state, "adaptation_log", None)
    if rows is None and isinstance(state, Mapping):
        rows = state.get("adaptation_log")
    return [_as_dict(row) for row in (rows or [])]


def _calibration_rows(state: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _history_rows(state):
        calibration = row.get("response_calibration")
        if calibration:
            rows.append(_as_dict(calibration))
    active = _active_session(state)
    if active.get("calibration"):
        rows.append(_as_dict(active["calibration"]))
    return rows


def _active_session(state: Any) -> dict[str, Any]:
    """The unfinished session, whether the caller sent a state object or a mapping."""
    if state is None:
        return {}
    if isinstance(state, Mapping):
        return _as_dict(state.get("active_session"))
    return _as_dict(getattr(state, "active_session", None))


def _response_feedback(state: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _history_rows(state):
        feedback = row.get("response_feedback")
        if feedback:
            rows.append({"date": row.get("date"), "focus": row.get("primary_focus") or row.get("training_type"),
                         "feedback": _as_dict(feedback)})
    rows.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    return rows[:3]


# --------------------------------------------------------------------------- #
# Structured context
# --------------------------------------------------------------------------- #


def build_agent_context(profile: Mapping[str, Any], assessment: Mapping[str, Any],
                        recommendation: Mapping[str, Any], decision: Mapping[str, Any] | None = None,
                        state: Any | None = None, today: date | None = None) -> dict[str, Any]:
    """The verified structured context one user turn is answered from."""
    day = today or date.today()
    decision = dict(decision or {})
    facts = ai_facts.build_personal_facts(dict(profile), dict(assessment), dict(recommendation), day)
    summary = training_service.summary(dict(recommendation))
    final = response_service.apply_to_summary(summary, decision, summary.get("rir_guidance")) if decision else summary
    response_payload = response_service.payload(decision) if decision else {}
    response_summary = dict(response_payload.get("summary") or {})
    confidence = dict(decision.get("confidence") or {})
    calibrations = _calibration_rows(state) if state is not None else []
    load = dict(facts["training_load"])
    active = _active_session(state)

    return {
        "as_of": day.isoformat(),
        "readiness": {
            "status": facts["readiness"]["status"],
            "index": facts["readiness"]["index"],
            "index_scale": dict(facts["readiness"]["index_scale"]),
            "confidence": facts["readiness"]["confidence"],
            "domains": dict(facts["readiness"]["domains"]),
            "contributors": list(facts["readiness"]["contributors"])[:2],
            "safety_flags": list(facts["readiness"]["safety_flags"]),
        },
        "recommendation": {
            "primary": final.get("primary_name"),
            "training_type": final.get("training_type"),
            "session_demand": final.get("session_demand"),
            "base_session_demand": final.get("base_session_demand"),
            "duration": final.get("duration"),
            "rir_guidance": final.get("rir_guidance"),
            "alternatives": [row.get("name") for row in (final.get("alternatives") or [])][:3],
            "avoid": list(final.get("avoid") or [])[:4],
            "rationale": list(final.get("rationale") or [])[:3],
            "source": "training_recommendation_engine.recommend_training",
        },
        "personal_response": {
            "available": response_payload.get("available"),
            "base_band": response_payload.get("base_band"),
            "final_band": response_payload.get("final_band"),
            "adjustment": response_payload.get("adjustment"),
            "direction": response_payload.get("direction"),
            "evidence": response_payload.get("evidence"),
            "reason": response_payload.get("reason"),
            "confidence_state": response_payload.get("confidence_state"),
            "episodes_complete": response_summary.get("episodes_complete"),
            "source": "adaptive_response.evaluate",
        },
        "recommendation_confidence": {
            "state": confidence.get("state"),
            "label": confidence.get("label"),
            "relevant_episodes": confidence.get("relevant_episodes"),
            "source": "adaptive_response.recommendation_confidence",
        },
        "recent_sessions": [
            {"date": row.get("date"), "focus": row.get("focus"), "session_rpe": row.get("session_rpe"),
             "duration_min": row.get("duration_min"), "working_sets": row.get("working_sets")}
            for row in training_service.recent_sessions(dict(profile), MAX_RECENT_SESSIONS)
        ],
        "weekly_exposure": {
            "period": facts["weekly_exposure"]["period"],
            "unit": "weighted working sets",
            "groups": [
                {"group": group, "value": float((entry or {}).get("value") or 0), "target": (entry or {}).get("target")}
                for group, entry in facts["weekly_exposure"]["groups"].items()
            ],
            "completed_sessions": facts["weekly_sessions"]["value"],
            "training_days": facts["weekly_training_days"]["value"],
        },
        "training_load": {
            "value": load.get("value"),
            "unit": "Training Load Points (pts)",
            "reference_value": load.get("reference_value"),
            "period": load.get("period"),
            "status": load.get("status"),
        },
        "local_soreness": {
            "groups": dict(facts["local_soreness"]["groups"]),
            "subjective": facts["local_soreness"]["subjective_soreness"],
        },
        "calibration": {
            "recorded": len(calibrations),
            "latest_result": (calibrations[-1].get("result") if calibrations else None),
            "active_session": {
                "primary_focus": active.get("primary_focus"),
                "planned_rir": active.get("planned_rir"),
            } if active else None,
            "source": "session_calibration",
        },
        "profile": {
            "goal": profile.get("training_goal"),
            "training_level": profile.get("training_level"),
            "programme_split": profile.get("training_split_preference"),
            "target_sessions_per_week": profile.get("target_sessions_per_week"),
            "weekly_set_targets": {str(key): value for key, value in (profile.get("weekly_set_targets") or {}).items()},
        },
        "memory": build_agent_memory(profile, state=state, today=day),
        "note": ("Structured projection of stored product state. It contains no inferred personality, health or "
                 "recovery judgement."),
    }


def build_agent_memory(profile: Mapping[str, Any], state: Any | None = None,
                       today: date | None = None) -> dict[str, Any]:
    """Conservative long-term memory: counts, dates and recorded values only."""
    day = today or date.today()
    sessions = [row for row in (profile.get("training_history") or []) if row.get("completed", True)]
    check_ins = [row for row in (profile.get("daily_history") or profile.get("history") or []) if row.get("date")]
    adaptations = _adaptation_rows(state) if state is not None else []
    calibrations = _calibration_rows(state) if state is not None else []
    feedback = _response_feedback(state) if state is not None else []
    return {
        "recorded_sessions": len(sessions),
        "recorded_check_ins": len(check_ins),
        "first_recorded_date": min((str(row.get("date")) for row in sessions + check_ins), default=None),
        "adaptation_events": [
            {"date": row.get("date"), "base_band": row.get("base_band"), "final_band": row.get("final_band"),
             "adjustment": row.get("adjustment"), "reason": row.get("reason")}
            for row in adaptations[-MAX_ADAPTATION_EVENTS:]
        ],
        "calibration_events": len(calibrations),
        "recent_post_session_feedback": [
            {"date": row.get("date"), "focus": row.get("focus"),
             "difficulty": (row.get("feedback") or {}).get("difficulty"),
             "performance": (row.get("feedback") or {}).get("performance"),
             "completion": (row.get("feedback") or {}).get("completion")}
            for row in feedback[:MAX_EPISODE_ROWS]
        ],
        "profile_settings": {
            "goal": profile.get("training_goal"),
            "programme_split": profile.get("training_split_preference"),
            "target_sessions_per_week": profile.get("target_sessions_per_week"),
        },
        "as_of": day.isoformat(),
        "note": ("Memory is the product's own persisted history. It stores no model-written text and no inferred "
                 "trait, and it is retrieved through tools rather than recalled by the model."),
    }


# --------------------------------------------------------------------------- #
# Prompt-facing digest
# --------------------------------------------------------------------------- #


def context_digest(context: Mapping[str, Any]) -> str:
    """A compact, unit-bearing digest. Never a raw history dump."""
    readiness = context.get("readiness") or {}
    recommendation = context.get("recommendation") or {}
    exposure = context.get("weekly_exposure") or {}
    response = context.get("personal_response") or {}
    confidence = context.get("recommendation_confidence") or {}
    calibrations = context.get("calibration") or {}
    soreness = (context.get("local_soreness") or {}).get("groups") or {}
    groups = "; ".join(
        f"{row.get('group')} {row.get('value'):g}"
        + (f" (target {row.get('target'):g})" if row.get("target") else "")
        for row in (exposure.get("groups") or [])[:4]
    )
    soreness_text = ", ".join(f"{group} {value}/5" for group, value in soreness.items()) or "not reported"
    return "\n".join([
        (f"Readiness: {readiness.get('status')} "
         f"(index {readiness.get('index')} on a 0-100 scale, confidence {readiness.get('confidence')}); "
         f"domains {readiness.get('domains')}."),
        (f"Today's recommendation: {recommendation.get('primary')} at {recommendation.get('session_demand')} demand, "
         f"{recommendation.get('duration')}, {recommendation.get('rir_guidance')} "
         f"(engine base demand {recommendation.get('base_session_demand')})."),
        (f"Weekly exposure for {exposure.get('period')} in weighted working sets: {groups or 'not available'}; "
         f"{exposure.get('completed_sessions')} completed sessions on {exposure.get('training_days')} days."),
        (f"Personal Response: adjustment {response.get('adjustment')}, {response.get('base_band')} -> "
         f"{response.get('final_band')}, evidence {response.get('evidence')}, "
         f"response confidence {response.get('confidence_state')}."),
        (f"Recommendation Confidence: {confidence.get('state')} ({confidence.get('label')}, "
         f"{confidence.get('relevant_episodes')} relevant episodes)."),
        (f"Local soreness today: {soreness_text}. Calibration events recorded: {calibrations.get('recorded')} "
         f"(latest {calibrations.get('latest_result')})."),
    ])


def bounded_history(history: Sequence[Mapping[str, str]], max_messages: int, max_chars: int) -> list[dict[str, str]]:
    """The bounded conversation window the planner and the answer both receive."""
    rows = [dict(row) for row in history if row.get("role") in {"user", "assistant"}]
    trimmed = rows[-max_messages:]
    return [{"role": str(row.get("role")), "content": str(row.get("content", ""))[:max_chars]} for row in trimmed]
