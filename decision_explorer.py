"""V1.3 — What-if / Decision Explorer (final sprint).

A small, transparent rule explorer. It answers one question:

    "如果这个条件不同，当前规则会如何决策？"
    "Under the current rules, if this one condition were different, what would
     the product decide?"

It is **not** a second recommendation model and **not** a predictor:

* the alternative is produced by the *same* deterministic engines
  (``readiness_engine`` → ``training_recommendation_engine`` → ``adaptive_response``),
  with exactly one input changed,
* nothing is written back: no profile edit, no check-in, no session, no Response
  Episode, no Personal Response and no adaptation history is touched,
* it never claims what *will* happen, only what the current rules would decide.

This module holds the lever vocabulary and the comparison logic only; the
recomputation lives in ``backend.services.explorer_service``.
"""

from __future__ import annotations

from typing import Any, Mapping


#: How sore a simulated muscle group becomes, on the product's own 1–5 scale.
DEFAULT_SORENESS_LEVEL = 4

#: The one input each lever changes. Kept deliberately small and reviewable.
LEVERS: tuple[dict[str, Any], ...] = (
    {
        "key": "soreness",
        "label": "More local soreness",
        "description": "What if one muscle group were sorer than you reported this morning?",
        "change_summary": "Higher local soreness",
        "needs_group": True,
    },
    {
        "key": "recovery",
        "label": "A poorer recovery night",
        "description": "What if last night had been shorter, with higher fatigue and a lower HRV reading?",
        "change_summary": "A poorer recovery night",
        "needs_group": False,
    },
    {
        "key": "personal_response",
        "label": "No recent poorer-response history",
        "description": "What if the recent poorer-response episodes were not in your history?",
        "change_summary": "No recent poorer-response history",
        "needs_group": False,
    },
)

_BY_KEY = {lever["key"]: lever for lever in LEVERS}

#: Fields compared between the current and the alternative decision.
COMPARED_FIELDS: tuple[tuple[str, str], ...] = (
    ("readiness_status", "Readiness status"),
    ("readiness_index", "Readiness index"),
    ("session_demand", "How hard (final demand)"),
    ("base_session_demand", "How hard (base demand)"),
    ("primary_focus", "Primary session"),
    ("rir_guidance", "Effort guidance"),
    ("personal_response_adjustment", "Personal Response"),
)

NOTE = ("Under the current rules, if this one condition were different, the recommendation would change as shown. "
        "This is a rule explorer, not a prediction of what will happen.")

READ_ONLY_NOTE = ("Simulation only: your saved profile, check-ins, sessions, Response Episodes, Personal Response "
                  "and adaptation history are not changed.")


def levers() -> list[dict[str, Any]]:
    """The lever vocabulary the UI renders."""
    return [dict(lever) for lever in LEVERS]


def lever(key: Any) -> dict[str, Any] | None:
    found = _BY_KEY.get(str(key or ""))
    return dict(found) if found else None


def default_change(key: str, group: str | None = None) -> dict[str, Any]:
    """The default value a lever uses when the UI does not supply one."""
    if key == "soreness":
        return {"key": "soreness", "group": group, "level": DEFAULT_SORENESS_LEVEL}
    return {"key": key}


def snapshot(assessment: Mapping[str, Any], recommendation: Mapping[str, Any],
             decision: Mapping[str, Any], summary: Mapping[str, Any]) -> dict[str, Any]:
    """The compact decision view the explorer compares (never a full payload)."""
    confidence = dict(decision.get("confidence") or {})
    adjustment = int(decision.get("adjustment") or 0)
    if adjustment:
        personal = f"Adjusted {decision.get('base_band')} → {decision.get('final_band')}"
    elif (decision.get("within_tier") or {}).get("available"):
        personal = "Within-tier guidance, no tier change"
    else:
        personal = "No adjustment"
    return {
        "readiness_status": assessment.get("overall_readiness"),
        "readiness_index": assessment.get("readiness_index"),
        "session_demand": summary.get("session_demand"),
        "base_session_demand": summary.get("base_session_demand"),
        "primary_focus": summary.get("primary_name") or (recommendation.get("primary") or {}).get("name"),
        "rir_guidance": summary.get("rir_guidance"),
        "personal_response_adjustment": personal,
        "personal_response_confidence": confidence.get("state"),
        "adjustment": adjustment,
    }


def differences(current: Mapping[str, Any], alternative: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Which of the compared fields actually changed, in a fixed order."""
    changed: list[dict[str, Any]] = []
    for key, label in COMPARED_FIELDS:
        before, after = current.get(key), alternative.get(key)
        if before == after:
            continue
        changed.append({"key": key, "label": label, "current": before, "alternative": after})
    return changed


def comparison(current: Mapping[str, Any], alternative: Mapping[str, Any],
               change: Mapping[str, Any], rationale: list[str]) -> dict[str, Any]:
    """The full explorer result: current, changed input, alternative, why."""
    found = lever(change.get("key")) or {}
    changed = differences(current, alternative)
    if current.get("session_demand") == alternative.get("session_demand"):
        conclusion = ("Under the current rules this single change would not alter today's session demand."
                      if not changed else
                      "Under the current rules this single change would not alter today's session demand; "
                      "the differences below are the reason.")
    else:
        conclusion = (f"Under the current rules this single change would move today's session demand from "
                      f"{current.get('session_demand')} to {alternative.get('session_demand')}.")
    return {
        "lever": found.get("key"),
        "lever_label": found.get("label"),
        "changed_input": found.get("change_summary"),
        "change": {key: value for key, value in dict(change).items() if key != "key"},
        "current": dict(current),
        "alternative": dict(alternative),
        "differences": changed,
        "changed": bool(changed),
        "conclusion": conclusion,
        "why": list(rationale or []),
        "note": NOTE,
        "read_only_note": READ_ONLY_NOTE,
    }
