"""Runtime profile operations; browser IndexedDB supplies durable persistence."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping
from uuid import uuid4

from demo_data import build_demo_profiles
from readiness_engine import assess_readiness


def initialise_store(state: Any) -> None:
    if "profiles" in state:
        for profile in state.profiles:
            profile.setdefault("training_history", [])
            profile.setdefault("training_split_preference", "No Preference")
            profile.setdefault("target_sessions_per_week", 3)
            profile.setdefault("weekly_set_targets", {})
            profile.setdefault("recommendations", [])
        return
    profiles = deepcopy(build_demo_profiles())
    # Add a small, profile-specific assessment trail without persisting user edits.
    for profile in profiles:
        history = profile["history"]
        for index in range(max(28, len(history) - 7), len(history)):
            row = history[index]
            assessment = assess_readiness(row, history[:index], profile["personal_sleep_need"])
            profile["assessments"].append(compact_assessment(assessment))
        profile["last_assessment_date"] = profile["assessments"][-1]["assessment_date"]
    state.profiles = profiles
    state.active_profile_id = "demo-ethan"
    state.chat_messages = []  # Legacy key retained for compatible local sessions.
    state.chat_histories = {}
    state.chat_notice = None
    state.local_preferences = {"privacy_notice_acknowledged": False}


def list_profiles(state: Any) -> list[dict[str, Any]]:
    return state.profiles


def get_profile(state: Any, user_id: str | None = None) -> dict[str, Any]:
    wanted = user_id or state.active_profile_id
    for profile in state.profiles:
        if profile["user_id"] == wanted:
            return profile
    raise KeyError(f"Profile not found: {wanted}")


def set_active_profile(state: Any, user_id: str) -> None:
    get_profile(state, user_id)
    state.active_profile_id = user_id
    state.chat_notice = None


def create_profile(state: Any, details: Mapping[str, Any]) -> dict[str, Any]:
    name = str(details.get("name", "")).strip()
    if not name:
        raise ValueError("Profile name is required.")
    profile = {
        "user_id": f"user-{uuid4().hex[:12]}",
        "name": name,
        "age": int(details.get("age", 18)),
        "sex": str(details.get("sex", "Prefer not to say")),
        "primary_activity": str(details.get("primary_activity", "General Fitness")),
        "training_goal": str(details.get("training_goal", "General Fitness")),
        "training_level": str(details.get("training_level", "Beginner")),
        "training_split_preference": str(details.get("training_split_preference", "No Preference")),
        "target_sessions_per_week": int(details.get("target_sessions_per_week", 3)),
        "weekly_set_targets": dict(details.get("weekly_set_targets", {})),
        "personal_sleep_need": float(details.get("personal_sleep_need", 8.0)),
        "created_at": date.today().isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_assessment_date": None,
        "history": [],
        "training_history": [],
        "assessments": [],
        "recommendations": [],
        "is_demo": False,
        "default_scenario": "Well Recovered Day",
    }
    state.profiles.append(profile)
    set_active_profile(state, profile["user_id"])
    return profile


def update_profile(profile: dict[str, Any], details: Mapping[str, Any]) -> None:
    for key in ("name", "sex", "primary_activity", "training_goal", "training_level", "training_split_preference"):
        if key in details:
            profile[key] = str(details[key]).strip()
    if "age" in details:
        profile["age"] = int(details["age"])
    if "personal_sleep_need" in details:
        profile["personal_sleep_need"] = float(details["personal_sleep_need"])
    if "target_sessions_per_week" in details:
        profile["target_sessions_per_week"] = int(details["target_sessions_per_week"])
    if "weekly_set_targets" in details:
        profile["weekly_set_targets"] = dict(details["weekly_set_targets"])
    profile["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def delete_profile(state: Any, user_id: str) -> None:
    if len(state.profiles) <= 1:
        raise ValueError("Keep at least one profile in the demo.")
    if not any(profile["user_id"] == user_id for profile in state.profiles):
        raise KeyError("Profile not found.")
    state.profiles = [profile for profile in state.profiles if profile["user_id"] != user_id]
    if state.active_profile_id == user_id:
        state.active_profile_id = state.profiles[0]["user_id"]
    state.chat_notice = None


def upsert_daily_metric(profile: dict[str, Any], row: Mapping[str, Any]) -> bool:
    """Insert or replace one profile-owned daily record; True means it replaced a date."""
    normalised = dict(row)
    normalised["date"] = str(normalised["date"])
    existing = {str(item["date"]): dict(item) for item in profile["history"]}
    normalised.setdefault("id", f"checkin-{profile['user_id']}-{normalised['date']}")
    normalised["profile_id"] = profile["user_id"]
    normalised.setdefault("created_at", existing.get(normalised["date"], {}).get("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds")))
    normalised["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for key in ("session_duration_min", "session_rpe", "session_load"):
        if normalised.get(key) is None and existing.get(normalised["date"], {}).get(key) is not None:
            normalised[key] = existing[normalised["date"]][key]
    replaced = normalised["date"] in existing
    existing[normalised["date"]] = normalised
    profile["history"] = [existing[key] for key in sorted(existing)]
    return replaced


def upsert_completed_session(profile: dict[str, Any], assessment_date: date, duration_min: float | None, rpe: float | None, rest_day: bool) -> bool:
    """Attach the most recent completed session to yesterday, never to morning readiness."""
    completed_date = (assessment_date - timedelta(days=1)).isoformat()
    existing = {str(item["date"]): dict(item) for item in profile["history"]}
    row = existing.get(completed_date, {"date": completed_date, "simulated": bool(profile.get("is_demo"))})
    row["session_duration_min"] = 0.0 if rest_day else float(duration_min or 0.0)
    row["session_rpe"] = None if rest_day else (float(rpe) if rpe is not None else None)
    row["session_load"] = 0.0 if rest_day else (round(float(duration_min) * float(rpe), 2) if duration_min is not None and rpe is not None else None)
    replaced = completed_date in existing
    existing[completed_date] = row
    profile["history"] = [existing[key] for key in sorted(existing)]
    return replaced


def log_training_session(profile: dict[str, Any], details: Mapping[str, Any]) -> dict[str, Any]:
    """Save an explicitly confirmed completed session and expose its load to future days.

    Nothing calls this function when a recommendation is made.  The compact
    daily history mirror is only to let the unchanged Readiness Engine read a
    completed session on later morning assessments.
    """
    session_date = str(details.get("date") or date.today().isoformat())
    duration = float(details.get("duration_min") or 0.0)
    rpe = float(details.get("session_rpe") or 0.0)
    from training_recommendation_engine import session_set_contributions
    exercises = list(details.get("exercises") or [])
    prescribed_sets = float(details.get("prescribed_sets") or 0)
    actual_sets = float(details.get("actual_sets") if details.get("actual_sets") is not None else sum(item.get("working_sets", 0) for item in exercises))
    session = {
        "session_id": str(details.get("session_id") or f"session-{uuid4().hex[:12]}"),
        "profile_id": profile["user_id"],
        "date": session_date,
        "training_type": str(details.get("training_type") or "Strength"),
        "primary_focus": str(details.get("primary_focus") or "General training"),
        "prescription_id": details.get("prescription_id"),
        "muscle_groups": list(details.get("muscle_groups") or []),
        "exercises": exercises,
        "prescribed_sets": prescribed_sets,
        "actual_sets": actual_sets,
        "duration_min": duration,
        "session_rpe": rpe,
        "session_load": round(duration * rpe, 1),
        # Backward-compatible alias. Exposure calculations use the actual exercise rows.
        "working_sets": actual_sets,
        "muscle_set_contributions": dict(details.get("muscle_set_contributions") or session_set_contributions({**details, "exercises": exercises, "actual_sets": actual_sets})),
        "notes": str(details.get("notes") or ""),
        "completed": str(details.get("completed", "Yes")) != "No",
        "completion_status": str(details.get("completion_status") or "Completed"),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "simulated": False,
    }
    profile.setdefault("training_history", []).append(session)
    profile["training_history"] = sorted(profile["training_history"], key=lambda row: str(row["date"]))
    daily_rows = {str(row["date"]): dict(row) for row in profile["history"]}
    daily = daily_rows.get(session_date, {"date": session_date, "simulated": False})
    same_day = [row for row in profile["training_history"] if str(row.get("date")) == session_date and row.get("completed", True)]
    daily.update({"session_duration_min": round(sum(float(row.get("duration_min") or 0) for row in same_day), 1), "session_rpe": None, "session_load": round(sum(float(row.get("session_load") or 0) for row in same_day), 1)})
    daily_rows[session_date] = daily
    profile["history"] = [daily_rows[key] for key in sorted(daily_rows)]
    return session


def compact_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": f"assessment-{assessment.get('profile_id', 'profile')}-{assessment['assessment_date']}",
        "assessment_date": assessment["assessment_date"],
        "overall_readiness": assessment["overall_readiness"],
        "autonomic_status": assessment["domains"]["autonomic"],
        "sleep_status": assessment["domains"]["sleep"],
        "subjective_status": assessment["domains"]["subjective"],
        "training_load_status": assessment["domains"]["training_load"],
        "readiness_index": assessment["readiness_index"],
        "assessment_confidence": assessment["assessment_confidence"],
        "key_contributors": list(assessment["key_contributors"]),
        "decision_support": list(assessment["decision_support"]),
        "safety_status": "STOP" if assessment.get("safety_flags") else "CLEAR",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def save_assessment(profile: dict[str, Any], assessment: Mapping[str, Any]) -> bool:
    """Update assessment on a date rather than allowing duplicate daily entries."""
    item = compact_assessment(assessment)
    item["profile_id"] = profile["user_id"]
    item["id"] = f"assessment-{profile['user_id']}-{item['assessment_date']}"
    existing = {str(row["assessment_date"]): dict(row) for row in profile["assessments"]}
    replaced = item["assessment_date"] in existing
    existing[item["assessment_date"]] = item
    profile["assessments"] = [existing[key] for key in sorted(existing)]
    profile["last_assessment_date"] = item["assessment_date"]
    return replaced


def save_recommendation(profile: dict[str, Any], recommendation: Mapping[str, Any], recommendation_date: str | None = None) -> bool:
    """Upsert the deterministic recommendation for one profile/date."""
    day = str(recommendation_date or date.today().isoformat())
    item = {
        "id": f"recommendation-{profile['user_id']}-{day}",
        "profile_id": profile["user_id"],
        "date": day,
        "primary": deepcopy(recommendation.get("primary", {})),
        "alternatives": deepcopy(recommendation.get("alternatives", [])),
        "avoid_today": list(recommendation.get("avoid", [])),
        "session_demand": recommendation.get("intensity"),
        "rationale": list(recommendation.get("rationale", [])),
        "decision_trace": deepcopy(recommendation.get("decision_trace", [])),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    existing = {str(row.get("date")): dict(row) for row in profile.setdefault("recommendations", [])}
    replaced = day in existing
    existing[day] = item
    profile["recommendations"] = [existing[key] for key in sorted(existing)]
    return replaced


def generate_sample_history(profile: dict[str, Any]) -> None:
    """Give a new profile generic but clearly simulated data without touching other profiles."""
    from demo_data import DEMO_PROFILES, generate_history

    template = dict(DEMO_PROFILES[0])
    template["seed"] = abs(hash(profile["user_id"])) % 100000
    profile["history"] = generate_history(template)
    profile["training_history"] = []
    profile["assessments"] = []


def import_rows(profile: dict[str, Any], rows: Iterable[Mapping[str, Any]]) -> tuple[int, int]:
    inserted = 0
    replaced = 0
    for row in rows:
        if upsert_daily_metric(profile, row):
            replaced += 1
        else:
            inserted += 1
    return inserted, replaced
