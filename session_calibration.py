"""V1.3 — In-session calibration (final sprint).

One optional checkpoint during a session, resolved by a transparent deterministic
rule into exactly three outcomes: **HOLD**, **EASE** or **OPTIONAL PUSH**.

The checkpoint answers one question the product previously could not: *during*
training, does the actual session response still match the planned guidance?

Hard bounds (see the module constants and ``SCOPE``):

* it never raises or lowers the session demand **tier**,
* it never changes the training focus, the programme, the exercise list or the set
  count, and never raises a weekly target,
* it never overrides safety or soreness,
* it only points at the conservative or the harder end of the effort range the
  product already prescribed.

No machine learning, no probability, no recovery score and no prediction.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from readiness_engine import GREEN


# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

#: The only three calibration outcomes the product may present.
CALIBRATION_RESULTS: tuple[str, ...] = ("HOLD", "EASE", "OPTIONAL PUSH")

EFFORT_OPTIONS: tuple[str, ...] = ("Easier than expected", "As expected", "Harder than expected")
PERFORMANCE_OPTIONS: tuple[str, ...] = ("Better than expected", "As expected", "Worse than expected")

EFFORT_EASIER = EFFORT_OPTIONS[0]
EFFORT_AS_EXPECTED = EFFORT_OPTIONS[1]
EFFORT_HARDER = EFFORT_OPTIONS[2]

PERFORMANCE_BETTER = PERFORMANCE_OPTIONS[0]
PERFORMANCE_AS_EXPECTED = PERFORMANCE_OPTIONS[1]
PERFORMANCE_WORSE = PERFORMANCE_OPTIONS[2]

#: Local soreness at or above this value blocks any optional extra effort and
#: forces the conservative guidance (same limit the Personal Response layer uses).
SORENESS_LIMIT = 4

#: Highest RIR a user can plausibly report on a working set (0 = to failure).
MAX_ACTUAL_RIR = 6

#: What calibration is allowed to touch. Published in the payload and the UI.
SCOPE = "Within the effort range already prescribed — no tier, focus, exercise or volume change"

_RIR_RANGE = re.compile(r"(\d+)\s*[–\-—]\s*(\d+)")
_RIR_SINGLE = re.compile(r"(\d+)\s*RIR", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rir_range(text: Any) -> tuple[int, int] | None:
    """Parse the product's own *RIR* wording, e.g. ``1–3 RIR`` or ``2–4 RIR``.

    The unit is mandatory: the aerobic path prescribes ``RPE 3–4 / 10``, and a bare
    number range must never be mistaken for reps in reserve.
    """
    if text is None:
        return None
    raw = str(text)
    if "rir" not in raw.casefold():
        return None
    found = _RIR_RANGE.search(raw)
    if found:
        low, high = int(found.group(1)), int(found.group(2))
        return (min(low, high), max(low, high))
    single = _RIR_SINGLE.search(raw)
    if single:
        value = int(single.group(1))
        return (value, value)
    return None


def _normalise(value: Any, options: Sequence[str], default: str) -> str:
    text = str(value or "").strip().casefold()
    for option in options:
        if text == option.casefold():
            return option
    return default


def _soreness_block(local_soreness: Mapping[str, Any] | None) -> list[str]:
    """Local soreness at or above the product's own extra-effort limit."""
    blocked: list[str] = []
    for group, value in (local_soreness or {}).items():
        amount = _number(value)
        if amount is not None and amount >= SORENESS_LIMIT:
            blocked.append(f"{group} soreness is {int(amount)}/5")
    return blocked


def _has(text: str, *words: str) -> bool:
    """Keyword match that respects word boundaries for Latin script.

    Plain substring matching reads "increase" as "ease" and "reduce" as part of
    unrelated words, so ASCII keywords are matched on boundaries and CJK keywords
    (which have no spaces) as plain substrings.
    """
    for word in words:
        if word.isascii():
            if re.search(rf"\b{re.escape(word)}\b", text):
                return True
        elif word in text:
            return True
    return False


# --------------------------------------------------------------------------- #
# The rule
# --------------------------------------------------------------------------- #

def checkpoint(observation: Mapping[str, Any], planned_rir: str | None,
               readiness_status: str | None, safety_flags: Iterable[str] = (),
               local_soreness: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Resolve one checkpoint into HOLD / EASE / OPTIONAL PUSH.

    Deterministic and readable:

    * **blocks** — an active safety flag, or local soreness at/above ``SORENESS_LIMIT``.
      A block always eases the remainder of the session.
    * **clear divergences** — the reported RIR is below the prescribed range, or
      performance felt worse than expected. Either one alone eases the session.
    * **a softer divergence** — the session was reported *harder than expected*
      while the RIR and performance stayed at plan. That is one hard moment, not a
      divergence from the plan, so it holds.
    * **OPTIONAL PUSH** needs *all* of: readiness GREEN, no block, easier than
      expected, reported RIR above the prescribed ceiling, and performance at
      least as expected. It is optional and never raises anything.
    """
    effort = _normalise(observation.get("effort"), EFFORT_OPTIONS, EFFORT_AS_EXPECTED)
    performance = _normalise(observation.get("performance"), PERFORMANCE_OPTIONS, PERFORMANCE_AS_EXPECTED)
    actual_rir = _number(observation.get("actual_rir"))
    if actual_rir is not None:
        actual_rir = max(0, min(MAX_ACTUAL_RIR, int(round(actual_rir))))
    planned = rir_range(planned_rir)

    blocks = []
    if list(safety_flags or []):
        blocks.append("a safety flag is active")
    blocks.extend(_soreness_block(local_soreness))

    below_plan = bool(planned and actual_rir is not None and actual_rir < planned[0])
    above_plan = bool(planned and actual_rir is not None and actual_rir > planned[1])

    conservative: list[str] = []
    if effort == EFFORT_HARDER:
        conservative.append("you reported the session feeling harder than expected")
    if below_plan:
        conservative.append(f"your {actual_rir} RIR is below the prescribed {planned[0]}–{planned[1]} RIR range")
    if performance == PERFORMANCE_WORSE:
        conservative.append("performance felt worse than expected")

    summary: dict[str, Any] = {
        "planned_rir": planned_rir or None,
        "planned_range": list(planned) if planned else None,
        "effort": effort,
        "actual_rir": actual_rir,
        "performance": performance,
        "blocks": blocks,
        "conservative_signals": conservative,
        "scope": SCOPE,
    }

    if blocks or below_plan or performance == PERFORMANCE_WORSE:
        result = "EASE"
        if planned:
            guidance = (
                f"Stay toward the more conservative end of the effort range you already have — about "
                f"{planned[1]} RIR in reserve — and end a set early if form or effort degrades. "
                f"The session demand, focus, exercises and volume are unchanged."
            )
        else:
            guidance = ("Stay toward the more conservative end of the effort you were prescribed, and end a set early "
                        "if form or effort degrades. The session demand, focus, exercises and volume are unchanged.")
        # Capitalise only the first character: ``str.capitalize()`` would flatten
        # the product's own "RIR" wording to "rir".
        joined = "; ".join(blocks + conservative)
        reason = joined[:1].upper() + joined[1:]
        reason += ". Calibration: make the remainder of this session slightly more conservative."
    elif (str(readiness_status or "") == GREEN and effort == EFFORT_EASIER and above_plan
          and performance in (PERFORMANCE_BETTER, PERFORMANCE_AS_EXPECTED)):
        result = "OPTIONAL PUSH"
        low = planned[0] if planned else None
        if low is not None:
            guidance = (f"You may work toward the harder end of the effort range you already have — about {low} RIR "
                        f"in reserve — if it still feels right. This is optional and changes nothing else about the "
                        f"session.")
        else:
            guidance = ("You may work toward the harder end of the effort you were already permitted if it still feels "
                        "right. This is optional and changes nothing else about the session.")
        reason = ("The session is going better than expected, the reported RIR is above the prescribed range and "
                  "today's readiness is Green, so the harder end of the same range is available — optionally.")
    else:
        result = "HOLD"
        guidance = (f"Continue with the guidance you started with ({planned_rir}). Nothing about the session changes."
                    if planned_rir else "Continue with the guidance you started with. Nothing about the session changes.")
        if conservative:
            reason = ("You reported the session feeling harder than expected, but the reported RIR and performance "
                      "stayed at plan, so this is one hard moment rather than a divergence from the plan. "
                      "Calibration: hold the current guidance.")
        else:
            reason = "Your checkpoint matched the plan, so the guidance stays exactly as prescribed."

    summary["result"] = result
    summary["reason"] = reason
    summary["guidance"] = guidance
    summary["note"] = ("In-session calibration is a transparent product heuristic. It does not change the session "
                       "demand tier, the training focus or the volume, and it is not a recovery measurement.")
    return summary


# --------------------------------------------------------------------------- #
# Session trace (separate from the pre-session Decision Trace)
# --------------------------------------------------------------------------- #

def _personal_response_value(decision: Mapping[str, Any]) -> str:
    adjustment = int(decision.get("adjustment") or 0)
    if adjustment < 0:
        return f"Reduced one step · {decision.get('base_band')} → {decision.get('final_band')}"
    if adjustment > 0:
        return f"Raised one step · {decision.get('base_band')} → {decision.get('final_band')}"
    if (decision.get("within_tier") or {}).get("available"):
        return "Within-tier effort guidance"
    if decision.get("base_band") is None:
        return "Not applicable today"
    if str(decision.get("evidence")) == "Insufficient":
        return "Not enough history yet"
    return "No adjustment"


def session_trace(decision: Mapping[str, Any], planned_rir: str | None,
                  calibration: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """The session's own causal chain: decision → calibration → final guidance."""
    observation = "Not recorded yet"
    calibration_value = "Not recorded yet"
    final_guidance = "Not recorded yet"
    if calibration:
        effort = calibration.get("effort")
        actual = calibration.get("actual_rir")
        performance = calibration.get("performance")
        observation = " · ".join(part for part in (
            str(effort) if effort else None,
            f"{actual} RIR" if actual is not None else None,
            str(performance) if performance else None,
        ) if part) or "Recorded"
        calibration_value = str(calibration.get("result") or "Recorded")
        final_guidance = str(calibration.get("guidance") or "Recorded")
    steps = [
        ("PRE-SESSION DECISION", str(decision.get("base_demand") or "Not applicable today")),
        ("PERSONAL RESPONSE", _personal_response_value(decision)),
        ("STARTING GUIDANCE", planned_rir or "As prescribed"),
        ("IN-SESSION OBSERVATION", observation),
        ("CALIBRATION", calibration_value),
        ("FINAL SESSION GUIDANCE", final_guidance),
    ]
    return [{"index": index, "step": step, "value": value, "source": "deterministic"}
            for index, (step, value) in enumerate(steps, start=1)]


# --------------------------------------------------------------------------- #
# History and factual answers
# --------------------------------------------------------------------------- #

def calibration_event(calibration: Mapping[str, Any], plan: Mapping[str, Any] | None = None,
                      day: date | None = None) -> dict[str, Any]:
    """One stored calibration record (kept minimal on purpose)."""
    when = day or date.today()
    plan = dict(plan or {})
    return {
        "date": when.isoformat(),
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": plan.get("session_id"),
        "focus": plan.get("focus"),
        "session_demand": plan.get("session_demand"),
        "starting_guidance": calibration.get("planned_rir"),
        "effort": calibration.get("effort"),
        "actual_rir": calibration.get("actual_rir"),
        "performance": calibration.get("performance"),
        "result": calibration.get("result"),
        "reason": calibration.get("reason"),
        "guidance": calibration.get("guidance"),
        "relevance_window": "This session only",
    }


def summarise(calibrations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts and a plain-language trend over recorded calibrations."""
    rows = [dict(row) for row in calibrations]
    counts = {key: 0 for key in CALIBRATION_RESULTS}
    for row in rows:
        result = str(row.get("result") or "")
        if result in counts:
            counts[result] += 1
    total = len(rows)
    eased = counts["EASE"]
    if total == 0:
        trend = "No checkpoints recorded yet"
    elif eased == 0:
        trend = "Every checkpoint so far matched the plan"
    elif eased / total >= 0.5:
        trend = "Calibration has often asked you to ease off"
    else:
        trend = "Calibration has occasionally asked you to ease off"
    rir_values = [row.get("actual_rir") for row in rows if row.get("actual_rir") is not None]
    return {
        "total": total,
        "counts": counts,
        "eased": eased,
        "trend": trend,
        "latest": rows[-1] if rows else None,
        "reported_rir_values": rir_values[-5:],
        "note": ("Calibration events describe how the checkpoint compared with the plan on the day. They are "
                 "transparent product heuristics, not a recovery or tolerance measurement."),
    }


def answer_question(question: str, calibrations: Sequence[Mapping[str, Any]]) -> str | None:
    """Deterministic calibration answers. ``None`` means "not this layer's question"."""
    text = (question or "").casefold().strip()
    if not text:
        return None
    summary = summarise(calibrations)
    latest = summary["latest"]

    easing_words = ("ease", "easier", "reduce", "lower", "back off", "conservative", "降", "降低", "低一点", "保守")
    calibration_words = ("calibration", "calibrate", "checkpoint", "校准", "校准点", "检查点")
    rir_words = ("rir", "reps in reserve", "余力")
    history_words = ("often", "recently", "lately", "how many times", "经常", "最近", "多久")

    if _has(text, *rir_words) and _has(text, "what", "record", "logged", "log", "记", "多少"):
        if latest is None:
            return "No in-session checkpoint has been recorded yet, so there is no RIR from a checkpoint to report."
        reported = latest.get("actual_rir")
        if reported is None:
            return (f"Your most recent checkpoint on {latest.get('date')} did not include an RIR value. "
                    f"The prescribed guidance that session was {latest.get('starting_guidance') or 'not recorded'}.")
        return (f"Your most recent checkpoint on {latest.get('date')} recorded {reported} RIR on a representative "
                f"working set, against prescribed guidance of {latest.get('starting_guidance') or 'not recorded'}. "
                f"The result was {latest.get('result')}.")

    if _has(text, *history_words) and _has(text, *easing_words):
        if summary["total"] == 0:
            return "No in-session checkpoints have been recorded yet, so there is nothing to describe."
        return (f"You have recorded {summary['total']} in-session checkpoint"
                f"{'' if summary['total'] == 1 else 's'}, and {summary['eased']} of them asked for a slightly more "
                f"conservative remainder of the session. {summary['trend']}.")

    if _has(text, *easing_words) and _has(text, "why", "为什么"):
        if latest is None:
            return "No in-session checkpoint has been recorded yet."
        return (f"Today's checkpoint resolved as {latest.get('result')}. " + str(latest.get("reason") or "")
                + f" You reported: {latest.get('effort')} effort, "
                + (f"{latest.get('actual_rir')} RIR, " if latest.get("actual_rir") is not None else "")
                + f"{latest.get('performance')} performance.")

    if _has(text, *calibration_words) and _has(text, "what", "which", "status", "today", "my", "是", "什么"):
        if latest is None:
            return ("No in-session checkpoint has been recorded for today. It is optional, and it asks only how the "
                    "session compared with the plan.")
        return (f"Today's in-session calibration is {latest.get('result')}. {latest.get('guidance')} "
                f"({summary['note']})")

    return None
