"""In-session calibration orchestration.

Orchestration only: the rule itself lives in ``session_calibration`` and the
readiness / recommendation / personal-response numbers keep coming from the same
engines the rest of the product uses. Nothing here is a second decision model.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import session_calibration
from backend.services import readiness_service, response_service, state_service, training_service


def _context(state: state_service.UserState) -> dict[str, Any]:
    """Everything calibration needs, computed by the existing engines."""
    profile = state_service.materialise(state)
    draft = state_service.check_in_draft(state, profile)
    assessment = readiness_service.assess(profile, draft)
    recommendation = training_service.recommend(profile, assessment)
    decision = response_service.evaluate(profile, assessment, recommendation)
    base_summary = training_service.summary(recommendation)
    summary = response_service.apply_to_summary(base_summary, decision, base_summary.get("rir_guidance"))
    return {
        "profile": profile,
        "draft": draft,
        "assessment": assessment,
        "recommendation": recommendation,
        "decision": decision,
        "summary": summary,
    }


def plan(context: Mapping[str, Any]) -> dict[str, Any]:
    """The starting guidance an active session is opened with."""
    summary = dict(context["summary"])
    decision = dict(context["decision"])
    return {
        "prescription_id": summary.get("prescription_id"),
        "primary_focus": summary.get("primary_name"),
        "session_demand": summary.get("session_demand"),
        "base_session_demand": summary.get("base_session_demand"),
        "adjustment": int(decision.get("adjustment") or 0),
        "planned_rir": summary.get("rir_guidance"),
        "duration": summary.get("duration"),
        "muscle_groups": list(summary.get("muscle_groups") or []),
    }


def start(state: state_service.UserState, prescription_id: str | None = None) -> dict[str, Any]:
    """Open the active session (an explicit choice of alternative is preserved)."""
    context = _context(state)
    opened = plan(context)
    if prescription_id:
        opened["prescription_id"] = prescription_id
    new_state = state_service.start_active_session(state, opened)
    return {
        "state": new_state,
        "active_session": new_state.active_session,
        "session_trace": session_calibration.session_trace(context["decision"], opened.get("planned_rir")),
        "context": context,
    }


def checkpoint(state: state_service.UserState, observation: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one checkpoint and store it on the active session."""
    context = _context(state)
    opened = plan(context)
    active = dict(state.active_session or {})
    # Prefer the guidance the session was actually started with, so a checkpoint is
    # always compared with the plan the user saw.
    planned_rir = active.get("planned_rir") or opened.get("planned_rir")
    if active.get("primary_focus"):
        opened["primary_focus"] = active.get("primary_focus")
    if active.get("session_demand"):
        opened["session_demand"] = active.get("session_demand")

    result = session_calibration.checkpoint(
        observation,
        planned_rir,
        context["assessment"].get("overall_readiness"),
        context["assessment"].get("safety_flags") or [],
        context["draft"].get("local_soreness") or {},
    )
    event = session_calibration.calibration_event(result, opened, date.today())
    new_state = state_service.attach_calibration(state, event)
    return {
        "state": new_state,
        "calibration": result,
        "event": event,
        "session_trace": session_calibration.session_trace(context["decision"], planned_rir, result),
        "context": context,
    }


def session_trace(state: state_service.UserState) -> list[dict[str, Any]]:
    """The session's own trace, including whatever has been recorded so far."""
    context = _context(state)
    active = dict(state.active_session or {})
    calibration = (active.get("calibration") or {}).get("result") and active.get("calibration")
    return session_calibration.session_trace(context["decision"], active.get("planned_rir") or
                                             context["summary"].get("rir_guidance"), calibration)


def history(state: state_service.UserState) -> list[dict[str, Any]]:
    """Recorded calibration events, oldest first, read from the sessions themselves."""
    rows: list[dict[str, Any]] = []
    for row in (state.training_history or []):
        payload = row.model_dump() if hasattr(row, "model_dump") else dict(row)
        calibration = payload.get("response_calibration")
        if calibration:
            rows.append(dict(calibration))
    active = dict(state.active_session or {})
    if active.get("calibration"):
        rows.append(dict(active["calibration"]))
    rows.sort(key=lambda row: str(row.get("recorded_at") or row.get("date") or ""))
    return rows


def summary(state: state_service.UserState) -> dict[str, Any]:
    return session_calibration.summarise(history(state))


def answer_question(state: state_service.UserState, question: str) -> str | None:
    return session_calibration.answer_question(question, history(state))
