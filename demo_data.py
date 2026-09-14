"""Stable simulated profiles and historical data for the public demo."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np


DEMO_PROFILES = (
    {
        "user_id": "demo-ethan",
        "name": "Ethan",
        "age": 25,
        "sex": "Male",
        "primary_activity": "Strength Training",
        "training_goal": "Muscle Gain",
        "training_level": "Advanced",
        "training_split_preference": "Body Part Split",
        "target_sessions_per_week": 5,
        "weekly_set_targets": {"Chest": 6, "Back": 12, "Quads": 10, "Hamstrings / Glutes": 10, "Shoulders": 8, "Arms": 8, "Core": 4},
        "personal_sleep_need": 8.0,
        "seed": 1107,
        "centre": (58.0, 55.0, 7.8, 430.0),
        "default_scenario": "Moderate Fatigue Day",
    },
    {
        "user_id": "demo-alex",
        "name": "Alex",
        "age": 31,
        "sex": "Prefer not to say",
        "primary_activity": "Running",
        "training_goal": "Endurance",
        "training_level": "Intermediate",
        "training_split_preference": "Running-focused",
        "target_sessions_per_week": 5,
        "weekly_set_targets": {},
        "personal_sleep_need": 7.5,
        "seed": 2208,
        "centre": (49.0, 49.0, 7.4, 360.0),
        "default_scenario": "Well Recovered Day",
    },
    {
        "user_id": "demo-jessica",
        "name": "Jessica",
        "age": 28,
        "sex": "Female",
        "primary_activity": "General Fitness",
        "training_goal": "Fat Loss",
        "training_level": "Intermediate",
        "training_split_preference": "Upper / Lower",
        "target_sessions_per_week": 4,
        "weekly_set_targets": {"Chest": 8, "Back": 8, "Quads": 8, "Hamstrings / Glutes": 8, "Shoulders": 6, "Arms": 6, "Core": 4},
        "personal_sleep_need": 8.0,
        "seed": 3309,
        "centre": (45.0, 61.0, 7.7, 310.0),
        "default_scenario": "High Load / Poor Sleep Day",
    },
)


def generate_history(profile: dict[str, Any], days: int = 35, anchor: date | None = None) -> list[dict[str, Any]]:
    """Generate reproducible, clearly simulated day-level history for one profile."""
    rng = np.random.default_rng(int(profile["seed"]))
    hrv_centre, rhr_centre, sleep_centre, load_centre = profile["centre"]
    end = (anchor or date.today()) - timedelta(days=1)
    rows: list[dict[str, Any]] = []
    for offset in range(days):
        day = end - timedelta(days=days - offset - 1)
        duration = max(20, round(rng.normal(58, 13)))
        rpe = int(np.clip(round(rng.normal(load_centre / max(duration, 1), 1.1)), 2, 9))
        rows.append({
            "date": day.isoformat(),
            "rmssd_ms": round(max(15, rng.normal(hrv_centre, 4.5)), 1),
            "resting_hr_bpm": round(max(35, rng.normal(rhr_centre, 1.8)), 1),
            "sleep_hours": round(float(np.clip(rng.normal(sleep_centre, 0.45), 4.5, 10.0)), 1),
            "sleep_quality": int(np.clip(round(rng.normal(4.0, 0.7)), 1, 5)),
            "session_duration_min": duration,
            "session_rpe": rpe,
            "session_load": round(duration * rpe, 1),
            "fatigue": int(np.clip(round(rng.normal(2.1, 0.7)), 1, 5)),
            "soreness": int(np.clip(round(rng.normal(2.0, 0.7)), 1, 5)),
            "stress": int(np.clip(round(rng.normal(2.1, 0.7)), 1, 5)),
            "motivation": int(np.clip(round(rng.normal(4.0, 0.6)), 1, 5)),
            "simulated": True,
        })
    return rows


def generate_training_history(profile: dict[str, Any], anchor: date | None = None) -> list[dict[str, Any]]:
    """Create fixed-seed completed sessions separate from morning readiness rows."""
    today = anchor or date.today()
    user_id = str(profile["user_id"])
    if user_id == "demo-ethan":
        pattern = [(1, "Strength", "Legs", ["Quads", "Hamstrings / Glutes"], 75, 8), (2, "Strength", "Push", ["Chest", "Arms"], 65, 7), (4, "Strength", "Pull", ["Back", "Arms"], 70, 8), (6, "Strength", "Shoulders + Arms", ["Shoulders", "Arms"], 60, 7), (8, "Strength", "Legs", ["Quads", "Hamstrings / Glutes"], 72, 8)]
    elif user_id == "demo-alex":
        pattern = [(1, "Aerobic", "Easy run", ["Quads", "Hamstrings / Glutes"], 45, 4), (2, "Aerobic", "Intervals", ["Quads", "Hamstrings / Glutes"], 55, 7), (4, "Aerobic", "Long run", ["Quads", "Hamstrings / Glutes"], 80, 6), (6, "Strength", "Lower support", ["Quads", "Hamstrings / Glutes"], 45, 6), (8, "Aerobic", "Tempo run", ["Quads", "Hamstrings / Glutes"], 50, 7)]
    else:
        pattern = [(1, "Strength", "Lower", ["Quads", "Hamstrings / Glutes"], 55, 7), (2, "Aerobic", "Aerobic base", ["Quads", "Hamstrings / Glutes"], 40, 5), (4, "Strength", "Upper", ["Chest", "Back", "Shoulders", "Arms"], 55, 7), (6, "Aerobic", "Intervals", ["Quads", "Hamstrings / Glutes"], 35, 7), (8, "Strength", "Lower", ["Quads", "Hamstrings / Glutes"], 50, 6)]
    rows: list[dict[str, Any]] = []
    # Repeat the pattern across three blocks: 15 deterministic completed sessions.
    for block in range(3):
        for index, (days_ago, training_type, focus, groups, duration, rpe) in enumerate(pattern):
            session_date = today - timedelta(days=days_ago + block * 10)
            from training_recommendation_engine import fractional_set_contributions, WORKOUTS
            template = next((item for item in WORKOUTS if item["focus"] == focus), None)
            exercises = template["exercises"] if template else []
            actual_sets = sum(item.get("working_sets", 0) for item in exercises)
            rows.append({"session_id": f"{user_id}-session-{block * len(pattern) + index + 1:02d}", "profile_id": user_id, "date": session_date.isoformat(), "training_type": training_type, "primary_focus": focus, "muscle_groups": groups, "exercises": exercises, "prescribed_sets": actual_sets, "actual_sets": actual_sets, "duration_min": duration, "session_rpe": rpe, "session_load": duration * rpe, "working_sets": actual_sets, "muscle_set_contributions": fractional_set_contributions(exercises), "notes": "Fixed simulated demo session.", "completed": True, "completion_status": "Completed", "simulated": True})
    return sorted(rows, key=lambda row: row["date"])


def build_demo_profiles(anchor: date | None = None) -> list[dict[str, Any]]:
    """Create independent session templates; caller is free to mutate its copy."""
    created = (anchor or date.today()).isoformat()
    return [
        {
            **{key: value for key, value in spec.items() if key not in {"seed", "centre", "default_scenario"}},
            "created_at": created,
            "last_assessment_date": None,
            "history": generate_history(spec, anchor=anchor),
            "training_history": generate_training_history(spec, anchor=anchor),
            "assessments": [],
            "recommendations": [],
            "is_demo": True,
            "default_scenario": spec["default_scenario"],
        }
        for spec in DEMO_PROFILES
    ]
