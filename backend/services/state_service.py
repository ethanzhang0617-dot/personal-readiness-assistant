"""Browser-owned state → existing engines.

The API is a stateless compute + explain layer. The client keeps the user's
check-ins, logged sessions and profile edits in its own browser storage and sends
them with each request; nothing is written to a server database.

Materialising a request means:

    seeded demo profile
      → apply the user's profile edits      (profile_store.update_profile)
      → upsert the user's daily check-ins   (profile_store.upsert_daily_metric)
      → append the user's logged sessions   (raw rows produced when they were logged)

Every scientific step after that is the unmodified engine.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping

from profile_store import log_training_session, update_profile, upsert_daily_metric
from product_options import ACTIVITIES, GOALS, LEVELS, SEXES, SPLITS
from readiness_engine import SAFETY_FLAGS
from scenario_data import SCENARIOS, SCENARIO_FIELDS, default_scenario, scenario_values
from training_recommendation_engine import MUSCLE_GROUPS

from adaptive_response import demo_seed as demo_response_seed

from backend.schemas.models import DailyRow, UserState
from backend.services import demo_service


def scenario_list() -> list[dict[str, Any]]:
    profile = demo_service.get_profile()
    return [{"name": name, "label": name, "values": scenario_values(profile, name)} for name in SCENARIOS]


def safety_flags() -> tuple[str, ...]:
    """The product's own safety screen options, straight from the engine."""
    return tuple(SAFETY_FLAGS)


def muscle_groups() -> tuple[str, ...]:
    """The product's muscle taxonomy, used for local soreness and weekly targets."""
    return tuple(MUSCLE_GROUPS)


def profile_options() -> dict[str, list[str]]:
    """The same selectable profile values the reference app offers."""
    return {
        "activities": list(ACTIVITIES),
        "goals": list(GOALS),
        "levels": list(LEVELS),
        "sexes": list(SEXES),
        "splits": list(SPLITS),
    }


def base_state(profile_id: str | None = None, scenario: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """The seeded profile plus an empty overlay, ready for the client to own."""
    profile = demo_service.get_profile(profile_id)
    chosen = scenario if scenario in SCENARIOS else default_scenario(profile)
    state = UserState(profile_id=str(profile["user_id"]), scenario=chosen)
    return profile, state.model_dump()


def materialise(state: UserState | Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the runtime profile the engines expect, without mutating stored data."""
    payload = state.model_dump() if isinstance(state, UserState) else dict(state)
    profile = deepcopy(demo_service.get_profile(payload.get("profile_id")))

    edits = {key: value for key, value in (payload.get("edits") or {}).items() if value is not None}
    if edits:
        update_profile(profile, edits)

    for row in payload.get("daily_history") or []:
        if row.get("date"):
            upsert_daily_metric(profile, row)

    # Overlay sessions are merged onto the seeded row with the same id (so a client
    # can attach a pre-session snapshot or post-session feedback to a seeded
    # session), and appended when the id is new.
    by_id = {str(session.get("session_id")): session for session in profile.get("training_history") or []}
    for session in payload.get("training_history") or []:
        session_id = str(session.get("session_id") or "")
        if not session_id:
            continue
        existing = by_id.get(session_id)
        if existing is None:
            profile.setdefault("training_history", []).append(dict(session))
            by_id[session_id] = profile["training_history"][-1]
        else:
            existing.update(_patch_fields(session))
    profile["training_history"] = sorted(profile.get("training_history") or [], key=lambda row: str(row.get("date")))
    return profile


def _patch_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    """Fields a client patch actually carries.

    A serialised overlay row fills every unused field with ``None`` (or an empty
    container), so merging it wholesale would erase the seeded session. Only
    values the client really provided are applied.
    """
    patch: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
            continue
        patch[key] = value
    return patch


def check_in_draft(state: UserState | Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    """Today's check-in: an explicit user check-in wins over the demo scenario."""
    payload = state.model_dump() if isinstance(state, UserState) else dict(state)
    explicit = payload.get("check_in")
    if explicit:
        draft = {key: explicit.get(key) for key in SCENARIO_FIELDS if explicit.get(key) is not None}
        for extra in ("local_soreness",):
            if explicit.get(extra):
                draft[extra] = explicit[extra]
        if not draft.get("safety_flags"):
            draft["safety_flags"] = list(explicit.get("safety_flags") or [])
        return draft
    scenario = payload.get("scenario") or default_scenario(profile)
    return scenario_values(profile, scenario)


def _merge_daily(existing: list[dict[str, Any]], row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Upsert by date, matching the product's own one-record-per-date rule."""
    target = str(row["date"])
    merged = [dict(item) for item in existing if str(item.get("date")) != target]
    merged.append(dict(row))
    merged.sort(key=lambda item: str(item.get("date")))
    return merged


def apply_check_in(state: UserState, check_in: DailyRow) -> UserState:
    payload = state.model_dump()
    row = {"date": check_in.date or date.today().isoformat()}
    row.update({key: value for key, value in check_in.model_dump().items() if value is not None})
    payload["check_in"] = row
    payload["daily_history"] = _merge_daily(payload.get("daily_history") or [], row)
    return UserState(**payload)


def apply_profile_edits(state: UserState, edits: Mapping[str, Any]) -> UserState:
    payload = state.model_dump()
    current = dict(payload.get("edits") or {})
    current.update({key: value for key, value in edits.items() if value is not None})
    payload["edits"] = current
    return UserState(**payload)


def apply_session(state: UserState, details: Mapping[str, Any]) -> tuple[UserState, dict[str, Any]]:
    """Log a completed session through the product's own logging function."""
    profile = materialise(state)
    session = log_training_session(profile, details)
    daily_row = next((row for row in profile["history"] if str(row.get("date")) == str(session["date"])), None)
    payload = state.model_dump()
    payload["training_history"] = [dict(row) for row in (payload.get("training_history") or [])] + [dict(session)]
    if daily_row is not None:
        payload["daily_history"] = _merge_daily(payload.get("daily_history") or [], daily_row)
    return UserState(**payload), session


def set_scenario(state: UserState, scenario: str | None) -> UserState:
    payload = state.model_dump()
    if scenario in SCENARIOS:
        payload["scenario"] = scenario
    return UserState(**payload)


def upsert_session_overlay(state: UserState, session_id: str, fields: Mapping[str, Any]) -> UserState:
    """Attach fields (snapshot or feedback) to one session in the client overlay."""
    payload = state.model_dump()
    rows = [dict(row) for row in (payload.get("training_history") or [])]
    target = next((row for row in rows if str(row.get("session_id")) == str(session_id)), None)
    if target is None:
        target = {"session_id": str(session_id)}
        rows.append(target)
    target.update({key: value for key, value in fields.items() if value is not None})
    payload["training_history"] = rows
    return UserState(**payload)


def seed_demo_responses(state: UserState, case: str) -> UserState:
    """Demo-only: attach seeded response data to the client overlay.

    The seeded episodes are recorded at the demand the product actually prescribes
    for this state today, so a demo case can never claim an established pattern
    that the current recommendation would not even count.
    """
    # Imported lazily: readiness/training services import this package's siblings
    # at module import time, and this keeps that ordering free of cycles.
    from backend.services import readiness_service, training_service

    profile = materialise(state)
    draft = check_in_draft(state, profile)
    assessment = readiness_service.assess(profile, draft)
    recommendation = training_service.recommend(profile, assessment)
    seed = demo_response_seed(profile, case, str(recommendation.get("intensity") or "Normal"))
    if not seed:
        return state
    payload = state.model_dump()
    rows = {str(row.get("session_id")): dict(row) for row in (payload.get("training_history") or [])}
    for session_id, fields in seed.items():
        row = rows.get(session_id, {"session_id": session_id})
        row.update(fields)
        rows[session_id] = row
    payload["training_history"] = list(rows.values())
    return UserState(**payload)


def record_adaptation(state: UserState, event: Mapping[str, Any]) -> UserState:
    """Upsert today's Personal Response decision into the adaptation history.

    One meaningful event per day: if the product recomputes the same day (a new
    check-in, a logged session), the entry is replaced rather than duplicated.
    Older episodes stay in the history; the log is only bounded for size.
    """
    payload = state.model_dump()
    when = str(event.get("date") or "")
    log = [dict(row) for row in (payload.get("adaptation_log") or []) if str(row.get("date")) != when]
    if when:
        log.append(dict(event))
    log.sort(key=lambda row: str(row.get("date")))
    payload["adaptation_log"] = log[-90:]
    return UserState(**payload)
