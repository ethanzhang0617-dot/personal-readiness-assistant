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
from typing import Any, Mapping, Sequence

import adaptive_response


_TRACE_LABEL = "PERSONAL RESPONSE"


def evaluate(profile: Mapping[str, Any], assessment: Mapping[str, Any],
             recommendation: Mapping[str, Any], today: date | None = None) -> dict[str, Any]:
    return adaptive_response.evaluate(profile, assessment, recommendation, today)


def payload(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Client-facing personal response payload (summary + episodes + adaptation)."""
    summary = dict(decision.get("summary") or {})
    confidence = dict(decision.get("confidence") or {})
    coverage = dict(decision.get("coverage") or {})
    consistency = dict(decision.get("consistency") or {})
    profile = dict(decision.get("profile") or {})
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
        "no_increase_reason": decision.get("no_increase_reason"),
        "confidence": confidence,
        "confidence_state": confidence.get("state"),
        "coverage": coverage,
        "consistency": consistency,
        "relevant": dict(decision.get("relevant") or {}),
        "relevant_episodes": int((decision.get("relevant") or {}).get("count", 0)),
        "profile": profile,
        "bands_profile": profile.get("bands", []),
        "focus_profile": profile.get("focus", []),
        "within_tier": dict(decision.get("within_tier") or {}),
        "summary": summary,
        "bands": summary.get("bands", []),
        "episodes": list(decision.get("episodes") or [])[:20],
        "note": summary.get("note"),
    }


def log_event(decision: Mapping[str, Any], today: date | None = None) -> dict[str, Any]:
    """One adaptation-history entry for the current decision."""
    return adaptive_response.adaptation_event(decision, today)


def with_history(payload_dict: Mapping[str, Any], history: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Attach the stored adaptation history (newest first) to a payload."""
    rows = [dict(row) for row in history]
    rows.reverse()
    return {**dict(payload_dict), "adaptation_history": rows[:30]}


def apply_to_summary(summary: Mapping[str, Any], decision: Mapping[str, Any],
                     engine_rir: str | None) -> dict[str, Any]:
    """Overlay the bounded adjustment onto a base recommendation summary."""
    adjusted = dict(summary)
    adjusted["base_session_demand"] = decision.get("base_demand")
    adjusted["session_demand"] = decision.get("final_demand")
    adjusted["personal_response"] = payload(decision)
    adjusted["recommendation_confidence"] = dict(decision.get("confidence") or {})
    if decision.get("adjustment"):
        adjusted["rir_guidance"] = adaptive_response.final_rir(decision, engine_rir)
        adjusted["adaptation"] = {
            "label": "Adjusted from your recent response",
            "direction": decision.get("direction"),
            "from": decision.get("base_band"),
            "to": decision.get("final_band"),
            "reason": decision.get("reason"),
            "confidence": (decision.get("confidence") or {}).get("state"),
            "scope": "Demand tier, one step maximum",
        }
    elif (decision.get("within_tier") or {}).get("available"):
        # Within-tier personalisation: the demand tier is unchanged, so this is not
        # an "adjusted" recommendation — it is optional extra effort inside the
        # range the product already prescribed.
        adjusted["adaptation"] = {
            "label": "Personalized from recent response",
            "direction": "within_tier",
            "from": decision.get("base_band"),
            "to": decision.get("final_band"),
            "reason": decision.get("within_tier", {}).get("guidance"),
            "confidence": (decision.get("confidence") or {}).get("state"),
            "scope": "Within the demand already prescribed — no tier change",
        }
    else:
        adjusted["adaptation"] = None
    return adjusted


def apply_to_trace(trace: list[dict[str, Any]], decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Insert the PERSONAL RESPONSE step between READINESS and SESSION DEMAND."""
    step = {"step": _TRACE_LABEL, "value": _trace_value(decision), "source": "deterministic",
            "detail": _trace_detail(decision)}
    rows = [dict(row) for row in trace]
    insert_at = next((index for index, row in enumerate(rows) if str(row.get("step")) == "SESSION DEMAND"), len(rows))
    rows.insert(insert_at, step)
    for index, row in enumerate(rows, start=1):
        row["index"] = index
    return rows


def _trace_detail(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Structured, scannable detail for the PERSONAL RESPONSE trace step."""
    relevant = dict(decision.get("relevant") or {})
    confidence = dict(decision.get("confidence") or {})
    consistency = dict(decision.get("consistency") or {})
    counts = consistency.get("counts") or {}
    adjustment = int(decision.get("adjustment") or 0)
    band = decision.get("base_band")
    if adjustment < 0:
        change = f"Reduced one step ({band} → {decision.get('final_band')})"
    elif adjustment > 0:
        change = f"Raised one step ({band} → {decision.get('final_band')})"
    elif (decision.get("within_tier") or {}).get("available"):
        change = "No tier change · optional within-tier effort guidance"
    else:
        change = "None"
    if band is None:
        pattern = "Not applicable today"
    elif int(relevant.get("count", 0)) == 0:
        pattern = "Not enough history yet"
    else:
        pattern = (f"{counts.get('poorer_than_usual', 0)} poorer · {counts.get('as_usual', 0)} as usual · "
                   f"{counts.get('better_than_usual', 0)} better ({consistency.get('label', 'Not enough evidence')})")
    return {
        "evidence": f"{int(relevant.get('count', 0))} relevant sessions at {band} demand" if band else "Not applicable today",
        "pattern": pattern,
        "confidence": confidence.get("label") or "Limited evidence",
        "confidence_state": confidence.get("state"),
        "adjustment": change,
    }


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


def answer_question(question: str, decision: Mapping[str, Any],
                    adaptation_history: Sequence[Mapping[str, Any]] = ()) -> str | None:
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
    confidence = dict(decision.get("confidence") or {})
    coverage = dict(decision.get("coverage") or {})
    relevant = dict(decision.get("relevant") or {})
    consistency = dict(decision.get("consistency") or {})
    within_tier = dict(decision.get("within_tier") or {})
    completion_words = ("respond", "response", "tolerate", "tolerance", "recover from", "adapt",
                        "learn", "pattern", "know about")
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
    if "how confident" in text or ("confidence" in text and "recommend" in text):
        return (f"Recommendation Confidence today is {confidence.get('state', 'Limited')} "
                f"({confidence.get('label', 'Limited evidence')}). {confidence.get('explanation', '')} "
                f"That describes how much recent personal evidence supports the personalisation — "
                f"{confidence.get('note', '')}")
    if ("how many sessions" in text or "how many episodes" in text) and any(
            word in text for word in ("support", "adjust", "change", "relevant")):
        return (f"{relevant.get('count', 0)} of your recent sessions at "
                f"{relevant.get('band') or 'this'} demand count toward today's evaluation "
                f"(most recent {relevant.get('max_episodes', 12)} episodes within {relevant.get('window_days', 56)} days). "
                f"You have {coverage.get('episodes_complete', 0)} complete episodes in total, and older episodes stay in "
                f"your history even when they no longer drive today's decision.")
    if "changed my training" in text or ("changed" in text and "before" in text) or "adaptation history" in text:
        changed = [row for row in adaptation_history if int(row.get("adjustment") or 0) != 0]
        if not adaptation_history:
            return ("No adaptation events are recorded yet. Today's evaluation is saved as soon as the product computes "
                    "your recommendation.")
        if not changed:
            return (f"Personal Response has not changed a session demand yet. {len(adaptation_history)} daily evaluations "
                    f"are recorded, all without a demand change.")
        latest = changed[-1]
        return (f"Personal Response has reduced the session demand on {len(changed)} day"
                f"{'' if len(changed) == 1 else 's'}. Most recently on {latest.get('date')}: "
                f"{latest.get('base_band')} → {latest.get('final_band')}. Reason: {latest.get('reason')}")
    if ("why didn't you increase" in text or "why did you not increase" in text
            or ("increase" in text and "why" in text)):
        if within_tier.get("available"):
            return (f"Today's session demand stays at {decision.get('base_band')} because that is the demand your "
                    f"readiness permits. Your recent sessions were tolerated well, so the guidance is optional extra "
                    f"effort inside the prescribed range: {within_tier.get('guidance')}")
        if decision.get("no_increase_reason"):
            return decision["no_increase_reason"]
        return ("Today's session demand is not increased because the personal evidence is not strong enough yet. "
                f"Recommendation Confidence is {confidence.get('state', 'Limited')}. "
                f"{confidence.get('explanation', '')}")
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
