"""What-if / Decision Explorer orchestration.

Recomputes the decision through the *same* engines with exactly one input changed.
Read-only by construction: the function receives a state, deep-copies what it
needs, and returns a comparison — it never returns a state for the client to
persist, so a simulation cannot leak into saved data.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import decision_explorer
from backend.services import readiness_service, response_service, state_service, training_service


def levers() -> list[dict[str, Any]]:
    return decision_explorer.levers()


def _evaluate(profile: Mapping[str, Any], draft: Mapping[str, Any]) -> dict[str, Any]:
    assessment = readiness_service.assess(profile, draft)
    recommendation = training_service.recommend(profile, assessment)
    decision = response_service.evaluate(profile, assessment, recommendation)
    base_summary = training_service.summary(recommendation)
    summary = response_service.apply_to_summary(base_summary, decision, base_summary.get("rir_guidance"))
    return {
        "snapshot": decision_explorer.snapshot(assessment, recommendation, decision, summary),
        "rationale": list(summary.get("rationale") or []),
        "assessment": assessment,
        "summary": summary,
    }


def _default_group(summary: Mapping[str, Any]) -> str | None:
    groups = [group for group in (summary.get("muscle_groups") or []) if group]
    if groups:
        return str(groups[0])
    avoid = summary.get("avoid") or []
    return str(avoid[0]) if avoid else None


def _apply(profile: dict[str, Any], draft: dict[str, Any], change: Mapping[str, Any],
           summary: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Change exactly one input and report what it was."""
    key = str(change.get("key") or "")
    if key == "soreness":
        group = str(change.get("group") or _default_group(summary) or "Quads")
        level = int(change.get("level") or decision_explorer.DEFAULT_SORENESS_LEVEL)
        level = max(1, min(5, level))
        draft["local_soreness"] = {**(draft.get("local_soreness") or {}), group: level}
        return profile, draft, f"{group} soreness set to {level}/5"

    if key == "recovery":
        sleep = float(draft.get("sleep_hours") or 8.0)
        quality = int(draft.get("sleep_quality") or 4)
        draft["sleep_hours"] = round(max(3.0, sleep - 1.5), 1)
        draft["sleep_quality"] = min(quality, 2)
        draft["fatigue"] = min(5, int(draft.get("fatigue") or 1) + 1)
        draft["soreness"] = min(5, int(draft.get("soreness") or 1) + 1)
        rmssd = draft.get("rmssd_ms")
        if rmssd is not None:
            draft["rmssd_ms"] = round(float(rmssd) * 0.9, 1)
        return profile, draft, "1.5 h less sleep, lower HRV, higher fatigue"

    if key == "personal_response":
        # Removing the recorded response data makes today's evaluation see no
        # response history at all — the base (engine) decision is untouched.
        removed = 0
        for row in profile.get("training_history") or []:
            if row.pop("response_context", None) is not None or row.pop("response_feedback", None) is not None:
                removed += 1
        return profile, draft, (f"{removed} recorded response episode"
                                f"{'' if removed == 1 else 's'} ignored" if removed
                                else "no recorded response history to ignore")

    return profile, draft, "unchanged"


def explore(state: state_service.UserState, change: Mapping[str, Any]) -> dict[str, Any]:
    """Current decision vs the same decision with one input changed."""
    key = str(change.get("key") or "")
    found = decision_explorer.lever(key)
    if found is None:
        raise ValueError(f"Unknown what-if lever: {key}")

    profile = state_service.materialise(state)
    draft = dict(state_service.check_in_draft(state, profile))
    current = _evaluate(profile, draft)

    alt_profile = deepcopy(profile)
    alt_draft = dict(draft)
    resolved = dict(change)
    alt_profile, alt_draft, changed_input = _apply(alt_profile, alt_draft, resolved, current["summary"])
    if key == "soreness":
        resolved["group"] = str(resolved.get("group") or _default_group(current["summary"]) or "Quads")
        resolved["level"] = int(resolved.get("level") or decision_explorer.DEFAULT_SORENESS_LEVEL)
    alternative = _evaluate(alt_profile, alt_draft)

    result = decision_explorer.comparison(current["snapshot"], alternative["snapshot"], resolved,
                                          alternative["rationale"])
    result["changed_input"] = changed_input
    result["current_view"] = {
        "readiness_why": list(current["assessment"].get("why_this_status") or []),
        "rationale": current["rationale"],
    }
    result["alternative_view"] = {
        "readiness_why": list(alternative["assessment"].get("why_this_status") or []),
        "rationale": alternative["rationale"],
    }
    return result
