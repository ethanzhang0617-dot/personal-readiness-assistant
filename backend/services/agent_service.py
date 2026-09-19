"""V1.4 — Coach entry point for the Agent layer.

The Coach route keeps its existing responsibilities (calibration questions and
Personal Response questions are still answered deterministically before anything
else) and then hands the turn to ``agent_orchestrator``. Nothing scientific is
implemented here: this module materialises the context, calls the orchestrator
and shapes the response the frontend contract already understands.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import agent_tools
import agent_orchestrator
from backend.services import coach_service


def verified_answer(text: str, notice: str | None = None, tools_used: Sequence[str] = (),
                    intent: str | None = None) -> dict[str, Any]:
    """A deterministic answer produced before the Agent layer runs.

    The tool trace still names the verified source, so the UI can show where the
    answer came from without pretending an Agent step happened.
    """
    payload = coach_service.verified_answer(text, notice)
    payload.update({
        "tools_used": _unique(tools_used),
        "tool_trace": _trace(tools_used),
        "grounded": True,
        "fallback_used": False,
        "agent": {
            "strategy": "deterministic_layer",
            "intent": intent,
            "plan_source": None,
            "steps": 0,
            "rejected": [],
            "planner_error": None,
            "limit_reached": False,
            "provider_seconds": None,
        },
    })
    return payload


def answer(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any],
           recommendation: Mapping[str, Any], decision: Mapping[str, Any] | None = None,
           state: Any | None = None, history: Sequence[Mapping[str, str]] = (),
           secrets: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One Coach turn through the Agent orchestrator."""
    result = agent_orchestrator.run(
        question=question,
        profile=profile,
        assessment=assessment,
        recommendation=recommendation,
        decision=decision,
        state=state,
        history=history,
        secrets=secrets if secrets is not None else coach_service.server_secrets(),
    )
    result["contract"] = coach_service.contract()
    return result


def personal_response_tools(question: str) -> list[str]:
    """The verified sources a deterministic Personal Response answer used."""
    lowered = str(question or "").casefold()
    if any(term in lowered for term in ("confid", "support", "how many sessions", "how many episodes")):
        return ["get_personal_response", "get_recommendation_confidence"]
    return ["get_personal_response"]


def _unique(names: Sequence[str]) -> list[str]:
    unique: list[str] = []
    for name in names:
        if name and name not in unique:
            unique.append(name)
    return unique


def _trace(names: Sequence[str]) -> list[dict[str, Any]]:
    return [agent_tools.trace_entry(name) for name in _unique(names)]
