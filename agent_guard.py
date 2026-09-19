"""V1.4 — Grounding and safety validation for Agent answers.

The Agent never owns a training decision. After DeepSeek writes the wording, this
module proves that the wording stayed inside what the deterministic system had
already decided:

* **numbers** must exist in the verified facts or in a tool result from this turn
  (so the model cannot invent a readiness index, a set count, a load value or a
  period),
* **units and periods** keep the product's own meanings (training load is points,
  exposure is weighted working sets, duration is minutes),
* **the recommendation is not overridden**: an asserted session-demand tier must
  be the tier the deterministic engine produced,
* **safety keeps precedence**: when the deterministic system reported a safety
  restriction, the final answer must still carry it. The orchestrator never even
  sends a safety turn to the model; this is the second line of defence.

Nothing in this module computes a training value. It only accepts or rejects.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import ai_engine
import ai_facts
from readiness_engine import STOP


#: The demand tiers the deterministic engine can produce. A model may explain a
#: tier; it may not replace it with a different one.
DEMAND_TIERS: tuple[str, ...] = ("Normal", "Reduced strength", "Reduced / autoregulated", "Recovery",
                                 "Rest or lower-demand", "Lower-demand", "No normal training recommendation")

_SAFETY_ANCHORS: tuple[str, ...] = ("safety", "professional review", "medical", "urgent", "stop",
                                    "pause demanding training")


def merged_facts(facts: Mapping[str, Any], tool_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The verified fact projection plus this turn's successful tool results.

    The existing numeric guard walks the whole mapping, so every number the tools
    returned becomes licensed for the answer, and nothing else does.
    """
    merged = dict(facts)
    merged["agent_tool_results"] = {
        str(result.get("tool")): result.get("data")
        for result in tool_results
        if result.get("ok")
    }
    merged["agent_tool_status"] = {
        str(result.get("tool")): ("verified" if result.get("ok") else str(result.get("error") or "unavailable"))
        for result in tool_results
    }
    return merged


def guard_safety_precedence(text: str, assessment: Mapping[str, Any]) -> tuple[bool, str]:
    """A reported safety restriction must survive into the final answer."""
    status = str(assessment.get("overall_readiness") or "")
    flags = [str(flag) for flag in (assessment.get("safety_flags") or [])]
    if status != STOP and not flags:
        return True, "No safety restriction today"
    lowered = text.casefold()
    if any(anchor in lowered for anchor in _SAFETY_ANCHORS) or any(flag.casefold() in lowered for flag in flags):
        return True, "The safety restriction is preserved"
    return False, "The draft dropped the recorded safety restriction."


def _tier_in(claim: str) -> str | None:
    lowered = claim.casefold()
    if "autoregulat" in lowered:
        return "Reduced / autoregulated"
    if "reduced" in lowered and "strength" in lowered:
        return "Reduced strength"
    if lowered.startswith(("no normal",)):
        return "No normal training recommendation"
    if lowered.startswith("rest"):
        return "Rest or lower-demand"
    if lowered.startswith(("lower-demand", "lower demand")):
        return "Lower-demand"
    if lowered.startswith("recovery"):
        return "Recovery"
    if lowered.startswith("normal"):
        return "Normal"
    if lowered.startswith("reduced"):
        return "Reduced strength"
    return None


def _same_family(left: str, right: str) -> bool:
    """``Reduced strength`` and ``Reduced / autoregulated`` are one family."""
    return left.casefold().startswith("reduced") and right.casefold().startswith("reduced")


def guard_demand_authority(text: str, decision: Mapping[str, Any]) -> tuple[bool, str]:
    """The model explains the recorded demand tier; it does not replace it."""
    verified = str(decision.get("final_demand") or "").strip()
    if not verified:
        return True, "No session demand recorded to protect"
    lowered = text.casefold()
    claims = re.findall(r"(?:session demand|today'?s demand|demand)\s+is\s+(?:now\s+)?([a-z][a-z /-]{2,32})", lowered)
    for claim in claims:
        if claim.strip().startswith(("not ", "still ", "unchanged", "the same")):
            continue
        claimed = _tier_in(claim.strip())
        if claimed and claimed != verified and not _same_family(claimed, verified):
            return False, f"The draft replaced the recorded session demand ({verified}) with {claimed}."
    return True, "The recorded session demand is preserved"


def guard_agent_answer(text: str, question: str, facts: Mapping[str, Any],
                       tool_results: Sequence[Mapping[str, Any]],
                       assessment: Mapping[str, Any], decision: Mapping[str, Any],
                       route: ai_facts.Route | None = None,
                       recommendation: Mapping[str, Any] | None = None) -> tuple[bool, str]:
    """Accept or reject one model draft. Rejection falls back to verified data."""
    primary = ((recommendation or {}).get("primary") or {}).get("name")
    accepted, reason = ai_engine.validate_llm_response(
        text, str(assessment.get("overall_readiness") or ""), primary, question, recommendation)
    if not accepted:
        return False, reason
    accepted, reason = ai_facts.guard_llm_response(text, merged_facts(facts, tool_results), question, route)
    if not accepted:
        return False, reason
    if route is not None and route.kind == "EXPLANATION":
        accepted, reason = ai_facts.guard_explanation_grounding(text, facts)
        if not accepted:
            return False, reason
    accepted, reason = guard_safety_precedence(text, assessment)
    if not accepted:
        return False, reason
    accepted, reason = guard_demand_authority(text, decision)
    if not accepted:
        return False, reason
    return True, "Grounded in verified tool results and deterministic facts"
