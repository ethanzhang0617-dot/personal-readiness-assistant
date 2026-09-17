"""V1.3 Adaptive Decision Loop — Phase 1: Personal Response foundation.

Deterministic, inspectable and bounded. This module never replaces the existing
engines: it reads their output plus the user's own recorded history and may move
HOW HARD by at most one demand step. It contains:

1. **Response episodes** — a compact link between the pre-session snapshot, the
   recommendation that was given, the session actually performed, the user's own
   post-session feedback and the next available morning check-in.
2. **Evidence states** — Insufficient / Emerging / Established, from simple
   transparent counts. These are product heuristics, not validated statistics.
3. **A bounded adaptation rule** — at most one demand step, never against RED or
   STOP, and upward only with stronger evidence than downward.

No machine learning, no probabilities, no recovery percentage. Nothing here
writes to the deterministic engines, and nothing here changes WHAT to train.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping

from readiness_engine import AMBER, GREEN, RED, STOP


# --------------------------------------------------------------------------- #
# Demand ladder (the product's own vocabulary, in order)
# --------------------------------------------------------------------------- #

#: Ordered demand bands. The engine can emit the Low and Moderate bands; the
#: High band is its normal-demand strength/aerobic prescription.
DEMAND_BANDS: tuple[str, ...] = ("Low", "Moderate", "High")

#: Canonical demand wording per band, reusing the engine's own strings.
BAND_DEMAND: dict[str, str] = {
    "Low": "Rest or lower-demand",
    "Moderate": "Reduced / autoregulated",
    "High": "Normal",
}

#: Effort guidance per band. High/Moderate reuse RECOMMENDATION_RULE_METADATA's
#: published prototype ranges; Low never prescribes hard sets.
BAND_RIR: dict[str, str] = {
    "Low": "No prescribed hard sets",
    "Moderate": "2–4 RIR; avoid unnecessary failure",
    "High": "1–3 RIR",
}

_DEMAND_TO_BAND: dict[str, str] = {
    "normal": "High",
    "reduced / autoregulated": "Moderate",
    "reduced strength": "Moderate",
    "reduced": "Moderate",
    "rest or lower-demand": "Low",
    "lower-demand": "Low",
    "no normal training recommendation": "Low",
}

#: Evidence sufficiency thresholds (product heuristics).
INSUFFICIENT_MAX = 2
EMERGING_MAX = 5

#: A check-in links to the most recent completed session within this many days.
MAX_LINK_GAP_DAYS = 3

#: How many prior check-ins define "the user's own recent context".
CONTEXT_WINDOW = 7

#: Recency policy (product heuristic): only the most recent episodes inside this
#: window are allowed to drive personalisation. Older episodes stay visible in the
#: history and in the profile counts, they simply stop influencing today.
RECENT_WINDOW_DAYS = 56
MAX_RECENT_EPISODES = 12

#: Consistency: the largest group of episodes pointing the same way.
CONSISTENT_RATIO = 0.6

#: Recommendation Confidence states (evidence about the personalisation, never
#: confidence that the user is physiologically recovered).
CONFIDENCE_STATES = ("Limited", "Developing", "Strong")

#: Local soreness at or above this value blocks any optional extra effort.
EXTRA_EFFORT_SORENESS_LIMIT = 4

#: How many sessions a demo seed attaches feedback to.
DEMO_CASES = ("insufficient", "emerging", "poor_high_tolerance", "established_good")


def band_for_demand(demand: str | None) -> str | None:
    if not demand:
        return None
    return _DEMAND_TO_BAND.get(str(demand).strip().casefold())


def evidence_state(observations: int) -> str:
    if observations <= INSUFFICIENT_MAX:
        return "Insufficient"
    if observations <= EMERGING_MAX:
        return "Emerging"
    return "Established"


def _as_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _daily_rows(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in (profile.get("history") or []) if _as_date(row.get("date"))]
    rows.sort(key=lambda row: str(row["date"]))
    return rows


def _completed_sessions(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in (profile.get("training_history") or [])
            if row.get("completed", True) and _as_date(row.get("date"))]
    rows.sort(key=lambda row: str(row["date"]))
    return rows


def _recent_context(rows: list[dict[str, Any]], before: date) -> dict[str, float | None]:
    """Personal mean of the check-ins before a date, for fatigue and soreness."""
    prior = [row for row in rows if (_as_date(row.get("date")) or before) < before][-CONTEXT_WINDOW:]

    def mean(field: str) -> float | None:
        values = [value for value in (_number(row.get(field)) for row in prior) if value is not None]
        return round(sum(values) / len(values), 2) if values else None

    return {"fatigue": mean("fatigue"), "soreness": mean("soreness")}


def _interpret(feedback: Mapping[str, Any], after: Mapping[str, Any] | None,
               context: Mapping[str, float | None]) -> tuple[str, list[str]]:
    """Compare the observed response with the user's own recent context.

    Deliberately simple and readable: count plain negative and positive signals
    and let them cancel out. Product heuristic, not a physiological measure.
    """
    negative: list[str] = []
    positive: list[str] = []

    completion = str(feedback.get("completion") or "Completed")
    difficulty = _number(feedback.get("difficulty"))
    performance = _number(feedback.get("performance"))
    if completion == "Stopped early":
        negative.append("Session stopped early")
    elif completion == "Modified":
        negative.append("Session modified")
    if difficulty is not None and performance is not None and difficulty >= 4 and performance <= 2:
        negative.append("High perceived difficulty with low performance feeling")
    if difficulty is not None and difficulty <= 2 and completion == "Completed":
        positive.append("Low perceived difficulty, completed as planned")
    if performance is not None and performance >= 4:
        positive.append("Performance felt good")

    if after:
        for field, label in (("fatigue", "fatigue"), ("soreness", "soreness")):
            observed = _number(after.get(field))
            baseline = context.get(field)
            if observed is None or baseline is None:
                continue
            delta = observed - baseline
            if delta >= 1:
                negative.append(f"Next-day {label} above your recent usual")
            elif delta <= -1:
                positive.append(f"Next-day {label} below your recent usual")

    score = len(positive) - len(negative)
    if score <= -1:
        verdict = "poorer_than_usual"
    elif score >= 1:
        verdict = "better_than_usual"
    else:
        verdict = "as_usual"
    return verdict, (negative + positive)


def build_episodes(profile: Mapping[str, Any], today: date | None = None) -> list[dict[str, Any]]:
    """Transparent response episodes, newest first."""
    day = today or date.today()
    rows = _daily_rows(profile)
    sessions = _completed_sessions(profile)

    # Each check-in links to the most recent completed session before it; a session
    # whose check-in is already claimed by a closer session is marked ambiguous
    # instead of being double-linked.
    claimed: dict[str, str] = {}
    links: dict[str, tuple[str, str]] = {}
    for row in rows:
        check_in_date = _as_date(row.get("date"))
        if check_in_date is None or check_in_date > day:
            continue
        candidates = [session for session in sessions if (_as_date(session.get("date")) or day) < check_in_date]
        if not candidates:
            continue
        nearest = candidates[-1]
        gap = (check_in_date - (_as_date(nearest.get("date")) or check_in_date)).days
        session_id = str(nearest.get("session_id"))
        if gap > MAX_LINK_GAP_DAYS:
            continue
        if session_id in links:
            continue
        links[session_id] = (str(row.get("date")), "linked")
        claimed[session_id] = str(row.get("date"))

    episodes: list[dict[str, Any]] = []
    for session in sessions:
        session_id = str(session.get("session_id"))
        snapshot = dict(session.get("response_context") or {})
        feedback = dict(session.get("response_feedback") or {})
        session_date = _as_date(session.get("date")) or day
        link_date, link_state = links.get(session_id, (None, "pending"))
        after_row = next((row for row in rows if str(row.get("date")) == link_date), None) if link_date else None
        if link_state == "linked" and after_row is None:
            link_state = "unavailable"

        # Sessions logged before this phase have no pre-session snapshot, so they
        # stay unclassified and never contribute to a demand-band pattern.
        band = band_for_demand(snapshot.get("base_session_demand"))

        verdict = "unavailable"
        signals: list[str] = []
        if feedback and (after_row is not None or feedback):
            verdict, signals = _interpret(feedback, after_row, _recent_context(rows, _as_date(link_date) or session_date))

        complete = bool(feedback) and link_state == "linked" and band is not None
        episodes.append({
            "session_id": session_id,
            "date": str(session.get("date")),
            "focus": session.get("primary_focus") or session.get("training_type"),
            "band": band,
            "before": {
                "readiness_status": snapshot.get("readiness_status"),
                "readiness_index": snapshot.get("readiness_index"),
                "confidence": snapshot.get("readiness_confidence"),
                "local_soreness": snapshot.get("local_soreness") or {},
            },
            "recommendation": {
                "base_demand": snapshot.get("base_session_demand"),
                "final_demand": snapshot.get("final_session_demand"),
                "band": band,
                "adjustment": snapshot.get("adjustment", 0),
                "duration": snapshot.get("recommended_duration"),
                "rir": snapshot.get("recommended_rir"),
                "exposure_note": snapshot.get("exposure_note"),
            },
            # V1.3 final sprint: the optional in-session checkpoint, when one was
            # recorded. Episodes logged without a checkpoint stay valid and simply
            # carry ``None`` here — no data is rewritten.
            "calibrated": dict(session["response_calibration"])
            if isinstance(session.get("response_calibration"), Mapping) else None,
            "performed": {
                "duration_min": session.get("duration_min"),
                "session_rpe": session.get("session_rpe"),
                "working_sets": session.get("working_sets", session.get("actual_sets")),
                "completion": feedback.get("completion") or session.get("completion_status"),
            },
            "feedback": feedback or None,
            "after": None if after_row is None else {
                "date": after_row.get("date"),
                "fatigue": after_row.get("fatigue"),
                "soreness": after_row.get("soreness"),
                "motivation": after_row.get("motivation"),
                "stress": after_row.get("stress"),
                "sleep_hours": after_row.get("sleep_hours"),
                "rmssd_ms": after_row.get("rmssd_ms"),
                "resting_hr_bpm": after_row.get("resting_hr_bpm"),
            },
            "response": {"verdict": verdict, "signals": signals},
            "link": link_state,
            "complete": complete,
        })
    episodes.reverse()
    return episodes


def summarise(episodes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Per-band tolerance pattern plus the overall evidence state."""
    rows = list(episodes)
    complete = [row for row in rows if row.get("complete")]
    bands: list[dict[str, Any]] = []
    for band in DEMAND_BANDS:
        band_rows = [row for row in complete if row.get("band") == band]
        poorer = sum(1 for row in band_rows if row["response"]["verdict"] == "poorer_than_usual")
        better = sum(1 for row in band_rows if row["response"]["verdict"] == "better_than_usual")
        observations = len(band_rows)
        if observations < 3:
            pattern = "Insufficient evidence"
        elif poorer / observations >= 0.6:
            pattern = "Usually harder to recover from"
        elif better / observations >= 0.6:
            pattern = "Generally tolerated better than expected"
        else:
            pattern = "Generally tolerated as expected"
        bands.append({
            "band": band,
            "demand": BAND_DEMAND[band],
            "observations": observations,
            "poorer": poorer,
            "better": better,
            "pattern": pattern,
            "evidence": evidence_state(observations),
        })
    return {
        "episodes_total": len(rows),
        "episodes_complete": len(complete),
        "episodes_pending": sum(1 for row in rows if row.get("link") == "pending"),
        "evidence": evidence_state(len(complete)),
        "bands": bands,
        "note": ("Response patterns describe how this user's own sessions were followed by their own next "
                 "check-ins. They are transparent product heuristics, not a recovery measurement."),
    }


def evaluate(profile: Mapping[str, Any], assessment: Mapping[str, Any],
             recommendation: Mapping[str, Any], today: date | None = None) -> dict[str, Any]:
    """Bounded adaptation layer. Returns the decision, the reason and the evidence."""
    episodes = build_episodes(profile, today)
    summary = summarise(episodes)
    status = str(assessment.get("overall_readiness") or "")
    base_demand = str(recommendation.get("intensity") or "")
    base_band = band_for_demand(base_demand)
    relevant = relevant_episodes(episodes, base_band, today)
    consistency = pattern_consistency(relevant)
    confidence = recommendation_confidence(relevant, consistency)
    coverage = evidence_coverage(episodes, today)
    profile_view = response_profile(episodes, today)

    decision: dict[str, Any] = {
        "available": base_band is not None,
        "base_demand": base_demand,
        "base_band": base_band,
        "final_demand": base_demand,
        "final_band": base_band,
        "adjustment": 0,
        "direction": "none",
        "evidence": summary["evidence"],
        "summary": summary,
        "episodes": episodes,
        "relevant": relevant_summary(relevant, base_band),
        "consistency": consistency,
        "confidence": confidence,
        "coverage": coverage,
        "profile": profile_view,
        "_relevant_episodes": relevant,
        "within_tier": {"available": False, "guidance": None, "reason": None},
        "no_increase_reason": None,
        "reason": "No adjustment",
        "detail": "Not enough history yet" if summary["evidence"] == "Insufficient" else "Recent response did not change today's demand",
    }

    # Safety and readiness precedence: RED/STOP never adapts, and the Low band has
    # no room to move inside Phase 1's one-step bound.
    if status in {RED, STOP} or base_band in (None, "Low"):
        if status in {RED, STOP}:
            decision["detail"] = "Readiness or safety routing takes precedence"
        elif base_band is None:
            decision["detail"] = ("Today's training type sits outside the demand bands Personal Response covers, "
                                  "so the session is unchanged.")
        else:
            decision["detail"] = ("Today's base recommendation is already the lowest demand band, so Personal "
                                  "Response leaves it unchanged.")
        decision["within_tier"] = within_tier_guidance(decision, assessment, base_band, status)
        if decision["within_tier"].get("reason") and not decision["within_tier"].get("available"):
            decision["no_increase_reason"] = decision["within_tier"]["reason"]
        return decision

    index = DEMAND_BANDS.index(base_band)
    current = summary["bands"][index]
    lower = summary["bands"][index - 1] if index > 0 else None

    # Downward: repeated poorer-than-usual responses at the current demand.
    if (current["observations"] >= 3 and current["poorer"] / current["observations"] >= 0.6
            and consistency["direction"] == "poorer_than_usual"):
        decision = _decide(decision, summary, index, -1,
                           f"We reduced today's session from {base_band} to {DEMAND_BANDS[index - 1]} demand because "
                           f"{current['poorer']} of your last {current['observations']} {base_band.lower()}-demand sessions "
                           f"were followed by a poorer-than-usual next-day response.")
        decision["within_tier"] = within_tier_guidance(decision, assessment, base_band, status)
        return decision

    # Phase 2 replaces the unreachable "raise the demand tier" branch with an
    # honest within-tier option: when the user repeatedly tolerates the current
    # prescribed demand well, the product may point at the harder end of the
    # *existing* effort range. It never invents a new tier, volume or precision.
    decision["within_tier"] = within_tier_guidance(decision, assessment, base_band, status)
    if decision["within_tier"]["available"]:
        decision["reason"] = decision["within_tier"]["guidance"]
        decision["direction"] = "within_tier"
    elif decision["within_tier"]["reason"]:
        decision["no_increase_reason"] = decision["within_tier"]["reason"]

    if summary["evidence"] == "Insufficient":
        decision["detail"] = "Not enough history yet"
    elif lower is not None and current["poorer"] > 0:
        decision["detail"] = (f"{current['poorer']} of {current['observations']} {base_band.lower()}-demand sessions "
                              f"showed a poorer next-day response, which is not yet a repeated pattern.")
    else:
        decision["detail"] = f"{current['observations']} {base_band.lower()}-demand sessions observed; response as usual"
    return decision


def _decide(decision: dict[str, Any], summary: Mapping[str, Any], index: int, adjustment: int,
            reason: str) -> dict[str, Any]:
    final_band = DEMAND_BANDS[index + adjustment]
    decision.update({
        "final_demand": BAND_DEMAND[final_band],
        "final_band": final_band,
        "adjustment": adjustment,
        "direction": "reduce" if adjustment < 0 else "raise",
        "reason": reason,
        "detail": reason,
        "evidence": summary["evidence"],
    })
    return decision


# --------------------------------------------------------------------------- #
# Phase 2 — profile, evidence coverage, confidence, consistency and within-tier
# --------------------------------------------------------------------------- #


def relevant_episodes(episodes: Iterable[Mapping[str, Any]], band: str | None,
                      today: date | None = None) -> list[dict[str, Any]]:
    """Complete episodes at this demand inside the recency window, newest first."""
    if band is None:
        return []
    cutoff = (today or date.today()) - timedelta(days=RECENT_WINDOW_DAYS)
    rows = [
        dict(row) for row in episodes
        if row.get("complete") and row.get("band") == band and (_as_date(row.get("date")) or cutoff) >= cutoff
    ]
    return rows[:MAX_RECENT_EPISODES]


def relevant_summary(relevant: Iterable[Mapping[str, Any]], band: str | None) -> dict[str, Any]:
    rows = list(relevant)
    return {
        "band": band,
        "count": len(rows),
        "session_ids": [row.get("session_id") for row in rows],
        "window_days": RECENT_WINDOW_DAYS,
        "max_episodes": MAX_RECENT_EPISODES,
    }


def pattern_consistency(episodes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """How much the observed episodes point the same way (never a probability)."""
    rows = list(episodes)
    counts = {"poorer_than_usual": 0, "as_usual": 0, "better_than_usual": 0}
    for row in rows:
        verdict = str((row.get("response") or {}).get("verdict"))
        if verdict in counts:
            counts[verdict] += 1
    total = len(rows)
    if total == 0:
        return {"label": "Not enough evidence", "direction": None, "ratio": 0.0,
                "consistent": False, "counts": counts, "episodes": 0}
    # Deterministic tie-break order (poorer → as usual → better) so the reported
    # leader never changes between two identical runs.
    order = ("poorer_than_usual", "as_usual", "better_than_usual")
    leader = max(order, key=lambda key: (counts[key], -order.index(key)))
    ratio = counts[leader] / total
    consistent = total >= 3 and ratio >= CONSISTENT_RATIO
    label = "Consistent" if consistent else ("Mixed" if total >= 3 else "Not enough evidence")
    return {
        "label": label,
        "direction": leader if consistent else "mixed",
        "ratio": round(ratio, 2),
        "consistent": consistent,
        "counts": counts,
        "episodes": total,
    }


def recommendation_confidence(relevant: Iterable[Mapping[str, Any]], consistency: Mapping[str, Any]) -> dict[str, Any]:
    """Qualitative confidence in the *personalisation evidence*, never in recovery."""
    count = len(list(relevant))
    if count < 3:
        state = "Limited"
        explanation = "Fewer than three recent sessions at this demand have a complete response episode."
    elif count >= 6 and consistency.get("consistent"):
        state = "Strong"
        explanation = f"{count} recent sessions at this demand with a consistent response pattern."
    else:
        state = "Developing"
        explanation = (f"{count} relevant sessions at this demand; the pattern is still "
                       f"{'mixed' if not consistency.get('consistent') else 'building'}.")
    return {
        "state": state,
        "label": f"{state} evidence",
        "explanation": explanation,
        "relevant_episodes": count,
        "consistent": bool(consistency.get("consistent")),
        "factors": {
            "relevant_episodes": count,
            "recency_window_days": RECENT_WINDOW_DAYS,
            "max_recent_episodes": MAX_RECENT_EPISODES,
            "agreement_ratio": consistency.get("ratio", 0.0),
            "dominant_direction": consistency.get("direction"),
        },
        "note": ("Recommendation Confidence describes how much recent personal evidence supports the "
                 "personalisation. It is not a clinical confidence, a statistical probability, or a claim about recovery."),
    }


def evidence_coverage(episodes: Iterable[Mapping[str, Any]], today: date | None = None) -> dict[str, Any]:
    day = today or date.today()
    rows = list(episodes)
    complete = [row for row in rows if row.get("complete")]
    pending = [row for row in rows if row.get("link") == "pending"]
    feedback_only = [row for row in rows if row.get("feedback") and row.get("link") != "linked"]
    dates = [_as_date((row.get("after") or {}).get("date")) for row in complete]
    last_date = max((value for value in dates if value), default=None)
    band_counts = []
    for band in DEMAND_BANDS:
        band_counts.append({"band": band, "observations": sum(1 for row in complete if row.get("band") == band)})
    return {
        "episodes_total": len(rows),
        "episodes_complete": len(complete),
        "episodes_pending": len(pending),
        "feedback_without_check_in": len(feedback_only),
        "last_complete_date": last_date.isoformat() if last_date else None,
        "last_complete_days_ago": (day - last_date).days if last_date else None,
        "bands": band_counts,
        "note": ("Complete episodes have your post-session feedback and a following morning check-in. "
                 "Older episodes stay in the history even when they are outside the recent window."),
    }


def _focus_pattern(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations = len(rows)
    poorer = sum(1 for row in rows if (row.get("response") or {}).get("verdict") == "poorer_than_usual")
    better = sum(1 for row in rows if (row.get("response") or {}).get("verdict") == "better_than_usual")
    as_usual = observations - poorer - better
    if observations < 3:
        pattern = "Insufficient evidence"
    elif poorer / observations >= CONSISTENT_RATIO:
        pattern = "Usually harder to recover from"
    elif better / observations >= CONSISTENT_RATIO:
        pattern = "Generally tolerated better than expected"
    else:
        pattern = "Generally tolerated as expected"
    return {"observations": observations, "poorer": poorer, "as_usual": as_usual, "better": better,
            "pattern": pattern, "evidence": evidence_state(observations)}


def response_profile(episodes: Iterable[Mapping[str, Any]], today: date | None = None) -> dict[str, Any]:
    """Personal Response Profile: by demand band, and by focus only where supported."""
    day = today or date.today()
    rows = list(episodes)
    complete = [row for row in rows if row.get("complete")]
    bands = []
    for band in DEMAND_BANDS:
        band_rows = [row for row in complete if row.get("band") == band]
        stats = _focus_pattern(band_rows)
        recent = relevant_episodes(rows, band, day)
        recent_stats = _focus_pattern(recent)
        bands.append({
            "band": band,
            "demand": BAND_DEMAND[band],
            **stats,
            "recent_observations": recent_stats["observations"],
            "recent_pattern": recent_stats["pattern"] if recent_stats["observations"] >= 3 else "Insufficient evidence",
        })

    focus: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in complete:
        name = str(row.get("focus") or "").strip()
        if name:
            grouped.setdefault(name, []).append(row)
    for name, group in sorted(grouped.items(), key=lambda item: -len(item[1])):
        if len(group) < 3:      # never present a category the data cannot support
            continue
        focus.append({"focus": name, **_focus_pattern(group)})
    focus = focus[:4]

    return {
        "bands": bands,
        "focus": focus,
        "focus_note": ("Training-focus patterns appear only once at least three complete episodes exist for that "
                       "focus, so the product never presents a category its data cannot support."),
    }


CEILING_MESSAGE = ("Good tolerance observed. No additional increase is recommended because today's base "
                   "recommendation already uses the available demand range.")


def within_tier_guidance(decision: Mapping[str, Any], assessment: Mapping[str, Any],
                         base_band: str | None, status: str) -> dict[str, Any]:
    """Optional extra effort *inside* the already-permitted session demand.

    Phase 1 identified that raising the demand *tier* is unreachable, because the
    engine's demand is already the tier readiness permits. Phase 2 therefore offers
    a bounded within-tier option instead: when the user repeatedly tolerates the
    prescribed demand well, they may work toward the harder end of the existing RIR
    range. No tier change, no extra sets, no new precision.
    """
    relevant = list(decision.get("_relevant_episodes") or [])
    confidence = str((decision.get("confidence") or {}).get("state"))
    counts = (decision.get("consistency") or {}).get("counts") or {}
    total = len(relevant)
    poorer = int(counts.get("poorer_than_usual", 0))
    tolerates_well = total >= 3 and poorer / total <= 0.2

    if confidence != "Strong" or not tolerates_well:
        return {"available": False, "guidance": None, "reason": None}
    if status != GREEN:
        return {"available": False, "guidance": None,
                "reason": ("Good tolerance observed. No extra effort is suggested today because today's readiness is "
                           "not Green, so the session stays as prescribed.")}
    soreness = (assessment.get("today_data") or {}).get("local_soreness") or {}
    if assessment.get("safety_flags") or any(_number(value) and _number(value) >= EXTRA_EFFORT_SORENESS_LIMIT
                                            for value in soreness.values()):
        return {"available": False, "guidance": None,
                "reason": ("Good tolerance observed. No extra effort is suggested today because of the safety or "
                           "soreness you reported.")}
    if base_band not in {"Moderate", "High"}:
        return {"available": False, "guidance": None, "reason": CEILING_MESSAGE}

    effort = BAND_RIR.get(base_band, "")
    range_text = effort.split(" ", 1)[0] if effort else "the prescribed"
    return {
        "available": True,
        "guidance": (f"You have tolerated this demand well in your recent sessions. If it feels right today, take "
                     f"your main sets toward the harder end of the prescribed {range_text} RIR range. "
                     f"No extra sets are added."),
        "reason": None,
        "scope": "Within the demand already prescribed — no tier change",
    }


def adaptation_event(decision: Mapping[str, Any], day: date | None = None) -> dict[str, Any]:
    """One meaningful decision event for the adaptation history (per day)."""
    when = day or date.today()
    adjustment = int(decision.get("adjustment") or 0)
    if adjustment < 0:
        result = "reduced"
    elif adjustment > 0:
        result = "raised"
    elif (decision.get("within_tier") or {}).get("available"):
        result = "within_tier"
    else:
        result = "no_change"
    reason = decision.get("reason") if adjustment or result == "within_tier" else None
    return {
        "date": when.isoformat(),
        "base_demand": decision.get("base_demand"),
        "base_band": decision.get("base_band"),
        "final_demand": decision.get("final_demand"),
        "final_band": decision.get("final_band"),
        "adjustment": adjustment,
        "result": result,
        "confidence": (decision.get("confidence") or {}).get("state"),
        "evidence": decision.get("evidence"),
        "relevant_episodes": (decision.get("relevant") or {}).get("count", 0),
        "reason": reason or decision.get("no_increase_reason") or decision.get("detail") or "No adjustment",
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }


def final_rir(decision: Mapping[str, Any], engine_rir: str | None) -> str | None:
    """Effort guidance for the final demand band (engine wording when unchanged)."""
    if not decision.get("adjustment"):
        return engine_rir
    return BAND_RIR.get(str(decision.get("final_band")), engine_rir)


def demo_seed(profile: Mapping[str, Any], case: str,
              base_demand: str = "Normal") -> dict[str, dict[str, Any]]:
    """Demo-only response data, keyed by session id.

    Gives the portfolio demo the four required cases without cluttering the normal
    consumer workflow, and without inventing data for real user sessions.

    The seeded episodes are recorded at ``base_demand`` — the demand the product
    actually prescribes for this profile today. A demo that seeded episodes at a
    *different* demand would show "Limited evidence" while claiming to show an
    established pattern, which is exactly the kind of dishonest demo Phase 2
    removes.
    """
    if case not in DEMO_CASES:
        return {}
    if band_for_demand(base_demand) is None:
        base_demand = "Normal"
    # Only sessions that are actually followed by a check-in inside the linking
    # window can become a complete episode, so the demo seeds those.
    rows = _daily_rows(profile)
    check_in_dates = [day for day in (_as_date(row.get("date")) for row in rows) if day]
    sessions = [
        row for row in _completed_sessions(profile)
        if row.get("primary_focus") and any(
            0 < (day - (_as_date(row.get("date")) or day)).days <= MAX_LINK_GAP_DAYS for day in check_in_dates
        )
    ]
    sessions = sessions[-8:] if len(sessions) > 8 else sessions
    if not sessions:
        return {}

    def snapshot(session: Mapping[str, Any], demand: str, adjustment: int = 0) -> dict[str, Any]:
        band = band_for_demand(demand)
        return {
            "captured_at": f"{session.get('date')}T07:30:00+00:00",
            "readiness_status": GREEN,
            "readiness_index": 86,
            "readiness_confidence": "NORMAL",
            "base_session_demand": demand,
            "final_session_demand": demand,
            "adjustment": adjustment,
            "recommended_focus": session.get("primary_focus"),
            "recommended_duration": "50–65 min" if demand == "Normal" else "35–55 min",
            "recommended_rir": BAND_RIR.get(band or "High"),
            "local_soreness": {},
            "exposure_note": "Demo seed",
        }

    if case == "insufficient":
        session = sessions[-1]
        return {str(session.get("session_id")): {
            "response_context": snapshot(session, "Normal"),
            "response_feedback": {"difficulty": 3, "performance": 4, "completion": "Completed", "note": "", "submitted_at": "demo"},
        }}

    if case == "emerging":
        seed: dict[str, dict[str, Any]] = {}
        for session in sessions[-4:]:
            seed[str(session.get("session_id"))] = {
                "response_context": snapshot(session, base_demand),
                "response_feedback": {"difficulty": 3, "performance": 3, "completion": "Completed", "note": "", "submitted_at": "demo"},
            }
        return seed

    if case == "poor_high_tolerance":
        seed = {}
        for session in sessions[-3:]:
            seed[str(session.get("session_id"))] = {
                "response_context": snapshot(session, base_demand),
                "response_feedback": {"difficulty": 5, "performance": 2, "completion": "Stopped early",
                                      "note": "Demo: high-demand sessions were not well tolerated.", "submitted_at": "demo"},
            }
        return seed

    seed = {}
    for session in sessions[-6:]:
        seed[str(session.get("session_id"))] = {
            "response_context": snapshot(session, base_demand),
            "response_feedback": {"difficulty": 2, "performance": 4, "completion": "Completed", "note": "", "submitted_at": "demo"},
        }
    return seed
