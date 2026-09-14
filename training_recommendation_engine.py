"""Transparent, ordered rules for daily training decision support.

Readiness primarily controls session demand. Goal, programme continuity,
completed work, weekly exposure and today's local soreness determine which
compatible option is presented. No LLM participates in this module.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any, Iterable, Mapping

from readiness_engine import AMBER, GREEN, INSUFFICIENT, RED, STOP

MUSCLE_GROUPS = ("Chest", "Back", "Shoulders", "Arms", "Quads", "Hamstrings / Glutes", "Core")
_GROUP_ALIASES = {"chest": "Chest", "back": "Back", "shoulders": "Shoulders", "shoulder": "Shoulders", "arms": "Arms", "biceps": "Arms", "triceps": "Arms", "quads": "Quads", "quadriceps": "Quads", "hamstrings": "Hamstrings / Glutes", "glutes": "Hamstrings / Glutes", "hamstrings / glutes": "Hamstrings / Glutes", "core": "Core"}

RECOMMENDATION_RULE_METADATA = {
    "decision_order": ["Safety", "Data Sufficiency", "Training Goal", "Preferred Programme / Split", "Weekly Training Exposure", "Recent Completed Sessions", "Local Soreness", "Overall Readiness", "Domain-specific Modifiers", "Session Demand", "Primary + Alternatives + Avoid Today"],
    "fractional_sets": {"direct": 1.0, "indirect": 0.5, "label": "Transparent product estimate; not an exact physiological stimulus ratio."},
    "readiness_demand": {GREEN: "Normal", AMBER: "Reduced / autoregulated", RED: "Rest or lower-demand", STOP: "No normal training recommendation"},
    "rir_guidance": {"Normal": "1–3 RIR", "Reduced strength": "2–4 RIR; avoid unnecessary failure"},
}


def _canonical_group(value: object) -> str:
    text = str(value).strip()
    return _GROUP_ALIASES.get(text.casefold(), text)


EXERCISE_MUSCLE_MAPPING: dict[str, dict[str, list[str]]] = {
    "Bench Press": {"direct": ["Chest"], "secondary": ["Arms", "Shoulders"]},
    "Incline Press": {"direct": ["Chest"], "secondary": ["Arms", "Shoulders"]},
    "Lat Pulldown": {"direct": ["Back"], "secondary": ["Arms"]},
    "Chest-Supported Row": {"direct": ["Back"], "secondary": ["Arms", "Shoulders"]},
    "Cable Row": {"direct": ["Back"], "secondary": ["Arms"]},
    "Squat": {"direct": ["Quads", "Hamstrings / Glutes"], "secondary": []},
    "Romanian Deadlift": {"direct": ["Hamstrings / Glutes"], "secondary": ["Back"]},
    "Shoulder Press": {"direct": ["Shoulders"], "secondary": ["Arms"]},
    "Curl": {"direct": ["Arms"], "secondary": []},
    "Triceps Extension": {"direct": ["Arms"], "secondary": []},
    "Rear Delt Fly": {"direct": ["Shoulders"], "secondary": []},
}


def _exercise(name: str, sets: int, reps: str = "8–12") -> dict[str, Any]:
    return {"name": name, "sets": sets, "working_sets": sets, "reps": reps}


WORKOUTS: tuple[dict[str, Any], ...] = (
    {"id": "back_biceps", "name": "Back + Biceps", "training_type": "Strength", "focus": "Pull", "muscle_groups": ["Back", "Arms"], "split": "Push / Pull / Legs", "exercises": [_exercise("Lat Pulldown", 3), _exercise("Chest-Supported Row", 3), _exercise("Cable Row", 2), _exercise("Rear Delt Fly", 2, "10–15"), _exercise("Curl", 3, "8–15")]},
    {"id": "chest_triceps", "name": "Chest + Triceps", "training_type": "Strength", "focus": "Push", "muscle_groups": ["Chest", "Arms"], "split": "Push / Pull / Legs", "exercises": [_exercise("Bench Press", 3), _exercise("Incline Press", 3), _exercise("Triceps Extension", 3, "8–15")]},
    {"id": "legs", "name": "Legs", "training_type": "Strength", "focus": "Legs", "muscle_groups": ["Quads", "Hamstrings / Glutes"], "split": "Push / Pull / Legs", "exercises": [_exercise("Squat", 3, "5–10"), _exercise("Romanian Deadlift", 3, "6–10")]},
    {"id": "shoulders_arms", "name": "Shoulders + Arms", "training_type": "Strength", "focus": "Upper accessory", "muscle_groups": ["Shoulders", "Arms"], "split": "Body Part Split", "exercises": [_exercise("Shoulder Press", 3), _exercise("Rear Delt Fly", 2, "10–15"), _exercise("Curl", 2, "8–15"), _exercise("Triceps Extension", 2, "8–15")]},
    {"id": "upper_body", "name": "Upper Body", "training_type": "Strength", "focus": "Upper", "muscle_groups": ["Chest", "Back", "Shoulders", "Arms"], "split": "Upper / Lower", "exercises": [_exercise("Bench Press", 2), _exercise("Chest-Supported Row", 2), _exercise("Shoulder Press", 2)]},
    {"id": "lower_body", "name": "Lower Body", "training_type": "Strength", "focus": "Lower", "muscle_groups": ["Quads", "Hamstrings / Glutes"], "split": "Upper / Lower", "exercises": [_exercise("Squat", 3, "5–10"), _exercise("Romanian Deadlift", 2, "6–10")]},
    {"id": "full_body", "name": "Full Body Strength", "training_type": "Strength", "focus": "Full body", "muscle_groups": ["Chest", "Back", "Shoulders", "Arms", "Quads", "Hamstrings / Glutes"], "split": "Full Body", "exercises": [_exercise("Squat", 2, "5–10"), _exercise("Bench Press", 2), _exercise("Chest-Supported Row", 2)]},
    {"id": "easy_aerobic_mobility", "name": "Easy Aerobic + Mobility", "training_type": "Aerobic", "focus": "Low-intensity aerobic", "muscle_groups": [], "split": "Recovery", "exercises": []},
    {"id": "easy_aerobic", "name": "Easy Aerobic Session", "training_type": "Aerobic", "focus": "Aerobic base", "muscle_groups": [], "split": "Running-focused", "exercises": []},
)


def _as_date(value: object) -> date:
    return value if isinstance(value, date) else datetime.fromisoformat(str(value)).date()


def fractional_set_contributions(exercises: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Count actual direct sets as 1.0 and mapped secondary sets as 0.5."""
    result = {group: 0.0 for group in MUSCLE_GROUPS}
    for exercise in exercises:
        mapping = EXERCISE_MUSCLE_MAPPING.get(str(exercise.get("name", "")))
        if not mapping:
            continue
        sets = float(exercise.get("working_sets", exercise.get("actual_sets", exercise.get("sets", 0))) or 0)
        for group in mapping["direct"]:
            result[group] += sets
        for group in mapping["secondary"]:
            result[group] += sets * RECOMMENDATION_RULE_METADATA["fractional_sets"]["indirect"]
    return {key: round(value, 1) for key, value in result.items() if value}


def _fallback_muscle_group(row: Mapping[str, Any], exercise: Mapping[str, Any] | None = None) -> str | None:
    """Resolve one explicit muscle for an otherwise unmapped exercise/session."""
    for key in ("primary_muscle_group", "muscle_group"):
        explicit = (exercise or {}).get(key) or row.get(key)
        group = _canonical_group(explicit) if explicit else None
        if group in MUSCLE_GROUPS:
            return group
    focus = str(row.get("primary_focus", "")).strip()
    focus_aliases = {"Chest + Triceps": "Chest", "Push": "Chest", "Back + Biceps": "Back", "Pull": "Back", "Legs": "Quads", "Lower": "Quads", "Upper": "Chest"}
    group = _canonical_group(focus_aliases.get(focus, focus))
    if group in MUSCLE_GROUPS:
        return group
    declared = [_canonical_group(item) for item in row.get("muscle_groups", [])]
    declared = [item for item in declared if item in MUSCLE_GROUPS]
    return declared[0] if len(declared) == 1 else None


def session_set_contributions(row: Mapping[str, Any]) -> dict[str, float]:
    """Map actual exercise sets, falling back per unknown exercise exactly once."""
    result = {group: 0.0 for group in MUSCLE_GROUPS}
    exercises = list(row.get("exercises") or [])
    for exercise in exercises:
        sets = float(exercise.get("working_sets", exercise.get("actual_sets", exercise.get("sets", 0))) or 0)
        if sets <= 0:
            continue
        mapping = EXERCISE_MUSCLE_MAPPING.get(str(exercise.get("name", "")))
        if mapping:
            for group in mapping["direct"]:
                result[group] += sets
            for group in mapping["secondary"]:
                result[group] += sets * RECOMMENDATION_RULE_METADATA["fractional_sets"]["indirect"]
        else:
            fallback = _fallback_muscle_group(row, exercise)
            if fallback:
                result[fallback] += sets
    if not exercises:
        fallback = _fallback_muscle_group(row)
        if fallback:
            result[fallback] += float(row.get("actual_sets", row.get("working_sets", 0)) or 0)
    return {key: round(value, 1) for key, value in result.items() if value}


def _sets_from_row(row: Mapping[str, Any]) -> dict[str, float]:
    result = {group: 0.0 for group in MUSCLE_GROUPS}
    contributions = row.get("muscle_set_contributions")
    valid_contribution = False
    if isinstance(contributions, Mapping) and contributions:
        for key, value in contributions.items():
            group = _canonical_group(key)
            try:
                amount = float(value or 0)
            except (TypeError, ValueError):
                continue
            if group in result and amount > 0:
                result[group] += amount
                valid_contribution = True
        if valid_contribution:
            return result
    mapped = session_set_contributions(row)
    if mapped:
        result.update(mapped)
        return result
    return result


def weekly_training_exposure(training_history: Iterable[Mapping[str, Any]], as_of: date | None = None) -> dict[str, float]:
    today = as_of or date.today()
    totals = {group: 0.0 for group in MUSCLE_GROUPS}
    for row in training_history:
        if not row.get("completed", True) or not row.get("date"):
            continue
        age = (today - _as_date(row["date"])).days
        if 0 <= age < 7:
            for group, value in _sets_from_row(row).items(): totals[group] += value
    return {key: round(value, 1) for key, value in totals.items()}


def _recent(training_history: Iterable[Mapping[str, Any]], today: date) -> list[dict[str, Any]]:
    rows = []
    for source in training_history:
        if source.get("completed", True) and source.get("date") and _as_date(source["date"]) <= today:
            row = deepcopy(dict(source)); row["muscle_groups"] = [_canonical_group(item) for item in row.get("muscle_groups", [])]; rows.append(row)
    return sorted(rows, key=lambda row: (_as_date(row["date"]), str(row.get("session_id", ""))), reverse=True)


def _local_soreness(group: str, current: Mapping[str, Any]) -> int | None:
    if current.get(group) is not None: return int(current[group])
    if group == "Hamstrings / Glutes" and current.get("Quads / Glutes") is not None: return int(current["Quads / Glutes"])
    return None


def _target_sets(profile: Mapping[str, Any], history: Iterable[Mapping[str, Any]], today: date) -> tuple[dict[str, float], str]:
    configured = profile.get("weekly_set_targets") or {}
    if configured: return {group: float(configured.get(group, 0) or 0) for group in MUSCLE_GROUPS}, "User-entered weekly set targets"
    rows = [row for row in history if row.get("date") and row.get("completed", True)]
    if rows:
        prior_weeks = [weekly_training_exposure(rows, today - timedelta(days=7 * offset)) for offset in range(1, 5)]
        values = {group: round(float(median([week[group] for week in prior_weeks])), 1) for group in MUSCLE_GROUPS}
        return values, "Median of four prior logged weeks; descriptive baseline, not an individualized prescription"
    return {group: 8.0 for group in MUSCLE_GROUPS}, "Demo heuristic starting point; not an individualized prescription"


def _split_order(profile: Mapping[str, Any], goal: str) -> list[str]:
    split = str(profile.get("training_split_preference", "No Preference"))
    if split == "Push / Pull / Legs": return ["Back + Biceps", "Chest + Triceps", "Legs", "Shoulders + Arms"]
    if split == "Upper / Lower": return ["Upper Body", "Lower Body", "Full Body Strength"]
    if split == "Body Part Split": return ["Back + Biceps", "Shoulders + Arms", "Chest + Triceps", "Legs"]
    if split == "Full Body": return ["Full Body Strength", "Upper Body", "Lower Body"]
    if split == "Running-focused" or "endurance" in goal.casefold(): return ["Easy Aerobic Session", "Easy Aerobic + Mobility", "Full Body Strength"]
    if "recovery" in goal.casefold(): return ["Easy Aerobic + Mobility", "Full Body Strength"]
    return ["Back + Biceps", "Chest + Triceps", "Legs", "Shoulders + Arms", "Full Body Strength", "Upper Body", "Lower Body"]


def _candidate_category(workout: Mapping[str, Any], exposure: Mapping[str, float], targets: Mapping[str, float], recent: list[dict[str, Any]], today: date, soreness: Mapping[str, Any]) -> str:
    groups = workout.get("muscle_groups", [])
    if groups and any((_local_soreness(group, soreness) or 0) >= 4 for group in groups): return "AVOID TODAY"
    if groups and all(targets.get(group, 0) > 0 and exposure.get(group, 0) >= targets.get(group, 0) for group in groups): return "LOW PRIORITY"
    for row in recent:
        # Do not let generic arm/shoulder secondary exposure block a programme
        # rotation (for example Push yesterday → Pull today).
        primary_groups = set(groups) - {"Arms", "Shoulders"} or set(groups)
        recent_primary = set(row.get("muscle_groups", [])) - {"Arms", "Shoulders"} or set(row.get("muscle_groups", []))
        if not primary_groups.intersection(recent_primary): continue
        days = (today - _as_date(row["date"])).days
        if days == 0 or (days == 1 and float(row.get("session_rpe") or 0) >= 8): return "LOW PRIORITY"
        if days == 1: return "AVAILABLE"
    return "HIGH PRIORITY" if groups and any(exposure.get(group, 0) < targets.get(group, 0) for group in groups) else "AVAILABLE"


def workout_prescription(workout: Mapping[str, Any], demand: str, duration: str | None = None) -> dict[str, Any]:
    """Build the single object consumed by both workout UI and training log."""
    item = deepcopy(dict(workout))
    if item["training_type"] == "Aerobic":
        item.update({"prescription_id": f"{item['id']}_lower_demand", "session_demand": "Lower-demand", "estimated_duration_min": [30, 40], "duration": duration or "30–40 min", "intensity": "RPE 3–4 / 10", "exercises": [], "instructions": ["Easy conversational pace", "Use the talk test: speak in full sentences", "Optional short mobility work"]})
        return item
    reduced = demand != "Normal"; rir = "2–4 RIR; avoid unnecessary failure" if reduced else "1–3 RIR"
    exercises = []
    for source in item.get("exercises", []):
        sets = max(1, int(source["sets"]) - 1) if reduced else int(source["sets"])
        exercises.append({"name": source["name"], "sets": sets, "working_sets": sets, "reps": source.get("reps", "8–12"), "rir": rir})
    item.update({"prescription_id": f"{item['id']}_{'reduced' if reduced else 'normal'}", "session_demand": demand, "estimated_duration_min": [35, 55] if reduced else [50, 65], "duration": duration or ("35–55 min" if reduced else "50–65 min"), "intensity": demand, "exercises": exercises, "instructions": []})
    return item


def workout_template(prescription: Mapping[str, Any]) -> dict[str, Any]:
    if prescription["training_type"] == "Aerobic":
        items = list(prescription.get("instructions", [])); note = "This is a lower-demand option; it is not described as accelerating recovery."
    else:
        items = [f"{item['name']}: {item['sets']} sets × {item['reps']} · {item['rir']}" for item in prescription.get("exercises", [])]; note = "The set and RIR ranges are practical prototype guidance, not clinical thresholds."
    return {"title": prescription["name"], "duration": prescription["duration"], "intensity": prescription["intensity"], "items": items, "note": note}


def prescription_log_defaults(prescription: Mapping[str, Any]) -> dict[str, Any]:
    """Return training-log defaults from the selected prescription only."""
    exercises = [{"name": item["name"], "working_sets": int(item["sets"]), "prescribed_sets": int(item["sets"])} for item in prescription.get("exercises", [])]
    return {"prescription_id": prescription["prescription_id"], "training_type": prescription["training_type"], "primary_focus": prescription["name"], "muscle_groups": list(prescription.get("muscle_groups", [])), "exercises": exercises, "prescribed_sets": sum(item["prescribed_sets"] for item in exercises), "actual_sets": sum(item["working_sets"] for item in exercises)}


def _recent_summary(history: list[dict[str, Any]], today: date) -> str:
    if not history: return "No completed sessions logged"
    row = history[0]; days = (today - _as_date(row["date"])).days
    timing = "today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"
    effort = "high effort" if float(row.get("session_rpe") or 0) >= 8 else "moderate effort" if float(row.get("session_rpe") or 0) >= 5 else "low effort"
    return f"{row.get('primary_focus', row.get('training_type', 'Training'))} {timing} · {effort}"


def _build_result(primary_workout: Mapping[str, Any], alternative_workouts: list[Mapping[str, Any]], status: str, demand: str, duration: str, profile: Mapping[str, Any], assessment: Mapping[str, Any], history: list[dict[str, Any]], exposure: Mapping[str, float], targets: Mapping[str, float], target_source: str, priority: Mapping[str, list[str]], today: date, extra: list[str]) -> dict[str, Any]:
    primary = workout_prescription(primary_workout, demand, duration); alternatives = [workout_prescription(item, demand) for item in alternative_workouts]
    groups = primary.get("muscle_groups", []); below = [group for group in groups if exposure.get(group, 0) < targets.get(group, 0)]
    soreness = assessment.get("today_data", {}).get("local_soreness") or {}
    soreness_text = ", ".join(f"{group} {soreness[group]}/5" for group in groups if soreness.get(group) is not None) or "No relevant local soreness reported"
    exposure_text = (", ".join(f"{group} {exposure.get(group, 0):g}/{targets.get(group, 0):g}" for group in below) + " · below target") if below else target_source
    recent_text = _recent_summary(history, today)
    factors = [f"Goal: {profile.get('training_goal', 'General Fitness')}", f"Preferred split: {profile.get('training_split_preference', 'No Preference')}", f"Weekly exposure: {exposure_text}", f"Recent completed training: {recent_text}", f"Local soreness: {soreness_text}", f"Readiness: {status}", f"Session demand: {demand}"]
    rationale = extra or [f"Readiness is {status}; today's session demand is {demand.casefold()}.", "The selected option follows programme continuity and categorical weekly-exposure priorities.", "Recent completed sessions and today's local soreness are modifiers, not absolute recovery clocks."]
    avoid = list(dict.fromkeys(priority.get("AVOID TODAY", [])))
    if int(assessment.get("today_data", {}).get("soreness", 1) or 1) >= 4: avoid.append("High reported global soreness")
    trace = [{"step": "GOAL", "value": str(profile.get("training_goal", "General Fitness"))}, {"step": "PROGRAMME", "value": str(profile.get("training_split_preference", "No Preference"))}, {"step": "WEEKLY EXPOSURE", "value": exposure_text}, {"step": "RECENT TRAINING", "value": recent_text}, {"step": "LOCAL SORENESS", "value": soreness_text}, {"step": "READINESS", "value": status}, {"step": "SESSION DEMAND", "value": demand}, {"step": "RECOMMENDATION", "value": primary["name"]}]
    return {"primary": primary, "alternatives": alternatives, "intensity": primary["intensity"], "duration": primary["duration"], "volume_modifier": demand, "reason": rationale[0], "rationale": rationale, "decision_factors": factors, "decision_trace": trace, "avoid": avoid, "priority": {key: list(value) for key, value in priority.items()}, "weekly_exposure": dict(exposure), "weekly_targets": dict(targets), "target_source": target_source, "template": workout_template(primary), "recent_training": history[:7], "evidence": {"positioning": "Evidence-informed transparent heuristic", "references": ["Saw et al. 2016 · PMID 26423706", "Bourdon et al. 2017 · PMID 28463642", "Haddad et al. 2017 · PMID 29163016", "Pelland et al. 2026 · PMID 41343037", "Refalo et al. 2023 · PMID 36334240"]}}


def recommend_training(profile: Mapping[str, Any], assessment: Mapping[str, Any], training_history: Iterable[Mapping[str, Any]], as_of: date | None = None) -> dict[str, Any]:
    today = as_of or _as_date(assessment.get("assessment_date", date.today().isoformat())); status = str(assessment.get("overall_readiness", INSUFFICIENT)); history = _recent(training_history, today)
    soreness = assessment.get("today_data", {}).get("local_soreness") or {}; exposure = weekly_training_exposure(history, today); targets, target_source = _target_sets(profile, history, today)
    goal = str(profile.get("training_goal", "General Fitness")); ordered_names = _split_order(profile, goal); by_name = {item["name"]: item for item in WORKOUTS}
    priority: dict[str, list[str]] = {"HIGH PRIORITY": [], "AVAILABLE": [], "LOW PRIORITY": [], "AVOID TODAY": []}
    for name in ordered_names: priority[_candidate_category(by_name[name], exposure, targets, history, today, soreness)].append(name)
    if status == STOP:
        primary = {"id": "stop", "name": "No normal workout recommendation", "training_type": "Rest", "focus": "Professional review", "muscle_groups": [], "exercises": []}; priority["AVOID TODAY"] = ["Normal strength", "HIIT", "Hard cardio", "Maximal testing"]
        return _build_result(primary, [], status, "STOP", "No training recommendation", profile, assessment, history, exposure, targets, target_source, priority, today, ["A selected safety concern overrides normal training advice."])
    if status == RED:
        priority["AVOID TODAY"] = ["Heavy strength", "HIIT", "Maximal testing"]
        return _build_result(by_name["Easy Aerobic + Mobility"], [], status, "Recovery", "20–30 min", profile, assessment, history, exposure, targets, target_source, priority, today, ["RED readiness overrides weekly volume goals.", "Choose rest or a very low-demand option; avoid heavy strength, HIIT and maximal testing."])
    if status == INSUFFICIENT:
        return _build_result(by_name["Easy Aerobic + Mobility"], [], status, "Recovery", "20–30 min", profile, assessment, history, exposure, targets, target_source, priority, today, ["Readiness data is insufficient for a normal training decision.", "Choose a conservative, lower-demand option while continuing to collect check-ins."])
    load_or_soreness = assessment.get("domains", {}).get("training_load") in {AMBER, RED} or int(assessment.get("today_data", {}).get("soreness", 1) or 1) >= 4
    endurance = "endurance" in goal.casefold() or profile.get("training_split_preference") == "Running-focused"
    endurance_autonomic = endurance and assessment.get("domains", {}).get("autonomic") == AMBER
    demand = "Reduced strength" if status == AMBER else "Normal"
    if status == AMBER and (load_or_soreness or endurance_autonomic): selected = by_name["Easy Aerobic + Mobility"]; demand, duration = "Recovery", "30–40 min"
    else:
        candidates = [by_name[name] for name in ordered_names if name in by_name]; allowed = [item for item in candidates if item["name"] not in priority["AVOID TODAY"]]
        if endurance: selected = next((item for item in allowed if item["training_type"] == "Aerobic"), allowed[0])
        else:
            category_rank = {name: rank for rank, category in enumerate(("HIGH PRIORITY", "AVAILABLE", "LOW PRIORITY")) for name in priority[category]}
            def sort_key(item: Mapping[str, Any]) -> tuple[float, float, int]:
                ratios = [exposure.get(group, 0) / targets.get(group, 1) for group in item.get("muscle_groups", []) if targets.get(group, 0) > 0]
                return category_rank.get(item["name"], 9), min(ratios) if ratios else 1.0, ordered_names.index(item["name"])
            selected = min(allowed, key=sort_key) if allowed else candidates[0]
        duration = "50–65 min" if demand == "Normal" else "35–55 min"
    alternatives = [by_name[name] for name in ordered_names if name != selected["name"] and name not in priority["AVOID TODAY"]][:2]
    if len(alternatives) < 2:
        alternatives.extend(item for item in WORKOUTS if item["name"] != selected["name"] and item not in alternatives and item["name"] not in priority["AVOID TODAY"]); alternatives = alternatives[:2]
    return _build_result(selected, alternatives, status, demand, duration, profile, assessment, history, exposure, targets, target_source, priority, today, [])
