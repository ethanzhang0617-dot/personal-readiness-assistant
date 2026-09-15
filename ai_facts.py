"""Deterministic personal-fact layer for the Coach (hotfix AI-01).

The Coach must never let a language model decide *what a personal fact is*. This
module owns three things:

1. **Unit registry** — every personal metric carries an explicit unit and the
   units it must never be expressed in (``sets`` != ``days``, ``minutes`` !=
   ``training load``, ``ms`` != ``bpm``).
2. **Structured facts** — read-only projections of the deterministic engines and
   the stored history. No value here is invented: each one names its source.
3. **Router + grounded answers** — a deterministic intent router, factual answers
   rendered from the facts, correction handling, and a guard that rejects model
   output which adds numbers, changes units or shifts the time period.

Nothing in this module writes to the engines or changes a calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping
import re

from readiness_engine import STOP


# --------------------------------------------------------------------------- #
# 1. Unit registry
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Unit:
    """A unit plus the units it must never be confused with."""

    unit_id: str
    singular: str
    plural: str
    forbidden: tuple[str, ...] = ()


UNITS: dict[str, Unit] = {
    "weighted_working_sets": Unit("weighted_working_sets", "weighted working set", "weighted working sets",
                                  ("day", "days", "session", "sessions", "minute", "minutes", "hour", "hours", "bpm", "au")),
    "working_sets": Unit("working_sets", "working set", "working sets",
                         ("day", "days", "minute", "minutes", "hour", "hours", "bpm")),
    "sessions": Unit("sessions", "session", "sessions", ("day", "days", "set", "sets", "minute", "minutes")),
    "training_days": Unit("training_days", "training day", "training days",
                          ("set", "sets", "minute", "minutes", "hour", "hours", "au")),
    "minutes": Unit("minutes", "minute", "minutes", ("set", "sets", "day", "days", "au", "load")),
    "hours": Unit("hours", "hour", "hours", ("set", "sets", "minute", "minutes", "au")),
    "ms": Unit("ms", "millisecond", "milliseconds", ("bpm", "beats per minute")),
    "bpm": Unit("bpm", "beat per minute", "beats per minute", ("millisecond", "milliseconds", "ms")),
    "rpe": Unit("rpe", "RPE point", "RPE points", ("rir",)),
    "rir": Unit("rir", "RIR", "RIR", ("rpe",)),
    "readiness_index": Unit("readiness_index", "index point", "index points",
                            ("set", "sets", "minute", "minutes", "au", "bpm", "ms")),
    "training_load_au": Unit("training_load_au", "arbitrary unit", "arbitrary units",
                             ("minute", "minutes", "hour", "hours", "set", "sets", "day", "days")),
    "confidence_label": Unit("confidence_label", "confidence level", "confidence level", ()),
    "status_label": Unit("status_label", "status", "status", ()),
}


def format_quantity(value: float | int, unit_id: str) -> str:
    """Render a number with its unit, e.g. ``9.5 weighted working sets``."""
    unit = UNITS[unit_id]
    number = f"{float(value):g}"
    label = unit.singular if abs(float(value) - 1) < 1e-9 else unit.plural
    if unit_id == "bpm":
        return f"{number} bpm"
    return f"{number} {label}"


# --------------------------------------------------------------------------- #
# 2. Muscle taxonomy aliases (only what the product taxonomy supports)
# --------------------------------------------------------------------------- #


LEG_GROUPS: tuple[str, ...] = ("Quads", "Hamstrings / Glutes")

#: alias -> (canonical group(s), optional clarifying note)
MUSCLE_ALIASES: dict[str, tuple[tuple[str, ...], str | None]] = {
    "back": (("Back",), None),
    "lats": (("Back",), "lats are tracked inside the Back group"),
    "lat": (("Back",), "lats are tracked inside the Back group"),
    "chest": (("Chest",), None),
    "pecs": (("Chest",), "pecs are tracked inside the Chest group"),
    "pec": (("Chest",), "pecs are tracked inside the Chest group"),
    "shoulders": (("Shoulders",), None),
    "shoulder": (("Shoulders",), None),
    "delts": (("Shoulders",), "deltoids are tracked inside the Shoulders group"),
    "arms": (("Arms",), None),
    "biceps": (("Arms",), "biceps are tracked inside the Arms group"),
    "triceps": (("Arms",), "triceps are tracked inside the Arms group"),
    "quads": (("Quads",), None),
    "quad": (("Quads",), None),
    "quadriceps": (("Quads",), None),
    "hamstrings": (("Hamstrings / Glutes",), None),
    "hams": (("Hamstrings / Glutes",), None),
    "glutes": (("Hamstrings / Glutes",), None),
    "core": (("Core",), None),
    "abs": (("Core",), "abdominals are tracked inside the Core group"),
    "legs": (LEG_GROUPS, "the product tracks quads and hamstrings/glutes as separate groups"),
}


def muscle_groups_from_text(text: str) -> tuple[tuple[str, ...], str | None]:
    """Resolve muscle aliases that the product taxonomy can map reliably."""
    lowered = text.casefold()
    for alias in sorted(MUSCLE_ALIASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            groups, note = MUSCLE_ALIASES[alias]
            return groups, note
    return (), None


# --------------------------------------------------------------------------- #
# 3. Structured facts
# --------------------------------------------------------------------------- #


EXPOSURE_PERIOD = "the last seven days including today"
TRAINING_LOAD_PERIOD = "the last 7 complete calendar days"


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _completed_rows(profile: Mapping[str, Any], today: date) -> list[dict[str, Any]]:
    rows = [dict(row) for row in profile.get("training_history", []) if row.get("date") and row.get("completed", True)]
    return [row for row in rows if (_as_date(row["date"]) or today) <= today]


def _weekly_rows(profile: Mapping[str, Any], today: date) -> list[dict[str, Any]]:
    """Same window as ``training_recommendation_engine.weekly_training_exposure``."""
    rows = []
    for row in _completed_rows(profile, today):
        age = (today - _as_date(row["date"])).days
        if 0 <= age < 7:
            rows.append(row)
    return rows


def _last_trained(rows: Iterable[Mapping[str, Any]], group: str, today: date) -> dict[str, Any] | None:
    for row in sorted(rows, key=lambda item: _as_date(item["date"]), reverse=True):
        groups = [str(item) for item in row.get("muscle_groups", [])]
        contributions = row.get("muscle_set_contributions") or {}
        if group in groups or float(contributions.get(group, 0) or 0) > 0:
            when = _as_date(row["date"])
            return {"date": when.isoformat() if when else None, "days_ago": (today - when).days if when else None,
                    "session": row.get("primary_focus") or row.get("training_type")}
    return None


def build_personal_facts(profile: Mapping[str, Any], assessment: Mapping[str, Any],
                         recommendation: Mapping[str, Any] | None, today: date | None = None) -> dict[str, Any]:
    """Read-only projection of the deterministic state. Every value names a source."""
    day = today or date.today()
    today_data = dict(assessment.get("today_data") or {})
    measurements = dict(assessment.get("measurements") or {})
    baseline = dict(assessment.get("baseline") or {})
    load = dict(measurements.get("training_load") or {})
    weekly_rows = _weekly_rows(profile, day)
    exposure = dict((recommendation or {}).get("weekly_exposure") or {})
    targets = dict((recommendation or {}).get("weekly_targets") or {})
    target_source = (recommendation or {}).get("target_source")

    facts: dict[str, Any] = {
        "as_of": day.isoformat(),
        "profile": {"name": profile.get("name"), "is_demo": bool(profile.get("is_demo"))},
        "readiness": {
            "status": assessment.get("overall_readiness"),
            "index": assessment.get("readiness_index"),
            "confidence": assessment.get("assessment_confidence"),
            "domains": dict(assessment.get("domains") or {}),
            "contributors": list(assessment.get("key_contributors") or []),
            "safety_flags": list(assessment.get("safety_flags") or []),
            "period": "today",
            "source": "readiness_engine.assess_readiness",
        },
        "weekly_exposure": {
            "period": EXPOSURE_PERIOD,
            "unit": "weighted_working_sets",
            "target_period": "configured weekly target",
            "target_source": target_source,
            "groups": {group: {"value": float(value or 0), "unit": "weighted_working_sets",
                               "target": float(targets.get(group, 0) or 0) if targets else None}
                       for group, value in exposure.items()},
            "source": "training_recommendation_engine.weekly_training_exposure",
        },
        "weekly_training_days": {
            "value": len({row["date"] for row in weekly_rows}),
            "unit": "training_days",
            "period": EXPOSURE_PERIOD,
            "dates": sorted({row["date"] for row in weekly_rows}),
            "source": "profile.training_history (completed sessions)",
        },
        "weekly_sessions": {
            "value": len(weekly_rows),
            "unit": "sessions",
            "period": EXPOSURE_PERIOD,
            "source": "profile.training_history (completed sessions)",
        },
        "muscle_last_trained": {group: _last_trained(_completed_rows(profile, day), group, day)
                                for group in ("Chest", "Back", "Shoulders", "Arms", "Quads", "Hamstrings / Glutes", "Core")},
        "recent_training": [
            {"date": row.get("date"), "focus": row.get("primary_focus") or row.get("training_type"),
             "training_type": row.get("training_type"), "session_rpe": row.get("session_rpe"),
             "session_load": row.get("session_load"), "duration_min": row.get("duration_min"),
             "working_sets": row.get("actual_sets") or row.get("working_sets")}
            for row in sorted(_completed_rows(profile, day), key=lambda item: _as_date(item["date"]), reverse=True)[:7]
        ],
        "local_soreness": {
            "period": "today",
            "groups": dict(today_data.get("local_soreness") or {}),
            "subjective_soreness": today_data.get("soreness"),
            "source": "daily check-in (local soreness)",
        },
        "signals": {
            "hrv": {"value": today_data.get("rmssd_ms"), "unit": "ms", "z_score": (measurements.get("hrv") or {}).get("z_score"),
                    "status": (measurements.get("hrv") or {}).get("status"), "period": "today"},
            "resting_hr": {"value": today_data.get("resting_hr_bpm"), "unit": "bpm",
                           "z_score": (measurements.get("rhr") or {}).get("z_score"),
                           "status": (measurements.get("rhr") or {}).get("status"), "period": "today"},
            "sleep": {"value": today_data.get("sleep_hours"), "unit": "hours",
                      "need": today_data.get("personal_sleep_need") or profile.get("personal_sleep_need"),
                      "status": (measurements.get("sleep_duration") or {}).get("status"), "period": "today"},
            "subjective": {"fatigue": today_data.get("fatigue"), "stress": today_data.get("stress"),
                           "soreness": today_data.get("soreness"), "motivation": today_data.get("motivation"),
                           "unit": "1-5 scale", "period": "today"},
            "baseline": {"confidence": baseline.get("confidence"), "valid_days": baseline.get("valid_days"),
                         "window_days": baseline.get("window_days")},
        },
        "training_load": {
            "value": load.get("recent_7d_mean"),
            "unit": "training_load_au",
            "definition": "daily session duration (min) x session RPE, averaged per day",
            "period": TRAINING_LOAD_PERIOD,
            "comparison": "the preceding 21 complete calendar days",
            "reference_value": load.get("reference_21d_mean"),
            "status": load.get("status"),
            "detail": load.get("detail"),
            "source": "readiness_engine.assess_readiness (training load domain)",
        },
        "recommendation": {
            "primary": ((recommendation or {}).get("primary") or {}).get("name"),
            "training_type": ((recommendation or {}).get("primary") or {}).get("training_type"),
            "session_demand": (recommendation or {}).get("intensity"),
            "duration": {"text": (recommendation or {}).get("duration"),
                         "value": ((recommendation or {}).get("primary") or {}).get("estimated_duration_min"),
                         "unit": "minutes"},
            "prescription": [
                {"exercise": item.get("name"), "sets": item.get("working_sets", item.get("sets")),
                 "reps": item.get("reps"), "rir": item.get("rir")}
                for item in ((recommendation or {}).get("primary") or {}).get("exercises", [])
            ],
            "alternatives": [item.get("name") for item in (recommendation or {}).get("alternatives", [])],
            "avoid": list((recommendation or {}).get("avoid") or []),
            "rationale": list((recommendation or {}).get("rationale") or []),
            "period": "today",
            "source": "training_recommendation_engine.recommend_training",
        },
    }
    return facts


def facts_numbers(facts: Mapping[str, Any]) -> set[str]:
    """Every number the facts legitimately contain (used by the response guard)."""
    numbers: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple, set)):
            for value in node:
                walk(value)
        elif isinstance(node, bool):
            return
        elif isinstance(node, (int, float)):
            numbers.add(f"{float(node):g}")
        elif isinstance(node, str):
            for found in re.findall(r"\d+(?:\.\d+)?", node):
                numbers.add(f"{float(found):g}")

    walk(facts)
    numbers.update({"1", "0.5", "1.0"})  # documented direct/indirect set weighting
    return numbers


def facts_for_prompt(facts: Mapping[str, Any]) -> str:
    """Unit-bearing context. Never emits a bare number."""
    lines: list[str] = []
    readiness = facts["readiness"]
    lines.append(f"Today's readiness: {readiness['status']} (index {readiness['index']}/100, baseline confidence {readiness['confidence']}).")
    lines.append("Readiness domains: " + ", ".join(f"{name} {value}" for name, value in readiness["domains"].items()) + ".")
    if readiness["contributors"]:
        lines.append("Main contributors: " + "; ".join(readiness["contributors"][:3]) + ".")
    recommendation = facts["recommendation"]
    lines.append(f"Today's primary recommendation: {recommendation['primary']} (training type {recommendation['training_type']}, "
                 f"session demand {recommendation['session_demand']}, recommended session duration {recommendation['duration']['text']}).")
    if recommendation["alternatives"]:
        lines.append("Rule-generated alternatives: " + ", ".join(recommendation["alternatives"]) + ".")
    prescription = recommendation.get("prescription") or []
    if prescription:
        lines.append("Primary prescription: " + "; ".join(
            f"{item['exercise']} {item['sets']} sets x {item['reps']} at {item['rir']}" for item in prescription) + ".")
    lines.append("Avoid today: " + (", ".join(recommendation["avoid"]) or "none") + ".")
    exposure = facts["weekly_exposure"]
    exposure_items = []
    for group, entry in exposure["groups"].items():
        target = "" if entry.get("target") in (None, 0) else f" (target {format_quantity(entry['target'], 'weighted_working_sets')})"
        exposure_items.append(f"{group}: {format_quantity(entry['value'], 'weighted_working_sets')}{target}")
    lines.append(f"Weekly exposure for {exposure['period']} [unit: weighted working sets; direct sets count 1.0, mapped secondary sets 0.5; "
                 f"NOT days and NOT sessions]: " + "; ".join(exposure_items) + ".")
    days = facts["weekly_training_days"]
    sessions = facts["weekly_sessions"]
    lines.append(f"Completed training for {days['period']}: {format_quantity(days['value'], 'training_days')} "
                 f"across {format_quantity(sessions['value'], 'sessions')} completed sessions.")
    last = facts["muscle_last_trained"]
    last_items = [f"{group}: {entry['date']} ({entry['days_ago']} days ago, {entry['session']})"
                  for group, entry in last.items() if entry]
    if last_items:
        lines.append("Most recent completed session per muscle group: " + "; ".join(last_items) + ".")
    recent = facts.get("recent_training") or []
    if recent:
        lines.append("Recent completed sessions (newest first): " + "; ".join(
            f"{row['date']} {row['focus']} (RPE {row['session_rpe']}, {row['duration_min']} min, {row['working_sets']} working sets)"
            for row in recent[:5]) + ".")
    signals = facts["signals"]
    hrv, rhr, sleep = signals["hrv"], signals["resting_hr"], signals["sleep"]
    lines.append(f"Today's signals: HRV {hrv['value']} ms (z {hrv['z_score']}, status {hrv['status']}); "
                 f"resting HR {rhr['value']} bpm (z {rhr['z_score']}, status {rhr['status']}); "
                 f"sleep {sleep['value']} hours against a personal need of {sleep['need']} hours (status {sleep['status']}).")
    load = facts["training_load"]
    lines.append(f"Training load for {load['period']}: {load['value']} AU mean daily load "
                 f"(compared with {load['comparison']}: {load['reference_value']} AU). Definition: {load['definition']}. "
                 f"Training load is NOT session duration.")
    soreness = facts["local_soreness"]
    reported = ", ".join(f"{group} {value}/5" for group, value in soreness["groups"].items()) or "not reported"
    lines.append(f"Local soreness today: {reported}.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 4. Router
# --------------------------------------------------------------------------- #


SAFETY_TERMS = ("chest pain", "fainting", "passing out", "severe shortness", "shortness of breath",
                "acute injury", "fever", "numbness", "neurological", "can't breathe")

CORRECTION_PATTERNS = (
    r"\bthat'?s (wrong|incorrect|not right|false)\b", r"\bthat is (wrong|incorrect|not right|false)\b",
    r"\byou are wrong\b", r"\byou'?re wrong\b", r"\bmistake\b",
    r"\bare you sure\b", r"\bis that (right|correct|true)\b", r"\bcheck (that |it )?again\b",
    r"\bthat doesn'?t make sense\b", r"\bthat does not make sense\b", r"\bdoesn'?t add up\b",
    r"\byou said\b", r"\byou told me\b", r"\bthat can'?t be\b",
    r"\b(one|a|the) week (only )?(has|have) (only )?7 days\b", r"\b7 days in a week\b",
    r"\bnot \d+(\.\d+)? ?(days|sets|sessions|minutes|hours)\b", r"\bwrong (unit|number|answer)\b",
)

PERSONAL_MARKERS = ("my ", "i ", "i've", "i have", "have i", "did i", "do i", "am i", "how much", "how many")

EXPLANATION_PATTERNS = (
    r"\bwhy\b", r"\bexplain\b", r"\bcan i train harder\b", r"\bshould i (train|reduce|add)\b",
    r"\bcan i (train|do|swap|replace)\b", r"\bwhat does my readiness mean\b", r"\bis it ok(ay)? to\b",
)

GENERAL_PATTERNS = (
    r"\bwhat is rir\b", r"\bwhat'?s rir\b", r"\bdefine rir\b", r"\bwhat is rpe\b", r"\bwhat'?s rpe\b",
    r"\bwhat does rir mean\b", r"\bwarm ?up\b", r"\bwhy is sleep important\b", r"\bdeload\b",
    r"\bfailure\b", r"\bhow often\b", r"\btwice a week\b", r"\bper week\b", r"\bprotein\b", r"\bcreatine\b",
)

SCOPE_TERMS = ("capital of", "weather", "stock price", "who won", "translate", "write me a poem")


@dataclass(frozen=True)
class Route:
    kind: str
    metric: str | None = None
    groups: tuple[str, ...] = ()
    note: str | None = None
    previous_question: str | None = None
    matched: tuple[str, ...] = field(default_factory=tuple)

    def as_trace(self) -> dict[str, Any]:
        return {"route": self.kind, "metric": self.metric, "groups": list(self.groups), "note": self.note}


FACT_METRICS = ("readiness", "readiness_index", "baseline_confidence", "recommendation", "session_demand",
                "session_duration", "weekly_exposure", "weekly_target", "weekly_training_days",
                "weekly_sessions", "recent_training", "muscle_last_trained", "local_soreness",
                "hrv", "resting_hr", "sleep", "training_load")


def _previous_question(history: Iterable[Mapping[str, str]]) -> str | None:
    questions = [str(message.get("content", "")) for message in history if message.get("role") == "user"]
    return questions[-1] if questions else None


def _previous_assistant_answer(history: Iterable[Mapping[str, str]]) -> str | None:
    answers = [str(message.get("content", "")) for message in history if message.get("role") == "assistant"]
    return answers[-1] if answers else None


def _is_correction(question: str, history: Iterable[Mapping[str, str]]) -> bool:
    if not _previous_assistant_answer(history):
        return False
    lowered = question.casefold().strip()
    return any(re.search(pattern, lowered) for pattern in CORRECTION_PATTERNS)


def _fact_metric(question: str) -> tuple[str | None, tuple[str, ...], str | None]:
    """Deterministic metric detection. Returns (metric, groups, note)."""
    q = question.casefold()
    groups, note = muscle_groups_from_text(q)
    has_marker = any(marker in q for marker in PERSONAL_MARKERS)

    def has(*terms: str) -> bool:
        return any(term in q for term in terms)

    if has("training load", "session load", "load today", "my load", "how much load"):
        return "training_load", (), None
    if has("baseline confidence", "confidence in my baseline", "how confident"):
        return "baseline_confidence", (), None
    if has("readiness index", "readiness score"):
        return "readiness_index", (), None
    if has("session demand", "how hard should i train", "how hard is today", "how hard today"):
        return "session_demand", (), None
    if has("how long", "duration", "how many minutes") and has("train", "session", "workout", "today"):
        return "session_duration", (), None
    if has("how many days") and has("train", "train ", "session"):
        return "weekly_training_days", (), None
    if has("how many sessions", "how many workouts have i", "how many times have i trained"):
        return "weekly_sessions", (), None
    if has("when did i last train", "last time i trained", "last trained", "most recent session for"):
        return "muscle_last_trained", groups, note
    if has("recent training", "what did i train recently", "what have i trained recently", "last few sessions", "recent sessions"):
        return "recent_training", groups, note
    if has("weekly target", "my target", "target for", "goal for") and (groups or has("back", "chest", "legs", "arms", "shoulders", "core")):
        return "weekly_target", groups, note
    if has("exposure") or (has_marker and has("how much have i trained", "how much have i done", "how many sets",
                                              "sets have i done", "sets this week", "volume this week", "trained this week",
                                              "trained back", "trained chest", "trained legs")):
        return "weekly_exposure", groups, note
    if has("sore", "soreness"):
        return "local_soreness", groups, None
    if has("hrv", "rmssd", "heart rate variability"):
        return "hrv", (), None
    if has("resting heart rate", "resting hr", "rhr"):
        return "resting_hr", (), None
    if has("sleep"):
        return "sleep", (), None
    if has("what am i training", "what should i train", "today's workout", "todays workout", "my workout",
           "primary recommendation", "what workout", "what am i doing today"):
        return "recommendation", (), None
    if has_marker and has("readiness", "ready"):
        return "readiness", (), None
    return None, (), None


def route_question(question: str, history: Iterable[Mapping[str, str]] = (), facts: Mapping[str, Any] | None = None) -> Route:
    """Deterministic intent routing. No model is involved."""
    q = question.casefold().strip()
    if any(term in q for term in SAFETY_TERMS):
        return Route("SAFETY", matched=("safety-term",))
    if facts and (facts.get("readiness", {}).get("status") == STOP):
        return Route("SAFETY", matched=("safety-status",))
    if _is_correction(question, history):
        return Route("CORRECTION", previous_question=_previous_question(history), matched=("correction",))
    if any(term in q for term in SCOPE_TERMS):
        return Route("SCOPE", matched=("out-of-scope",))

    metric, groups, note = _fact_metric(question)
    if metric:
        return Route("PERSONAL_FACT", metric=metric, groups=groups, note=note, matched=("metric:" + metric,))

    if any(re.search(pattern, q) for pattern in EXPLANATION_PATTERNS):
        return Route("EXPLANATION", groups=groups, note=note, matched=("explanation",))
    if any(re.search(pattern, q) for pattern in GENERAL_PATTERNS):
        return Route("GENERAL", matched=("general",))
    personal_state_cues = ("how is my", "how are my", "how's my", "what's my", "what is my", "how am i",
                           "how did i", "how much", "how many", "is my", "are my")
    if any(marker in q for marker in PERSONAL_MARKERS) and (
        any(cue in q for cue in personal_state_cues)
        or any(word in q for word in ("week", "today", "set", "sets", "readiness", "train", "training", "recover", "sleep", "load"))
    ):
        return Route("UNRESOLVED_PERSONAL", groups=groups, note=note, matched=("unresolved-personal",))
    return Route("GENERAL", matched=("default",))


# --------------------------------------------------------------------------- #
# 5. Grounded answers
# --------------------------------------------------------------------------- #


NOT_AVAILABLE = "I don't have enough recorded data for that yet."
CLARIFICATION = ("I can answer from your recorded data for readiness, today's recommendation, weekly exposure, "
                 "recent training and recovery signals. Which metric do you want?")


def _target_suffix(entry: Mapping[str, Any]) -> str:
    target = entry.get("target")
    if target in (None, 0):
        return ""
    return f", against your current weekly target of {format_quantity(target, 'weighted_working_sets')}"


def grounded_answer(route: Route, facts: Mapping[str, Any]) -> str:
    """Deterministic factual answer. No model output is used here."""
    metric = route.metric
    if metric == "weekly_exposure":
        exposure = facts["weekly_exposure"]
        groups = route.groups or tuple(exposure["groups"])
        if facts["weekly_sessions"]["value"] == 0 and not any(
            (exposure["groups"].get(group) or {}).get("value") for group in groups
        ):
            return (f"I don't have enough recorded training data for {exposure['period']} - no completed sessions are "
                    f"recorded yet.")
        lines = []
        for group in groups:
            entry = exposure["groups"].get(group)
            if not entry or entry["value"] is None:
                lines.append(f"I don't have enough recorded {group} training data for {exposure['period']}.")
                continue
            lines.append(f"**{group}: {format_quantity(entry['value'], 'weighted_working_sets')}**{_target_suffix(entry)}")
        detail = (f"Weekly exposure covers {exposure['period']} and is measured in weighted working sets "
                  f"(direct sets count as 1.0 and mapped secondary sets as 0.5) - not days and not sessions.")
        if route.note:
            detail = f"Note: {route.note}. " + detail
        return " ".join(lines) + ". " + detail
    if metric == "weekly_target":
        exposure = facts["weekly_exposure"]
        groups = route.groups or tuple(exposure["groups"])
        lines = []
        for group in groups:
            entry = exposure["groups"].get(group) or {}
            if not entry.get("target"):
                lines.append(f"No weekly set target is configured for {group}.")
            else:
                lines.append(f"**{group} weekly target: {format_quantity(entry['target'], 'weighted_working_sets')}** "
                             f"(current exposure {format_quantity(entry['value'], 'weighted_working_sets')}).")
        return " ".join(lines) + f" Target source: {exposure.get('target_source') or 'not recorded'}."
    if metric == "weekly_training_days":
        days = facts["weekly_training_days"]
        sessions = facts["weekly_sessions"]
        if not days["value"]:
            return f"No completed sessions are recorded for {days['period']}."
        listed = ", ".join(days["dates"])
        return (f"You have completed **{format_quantity(days['value'], 'training_days')}** for {days['period']} "
                f"({format_quantity(sessions['value'], 'sessions')}: {listed}). Training days are counted from completed "
                f"sessions, not from weekly set exposure.")
    if metric == "weekly_sessions":
        sessions = facts["weekly_sessions"]
        if not sessions["value"]:
            return f"No completed sessions are recorded for {sessions['period']}."
        return f"You have completed **{format_quantity(sessions['value'], 'sessions')}** in {sessions['period']}."
    if metric == "session_duration":
        duration = facts["recommendation"]["duration"]
        if not duration["text"]:
            return "No session duration is available for today."
        return (f"Today's recommended session duration is **{duration['text']}**. This is session duration in minutes, "
                f"not training load.")
    if metric == "training_load":
        load = facts["training_load"]
        if load["value"] is None:
            return "Training load is not available yet - it needs completed sessions with duration and session RPE."
        return (f"Your training load is **{format_quantity(load['value'], 'training_load_au')}** (mean daily load over "
                f"{load['period']}), compared with {load['reference_value']} AU over {load['comparison']}. "
                f"Training load is duration x session RPE in arbitrary units - it is not minutes and not sets.")
    if metric == "recommendation":
        recommendation = facts["recommendation"]
        if not recommendation["primary"]:
            return "No workout recommendation has been generated yet."
        return (f"Today's primary recommendation is **{recommendation['primary']}** "
                f"({recommendation['session_demand']}, {recommendation['duration']['text']}, {recommendation['training_type']}).")
    if metric == "session_demand":
        recommendation = facts["recommendation"]
        return (f"Today's session demand is **{recommendation['session_demand']}** with the primary recommendation "
                f"{recommendation['primary']} ({recommendation['duration']['text']}).")
    if metric in {"readiness", "readiness_index"}:
        readiness = facts["readiness"]
        index = readiness["index"] if readiness["index"] is not None else "not available"
        if metric == "readiness_index":
            return (f"Your readiness index today is **{index} / 100**, with an overall readiness status of "
                    f"{readiness['status']} and baseline confidence {readiness['confidence']}.")
        domains = ", ".join(f"{name} {value}" for name, value in readiness["domains"].items())
        return (f"Your readiness today is **{readiness['status']}** (index {index} / 100, baseline confidence "
                f"{readiness['confidence']}). Domains: {domains}.")
    if metric == "baseline_confidence":
        return f"Your baseline confidence is **{facts['readiness']['confidence']}**."
    if metric == "local_soreness":
        soreness = facts["local_soreness"]
        groups = route.groups or tuple(soreness["groups"])
        if not soreness["groups"]:
            return "No local soreness was recorded in today's check-in, so I have no recorded value to report."
        lines = []
        for group in groups:
            value = soreness["groups"].get(group)
            if value is None:
                lines.append(f"No {group} soreness was recorded in today's check-in.")
            else:
                lines.append(f"**{group} soreness: {value}/5** (today's check-in).")
        return " ".join(lines)
    if metric in {"hrv", "resting_hr", "sleep"}:
        signal = facts["signals"]["hrv" if metric == "hrv" else "resting_hr" if metric == "resting_hr" else "sleep"]
        if signal["value"] is None:
            return f"No {metric.replace('_', ' ')} value is recorded for today."
        if metric == "sleep":
            return (f"Your recorded sleep today is **{signal['value']} hours** against a personal sleep need of "
                    f"{signal['need']} hours (status {signal['status']}).")
        return (f"Your recorded {metric.replace('_', ' ')} today is **{format_quantity(signal['value'], signal['unit'])}** "
                f"(status {signal['status']}, deviation {signal['z_score']} SD from your own baseline).")
    if metric == "recent_training":
        rows = facts.get("recent_training") or []
        if not rows:
            return "No completed sessions are recorded yet."
        listed = "; ".join(f"{row['date']}: {row['focus']}" for row in rows[:5])
        return f"Your most recent completed sessions: {listed}."
    if metric == "muscle_last_trained":
        groups = route.groups or tuple(facts["muscle_last_trained"])
        lines = []
        for group in groups:
            entry = facts["muscle_last_trained"].get(group)
            if not entry:
                lines.append(f"No completed {group} session is recorded.")
            else:
                lines.append(f"**{group} was last trained on {entry['date']}** ({entry['days_ago']} days ago, {entry['session']}).")
        return " ".join(lines)
    return NOT_AVAILABLE


def correction_answer(previous_route: Route | None, facts: Mapping[str, Any], previous_answer: str | None) -> str:
    """Re-read the source of truth and correct or re-confirm the previous claim."""
    if previous_route is None or previous_route.kind != "PERSONAL_FACT":
        return ("I could not verify the previous statement against your recorded data, so I will not repeat it. "
                + CLARIFICATION)
    corrected = grounded_answer(previous_route, facts)
    if _answer_was_wrong(previous_route, previous_answer, facts):
        return "You're right - I used the wrong unit or value in my previous answer. The verified value is: " + corrected
    return "I re-checked your recorded data. " + corrected


def _answer_was_wrong(route: Route, previous_answer: str | None, facts: Mapping[str, Any]) -> bool:
    if not previous_answer:
        return False
    lowered = previous_answer.casefold()
    allowed = facts_numbers(facts)
    metric_unit = {
        "weekly_exposure": "weighted_working_sets",
        "weekly_target": "weighted_working_sets",
        "weekly_training_days": "training_days",
        "weekly_sessions": "sessions",
        "session_duration": "minutes",
        "training_load": "training_load_au",
    }.get(route.metric or "")
    if metric_unit:
        # Only a *quantity* in the wrong unit counts as contamination: a correct
        # answer may legitimately say "this is not minutes and not sets".
        for word in UNITS[metric_unit].forbidden:
            if re.search(rf"\d+(?:\.\d+)?\s*{re.escape(word)}\b", lowered):
                return True
    for number in re.findall(r"\d+(?:\.\d+)?", lowered):
        if f"{float(number):g}" not in allowed:
            return True
    return False


def guard_llm_response(text: str, facts: Mapping[str, Any], question: str = "", route: Route | None = None) -> tuple[bool, str]:
    """Reject model output that adds numbers, changes units or shifts the period."""
    allowed = facts_numbers(facts)
    allowed.update(f"{float(value):g}" for value in re.findall(r"\d+(?:\.\d+)?", question))
    # Personal numbers are held to a strict allow-list. A purely general training
    # question may legitimately quote general guidance, so only unit and period
    # integrity is enforced there.
    if route is None or route.kind != "GENERAL":
        for number in re.findall(r"\d+(?:\.\d+)?", text):
            if f"{float(number):g}" not in allowed:
                return False, f"The draft introduced a number that is not in the verified facts: {number}"
    lowered = text.casefold()
    if re.search(r"\btraining load\b[^.]{0,24}\b\d+\s*(?:-|to|–)?\s*\d*\s*(?:min|minute|minutes)\b", lowered):
        return False, "The draft described session minutes as training load."
    if route and route.metric in {"weekly_exposure", "weekly_target"}:
        # A bare negation ("not days") is fine; a quantity is not.
        if re.search(r"\d+(?:\.\d+)?\s*(?:day|days|session|sessions)\b", lowered) or re.search(
            r"\b(?:trained|training|trained for)\b[^.]{0,24}\b(?:day|days|sessions)\b", lowered
        ):
            return False, "The draft expressed weekly set exposure as days or sessions."
    if route and route.metric == "weekly_training_days" and re.search(r"\d+(?:\.\d+)?\s*(?:set|sets)\b", lowered):
        return False, "The draft expressed training days in sets."
    if route and route.metric == "session_duration" and re.search(r"\btraining load\b|\bau\b", lowered):
        return False, "The draft described session duration as training load."
    if route and route.metric == "training_load" and re.search(r"\b(min|minute|minutes|hours)\b", lowered):
        return False, "The draft described training load in time units."
    if re.search(r"\b(month|monthly|last month)\b", lowered) and "month" not in question.casefold():
        return False, "The draft changed the reporting period."
    return True, "Grounded in the verified facts"


#: Concept words that appear in the deterministic rationale / decision factors.
RATIONALE_ANCHORS = ("readiness", "session demand", "exposure", "programme", "split", "soreness",
                     "goal", "recent training", "training load", "recovery", "volume", "target",
                     "completed session")


def guard_explanation_grounding(text: str, facts: Mapping[str, Any]) -> tuple[bool, str]:
    """An explanation of *the user's own plan* must reference verified rationale.

    A small model can otherwise invent a plausible-sounding reason ("you are
    training back to build your core") that contradicts the recorded decision
    factors. Deterministic rationale elements include the readiness status, the
    primary recommendation name, and the engine's decision-factor concepts.
    """
    lowered = text.casefold()
    anchors = {str(facts["readiness"]["status"]).casefold()}
    if facts["recommendation"]["primary"]:
        anchors.add(str(facts["recommendation"]["primary"]).casefold())
    if facts["recommendation"]["session_demand"]:
        anchors.add(str(facts["recommendation"]["session_demand"]).casefold())
    anchors.update(RATIONALE_ANCHORS)
    anchors.update(str(item).casefold() for item in facts["recommendation"].get("rationale", []))
    # Muscle-group names are deliberately NOT anchors: "training back" alone says
    # nothing about the recorded reason for the recommendation.
    if not any(anchor and anchor in lowered for anchor in anchors):
        return False, "The explanation did not reference any verified rationale element."
    return True, "The explanation references verified rationale elements"
