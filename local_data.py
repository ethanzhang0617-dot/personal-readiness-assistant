"""Versioned local-data contract used by the browser IndexedDB bridge.

This module is deliberately independent of Streamlit and JavaScript so the
serialization, validation, migration, import, export and hydration behaviour
can be unit tested.  IndexedDB stores the normalized document produced here;
``st.session_state`` is only the active runtime cache.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from typing import Any, Iterable, Mapping

from demo_data import build_demo_profiles


SCHEMA_VERSION = 1
BACKUP_COLLECTIONS = (
    "profiles",
    "daily_checkins",
    "readiness_history",
    "training_sessions",
    "training_recommendations",
    "chat_history",
)


class LocalDataError(ValueError):
    """Raised when browser state or a backup cannot be safely accepted."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_local_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "active_profile_id": None,
        "profiles": [],
        "daily_checkins": [],
        "readiness_history": [],
        "training_sessions": [],
        "training_recommendations": [],
        "preferences": {"privacy_notice_acknowledged": False},
        "chat_history": [],
    }


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise LocalDataError(f"'{key}' must be a list.")
    return value


def validate_local_state(payload: Any) -> dict[str, Any]:
    """Validate and normalize a schema-v1 browser/backup document."""
    if not isinstance(payload, Mapping):
        raise LocalDataError("The backup must contain a JSON object.")
    try:
        version = int(payload.get("schema_version"))
    except (TypeError, ValueError):
        raise LocalDataError("A valid schema_version is required.") from None
    if version > SCHEMA_VERSION:
        raise LocalDataError(f"Schema version {version} is newer than this app supports.")
    if version < 1:
        raise LocalDataError("Unsupported or missing schema version.")

    normalized = empty_local_state()
    normalized["updated_at"] = str(payload.get("updated_at") or utc_now())
    normalized["active_profile_id"] = payload.get("active_profile_id")
    for key in BACKUP_COLLECTIONS:
        normalized[key] = deepcopy(_require_list(payload, key))
    preferences = payload.get("preferences", {})
    if not isinstance(preferences, Mapping):
        raise LocalDataError("'preferences' must be an object.")
    normalized["preferences"] = {
        "privacy_notice_acknowledged": bool(preferences.get("privacy_notice_acknowledged", False))
    }

    profile_ids: set[str] = set()
    for index, profile in enumerate(normalized["profiles"]):
        if not isinstance(profile, Mapping):
            raise LocalDataError(f"Profile {index + 1} must be an object.")
        profile_id = str(profile.get("profile_id") or profile.get("user_id") or "").strip()
        if not profile_id or not str(profile.get("name") or "").strip():
            raise LocalDataError(f"Profile {index + 1} is missing profile_id or name.")
        if profile_id.startswith("demo-"):
            raise LocalDataError("Demo profiles cannot be imported as personal data.")
        if profile_id in profile_ids:
            raise LocalDataError(f"Duplicate profile_id: {profile_id}.")
        profile_ids.add(profile_id)
        profile["profile_id"] = profile_id
        profile["user_id"] = profile_id

    for key in ("daily_checkins", "readiness_history", "training_sessions", "training_recommendations", "chat_history"):
        for index, row in enumerate(normalized[key]):
            if not isinstance(row, Mapping):
                raise LocalDataError(f"{key} item {index + 1} must be an object.")
            profile_id = str(row.get("profile_id") or "")
            if profile_id not in profile_ids:
                raise LocalDataError(f"{key} item {index + 1} references an unknown profile_id.")
    for index, row in enumerate(normalized["daily_checkins"]):
        if not row.get("date"):
            raise LocalDataError(f"daily_checkins item {index + 1} is missing date.")
    chat_counts: dict[str, int] = {}
    bounded_chat: list[dict[str, Any]] = []
    for row in reversed(normalized["chat_history"]):
        profile_id = str(row.get("profile_id"))
        if chat_counts.get(profile_id, 0) < 30:
            bounded_chat.append(row)
            chat_counts[profile_id] = chat_counts.get(profile_id, 0) + 1
    normalized["chat_history"] = list(reversed(bounded_chat))
    session_ids: set[str] = set()
    for index, row in enumerate(normalized["training_sessions"]):
        session_id = str(row.get("session_id") or "")
        if not session_id or session_id in session_ids:
            raise LocalDataError(f"training_sessions item {index + 1} has a missing or duplicate session_id.")
        session_ids.add(session_id)
    return normalized


def serialize_runtime_state(
    profiles: Iterable[Mapping[str, Any]],
    active_profile_id: str | None,
    preferences: Mapping[str, Any] | None = None,
    chat_histories: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Flatten non-demo profiles into the durable IndexedDB document."""
    document = empty_local_state()
    local_profiles = [deepcopy(dict(profile)) for profile in profiles if not profile.get("is_demo")]
    local_ids = {str(profile["user_id"]) for profile in local_profiles}
    document["active_profile_id"] = active_profile_id if active_profile_id in local_ids else None
    document["preferences"].update(dict(preferences or {}))
    for profile in local_profiles:
        profile_id = str(profile["user_id"])
        base = {key: deepcopy(value) for key, value in profile.items() if key not in {"history", "training_history", "assessments", "recommendations", "local_soreness"}}
        base["profile_id"] = profile_id
        base["user_id"] = profile_id
        base["is_demo"] = False
        document["profiles"].append(base)
        for row in profile.get("history", []):
            document["daily_checkins"].append({**deepcopy(dict(row)), "profile_id": profile_id})
        for row in profile.get("assessments", []):
            document["readiness_history"].append({**deepcopy(dict(row)), "profile_id": profile_id})
        for row in profile.get("training_history", []):
            document["training_sessions"].append({**deepcopy(dict(row)), "profile_id": profile_id})
        for row in profile.get("recommendations", []):
            document["training_recommendations"].append({**deepcopy(dict(row)), "profile_id": profile_id})
        for message in list((chat_histories or {}).get(profile_id, []))[-30:]:
            document["chat_history"].append({**deepcopy(dict(message)), "profile_id": profile_id})
    document["updated_at"] = utc_now()
    return validate_local_state(document)


def profiles_from_local_state(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    document = validate_local_state(payload)
    by_id: dict[str, dict[str, Any]] = {}
    for source in document["profiles"]:
        profile = deepcopy(dict(source))
        profile_id = str(profile.get("profile_id") or profile["user_id"])
        profile.update({"user_id": profile_id, "is_demo": False, "history": [], "training_history": [], "assessments": [], "recommendations": []})
        profile.pop("profile_id", None)
        by_id[profile_id] = profile
    mappings = {
        "daily_checkins": "history",
        "readiness_history": "assessments",
        "training_sessions": "training_history",
        "training_recommendations": "recommendations",
    }
    for source_key, profile_key in mappings.items():
        for source in document[source_key]:
            row = deepcopy(dict(source))
            profile_id = str(row.pop("profile_id"))
            by_id[profile_id][profile_key].append(row)
    for profile in by_id.values():
        profile["history"].sort(key=lambda row: str(row.get("date", "")))
        profile["assessments"].sort(key=lambda row: str(row.get("assessment_date", row.get("date", ""))))
        profile["training_history"].sort(key=lambda row: (str(row.get("date", "")), str(row.get("session_id", ""))))
    return list(by_id.values())


def hydrate_runtime_state(runtime: Any, payload: Mapping[str, Any]) -> None:
    """Restore local profiles without ever replacing fixed demo profiles."""
    document = validate_local_state(payload)
    existing = runtime.get("profiles", [])
    demos = [deepcopy(profile) for profile in existing if profile.get("is_demo")] or build_demo_profiles()
    locals_ = profiles_from_local_state(document)
    runtime.profiles = demos + locals_
    local_ids = {profile["user_id"] for profile in locals_}
    wanted = document.get("active_profile_id")
    runtime.active_profile_id = wanted if wanted in local_ids else "demo-ethan"
    runtime.local_preferences = deepcopy(document["preferences"])
    histories: dict[str, list[dict[str, Any]]] = {profile_id: [] for profile_id in local_ids}
    for message in document.get("chat_history", []):
        row = deepcopy(dict(message))
        profile_id = str(row.pop("profile_id"))
        histories.setdefault(profile_id, []).append(row)
    runtime.chat_histories = histories


def clear_local_runtime(runtime: Any) -> None:
    """Remove personal profiles while retaining clean fixed demos."""
    existing = runtime.get("profiles", [])
    runtime.profiles = [deepcopy(profile) for profile in existing if profile.get("is_demo")] or build_demo_profiles()
    runtime.active_profile_id = "demo-ethan"
    runtime.chat_histories = {}
    runtime.local_preferences = {"privacy_notice_acknowledged": False}


def export_backup(document: Mapping[str, Any]) -> str:
    validated = validate_local_state(document)
    output = deepcopy(validated)
    output["exported_at"] = utc_now()
    return json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True)


def import_backup(raw: str | bytes) -> dict[str, Any]:
    try:
        decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalDataError(f"The backup is not valid UTF-8 JSON: {exc}.") from None
    return validate_local_state(payload)
