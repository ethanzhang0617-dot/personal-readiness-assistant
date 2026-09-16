"""Personal Response layer for the API.

The deterministic engines still produce the base decision. This service reads
their output plus the user's recorded history, asks ``adaptive_response`` for a
bounded adjustment, and expresses the result as:

    base recommendation  →  personal-response adjustment (±1 band, or none)  →  final recommendation

It also answers the deterministic Personal Response questions for the Coach, so
those never reach the AI provider.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import adaptive_response


_TRACE_LABEL = "PERSONAL RESPONSE"


def evaluate(profile: Mapping[str, Any], assessment: Mapping[str, Any],
             recommendation: Mapping[str, Any], today: date | None = None) -> dict[str, Any]:
    return adaptive_response.evaluate(profile, assessment, recommendation, today)


def payload(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Client-facing personal response payload (summary + episodes + adaptation)."""
    summary = dict(decision.get("summary") or {})
    return {
        "available": bool(decision.get("available")),
        "base_demand": decision.get("base_demand"),
        "base_band": decision.get("base_band"),
        "final_demand": decision.get("final_demand"),
        "final_band": decision.get("final_band"),
        "adjustment": decision.get("adjustment", 0),
        "direction": decision.get("direction", "none"),
        "evidence": decision.get("evidence"),
        "reason": decision.get("reason"),
        "detail": decision.get("detail"),
        "summary": summary,
        "bands": summary.get("bands", []),
        "episodes": list(decision.get("episodes") or [])[:20],
        "note": summary.get("note"),
    }


def apply_to_summary(summary: Mapping[str, Any], decision: Mapping[str, Any],
                     engine_rir: str | None) -> dict[str, Any]:
    """Overlay the bounded adjustment onto a base recommendation summary."""
    adjusted = dict(summary)
    adjusted["base_session_demand"] = decision.get("base_demand")
    adjusted["session_demand"] = decision.get("final_demand")
    adjusted["personal_response"] = payload(decision)
    if decision.get("adjustment"):
        adjusted["rir_guidance"] = adaptive_response.final_rir(decision, engine_rir)
        adjusted["adaptation"] = {
            "label": "Adjusted from your recent response",
            "direction": decision.get("direction"),
            "from": decision.get("base_band"),
            "to": decision.get("final_band"),
            "reason": decision.get("reason"),
        }
    else:
        adjusted["adaptation"] = None
    return adjusted


def apply_to_trace(trace: list[dict[str, Any]], decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Insert the PERSONAL RESPONSE step between READINESS and SESSION DEMAND."""
    step = {"step": _TRACE_LABEL, "value": _trace_value(decision), "source": "deterministic"}
    rows = [dict(row) for row in trace]
    insert_at = next((index for index, row in enumerate(rows) if str(row.get("step")) == "SESSION DEMAND"), len(rows))
    rows.insert(insert_at, step)
    for index, row in enumerate(rows, start=1):
        row["index"] = index
    return rows


def _trace_value(decision: Mapping[str, Any]) -> str:
    adjustment = int(decision.get("adjustment") or 0)
    if adjustment < 0:
        return f"Reduced one step · {decision.get('base_band')} → {decision.get('final_band')}"
    if adjustment > 0:
        return f"Raised one step · {decision.get('base_band')} → {decision.get('final_band')}"
    if decision.get("base_band") is None:
        return "Not applicable today"
    if str(decision.get("evidence")) == "Insufficient":
        return "Not enough history yet"
    return "No adjustment"


def answer_question(question: str, decision: Mapping[str, Any]) -> str | None:
    """Deterministic Personal Response answers. None means "not this layer's question".

    Returning text here guarantees the question is answered from recorded data and
    never reaches the AI provider (see the AI-01 grounding contract).
    """
    text = (question or "").casefold().strip()
    if not text:
        return None
    summary = dict(decision.get("summary") or {})
    episodes = list(decision.get("episodes") or [])
    bands = {row["band"]: row for row in summary.get("bands", [])}
    completion_words = ("respond", "response", "tolerate", "tolerance", "recover from", "adapt")
    mentions_demand = any(word in text for word in ("high-demand", "high demand", "hard session", "hard sessions",
                                                    "moderate-demand", "moderate demand", "low-demand", "low demand"))
    if mentions_demand and any(word in text for word in completion_words):
        band = "High" if "high" in text else "Moderate" if "moderate" in text else "Low"
        row = bands.get(band)
        if not row or row["observations"] == 0:
            return (f"I don't have enough recorded {band.lower()}-demand sessions yet. Personal Response needs a "
                    f"completed session, your feedback and a following check-in before it can describe a pattern.")
        return (f"{row['band']} demand: {row['observations']} observed response episode"
                f"{'' if row['observations'] == 1 else 's'}. {row['pattern']} "
                f"(evidence: {row['evidence']}; {row['poorer']} poorer than usual, {row['better']} better than usual). "
                f"These are observed response patterns from your own data, not a recovery measurement.")
    if "how many response episodes" in text or ("how many" in text and "episode" in text):
        return (f"You have {summary.get('episodes_complete', 0)} complete response episodes and "
                f"{summary.get('episodes_pending', 0)} waiting for the next check-in. "
                f"Overall evidence: {summary.get('evidence', 'Insufficient')}.")
    if "why was" in text and "adjust" in text:
        if int(decision.get("adjustment") or 0) == 0:
            return f"Today's session demand was not adjusted. {decision.get('detail') or 'No adjustment'}."
        return f"{decision.get('reason')} This is a bounded product rule: at most one demand step, never past safety or readiness routing."
    if "what happened after" in text and ("session" in text or "last" in text):
        for episode in episodes:
            if not episode.get("feedback"):
                continue
            performed = episode.get("performed") or {}
            after = episode.get("after")
            parts = [f"After your {episode.get('date')} {episode.get('focus')} session "
                     f"({performed.get('duration_min') or '—'} min, session RPE {performed.get('session_rpe') or '—'}):"]
            if after:
                parts.append(f"your next check-in on {after.get('date')} recorded fatigue {after.get('fatigue') or '—'}/5 "
                             f"and soreness {after.get('soreness') or '—'}/5.")
            else:
                parts.append("no following check-in has been recorded yet.")
            signals = (episode.get("response") or {}).get("signals") or []
            if signals:
                parts.append("Observed signals: " + "; ".join(signals[:3]) + ".")
            verdict = (episode.get("response") or {}).get("verdict")
            if verdict and verdict != "unavailable":
                parts.append(f"Overall this episode read as {verdict.replace('_', ' ')}.")
            return " ".join(parts)
        return "No post-session feedback has been recorded yet, so there is no response episode to describe."
    if "personal response" in text and any(word in text for word in ("what", "explain", "status", "summary")):
        return (f"Personal Response is built from {summary.get('episodes_complete', 0)} complete episodes. "
                f"Evidence state: {summary.get('evidence', 'Insufficient')}. "
                + " ".join(f"{row['band']}: {row['observations']} observations — {row['pattern']}." for row in bands.values()))
    return None
