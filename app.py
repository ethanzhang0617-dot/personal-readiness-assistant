"""Personal Readiness Assistant — a public Streamlit product prototype."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from html import escape
import json
import math
from typing import Any

import pandas as pd
import streamlit as st
import altair as alt

from ai_engine import ai_diagnostics, ai_engine_status, get_ai_response, get_instant_response
import styles
from browser_storage import browser_storage_bridge
from local_data import (LocalDataError, clear_local_runtime, export_backup, hydrate_runtime_state, import_backup,
                        serialize_runtime_state)
from mobile_shell import mobile_shell_bridge
from profile_store import (create_profile, delete_profile, generate_sample_history, get_profile, initialise_store,
                           list_profiles, log_training_session, save_assessment, save_recommendation,
                           set_active_profile, update_profile, upsert_daily_metric)
from readiness_engine import (AMBER, BASELINE_LIMITED_DAYS, BASELINE_NORMAL_DAYS, GREEN, INSUFFICIENT, RED,
                              SAFETY_FLAGS, assess_readiness, ln_rmssd)
from styles import inject_styles
from science_content import EVIDENCE_LABELS, EVIDENCE_MAP, LIMITATIONS, READINESS_RULE_METADATA, RECOMMENDATION_RULE_METADATA, REFERENCES
from training_recommendation_engine import MUSCLE_GROUPS, prescription_log_defaults, recommend_training, workout_template
from ui_components import (PRIMARY_NAV_ITEMS, SECONDARY_NAV_ITEMS, callout, decision_trace_section, detail_row,
                           flow_card, history_list, identity_badge, insight_card, metric_grid, metric_tile,
                           mobile_readiness_hero, page_intro, primary_cta, quick_questions, readiness_hero,
                           secondary_cta, status_badge, status_word, today_training_card, train_primary_card,
                           training_summary, why_today)
from ui_components import context_chip
from ui_components import mobile_bottom_nav_component, mobile_utility_nav_component


st.set_page_config(page_title="Personal Readiness Assistant", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

ACTIVITIES = ("Strength Training", "Running", "Cycling", "HYROX / Functional Fitness", "Team Sports", "General Fitness", "Other")
GOALS = ("General Fitness", "Strength", "Muscle Gain", "Fat Loss", "Endurance", "Performance", "Recovery / Health", "Other")
LEVELS = ("Beginner", "Intermediate", "Advanced")
SEXES = ("Male", "Female", "Prefer not to say")
SPLITS = ("No Preference", "Body Part Split", "Push / Pull / Legs", "Upper / Lower", "Full Body", "Running-focused", "Hybrid")
SCENARIOS = ("Well Recovered Day", "Moderate Fatigue Day", "High Load / Poor Sleep Day")
MORE_NAV_ITEMS = SECONDARY_NAV_ITEMS
NAV_ITEMS = PRIMARY_NAV_ITEMS + SECONDARY_NAV_ITEMS

#: Four high-value Coach entry points (PHASE FT). The exposure question keeps
#: running through the deterministic fact resolver; it is not removed.
COACH_QUICK_QUESTIONS = (
    "Why this workout?",
    "Can I train harder today?",
    "Explain my readiness",
    "What should I adjust in my recent training?",
)

#: Explicit direction for every check-in scale: the number alone is ambiguous
#: because a high motivation is good while high fatigue is not.
SUBJECTIVE_SCALE_GUIDANCE = {
    "Sleep quality": "1 = very poor · 5 = very good (higher is better)",
    "Fatigue": "1 = none · 5 = severe (higher = more fatigue)",
    "Soreness": "1 = none · 5 = severe (higher = more soreness)",
    "Stress": "1 = none · 5 = severe (higher = more stress)",
    "Motivation": "1 = very low · 5 = very high (higher is better)",
}


def scale_guidance(field: str) -> str:
    return SUBJECTIVE_SCALE_GUIDANCE[field]


def format_trend_date(value: Any) -> str:
    """One date format across Trends tables and history rows (for example ``16 Sep``)."""
    stamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(stamp):
        return str(value)
    return stamp.strftime("%d %b")


def build_trend_chart(frame: pd.DataFrame, value_col: str, mean_col: str, unit: str, baseline: float | None, colour: str) -> alt.LayerChart | None:
    """A readable trend line: real data range, rolling mean, optional baseline rule."""
    data = frame[["date", value_col, mean_col]].dropna(subset=[value_col])
    if data.empty:
        return None
    base = alt.Chart(data).encode(x=alt.X("date:T", axis=alt.Axis(format="%d %b", title=None, labelAngle=0)))
    layers = [
        base.mark_line(strokeDash=[4, 3], color=styles.COLOR_TOKENS["--ara-text-2"]).encode(
            y=alt.Y(f"{mean_col}:Q", title=unit, scale=alt.Scale(zero=False))),
        base.mark_line(color=colour, strokeWidth=2).encode(
            y=alt.Y(f"{value_col}:Q", title=unit, scale=alt.Scale(zero=False))),
        base.mark_point(filled=True, size=18, color=colour).encode(
            y=alt.Y(f"{value_col}:Q", title=unit, scale=alt.Scale(zero=False))),
    ]
    if baseline is not None:
        rule_frame = pd.DataFrame({"baseline": [float(baseline)]})
        layers.append(alt.Chart(rule_frame).mark_rule(strokeDash=[2, 2], color=styles.COLOR_TOKENS["--ara-status-amber"]).encode(
            y=alt.Y("baseline:Q", title=unit)))
    return alt.layer(*layers).properties(height=190).resolve_scale(y="shared")


def trend_chart(frame: pd.DataFrame, value_col: str, mean_col: str, unit: str, baseline: float | None, colour: str) -> None:
    chart = build_trend_chart(frame, value_col, mean_col, unit, baseline, colour)
    if chart is None:
        st.caption("Not enough recorded data yet.")
        return
    st.altair_chart(chart, width="stretch")


def _local_document() -> dict[str, Any]:
    return serialize_runtime_state(
        st.session_state.profiles,
        st.session_state.get("active_profile_id"),
        st.session_state.get("local_preferences", {}),
        st.session_state.get("chat_histories", {}),
    )


def _queue_browser_save() -> None:
    st.session_state.storage_revision = int(st.session_state.get("storage_revision", 0)) + 1
    st.session_state.pending_storage = {"operation": "save", "command_id": f"save-{st.session_state.storage_revision}", "state": _local_document()}


def _queue_browser_clear() -> None:
    st.session_state.storage_revision = int(st.session_state.get("storage_revision", 0)) + 1
    st.session_state.pending_storage = {"operation": "clear", "command_id": f"clear-{st.session_state.storage_revision}", "state": {}}


def _sync_browser_storage() -> None:
    """Hydrate once, then execute queued idempotent save/clear commands."""
    pending = st.session_state.get("pending_storage")
    command = pending or {"operation": "load", "command_id": "startup-load-v1", "state": {}}
    result = browser_storage_bridge(command["operation"], command["command_id"], command.get("state"))
    if not isinstance(result, dict) or result.get("command_id") != command["command_id"]:
        return
    if not result.get("ok"):
        st.session_state.storage_error = result.get("error", "Browser storage is unavailable.")
        if pending: st.session_state.pending_storage = None
        return
    if command["operation"] == "load" and not st.session_state.get("browser_hydrated"):
        if result.get("state"):
            try:
                hydrate_runtime_state(st.session_state, result["state"])
            except LocalDataError as exc:
                st.session_state.storage_error = f"Saved browser data was not loaded: {exc}"
        st.session_state.browser_hydrated = True
        st.session_state.storage_status = "Local browser history restored." if result.get("state") else "Local browser storage is ready."
        st.rerun()
    elif pending and command["operation"] in {"save", "clear"}:
        st.session_state.pending_storage = None
        st.session_state.storage_status = "Saved locally in this browser." if command["operation"] == "save" else "Local browser history cleared."


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def scenario_values(profile: dict[str, Any], scenario: str) -> dict[str, Any]:
    """Demo convenience only; it does not change the Readiness Engine."""
    history = profile["history"][-28:]
    def average(field: str, fallback: float) -> float:
        values = [float(row[field]) for row in history if row.get(field) is not None]
        return _mean(values) or fallback
    hrv, rhr = average("rmssd_ms", 55.0), average("resting_hr_bpm", 58.0)
    sleep_need = float(profile["personal_sleep_need"])
    if scenario == "High Load / Poor Sleep Day":
        return {"rmssd_ms": round(hrv * .82, 1), "resting_hr_bpm": round(rhr + 5), "sleep_hours": round(sleep_need * .72, 1), "sleep_quality": 2, "fatigue": 4, "soreness": 4, "stress": 4, "motivation": 2, "safety_flags": []}
    if scenario == "Moderate Fatigue Day":
        return {"rmssd_ms": round(hrv * .94, 1), "resting_hr_bpm": round(rhr + 1), "sleep_hours": round(sleep_need * .95, 1), "sleep_quality": 4, "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4, "safety_flags": []}
    return {"rmssd_ms": round(hrv * 1.04, 1), "resting_hr_bpm": round(max(35, rhr - 1)), "sleep_hours": round(sleep_need * 1.01, 1), "sleep_quality": 5, "fatigue": 1, "soreness": 1, "stress": 2, "motivation": 5, "safety_flags": []}


def draft_key(profile: dict[str, Any]) -> str:
    return f"draft_{profile['user_id']}"


def get_draft(profile: dict[str, Any]) -> dict[str, Any]:
    if draft_key(profile) not in st.session_state:
        if profile.get("is_demo"):
            initial = scenario_values(profile, profile.get("default_scenario", SCENARIOS[0]))
        else:
            today_row = next((row for row in reversed(profile.get("history", [])) if str(row.get("date")) == date.today().isoformat()), None)
            source = today_row or (profile.get("history", [])[-1] if profile.get("history") else {})
            initial = {
                "rmssd_ms": float(source.get("rmssd_ms") or 50), "resting_hr_bpm": float(source.get("resting_hr_bpm") or 60),
                "sleep_hours": float(source.get("sleep_hours") or profile.get("personal_sleep_need", 8)), "sleep_quality": int(source.get("sleep_quality") or 4),
                "fatigue": int(source.get("fatigue") or 2), "soreness": int(source.get("soreness") or 2), "stress": int(source.get("stress") or 2),
                "motivation": int(source.get("motivation") or 4), "local_soreness": dict(today_row.get("local_soreness", {}) if today_row else {}), "safety_flags": list(today_row.get("safety_flags", []) if today_row else []),
            }
        st.session_state[draft_key(profile)] = initial
    return st.session_state[draft_key(profile)]


def set_draft(profile: dict[str, Any], scenario: str) -> None:
    st.session_state[draft_key(profile)] = scenario_values(profile, scenario)
    st.session_state.chat_histories[profile["user_id"]] = []


def real_today_inputs(profile: dict[str, Any], today: date | None = None) -> dict[str, Any] | None:
    """Return only an actually saved local check-in for the requested date."""
    day = (today or date.today()).isoformat()
    return next((deepcopy(row) for row in reversed(profile.get("history", [])) if str(row.get("date")) == day), None)


def current_assessment(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile.get("is_demo"):
        today_row = real_today_inputs(profile)
        if today_row is None:
            draft = {"rmssd_ms": None, "resting_hr_bpm": None, "sleep_hours": None, "sleep_quality": None, "fatigue": None, "soreness": None, "stress": None, "motivation": None, "local_soreness": {}, "safety_flags": []}
        else:
            draft = deepcopy(today_row)
    else:
        draft = deepcopy(get_draft(profile))
    draft["date"] = date.today().isoformat()
    return assess_readiness(draft, profile["history"], profile["personal_sleep_need"], profile["assessments"])


def current_recommendation(profile: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    return recommend_training(profile, assessment, profile.get("training_history", []))


def rir_guidance(session: dict[str, Any]) -> str | None:
    """RIR wording straight from the prescription (for example ``2–4 RIR``)."""
    exercises = session.get("exercises") or []
    for exercise in exercises:
        raw = str(exercise.get("rir", ""))
        if "RIR" in raw.upper():
            head = raw.split(";")[0].strip()
            if head:
                return head
    return None


def coach_context_header(assessment: dict[str, Any], recommendation: dict[str, Any]) -> None:
    """Compact Coach context: readiness, today's session, session demand."""
    st.markdown(
        "<div class='ara-coach-context'>"
        + status_badge(assessment["overall_readiness"], label=status_word(assessment["overall_readiness"]))
        + context_chip(recommendation["primary"]["name"])
        + context_chip(f"{recommendation['intensity']} demand")
        + "</div>",
        unsafe_allow_html=True,
    )


def validate_uploaded_csv(uploaded: Any) -> tuple[list[dict[str, Any]], list[str]]:
    required = {"date", "rmssd_ms", "resting_hr_bpm", "sleep_hours", "sleep_quality", "session_duration_min", "session_rpe", "fatigue", "soreness", "stress", "motivation"}
    try:
        dataframe = pd.read_csv(uploaded)
    except Exception:
        return [], ["The CSV could not be read. Export it as a standard comma-separated file."]
    missing = required - set(dataframe.columns)
    if missing:
        return [], ["Missing required columns: " + ", ".join(sorted(missing))]
    rows, warnings = [], []
    for number, (_, raw) in enumerate(dataframe.iterrows(), start=2):
        try:
            row = {"date": pd.to_datetime(raw["date"], errors="raise").date().isoformat(), "rmssd_ms": float(raw["rmssd_ms"]), "resting_hr_bpm": float(raw["resting_hr_bpm"]), "sleep_hours": float(raw["sleep_hours"]), "sleep_quality": int(raw["sleep_quality"]), "session_duration_min": float(raw["session_duration_min"]), "session_rpe": float(raw["session_rpe"]), "fatigue": int(raw["fatigue"]), "soreness": int(raw["soreness"]), "stress": int(raw["stress"]), "motivation": int(raw["motivation"]), "simulated": False}
            if any(not math.isfinite(float(row[key])) for key in ("rmssd_ms", "resting_hr_bpm", "sleep_hours", "session_duration_min", "session_rpe")):
                raise ValueError("a numeric value is not finite")
            row["session_load"] = round(row["session_duration_min"] * row["session_rpe"], 1)
            rows = [item for item in rows if item["date"] != row["date"]] + [row]
        except Exception as exc:
            warnings.append(f"Row {number} was skipped: {exc}.")
    return rows, warnings


def go_to(page: str) -> None:
    st.session_state.current_page = page
    st.rerun()


def render_sidebar_navigation() -> str:
    current = st.session_state.get("current_page", "Today")
    for page, icon in NAV_ITEMS:
        if st.sidebar.button(f"{icon} {page}", key=f"sidebar_nav_{page}", type="primary" if page == current else "secondary", width="stretch"):
            go_to(page)
    return current


def render_bottom_navigation() -> None:
    """Mobile-only navigation.

    The reusable component lives in ``ui_components``; placement, height,
    safe-area spacing and the desktop hiding rule live in ``styles.SHELL_CSS``.
    """
    mobile_bottom_nav_component(st.session_state.get("current_page", "Today"), go_to)


def render_mobile_utility_nav() -> None:
    mobile_utility_nav_component(go_to)


def profile_options() -> tuple[list[dict[str, Any]], list[str]]:
    """One vocabulary for profile labels, shared by the sidebar and mobile More."""
    profiles = list_profiles(st.session_state)
    labels = [("DEMO · " if item.get("is_demo") else "LOCAL · ") + item["name"] for item in profiles]
    return profiles, labels


def profile_label(profile: dict[str, Any]) -> str:
    return ("DEMO · " if profile.get("is_demo") else "LOCAL · ") + profile["name"]


def switch_active_profile(state: Any, profiles: list[dict[str, Any]], labels: list[str], selected_label: str, current_id: str) -> bool:
    """Activate the selected profile. Returns True when a rerun is required."""
    selected = profiles[labels.index(selected_label)]["user_id"]
    if selected == current_id:
        return False
    set_active_profile(state, selected)
    return True


def profile_switcher(profile: dict[str, Any]) -> None:
    """Active profile card plus a switcher that works without the desktop sidebar."""
    profiles, labels = profile_options()
    demo = bool(profile.get("is_demo"))
    st.markdown(
        "<div class='ara-profile-card'>"
        "<div class='ara-fact-label'>ACTIVE PROFILE</div>"
        f"<div class='ara-fact-value'>{escape(profile['name'])}</div>"
        f"<div class='ara-fact-meta'>{identity_badge(demo)}{context_chip(profile.get('training_goal', 'General Fitness'))}</div>"
        "</div>", unsafe_allow_html=True,
    )
    if demo:
        st.caption("Demo data is separate from My Local Data and is not included in exports.")
    if len(profiles) > 1:
        choice = st.selectbox("Change profile", labels, index=labels.index(profile_label(profile)), key="mobile_profile_switch")
        if switch_active_profile(st.session_state, profiles, labels, choice, profile["user_id"]):
            st.rerun()
    if st.session_state.get("storage_error"):
        st.error(st.session_state.storage_error)
    elif st.session_state.get("storage_status"):
        st.caption(st.session_state.storage_status)


def render_sidebar(profile: dict[str, Any]) -> None:
    """Desktop shell: the sidebar owns its own active-profile selector."""
    with st.sidebar:
        st.markdown("### ⚡ Personal Readiness")
        profiles, labels = profile_options()
        selected_label = st.selectbox("Active profile", labels, index=labels.index(profile_label(profile)))
        if switch_active_profile(st.session_state, profiles, labels, selected_label, profile["user_id"]):
            st.rerun()
        st.caption(f"{profile['primary_activity']} · {profile['training_goal']}")
        if st.button("+ Create My Local Profile", width="stretch"):
            go_to("Profile")
        if st.session_state.get("storage_error"):
            st.error(st.session_state.storage_error)
        elif st.session_state.get("storage_status"):
            st.caption(st.session_state.storage_status)
        st.divider()


def _recent_training_table(history: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [{"Date": row["date"], "Type": row["training_type"], "Focus": row["primary_focus"], "Duration": f"{row['duration_min']:.0f} min", "RPE": row["session_rpe"], "Load": row["session_load"]} for row in sorted(history, key=lambda item: item["date"], reverse=True)[:5]]
    return pd.DataFrame(rows)


def _render_training_card(profile: dict[str, Any], assessment: dict[str, Any], recommendation: dict[str, Any]) -> None:
    primary = recommendation["primary"]
    st.subheader("TODAY'S TRAINING")
    st.markdown(f"### {primary['name']}")
    left, middle, right = st.columns(3)
    left.metric("Intensity", recommendation["intensity"])
    middle.metric("Duration", recommendation["duration"])
    right.metric("Training type", primary["training_type"])
    st.write(recommendation["reason"])
    c1, c2, c3 = st.columns(3)
    with c1:
        show_template = st.button("View workout", key=f"view_{profile['user_id']}", type="primary", width="stretch")
    with c2:
        choose_alternative = st.button("Choose another option", key=f"alternative_{profile['user_id']}", width="stretch")
    with c3:
        ask = st.button("Ask Coach", key=f"coach_{profile['user_id']}", width="stretch")
    if ask:
        go_to("Coach")
    selected = primary
    if choose_alternative:
        st.session_state[f"show_workout_choices_{profile['user_id']}"] = True
    if st.session_state.get(f"show_workout_choices_{profile['user_id']}"):
        choices = [primary, *recommendation["alternatives"]]
        names = [item["name"] for item in choices]
        current_name = st.session_state.get(f"selected_workout_{profile['user_id']}", primary["name"])
        if current_name not in names: current_name = primary["name"]
        name = st.selectbox("Selected workout", names, index=names.index(current_name), key=f"alternative_choice_{profile['user_id']}")
        st.session_state[f"selected_workout_{profile['user_id']}"] = name
        selected = next(item for item in choices if item["name"] == name)
        label = "PRIMARY RECOMMENDATION" if name == primary["name"] else "RULE-GENERATED ALTERNATIVE"
        st.caption(f"{label} · Selecting an alternative does not overwrite the primary recommendation.")
        show_template = True
    if show_template:
        template = workout_template(selected)
        with st.expander(f"Workout template · {template['title']}", expanded=True):
            st.caption(f"{template['intensity']} · {template['duration']}")
            for item in template["items"]:
                st.markdown(f"- {item}")
            st.caption(template["note"])
    if assessment["overall_readiness"] != "STOP":
        with st.expander("Log this workout", expanded=False):
            st.caption("Only log a session after you have completed it. A recommendation is never recorded automatically.")
            defaults = prescription_log_defaults(selected)
            with st.form(f"training_log_{profile['user_id']}"):
                duration_default = float(sum(selected.get("estimated_duration_min", [45, 45])) / 2)
                duration = st.number_input("Completed duration (min)", 0.0, 300.0, duration_default, step=5.0, key=f"duration_{profile['user_id']}_{selected['prescription_id']}")
                rpe = st.select_slider("Session RPE", options=list(range(1, 11)), value=6)
                actual_exercises = []
                for index, exercise in enumerate(defaults["exercises"]):
                    actual = st.number_input(f"{exercise['name']} · actual completed sets", 0, 20, int(exercise["prescribed_sets"]), key=f"actual_{profile['user_id']}_{selected['prescription_id']}_{index}")
                    actual_exercises.append({"name": exercise["name"], "working_sets": actual, "prescribed_sets": exercise["prescribed_sets"]})
                completion_status = st.selectbox("Completion", ("Completed", "Partial"))
                notes = st.text_input("Notes (optional)")
                log = st.form_submit_button("Log completed workout", type="primary", width="stretch")
            if log:
                prescribed_sets = defaults["prescribed_sets"]
                actual_sets = sum(item["working_sets"] for item in actual_exercises)
                logged = log_training_session(profile, {"date": date.today().isoformat(), "training_type": selected["training_type"], "primary_focus": selected["name"], "muscle_groups": selected["muscle_groups"], "prescription_id": selected["prescription_id"], "exercises": actual_exercises, "prescribed_sets": prescribed_sets, "actual_sets": actual_sets, "completion_status": completion_status, "duration_min": duration, "session_rpe": rpe, "notes": notes})
                if not profile.get("is_demo"):
                    _queue_browser_save()
                    st.session_state.storage_status = f"Logged {logged['primary_focus']} · saving to this browser…"
                    st.rerun()
                st.success(f"Logged {logged['primary_focus']} for {logged['duration_min']:.0f} min with {logged['actual_sets']:g} actual sets ({logged['prescribed_sets']:g} prescribed).")


def render_today(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    if not profile.get("is_demo") and not profile.get("history"):
        st.markdown("<div class='ara-today-greeting'><span>PERSONAL READINESS</span><h1>Start with today’s check-in</h1><p>Record your first recovery signals to turn this space into a personal daily decision view.</p></div>", unsafe_allow_html=True)
        st.info("Your local profile starts empty by design. Nothing is inferred from the demo profile or sent to a server.")
        if primary_cta("Complete your first check-in", key=f"first_checkin_{profile['user_id']}"):
            go_to("Check-in")
        return
    identity = identity_badge(True) if profile.get("is_demo") else ""
    st.markdown(
        f"<div class='ara-today-greeting'><div class='ara-today-meta'><span>{date.today().strftime('%A, %d %B')}</span>{identity}</div>"
        f"<h1>Good morning, {escape(profile['name'])}</h1></div>", unsafe_allow_html=True)
    if profile.get("is_demo"):
        st.caption("Simulated demo profile · separate from My Local Data.")
    elif assessment["data_sufficiency"] == INSUFFICIENT:
        st.info("No complete check-in is saved for today. Open Check-in to record today's real inputs; this page does not generate demo values for My Local Data.")

    # 1. Readiness — the only question the hero answers is "how am I today?".
    mobile_readiness_hero(profile, assessment)
    if assessment["safety_flags"]:
        st.error("Safety check selected: " + ", ".join(assessment["safety_flags"]) + ". Pause demanding training and seek appropriate professional assessment for acute or concerning symptoms.")

    # 2. Today's training — WHAT to train and HOW HARD, with the primary action.
    recommendation = current_recommendation(profile, assessment)
    primary = recommendation["primary"]
    today_training_card(primary["name"], primary["training_type"], recommendation["intensity"], recommendation["duration"])
    if primary_cta("View workout", key=f"open_train_{profile['user_id']}"):
        go_to("Train")

    # 3. Why today — deterministic decision trace, split into direction and demand.
    st.subheader("WHY TODAY?")
    # Decision-trace step names are human readable ("WEEKLY EXPOSURE"); normalise
    # so a rename cannot silently drop a factor from the explanation.
    trace = {str(entry["step"]).replace("_", " ").strip().upper(): entry["value"] for entry in recommendation.get("decision_trace", [])}
    direction = [f"{label}: {trace[step]}" for step, label in (
        ("WEEKLY EXPOSURE", "Weekly exposure"),
        ("RECENT TRAINING", "Recent training"),
        ("PROGRAMME", "Programme"),
    ) if trace.get(step)]
    demand = [f"{label}: {trace[step]}" for step, label in (
        ("READINESS", "Readiness"),
        ("SESSION DEMAND", "Session demand"),
    ) if trace.get(step)]
    why_today(direction, demand)
    with st.expander("View full Decision Trace", expanded=False):
        for entry in recommendation["decision_trace"]:
            detail_row(entry["step"].replace("_", " ").title(), entry["value"], "")
        st.caption("Decision Trace shows product rules and factual inputs. It is not hidden model reasoning or a clinical recovery estimate.")

    # 4. Key signals — a small set, with units and a labelled status, no z-scores.
    domains, measures, today = assessment["domains"], assessment["measurements"], assessment["today_data"]
    load_status = domains["training_load"]

    def range_context(status: str, recorded: bool = True) -> str:
        if not recorded:
            return "Not recorded today"
        return {"GREEN": "Within your usual range", "AMBER": "Slightly outside your usual range", "RED": "Below your usual range"}.get(status, "Insufficient personal data")

    hrv_value, rhr_value, sleep_value = today.get("rmssd_ms"), today.get("resting_hr_bpm"), today.get("sleep_hours")
    sleep_need = profile.get("personal_sleep_need")
    tiles = [
        metric_tile("HRV", "—" if hrv_value is None else f"{hrv_value:.0f}", unit="ms" if hrv_value is not None else None,
                    context=range_context(measures["hrv"]["status"], hrv_value is not None), status=measures["hrv"]["status"]),
        metric_tile("Resting HR", "—" if rhr_value is None else f"{rhr_value:.0f}", unit="bpm" if rhr_value is not None else None,
                    context=range_context(measures["rhr"]["status"], rhr_value is not None), status=measures["rhr"]["status"]),
        metric_tile("Sleep", "—" if sleep_value is None else f"{sleep_value:.1f}", unit="h" if sleep_value is not None else None,
                    context=f"Usual need {sleep_need:.1f} h" if sleep_need else range_context(measures["sleep_duration"]["status"], sleep_value is not None),
                    status=measures["sleep_duration"]["status"]),
        metric_tile("Training load", "—" if measures["training_load"].get("recent_7d_mean") is None else f"{measures['training_load']['recent_7d_mean']:.0f}",
                    unit="AU" if measures["training_load"].get("recent_7d_mean") is not None else None,
                    context=range_context(load_status, measures["training_load"].get("recent_7d_mean") is not None), status=load_status),
    ]
    st.subheader("KEY SIGNALS")
    metric_grid(tiles)

    # 5. Deeper detail stays collapsed on the second screen.
    with st.expander("Readiness details"):
        detail_row("Autonomic", domains["autonomic"], range_context(domains["autonomic"], hrv_value is not None))
        detail_row("Sleep", domains["sleep"], "Not recorded today" if sleep_value is None else f"{sleep_value:.1f} h / {sleep_need:.1f} h usual need")
        detail_row("Wellness", domains["subjective"], "Not recorded today" if assessment["measurements"]["subjective_badness"] is None else ("Feeling stable" if domains["subjective"] == GREEN else "Self-reported recovery needs attention"))
        detail_row("Training load", domains["training_load"], "Not enough completed sessions in the comparison window" if load_status == INSUFFICIENT else range_context(load_status))
        st.caption("Technical readiness rationale (z-scores, baseline windows and engine wording) lives in Science & Logic, not on the daily decision screen.")
        st.download_button("Download assessment JSON", data=json.dumps({"assessment": assessment, "recommendation": recommendation}, indent=2), file_name=f"readiness-{profile['name'].lower()}-{assessment['assessment_date']}.json", mime="application/json")


def render_checkin(profile: dict[str, Any]) -> None:
    page_intro("MORNING READINESS", "Check-in", "Record today's recovery signals. Completed session-RPE belongs in the training log after a workout.")
    if profile.get("is_demo"):
        st.caption("Demo shortcuts")
        with st.container(key="checkin_scenarios"):
            for column, scenario in zip(st.columns(3), SCENARIOS):
                with column:
                    if st.button(scenario.replace(" Day", ""), key=f"scenario_{scenario}_{profile['user_id']}", width="stretch"):
                        set_draft(profile, scenario)
                        st.rerun()
    draft = get_draft(profile)
    with st.form(f"checkin_{profile['user_id']}"):
        st.subheader("Recovery")
        left, right = st.columns(2)
        with left:
            rmssd = st.number_input("RMSSD / HRV (ms)", 1.0, 250.0, float(draft["rmssd_ms"]), step=.1)
            rhr = st.number_input("Resting HR (bpm)", 25.0, 220.0, float(draft["resting_hr_bpm"]), step=.5)
        with right:
            sleep = st.number_input("Sleep duration (hours)", 0.0, 24.0, float(draft["sleep_hours"]), step=.1)
            quality = st.select_slider("Sleep quality", options=[1, 2, 3, 4, 5], value=int(draft["sleep_quality"]), help="1 = very poor · 5 = very good")
        st.subheader("How do you feel?")
        st.caption("Every scale runs 1 → 5. Higher is better only for motivation; for fatigue, soreness and stress a higher number means more of it.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.caption(scale_guidance("Fatigue"))
            fatigue = st.select_slider("Fatigue", [1, 2, 3, 4, 5], value=int(draft["fatigue"]))
        with c2:
            st.caption(scale_guidance("Soreness"))
            soreness = st.select_slider("Soreness", [1, 2, 3, 4, 5], value=int(draft["soreness"]))
        with c3:
            st.caption(scale_guidance("Stress"))
            stress = st.select_slider("Stress", [1, 2, 3, 4, 5], value=int(draft["stress"]))
        with c4:
            st.caption(scale_guidance("Motivation"))
            motivation = st.select_slider("Motivation", [1, 2, 3, 4, 5], value=int(draft["motivation"]))
        st.subheader("Local soreness (optional)")
        st.caption("Not reported is left blank and is reset each day.")
        local_soreness = {}
        with st.container(key="checkin_soreness"):
            # Two per row on phones: seven full-width selects was the longest part
            # of the check-in, and four per row is too narrow to read.
            for index, group in enumerate(("Chest", "Back", "Shoulders", "Arms", "Quads", "Hamstrings / Glutes", "Core")):
                if index % 2 == 0:
                    row = st.columns(2)
                with row[index % 2]:
                    existing = draft.get("local_soreness", {}).get(group)
                    value = st.selectbox(group, ["Not reported", 0, 1, 2, 3, 4, 5], index=0 if existing is None else int(existing) + 1, key=f"checkin_soreness_{profile['user_id']}_{group}")
                    if value != "Not reported": local_soreness[group] = int(value)
        st.subheader("Safety check")
        flags = st.multiselect("Select any current safety concern", SAFETY_FLAGS, default=draft.get("safety_flags", []), help="Any selection disables a normal workout recommendation.")
        analyse = st.form_submit_button("Calculate readiness", type="primary", width="stretch")
    if analyse:
        record = {"date": date.today().isoformat(), "rmssd_ms": rmssd, "resting_hr_bpm": rhr, "sleep_hours": sleep, "sleep_quality": quality, "fatigue": fatigue, "soreness": soreness, "local_soreness": local_soreness, "stress": stress, "motivation": motivation, "safety_flags": flags, "session_duration_min": None, "session_rpe": None, "session_load": None, "simulated": bool(profile.get("is_demo"))}
        st.session_state[draft_key(profile)] = {key: value for key, value in record.items() if key != "date" and key not in {"session_duration_min", "session_rpe", "session_load", "simulated"}}
        upsert_daily_metric(profile, record)
        saved_assessment = assess_readiness(record, profile["history"], profile["personal_sleep_need"], profile["assessments"])
        save_assessment(profile, saved_assessment)
        save_recommendation(profile, recommend_training(profile, saved_assessment, profile.get("training_history", [])), record["date"])
        st.session_state.chat_histories[profile["user_id"]] = []
        if not profile.get("is_demo"):
            _queue_browser_save()
            st.session_state.storage_status = "Check-in saved · saving to this browser…"
        go_to("Today")


def render_train(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    """Why this session, how to execute it, and what was actually completed."""
    page_intro("TODAY'S SESSION", "Train", "Why this session was selected, how to execute it, and what you actually completed.")
    recommendation = current_recommendation(profile, assessment)
    primary = recommendation["primary"]
    choices = [primary, *recommendation["alternatives"]]
    names = [item["name"] for item in choices]
    selected_name = st.session_state.get(f"selected_workout_{profile['user_id']}", primary["name"])
    if selected_name not in names:
        selected_name = primary["name"]

    # 1. Primary recommendation — highest visual priority, straight from the engine.
    train_primary_card(primary["name"], primary["training_type"], recommendation["intensity"], recommendation["duration"], rir_guidance(primary))

    # 2. Alternatives — explicitly second class: they never replace the primary.
    if recommendation["alternatives"]:
        st.subheader("ALTERNATIVES")
        st.caption("Rule-generated options. Selecting one never overwrites the primary recommendation.")
        selected_name = st.radio("Preview another option", names, index=names.index(selected_name), horizontal=True, key=f"train_choice_{profile['user_id']}")
    else:
        selected_name = primary["name"]
    st.session_state[f"selected_workout_{profile['user_id']}"] = selected_name
    selected = next(item for item in choices if item["name"] == selected_name)
    label = "PRIMARY RECOMMENDATION" if selected_name == primary["name"] else "RULE-GENERATED ALTERNATIVE"

    # 3. Execution: the prescription for whichever session is selected.
    template = workout_template(selected)
    st.subheader("HOW TO EXECUTE IT")
    st.caption(f"{label} · {template['title']} · {template['intensity']} · {template['duration']}")
    for item in template["items"]:
        st.markdown(f"<section class='ara-exercise-card'>{escape(item)}</section>", unsafe_allow_html=True)
    st.caption(template["note"])

    # 4. Avoid today — lowest priority, neutral tone (no medical-style alarm).
    if recommendation["avoid"]:
        insight_card("Avoid today", " · ".join(recommendation["avoid"]) + ". Not the current priority for this week's exposure.")

    # 5. Decision trace — the deterministic factors, not model reasoning.
    st.subheader("DECISION TRACE")
    st.caption("The product rules and recorded inputs behind this session. Not hidden model reasoning.")
    decision_trace_section(recommendation["decision_trace"])

    # 6. Log what was actually completed.
    if assessment["overall_readiness"] != "STOP":
        st.subheader("LOG WORKOUT")
        st.caption("7-day exposure uses actual completed sets (weighted working sets), not the planned prescription.")
        defaults = prescription_log_defaults(selected)
        with st.form(f"mobile_training_log_{profile['user_id']}_{selected['prescription_id']}"):
            duration_default = float(sum(selected.get("estimated_duration_min", [45, 45])) / 2)
            duration = st.number_input("Completed duration (min)", 0.0, 300.0, duration_default, step=5.0)
            rpe = st.select_slider("Session RPE", options=list(range(1, 11)), value=6)
            actual_exercises = []
            for index, exercise in enumerate(defaults["exercises"]):
                actual = st.number_input(f"{exercise['name']} · actual completed sets", 0, 20, int(exercise["prescribed_sets"]), key=f"mobile_actual_{profile['user_id']}_{selected['prescription_id']}_{index}")
                actual_exercises.append({"name": exercise["name"], "working_sets": actual, "prescribed_sets": exercise["prescribed_sets"]})
            completion_status = st.selectbox("Completion", ("Completed", "Partial"))
            notes = st.text_input("Notes (optional)")
            log = st.form_submit_button("Log completed workout", type="primary", width="stretch")
        if log:
            logged = log_training_session(profile, {"date": date.today().isoformat(), "training_type": selected["training_type"], "primary_focus": selected["name"], "muscle_groups": selected["muscle_groups"], "prescription_id": selected["prescription_id"], "exercises": actual_exercises, "prescribed_sets": defaults["prescribed_sets"], "actual_sets": sum(item["working_sets"] for item in actual_exercises), "completion_status": completion_status, "duration_min": duration, "session_rpe": rpe, "notes": notes})
            if not profile.get("is_demo"):
                _queue_browser_save()
                st.session_state.storage_status = f"Logged {logged['primary_focus']} · saving to this browser…"
                st.rerun()
            st.success(f"Logged {logged['primary_focus']} for {logged['duration_min']:.0f} min with {logged['actual_sets']:g} actual sets.")


def render_trends(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    page_intro("YOUR TRENDS", "Trends", "Patterns across your own recovery signals and completed training, not a single score.")
    history = pd.DataFrame(profile["history"])
    if not history.empty:
        history["date"] = pd.to_datetime(history["date"])
        history = history.sort_values("date")
        history["ln_rmssd"] = history["rmssd_ms"].map(ln_rmssd)
        history["lnrmssd_7d"] = history["ln_rmssd"].rolling(7, min_periods=1).mean()
        history["rhr_7d"] = history["resting_hr_bpm"].rolling(7, min_periods=1).mean()
        history["sleep_7d"] = history["sleep_hours"].rolling(7, min_periods=1).mean()
        history["load_7d"] = history["session_load"].rolling(7, min_periods=1).mean()
        # The window selector counts recorded check-ins, so it is labelled as
        # check-ins rather than as calendar days.
        window = st.radio("Time window", (7, 28, len(history)),
                          format_func=lambda value: f"Last {value} check-ins" if value != len(history) else f"All {len(history)} check-ins",
                          horizontal=True)
        shown = history.tail(window)
        baseline = assessment.get("baseline") or {}
        charts = st.columns(2)
        with charts[0]:
            st.subheader("HRV")
            st.caption("LnRMSSD · personal-baseline reference")
            trend_chart(shown, "ln_rmssd", "lnrmssd_7d", "LnRMSSD", baseline.get("lnrmssd_mean"), "#171717")
        with charts[1]:
            st.subheader("Resting HR")
            st.caption("bpm · personal-baseline reference")
            trend_chart(shown, "resting_hr_bpm", "rhr_7d", "bpm", baseline.get("rhr_mean"), "#171717")
        with charts[0]:
            st.subheader("Sleep")
            st.caption("Hours · personal-baseline reference")
            trend_chart(shown, "sleep_hours", "sleep_7d", "hours", baseline.get("sleep_mean"), "#171717")
        with charts[1]:
            st.subheader("Training load")
            st.caption("AU (duration × session RPE) · rolling mean")
            trend_chart(shown, "session_load", "load_7d", "AU", None, "#171717")
        st.caption("Dashed line: rolling mean over the most recent 7 check-ins. Horizontal reference: your personal baseline mean where available.")
    st.subheader("Training history")
    training = pd.DataFrame(profile.get("training_history", []))
    if training.empty:
        st.info("No completed sessions logged yet.")
    else:
        training["date"] = pd.to_datetime(training["date"])
        start = pd.Timestamp(date.today() - timedelta(days=13))
        count = int((training["date"] >= start).sum())
        st.metric("Sessions in the last 14 days", count)
        rows = [
            {"date": format_trend_date(row["date"]), "title": str(row.get("primary_focus") or row.get("training_type") or "Session"),
             "meta": f"{row.get('training_type', 'Training')} · {float(row.get('duration_min') or 0):.0f} min",
             "extra": f"RPE {row.get('session_rpe', '—')} · {float(row.get('session_load') or 0):.0f} AU"}
            for _, row in training.sort_values("date", ascending=False).iterrows()
        ]
        history_list(rows, "No completed sessions logged yet.")
    st.subheader("Readiness history")
    assessments = pd.DataFrame(profile["assessments"])
    if not assessments.empty:
        rows = [
            {"date": format_trend_date(row["assessment_date"]), "title": f"{row.get('overall_readiness', '—')}",
             "meta": f"Index {row['readiness_index'] if row.get('readiness_index') is not None else '—'}",
             "extra": f"Baseline confidence {row.get('assessment_confidence', '—')}"}
            for _, row in assessments.sort_values("assessment_date", ascending=False).iterrows()
        ]
        history_list(rows, "No readiness assessments recorded yet.")


def profile_chat_history(profile: dict[str, Any]) -> list[dict[str, str]]:
    messages = st.session_state.setdefault("chat_histories", {}).setdefault(profile["user_id"], [])
    if len(messages) > 30:
        del messages[:-30]
    return messages


def _queue_chat_save(profile: dict[str, Any]) -> None:
    """Persist a completed exchange without making storage a chat dependency."""
    if profile.get("is_demo"):
        return
    try:
        _queue_browser_save()
        st.session_state.storage_status = "Chat saved locally in this browser."
    except Exception:
        st.session_state.storage_error = "Chat history could not be saved locally. The current answer is still available."


def _submit_question(question: str, profile: dict[str, Any], assessment: dict[str, Any], recommendation: dict[str, Any]) -> None:
    messages = profile_chat_history(profile)
    messages.append({"role": "user", "content": question})
    canonical, _, _ = get_instant_response(question, profile, assessment, recommendation)
    with st.spinner("Preparing your explanation…"):
        answer, provider, notice = get_ai_response(question, profile, assessment, recommendation, messages[:-1], st.secrets)
    if provider == "Instant explanation":
        answer = canonical
        provider = "Rule-based fallback"
    messages.append({"role": "assistant", "content": answer, "provider": provider, "source_question": question, "kind": "enhanced" if provider.startswith("Built-in") else "fallback", "ai_requested": True})
    if len(messages) > 30:
        del messages[:-30]
    _queue_chat_save(profile)
    st.session_state.chat_notice = notice


def _enhance_question(index: int, profile: dict[str, Any], assessment: dict[str, Any], recommendation: dict[str, Any]) -> None:
    message = profile_chat_history(profile)[index]
    message["ai_requested"] = True
    with st.spinner("Preparing the embedded open-source model. First use may take a little longer."):
        answer, provider, notice = get_ai_response(message["source_question"], profile, assessment, recommendation, profile_chat_history(profile)[:index], st.secrets)
    if provider in {"Instant explanation", "Safety rule"}:
        message["ai_unavailable"] = True
    else:
        profile_chat_history(profile).append({"role": "assistant", "content": answer, "provider": provider, "kind": "enhanced"})
        _queue_chat_save(profile)
    st.session_state.chat_notice = notice


def render_coach(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    recommendation = current_recommendation(profile, assessment)
    page_intro("AI COACH", "Context-aware Training Coach",
               "The Coach can answer general training and recovery questions and explain your readiness, today's session and recent training. Readiness and the primary recommendation stay deterministic.")
    coach_context_header(assessment, recommendation)
    questions = COACH_QUICK_QUESTIONS
    quick_questions(questions, lambda question: (_submit_question(question, profile, assessment, recommendation), st.rerun()))
    if st.session_state.get("chat_notice"):
        st.caption(st.session_state.chat_notice)
    for index, message in enumerate(profile_chat_history(profile)):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                provider = message.get("provider", "")
                label = ("VERIFIED DATA" if provider.startswith("Verified")
                         else "AI-ENHANCED EXPLANATION" if message.get("kind") == "enhanced"
                         else "RULE-BASED FALLBACK")
                st.caption(label + " · " + message.get("provider", ""))
            st.markdown(message["content"])
            if message.get("kind") == "fallback" and not str(message.get("provider", "")).startswith("Verified"):
                st.caption("Rule-based fallback · The deterministic recommendation remains valid.")
    if question := st.chat_input("Ask about readiness, training, recovery, RIR, volume, or today's workout…"):
        _submit_question(question, profile, assessment, recommendation)
        st.rerun()
    with st.expander("How the Coach works"):
        st.write("The Readiness Engine and Training Recommendation Engine create the status, recommendation and alternatives first. Optional Qwen wording is never used to choose, replace or modify a workout.")


def render_more(profile: dict[str, Any]) -> None:
    """A small settings-style routing surface; it preserves the existing data flows."""
    page_intro("SETTINGS", "More", "Profile, local data controls, disclosure and product information.")
    profile_switcher(profile)
    if not profile.get("is_demo"):
        callout("LOCAL BROWSER STORAGE", "Saved personal history is stored locally in this browser on this device. This prototype does not persist personal history to a remote personal database.")
    st.subheader("PROFILE")
    if secondary_cta("Training goal, split, sleep need and weekly targets", key="more_profile"):
        go_to("Profile")
    st.subheader("DATA")
    if secondary_cta("Export, import or clear local data", key="more_data"):
        go_to("Profile")
    st.subheader("LEARN")
    if secondary_cta("Science & Logic", key="more_science"):
        go_to("Science & Logic")
    st.subheader("INFO")
    if secondary_cta("Data & Privacy and About", key="more_about"):
        go_to("About")


def render_profile(profile: dict[str, Any]) -> None:
    page_intro("YOUR SETUP", "Profile", "Your goal, activity, training level, sleep need and preferred split guide contextual recommendations.")
    if profile.get("is_demo"):
        st.info("DEMO PROFILE · This fixed simulated profile is separate from My Local Data and is not written to your personal browser history.")
    else:
        callout("Data storage · Local browser only", "Saved personal history is stored locally in this browser. No remote personal-history database is used.")
    with st.form(f"profile_{profile['user_id']}"):
        left, right = st.columns(2)
        with left:
            name = st.text_input("Name", value=profile["name"])
            age = st.number_input("Age", 16, 100, int(profile["age"]))
            sex = st.selectbox("Sex", SEXES, index=SEXES.index(profile["sex"]))
            activity = st.selectbox("Primary activity", ACTIVITIES, index=ACTIVITIES.index(profile["primary_activity"]))
        with right:
            goal = st.selectbox("Training goal", GOALS, index=GOALS.index(profile["training_goal"]))
            level = st.selectbox("Training level", LEVELS, index=LEVELS.index(profile["training_level"]))
            split = st.selectbox("Preferred training split", SPLITS, index=SPLITS.index(profile.get("training_split_preference", "No Preference")))
            target_sessions = st.number_input("Target sessions / week", 0, 14, int(profile.get("target_sessions_per_week", 3)))
            sleep_need = st.number_input("Personal sleep need (hours)", 4.0, 12.0, float(profile["personal_sleep_need"]), step=.1)
        if st.form_submit_button("Save profile", type="primary", width="stretch"):
            update_profile(profile, {"name": name, "age": age, "sex": sex, "primary_activity": activity, "training_goal": goal, "training_level": level, "training_split_preference": split, "target_sessions_per_week": target_sessions, "personal_sleep_need": sleep_need})
            if not profile.get("is_demo"):
                _queue_browser_save()
                st.session_state.storage_status = "Profile updated · saving to this browser…"
                st.rerun()
            else:
                st.success("Demo profile updated for this session only.")
    if not profile.get("is_demo"):
        with st.expander("Weekly set targets", expanded=False):
            st.caption("Optional planning targets. They are not universal optimal-volume claims.")
            with st.form(f"targets_{profile['user_id']}"):
                targets = {}
                columns = st.columns(2)
                for index, group in enumerate(MUSCLE_GROUPS):
                    with columns[index % 2]:
                        targets[group] = st.number_input(group, 0.0, 40.0, float(profile.get("weekly_set_targets", {}).get(group, 0)), step=1.0, key=f"target_{profile['user_id']}_{group}")
                if st.form_submit_button("Save weekly targets"):
                    update_profile(profile, {"weekly_set_targets": {key: value for key, value in targets.items() if value > 0}})
                    _queue_browser_save()
                    st.session_state.storage_status = "Weekly targets updated · saving to this browser…"
                    st.rerun()
    if profile.get("is_demo"):
        with st.expander("Advanced demo tools"):
            if st.button("Regenerate simulated readiness history", key=f"sample_{profile['user_id']}"):
                generate_sample_history(profile)
                st.success("Simulated readiness history regenerated for this demo session.")
    else:
        with st.expander("Delete this local profile"):
            if st.button("Delete active profile", key=f"delete_{profile['user_id']}"):
                delete_profile(st.session_state, profile["user_id"])
                _queue_browser_save()
                st.rerun()
    st.subheader("Create My Local Profile")
    with st.form("new_profile"):
        new_name = st.text_input("Profile name")
        if st.form_submit_button("Create My Local Profile"):
            try:
                create_profile(st.session_state, {"name": new_name})
                _queue_browser_save()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.subheader("Backup & local data")
    st.caption("Another browser or device will not automatically contain this history. Clearing site data or using private browsing may make it unavailable.")
    local_profiles = [item for item in st.session_state.profiles if not item.get("is_demo")]
    if local_profiles:
        st.download_button("Export My Data", data=export_backup(_local_document()), file_name="personal-readiness-backup.json", mime="application/json", width="stretch")
    else:
        st.info("Create My Local Profile before exporting personal history.")
    with st.expander("Import Backup · Replace local data"):
        uploaded = st.file_uploader("Select personal-readiness-backup.json", type=["json"], key="backup_upload")
        if uploaded and st.button("Validate backup", key="validate_backup"):
            try:
                st.session_state.import_candidate = import_backup(uploaded.getvalue())
                st.success("Backup structure is valid. Confirm replacement below.")
            except LocalDataError as exc:
                st.session_state.import_candidate = None
                st.error(f"Backup rejected safely: {exc}")
        if st.session_state.get("import_candidate"):
            confirmed = st.checkbox("This will replace the Personal Readiness history currently stored in this browser.", key="confirm_import_replace")
            if st.button("Replace with validated backup", disabled=not confirmed, type="primary"):
                hydrate_runtime_state(st.session_state, st.session_state.import_candidate)
                st.session_state.import_candidate = None
                _queue_browser_save()
                st.rerun()
    with st.expander("Clear Local Data"):
        st.warning("This permanently removes the Personal Readiness data stored in this browser. Because no remote backup is used, it cannot be restored unless you exported a backup.")
        confirmed = st.checkbox("I understand that this deletes My Local Data from this browser.", key="confirm_clear_local")
        if st.button("Clear Local Data", disabled=not confirmed):
            clear_local_runtime(st.session_state)
            _queue_browser_clear()
            st.rerun()


def render_science_logic() -> None:
    page_intro("SCIENCE & LOGIC", "How the system works", "How Personal Readiness turns longitudinal data into an evidence-informed daily training decision.")
    st.info("This prototype combines published sports-science monitoring principles with transparent product heuristics. The cited literature supports the underlying concepts, but does not validate this application's exact algorithm or thresholds.")
    st.subheader("System overview")
    steps = ("PERSONAL BASELINE", "DAILY CHECK-IN", "FOUR READINESS DOMAINS", "SAFETY SCREEN", "OVERALL READINESS", "TRAINING HISTORY", "WEEKLY TRAINING EXPOSURE", "GOAL + SPLIT", "LOCAL SORENESS", "SESSION DEMAND", "TODAY'S TRAINING RECOMMENDATION")
    st.markdown(" → ".join(f"**{step}**" for step in steps))

    st.subheader("Readiness inputs")
    inputs = {
        "AUTONOMIC": "HRV / RMSSD · Resting heart rate",
        "SLEEP": "Sleep duration relative to personal sleep need · Sleep quality",
        "SUBJECTIVE WELLNESS": "Fatigue · Stress · Motivation · Global soreness",
        "TRAINING LOAD": "Completed-session duration · Session RPE · Recent load trend",
        "TRAINING CONTEXT": "Goal · Split · Completed sessions · Weekly muscle exposure · Today's local soreness",
    }
    for column, (title, body) in zip(st.columns(5), inputs.items()):
        with column: flow_card("INPUT", title, body)

    st.subheader("Personal baseline & four readiness domains")
    st.write("The product prioritises today-versus-your-own-history comparisons. RMSSD is log-transformed, then standardized against valid personal observations. This is a monitoring feature, not a medical abnormality score.")
    st.code(READINESS_RULE_METADATA["baseline"]["transform"] + "\n" + READINESS_RULE_METADATA["baseline"]["comparison"])
    st.caption(f"Baseline Confidence uses valid paired longitudinal observations: Insufficient < {READINESS_RULE_METADATA['baseline']['limited_valid_observations']}; Limited {READINESS_RULE_METADATA['baseline']['limited_valid_observations']}–{READINESS_RULE_METADATA['baseline']['normal_valid_observations'] - 1}; Normal ≥ {READINESS_RULE_METADATA['baseline']['normal_valid_observations']}. It describes data sufficiency, not model certainty.")
    threshold_rows = []
    names = {"hrv_z": "HRV / LnRMSSD z", "rhr_z": "Resting HR z", "sleep_ratio": "Sleep / personal need", "sleep_quality": "Sleep quality", "subjective_badness": "Subjective badness"}
    for key, values in READINESS_RULE_METADATA["thresholds"].items():
        threshold_rows.append({"Input": names[key], "GREEN": values[GREEN], "AMBER": values[AMBER], "RED": values[RED], "Evidence label": EVIDENCE_LABELS["heuristic"]})
    st.dataframe(pd.DataFrame(threshold_rows), hide_index=True, width="stretch")
    st.caption("All exact category boundaries above are transparent prototype operating thresholds — NOT A CLINICAL THRESHOLD.")

    st.subheader("Overall readiness logic")
    for rule in READINESS_RULE_METADATA["overall_rule"]:
        st.markdown(f"- {rule}")
    st.write("The Readiness Index is a secondary communication score: " + ", ".join(f"{key} = {value}" for key, value in READINESS_RULE_METADATA["readiness_index"].items()) + ", averaged across classifiable domains. It is not a recovery percentage, fatigue probability or injury probability.")
    st.warning("Safety override: chest pain, fainting / near fainting, fever / acute illness, acute injury preventing normal training, or unusual shortness of breath routes to STOP. This is conservative product routing, not a medical diagnosis.")

    st.subheader("How today's training is selected")
    for index, step in enumerate(RECOMMENDATION_RULE_METADATA["decision_order"], start=1):
        st.markdown(f"**{index}. {step}**")
    st.write("Readiness primarily modifies session demand: Green → Normal; Amber → Reduced / autoregulated; Red → rest or lower-demand; STOP → no normal recommendation. Goal and split maintain programme direction; completed work, weekly exposure and today's local soreness organize compatible options.")
    load_rules = READINESS_RULE_METADATA["training_load"]
    st.write(f"Training Load is calendar-based: mean daily session-RPE load across the {load_rules['recent_window']} is compared with the {load_rules['reference_window']}. All completed sessions on one date are summed. A tracked date with no completed session contributes 0 AU; a missing date remains unknown. A full comparison requires {load_rules['full_coverage_days']} covered calendar dates. A near-zero reference mean returns insufficient data instead of an unstable percentage.")
    st.write("Weekly resistance-training exposure uses actual completed working sets. Direct sets count as 1.0 and mapped secondary sets as 0.5. An unmapped exercise falls back, once per exercise, to an explicit primary muscle group or a clearly mappable session focus. This fractional model is a transparent approximation, not an exact physiological stimulus ratio.")
    st.write("Training frequency is used to distribute volume and preserve programme structure. It is not treated as a fixed 48- or 72-hour muscle-recovery clock. Easy aerobic work and mobility are labelled lower-demand options, not guaranteed recovery accelerators.")
    st.write("For strength templates, normal-demand guidance is typically 1–3 RIR; reduced-demand guidance is 2–4 RIR with unnecessary failure avoided. These are practical product ranges, not validated readiness thresholds. For Endurance / Running-focused users, autonomic status modifies hard versus lower-intensity aerobic demand rather than choosing chest versus back.")

    st.subheader("Evidence vs product heuristics")
    st.dataframe(pd.DataFrame([{"Concept": item["concept"], "Evidence": item["evidence"], "Implementation": item["implementation"], "Label": item["label"], "PMID": ", ".join(item["pmids"]) or "—"} for item in EVIDENCE_MAP.values()]), hide_index=True, width="stretch")

    st.subheader("Example decision")
    st.markdown("**Goal:** Muscle Gain  \n**Programme:** Body-part Split  \n**Today:** GREEN  \n**Back:** 6 / 12 weekly sets  \n**Chest:** 10 / 10  \n**Yesterday:** Legs · RPE 8  \n**Local soreness:** Quads 4 / 5  \n\n**Recommendation:** Back + Biceps")
    st.caption("Goal favours resistance training; Back is below target; Chest is near target; Legs were trained recently at high effort; lower-body soreness is elevated; Green readiness supports normal session demand.")

    st.subheader("What this system does not claim")
    for item in LIMITATIONS: st.markdown(f"- {item}")

    st.subheader("References")
    for reference in REFERENCES:
        st.markdown(f"**{reference['authors']}** ({reference['year']}). {reference['title']}. *{reference['journal']}*, {reference['citation']}. [PMID {reference['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{reference['pmid']}/)")


def render_about(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    page_intro("TRANSPARENT BY DESIGN", "About this prototype", "A personal-baseline readiness and workout decision-support prototype.")
    st.subheader("Product flow")
    for column, number, title, body in zip(st.columns(6), ("01", "02", "03", "04", "05", "06"), ("Profile", "Morning check-in", "Readiness", "Recent training", "Workout direction", "Training log"), ("Goal and split preference", "Recovery signals", "Four deterministic domains", "Completed sessions", "Rule-generated primary + alternatives", "Explicit completed-session record")):
        with column: flow_card(number, title, body)
    st.subheader("Safety and scope")
    st.warning("Workout recommendations are heuristic decision-support suggestions based on readiness, recent training history, reported soreness and goals. They are not clinically validated prescriptions, medical advice, injury prediction or a measurement of muscle recovery.")
    st.subheader("AI architecture")
    st.write("Readiness and workout recommendations are deterministic, transparent rules. Qwen2.5-0.5B is optional and supports context-aware training conversation after a Coach question. It runs with the application, uses no commercial AI API or API key, and cannot alter the stored readiness or deterministic primary recommendation.")
    st.subheader("Data & Privacy")
    callout("YOUR DATA STAYS LOCAL", "Your saved personal readiness, check-in and training-history data are stored only in your local browser on this device.")
    st.write("This prototype does not persist personal history to a remote database. Data required for readiness, recommendations and AI responses may be temporarily processed by the running application, but it is not intentionally written to a remote personal-history database.")
    st.write("Local browser data is not automatically synchronized across browsers or devices. Clearing browser site data, using private browsing, or changing the application's origin/domain may make it unavailable. Export Backup is recommended if the history matters to you.")
    st.caption("Personal history persistence: browser-local IndexedDB · AI inference: embedded model running with the application · Commercial AI API: none")
    with st.expander("Developer diagnostics"):
        st.json(ai_diagnostics(st.secrets))
    st.caption(f"Current walkthrough: {profile['name']} is {assessment['overall_readiness']} today. The engine does not expose private chain-of-thought; it exposes factual decision factors and rationale instead.")


def render_first_use_privacy_notice(profile: dict[str, Any]) -> None:
    if profile.get("is_demo") or st.session_state.get("local_preferences", {}).get("privacy_notice_acknowledged"):
        return
    with st.container(border=True):
        st.subheader("Your data stays in this browser")
        st.write("Your saved readiness, check-in and training-history data are stored locally in this browser on this device. This prototype does not use a remote database for persistent personal history.")
        st.caption("Your history will not automatically follow you to another browser or device. Clearing site data, using private/incognito mode, or changing browser/device may make it unavailable. Use Export My Data if you want to keep or transfer a copy.")
        if st.button("Got it", type="primary", key="acknowledge_privacy"):
            st.session_state.local_preferences["privacy_notice_acknowledged"] = True
            _queue_browser_save()
            st.rerun()


def main() -> None:
    initialise_store(st.session_state)
    st.session_state.setdefault("current_page", "Today")
    st.session_state.setdefault("chat_histories", {})
    st.session_state.setdefault("local_preferences", {"privacy_notice_acknowledged": False})
    st.session_state.setdefault("browser_hydrated", False)
    st.session_state.setdefault("storage_revision", 0)
    st.session_state.setdefault("pending_storage", None)
    _sync_browser_storage()
    inject_styles()
    mobile_shell_bridge()
    profile = get_profile(st.session_state)
    render_sidebar(profile)
    page = render_sidebar_navigation()
    render_mobile_utility_nav()
    assessment = current_assessment(profile)
    render_first_use_privacy_notice(profile)
    if page == "Today":
        render_today(profile, assessment)
    elif page == "Check-in":
        render_checkin(profile)
    elif page == "Train":
        render_train(profile, assessment)
    elif page == "Trends":
        render_trends(profile, assessment)
    elif page == "Coach":
        render_coach(profile, assessment)
    elif page == "More":
        render_more(profile)
    elif page == "Profile":
        render_profile(profile)
    elif page == "Science & Logic":
        render_science_logic()
    else:
        render_about(profile, assessment)
    render_bottom_navigation()


if __name__ == "__main__":
    main()
