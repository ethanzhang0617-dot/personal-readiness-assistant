"""Regression tests for readiness, deterministic training and optional AI boundaries."""

from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import json
import re

import pytest

import ai_engine
import ai_facts
from ai_engine import DEFAULT_DEEPSEEK_MODEL, get_ai_response, get_instant_response
from app import real_today_inputs, scenario_values, validate_uploaded_csv
from demo_data import build_demo_profiles
from local_data import LocalDataError, clear_local_runtime, empty_local_state, export_backup, hydrate_runtime_state, import_backup, profiles_from_local_state, serialize_runtime_state, validate_local_state
from profile_store import create_profile, log_training_session, save_assessment, save_recommendation, upsert_daily_metric
from readiness_engine import AMBER, GREEN, INSUFFICIENT, RED, STOP, READINESS_RULE_METADATA, assess_readiness, hrv_status, ln_rmssd, rhr_status, safe_z, session_load, sleep_duration_status, sleep_quality_status, subjective_badness, subjective_status, training_load_domain
from training_recommendation_engine import RECOMMENDATION_RULE_METADATA, recommend_training
from training_recommendation_engine import EXERCISE_MUSCLE_MAPPING, WORKOUTS, fractional_set_contributions, prescription_log_defaults, weekly_training_exposure, workout_template


class Runtime(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


#: A fake credential. Every AI test injects it so no test can reach a real
#: provider endpoint, and no test asserts on a real key.
_FAKE_KEY_VALUE = "test-key-not-a-real-credential"
_CONFIGURED = {"DEEPSEEK_API_KEY": _FAKE_KEY_VALUE}


def readiness_history(days: int = 35) -> list[dict]:
    today = date.today()
    return [{"date": (today - timedelta(days=days - item)).isoformat(), "rmssd_ms": 50 + item % 3, "resting_hr_bpm": 55 + item % 2, "sleep_hours": 8.0, "sleep_quality": 4, "session_duration_min": 60, "session_rpe": 5, "session_load": 300, "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4} for item in range(days)]


def assessment(status: str = GREEN, **overrides: object) -> dict:
    result = {"assessment_date": date.today().isoformat(), "overall_readiness": status, "domains": {"autonomic": GREEN, "sleep": GREEN, "subjective": GREEN, "training_load": GREEN}, "today_data": {"soreness": 1}, "key_contributors": [], "safety_flags": [], "decision_support": ["Use context."]}
    result.update(overrides)
    return result


def ethan() -> dict:
    return build_demo_profiles()[0]


def test_readiness_math_basics() -> None:
    assert round(ln_rmssd(50) or 0, 5) == round(3.912023005, 5)
    assert ln_rmssd(0) is None
    assert safe_z(4, 4, 0) is None
    assert hrv_status(-.5) == GREEN and hrv_status(-.7) == AMBER and hrv_status(-1.1) == RED
    assert rhr_status(.5) == GREEN and rhr_status(.7) == AMBER and rhr_status(1.1) == RED
    assert session_load(90, 7) == 630.0


def test_sleep_and_subjective_classification() -> None:
    assert sleep_duration_status(7.2, 8)[0] == GREEN
    assert sleep_duration_status(6.5, 8)[0] == AMBER
    assert sleep_duration_status(6.3, 8)[0] == RED
    assert sleep_quality_status(4) == GREEN and sleep_quality_status(3) == AMBER
    assert subjective_status(subjective_badness({"fatigue": 5, "soreness": 5, "stress": 5, "motivation": 1}) or 0) == RED


def test_readiness_engine_remains_separate_from_recommendation_engine() -> None:
    source = Path("readiness_engine.py").read_text(encoding="utf-8")
    assert "recommend_training" not in source
    assert "from ai_engine" not in source


def test_demo_profiles_have_fixed_training_history() -> None:
    profiles = build_demo_profiles()
    assert [profile["name"] for profile in profiles] == ["Ethan", "Alex", "Jessica"]
    assert all(len(profile["training_history"]) >= 14 for profile in profiles)
    assert all(row["completed"] for profile in profiles for row in profile["training_history"])


def test_green_legs_yesterday_does_not_recommend_legs_again() -> None:
    profile = ethan()
    result = recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert result["primary"]["name"] != "Legs"


def test_green_chest_yesterday_deprioritises_chest() -> None:
    profile = ethan()
    profile["training_history"] = [{"date": (date.today() - timedelta(days=1)).isoformat(), "completed": True, "primary_focus": "Push", "muscle_groups": ["chest", "triceps"]}]
    result = recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert result["primary"]["name"] != "Chest + Triceps"


def test_back_is_selected_when_legs_and_chest_are_more_recent() -> None:
    profile = ethan()
    result = recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert result["primary"]["name"] == "Back + Biceps"


def test_high_soreness_avoids_high_load_strength() -> None:
    profile = ethan()
    result = recommend_training(profile, assessment(AMBER, today_data={"soreness": 5}), profile["training_history"])
    assert result["primary"]["training_type"] == "Aerobic"
    assert any("soreness" in value.casefold() for value in result["avoid"])


def test_red_returns_recovery_not_hard_strength() -> None:
    result = recommend_training(ethan(), assessment(RED), [])
    assert result["primary"]["training_type"] == "Aerobic"
    assert "Heavy strength" in result["avoid"]


def test_stop_disables_normal_workout() -> None:
    result = recommend_training(ethan(), assessment(STOP, safety_flags=["Chest pain"]), [])
    assert result["primary"]["name"] == "No normal workout recommendation"
    assert result["intensity"] == "STOP"


def test_amber_load_driven_is_easy_aerobic() -> None:
    result = recommend_training(ethan(), assessment(AMBER, domains={"autonomic": GREEN, "sleep": GREEN, "subjective": GREEN, "training_load": AMBER}), [])
    assert result["primary"]["name"] == "Easy Aerobic + Mobility"
    assert result["duration"] == "30–40 min"


def test_amber_sleep_driven_low_soreness_allows_reduced_strength() -> None:
    result = recommend_training(ethan(), assessment(AMBER, domains={"autonomic": GREEN, "sleep": AMBER, "subjective": GREEN, "training_load": GREEN}), [])
    assert result["primary"]["training_type"] == "Strength"
    assert result["intensity"] == "Reduced strength"
    assert result["volume_modifier"] == "Reduced strength"


def test_endurance_goal_weights_aerobic_training() -> None:
    profile = build_demo_profiles()[1]
    result = recommend_training(profile, assessment(GREEN), [])
    assert result["primary"]["training_type"] == "Strength" or result["primary"]["training_type"] == "Aerobic"
    # The rule's alternatives retain an aerobic route and goal weighting is explicit.
    assert "Endurance" in result["decision_factors"][0]


def test_ppl_push_yesterday_prefers_pull() -> None:
    profile = ethan()
    profile["training_split_preference"] = "Push / Pull / Legs"
    profile["training_history"] = [{"date": (date.today() - timedelta(days=1)).isoformat(), "completed": True, "primary_focus": "Push", "muscle_groups": ["chest", "triceps"]}]
    result = recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert result["primary"]["focus"] == "Pull"


def test_upper_lower_rotation_is_respected() -> None:
    profile = ethan()
    profile["training_split_preference"] = "Upper / Lower"
    profile["training_history"] = [{"date": date.today().isoformat(), "completed": True, "primary_focus": "Lower", "muscle_groups": ["quads", "glutes"]}]
    result = recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert result["primary"]["focus"] == "Upper"


def test_recommendation_is_pure_and_never_auto_logs() -> None:
    profile = ethan()
    before = len(profile["training_history"])
    recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert len(profile["training_history"]) == before


def test_explicit_log_updates_history_and_future_context() -> None:
    profile = create_profile(type("State", (), {"profiles": [], "active_profile_id": "", "chat_notice": None})(), {"name": "Test"})
    log_training_session(profile, {"date": date.today().isoformat(), "training_type": "Strength", "primary_focus": "Legs", "muscle_groups": ["quads", "glutes"], "duration_min": 60, "session_rpe": 7})
    assert len(profile["training_history"]) == 1
    next_day = recommend_training(profile, assessment(GREEN, assessment_date=(date.today() + timedelta(days=1)).isoformat()), profile["training_history"], as_of=date.today() + timedelta(days=1))
    assert next_day["primary"]["name"] != "Legs"


def test_rationale_is_factual_and_has_no_fake_recovery_percentage() -> None:
    result = recommend_training(ethan(), assessment(GREEN), ethan()["training_history"])
    text = " ".join(result["rationale"] + result["decision_factors"])
    assert "Readiness is GREEN" in text
    assert "%" not in text


def test_ai_instant_uses_recent_training_recommendation() -> None:
    profile = ethan()
    recommendation = recommend_training(profile, assessment(GREEN), profile["training_history"])
    answer, provider, _ = get_instant_response("Why not train legs today?", profile, assessment(GREEN), recommendation)
    assert provider == "Instant explanation"
    assert "Legs" in answer


def test_ai_failure_leaves_deterministic_answer(monkeypatch) -> None:
    profile = ethan()
    recommendation = recommend_training(profile, assessment(GREEN), profile["training_history"])
    monkeypatch.setattr(ai_engine, "_generate", lambda *args: (_ for _ in ()).throw(RuntimeError("offline")))
    answer, provider, notice = get_ai_response("Why this workout?", profile, assessment(GREEN), recommendation, (), _CONFIGURED)
    assert provider == "Instant explanation"
    assert notice and "deterministic" in notice
    assert recommendation["primary"]["name"] in answer


def test_ai_diagnostics_report_the_provider_without_exposing_a_key() -> None:
    diagnostics = ai_engine.ai_diagnostics({})
    assert diagnostics["Provider"] == "DeepSeek"
    assert diagnostics["Model"] == DEFAULT_DEEPSEEK_MODEL
    assert diagnostics["API key"] == "Not configured"
    assert diagnostics["Explanation layer"] == "Disabled"
    configured = ai_engine.ai_diagnostics(_CONFIGURED)
    assert configured["API key"] == "Configured"
    assert configured["Explanation layer"] == "Enabled"
    # the key value itself is never part of the diagnostics payload
    assert _FAKE_KEY_VALUE not in json.dumps(configured)


def test_english_only_streamlit_cloud_source_has_no_language_selector() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    assert "language_toggle" not in source
    assert "from i18n" not in source
    assert "Streamlit Community Cloud" in Path("README.md").read_text(encoding="utf-8")


def test_old_modelscope_and_docker_files_are_removed() -> None:
    assert not Path("Dockerfile").exists()
    assert not Path("ms_deploy.json").exists()
    assert not Path("i18n.py").exists()
    assert "modelscope" not in Path("requirements.txt").read_text(encoding="utf-8").casefold()


def test_sidebar_and_training_cards_exist() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    for name in ("Today", "Check-in", "Train", "Trends", "Coach", "More", "Profile", "TODAY'S TRAINING", "WHY TODAY?", "KEY SIGNALS"):
        assert name in source
    assert "render_sidebar_navigation" in source
    assert "render_bottom_navigation" in source
    assert "mobile_bottom_nav" in source


def test_today_dashboard_renders_without_calling_the_ai_provider() -> None:
    from streamlit.testing.v1 import AppTest
    dashboard = AppTest.from_file("app.py").run(timeout=20)
    assert not dashboard.exception
    assert any(item.label == "View workout" for item in dashboard.button)
    assert ai_engine._diag["request_attempted"] is False


def test_csv_validation_still_rejects_missing_columns() -> None:
    rows, warnings = validate_uploaded_csv(BytesIO(b"date,rmssd_ms\n2026-01-01,50\n"))
    assert not rows and warnings


def test_scenarios_continue_to_produce_morning_inputs() -> None:
    values = scenario_values(ethan(), "High Load / Poor Sleep Day")
    assert values["sleep_quality"] == 2
    assert values["soreness"] == 4


def test_readiness_still_runs_without_training_recommendation_or_ai() -> None:
    row = {"date": date.today().isoformat(), "rmssd_ms": 51, "resting_hr_bpm": 55, "sleep_hours": 8, "sleep_quality": 4, "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4, "safety_flags": []}
    result = assess_readiness(row, readiness_history(), 8)
    assert result["overall_readiness"] in {GREEN, AMBER, RED, "INSUFFICIENT DATA"}


def test_fractional_set_accounting() -> None:
    values = fractional_set_contributions([{"name": "Bench Press", "working_sets": 3}, {"name": "Chest-Supported Row", "working_sets": 3}])
    assert values["Chest"] == 3.0
    assert values["Back"] == 3.0
    assert values["Arms"] == 3.0
    assert values["Shoulders"] == 3.0
    assert "Bench Press" in EXERCISE_MUSCLE_MAPPING


def test_weekly_exposure_uses_only_completed_last_seven_days() -> None:
    rows = [{"date": date.today().isoformat(), "completed": True, "exercises": [{"name": "Bench Press", "working_sets": 3}]}, {"date": (date.today() - timedelta(days=8)).isoformat(), "completed": True, "exercises": [{"name": "Bench Press", "working_sets": 10}]}, {"date": date.today().isoformat(), "completed": False, "exercises": [{"name": "Bench Press", "working_sets": 10}]}]
    assert weekly_training_exposure(rows)["Chest"] == 3.0


def test_weekly_target_and_exposure_are_visible_in_result() -> None:
    profile = ethan()
    result = recommend_training(profile, assessment(GREEN), profile["training_history"])
    assert result["weekly_exposure"]["Back"] < result["weekly_targets"]["Back"]
    assert result["target_source"] == "User-entered weekly set targets"


def test_low_effort_yesterday_is_available_not_absolute_ban() -> None:
    profile = ethan()
    profile["local_soreness"] = {}
    rows = [{"date": date.today().isoformat(), "completed": True, "primary_focus": "Pull", "muscle_groups": ["Back"], "session_rpe": 5, "working_sets": 2}]
    result = recommend_training(profile, assessment(GREEN), rows)
    assert "Back + Biceps" not in result["avoid"]


def test_validate_llm_allows_paraphrase_but_rejects_explicit_contradiction() -> None:
    assert ai_engine.validate_llm_response("Your recovery is somewhat below your normal level.", AMBER)[0]
    assert not ai_engine.validate_llm_response("Your overall readiness is Green.", AMBER)[0]
    assert ai_engine.validate_llm_response("Sleep is green, but overall readiness is Amber.", AMBER)[0]
    assert not ai_engine.validate_llm_response("RIR is resting heart rate index.", GREEN, question="What is RIR?")[0]


def test_general_training_questions_use_general_answer_not_fixed_today_script() -> None:
    profile = ethan(); rec = recommend_training(profile, assessment(GREEN), profile["training_history"])
    answer, _, _ = get_instant_response("What is RIR?", profile, assessment(GREEN), rec)
    assert "repetitions in reserve" in answer.casefold()
    assert rec["primary"]["name"] not in answer


def test_scope_question_gets_coach_scope_response() -> None:
    answer, _, _ = get_instant_response("What is the capital of Japan?", ethan(), assessment(GREEN), None)
    assert "designed for training" in answer


def test_four_week_baseline_is_not_last_seven_day_only() -> None:
    profile = ethan(); profile["weekly_set_targets"] = {}
    today = date.today()
    rows = []
    for week, sets in enumerate((2, 4, 6, 8), start=1):
        rows.append({"date": (today - timedelta(days=week * 7 + 1)).isoformat(), "completed": True, "primary_focus": "Chest", "muscle_groups": ["Chest"], "working_sets": sets})
    result = recommend_training(profile, assessment(GREEN), rows)
    assert result["target_source"].startswith("Median of four prior logged weeks")
    assert result["weekly_targets"]["Chest"] == 5.0


def test_daily_local_soreness_does_not_persist_into_next_day() -> None:
    profile = ethan(); profile["local_soreness"] = {"Quads": 5}
    today_result = recommend_training(profile, assessment(GREEN, today_data={"soreness": 1, "local_soreness": {"Quads": 5}}), [])
    next_result = recommend_training(profile, assessment(GREEN, assessment_date=(date.today() + timedelta(days=1)).isoformat(), today_data={"soreness": 1, "local_soreness": {}}), [], as_of=date.today() + timedelta(days=1))
    assert "Legs" in today_result["avoid"] or "Quads" in today_result["avoid"]
    assert "High reported soreness" not in next_result["avoid"]


def test_unknown_exercise_uses_logged_focus_fallback() -> None:
    rows = [{"date": date.today().isoformat(), "completed": True, "primary_focus": "Chest", "muscle_groups": ["Chest"], "exercises": [{"name": "Machine Chest Press", "working_sets": 10}], "working_sets": 10}]
    assert weekly_training_exposure(rows)["Chest"] == 10.0


def test_alternative_and_primary_templates_are_consistent() -> None:
    result = recommend_training(ethan(), assessment(GREEN), ethan()["training_history"])
    assert result["template"]["title"] == result["primary"]["name"]
    assert result["decision_trace"][-1]["value"] == result["primary"]["name"]
    assert all(item["name"] != result["primary"]["name"] for item in result["alternatives"])


def test_endurance_autonomic_amber_prefers_easy_aerobic() -> None:
    profile = build_demo_profiles()[1]
    result = recommend_training(profile, assessment(AMBER, domains={"autonomic": AMBER, "sleep": GREEN, "subjective": GREEN, "training_load": GREEN}), profile["training_history"])
    assert result["primary"]["training_type"] == "Aerobic"
    assert result["primary"]["name"] in {"Easy Aerobic + Mobility", "Easy Aerobic Session"}


def local_runtime() -> tuple[Runtime, dict]:
    runtime = Runtime(profiles=build_demo_profiles(), active_profile_id="demo-ethan", chat_histories={}, local_preferences={"privacy_notice_acknowledged": False})
    profile = create_profile(runtime, {"name": "Local Tester", "training_goal": "Muscle Gain", "training_split_preference": "Body Part Split"})
    return runtime, profile


def test_new_local_profile_can_be_serialized_without_demo_data() -> None:
    runtime, profile = local_runtime()
    document = serialize_runtime_state(runtime.profiles, profile["user_id"], runtime.local_preferences, runtime.chat_histories)
    assert [row["name"] for row in document["profiles"]] == ["Local Tester"]
    assert not any(row["profile_id"].startswith("demo-") for row in document["profiles"])


def test_local_profile_never_receives_unsaved_demo_today_inputs() -> None:
    _, profile = local_runtime()
    profile["history"] = [{"date": (date.today() - timedelta(days=1)).isoformat(), "rmssd_ms": 50}]
    assert real_today_inputs(profile) is None
    profile["history"].append({"date": date.today().isoformat(), "rmssd_ms": 51})
    assert real_today_inputs(profile)["rmssd_ms"] == 51


def test_checkin_and_readiness_can_be_persisted_and_upserted() -> None:
    runtime, profile = local_runtime()
    row = {"date": date.today().isoformat(), "rmssd_ms": 50, "resting_hr_bpm": 55, "sleep_hours": 8, "sleep_quality": 4, "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4, "local_soreness": {"Quads": 4}}
    assert not upsert_daily_metric(profile, row)
    assert upsert_daily_metric(profile, row | {"sleep_hours": 7.5})
    readiness = assess_readiness(row, readiness_history(), 8)
    save_assessment(profile, readiness)
    document = serialize_runtime_state(runtime.profiles, profile["user_id"])
    assert len(document["daily_checkins"]) == 1
    assert document["daily_checkins"][0]["sleep_hours"] == 7.5
    assert len(document["readiness_history"]) == 1


def test_training_sessions_have_unique_ids_and_actual_sets_drive_exposure() -> None:
    runtime, profile = local_runtime()
    first = log_training_session(profile, {"date": date.today().isoformat(), "primary_focus": "Chest", "muscle_groups": ["Chest"], "duration_min": 40, "session_rpe": 7, "prescribed_sets": 6, "actual_sets": 3, "exercises": [{"name": "Bench Press", "working_sets": 3}]})
    second = log_training_session(profile, {"date": date.today().isoformat(), "primary_focus": "Chest", "muscle_groups": ["Chest"], "duration_min": 20, "session_rpe": 5, "prescribed_sets": 4, "actual_sets": 2, "exercises": [{"name": "Bench Press", "working_sets": 2}]})
    assert first["session_id"] != second["session_id"]
    assert weekly_training_exposure(profile["training_history"])["Chest"] == 5.0
    assert all(row["prescribed_sets"] != row["actual_sets"] for row in profile["training_history"])
    assert next(row for row in profile["history"] if row["date"] == date.today().isoformat())["session_load"] == 380.0
    upsert_daily_metric(profile, {"date": date.today().isoformat(), "sleep_hours": 8, "session_load": None, "session_duration_min": None, "session_rpe": None})
    assert next(row for row in profile["history"] if row["date"] == date.today().isoformat())["session_load"] == 380.0


def test_local_soreness_remains_date_specific_after_round_trip() -> None:
    runtime, profile = local_runtime()
    upsert_daily_metric(profile, {"date": "2026-09-13", "local_soreness": {"Quads": 4}})
    upsert_daily_metric(profile, {"date": "2026-09-14", "local_soreness": {}})
    restored = profiles_from_local_state(serialize_runtime_state(runtime.profiles, profile["user_id"]))[0]
    assert restored["history"][0]["local_soreness"] == {"Quads": 4}
    assert restored["history"][1]["local_soreness"] == {}
    assert "local_soreness" not in {key for key in restored if key != "history"}


def test_data_restoration_recreates_runtime_and_keeps_demos_isolated() -> None:
    runtime, profile = local_runtime()
    upsert_daily_metric(profile, {"date": date.today().isoformat(), "sleep_hours": 8})
    document = serialize_runtime_state(runtime.profiles, profile["user_id"], {"privacy_notice_acknowledged": True})
    restored = Runtime()
    hydrate_runtime_state(restored, document)
    assert [row["name"] for row in restored.profiles[:3]] == ["Ethan", "Alex", "Jessica"]
    assert restored.active_profile_id == profile["user_id"]
    assert len([row for row in restored.profiles if not row.get("is_demo")]) == 1
    assert len(next(row for row in restored.profiles if row["user_id"] == profile["user_id"])["history"]) == 1


def test_schema_validation_and_corrupt_backup_rejection() -> None:
    assert validate_local_state(empty_local_state())["schema_version"] == 1
    bad = empty_local_state(); bad["schema_version"] = 999
    try:
        validate_local_state(bad)
        assert False, "newer schemas must be rejected"
    except LocalDataError:
        pass
    for raw in (b"not json", json.dumps({"schema_version": 1, "profiles": "bad"}).encode()):
        try:
            import_backup(raw)
            assert False, "corrupt backup must be rejected"
        except LocalDataError:
            pass


def test_export_clear_import_restore_round_trip() -> None:
    runtime, profile = local_runtime()
    upsert_daily_metric(profile, {"date": date.today().isoformat(), "local_soreness": {"Back": 2}})
    raw = export_backup(serialize_runtime_state(runtime.profiles, profile["user_id"]))
    clear_local_runtime(runtime)
    assert all(row.get("is_demo") for row in runtime.profiles)
    hydrate_runtime_state(runtime, import_backup(raw))
    assert any(row["name"] == "Local Tester" for row in runtime.profiles)


def test_recommendation_history_is_versioned_and_serializable() -> None:
    runtime, profile = local_runtime()
    rec = recommend_training(profile, assessment(GREEN), [])
    save_recommendation(profile, rec)
    document = serialize_runtime_state(runtime.profiles, profile["user_id"])
    assert document["training_recommendations"][0]["primary"]["name"] == rec["primary"]["name"]


def test_alternative_log_defaults_use_selected_prescription_only() -> None:
    rec = recommend_training(ethan(), assessment(GREEN), ethan()["training_history"])
    alternative = next(item for item in rec["alternatives"] if item["name"] != rec["primary"]["name"])
    defaults = prescription_log_defaults(alternative)
    assert defaults["primary_focus"] == alternative["name"]
    assert [row["name"] for row in defaults["exercises"]] == [row["name"] for row in alternative["exercises"]]
    assert [row["name"] for row in defaults["exercises"]] != [row["name"] for row in rec["primary"]["exercises"]]


def test_workout_prescription_is_single_source_for_view_and_log() -> None:
    rec = recommend_training(ethan(), assessment(GREEN), ethan()["training_history"])
    for prescription in [rec["primary"], *rec["alternatives"]]:
        template = workout_template(prescription)
        defaults = prescription_log_defaults(prescription)
        assert defaults["prescribed_sets"] == sum(row["sets"] for row in prescription["exercises"])
        for row in prescription["exercises"]:
            assert any(f"{row['sets']} sets" in line for line in template["items"])


def test_decision_trace_uses_explicit_recent_training_summary() -> None:
    profile = ethan()
    rows = [{"date": (date.today() - timedelta(days=1)).isoformat(), "completed": True, "primary_focus": "Legs", "muscle_groups": ["Quads", "Hamstrings / Glutes"], "session_rpe": 8, "actual_sets": 5}]
    rec = recommend_training(profile, assessment(GREEN), rows)
    trace = {row["step"]: row["value"] for row in rec["decision_trace"]}
    assert trace["RECENT TRAINING"] == "Legs yesterday · high effort"
    assert "Below-target exposure" not in trace["RECENT TRAINING"]


def test_ai_weekly_sets_answer_uses_recorded_exposure() -> None:
    import re

    profile = ethan(); rec = recommend_training(profile, assessment(GREEN), profile["training_history"])
    answer, _, _ = get_instant_response("How many back sets have I done this week?", profile, assessment(GREEN), rec)
    assert f"{rec['weekly_exposure']['Back']:g}" in answer
    # PHASE 3.5: the answer must name the real unit and must never fall back to days.
    assert "weighted working sets" in answer.casefold()
    assert "back" in answer.casefold()
    assert re.search(r"\d+(\.\d+)?\s*(day|days|session|sessions)\b", answer.casefold()) is None
    assert "not days" in answer.casefold()


def test_ai_success_keeps_the_model_wording_and_the_provider_label(monkeypatch) -> None:
    profile = ethan(); rec = recommend_training(profile, assessment(GREEN), profile["training_history"])
    monkeypatch.setattr(ai_engine, "_generate", lambda *args: "RIR means repetitions in reserve.")
    answer, provider, notice = get_ai_response("What is RIR?", profile, assessment(GREEN), rec, (), _CONFIGURED)
    assert provider == ai_engine.AI_PROVIDER_LABEL and notice is None
    assert answer.startswith("RIR means")
    assert "Approved recommendation" not in answer


def test_science_metadata_is_shared_with_executable_engines() -> None:
    from science_content import READINESS_RULE_METADATA as documented_readiness
    from science_content import RECOMMENDATION_RULE_METADATA as documented_recommendation
    assert documented_readiness is READINESS_RULE_METADATA
    assert documented_readiness["thresholds"]["hrv_z"][GREEN] == ">= -0.5"
    assert documented_readiness["training_load"]["window_basis"] == "calendar days"
    assert documented_readiness["training_load"]["full_coverage_days"] == 28
    assert documented_recommendation is RECOMMENDATION_RULE_METADATA
    assert documented_recommendation["fractional_sets"] == RECOMMENDATION_RULE_METADATA["fractional_sets"]


def test_science_page_and_privacy_content_are_present() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    for text in ("Science & Logic", "Personal baseline", "four readiness domains", "Overall readiness logic", "How today's training is selected", "Evidence vs product heuristics", "What this system does not claim", "References"):
        assert text.casefold() in source.casefold()
    assert "Persistent personal history" not in source or "remote database" in source
    assert Path("browser_storage/frontend/storage.js").exists()
    assert "indexedDB.open" in Path("browser_storage/frontend/storage.js").read_text(encoding="utf-8")


def test_no_remote_personal_database_dependencies_or_tokens() -> None:
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in Path(".").glob("*.py") if not path.name.startswith("test_")) + Path("requirements.txt").read_text()
    for forbidden in ("supabase", "firebase", "postgres", "github_token"):
        assert forbidden not in text.casefold()


def calendar_load_history(anchor: date, covered_days: int = 28) -> list[dict]:
    start = anchor - timedelta(days=covered_days)
    return [{"date": (start + timedelta(days=offset)).isoformat(), "session_load": None} for offset in range(covered_days)]


def test_training_load_uses_calendar_days_not_sessions() -> None:
    anchor = date(2026, 9, 14)
    rows = calendar_load_history(anchor)
    for row in rows:
        day = date.fromisoformat(row["date"])
        if day.weekday() in {0, 2, 4, 6}:
            row["session_load"] = 280.0
    result = training_load_domain(rows, anchor)
    assert result["calendar_days_covered"] == 28
    assert result["recent_window_start"] == "2026-09-07"
    assert result["recent_window_end"] == "2026-09-13"
    assert result["reference_window_start"] == "2026-08-17"
    assert result["reference_window_end"] == "2026-09-06"
    assert len(result["daily_loads"]) == 28
    assert sum(value > 0 for value in list(result["daily_loads"].values())[-7:]) == 4


def test_training_load_aggregates_multiple_sessions_same_day() -> None:
    anchor = date(2026, 9, 14)
    rows = calendar_load_history(anchor)
    target = "2026-09-10"
    rows.extend([{"date": target, "completed": True, "session_load": 150}, {"date": target, "completed": True, "session_load": 420}])
    result = training_load_domain(rows, anchor)
    assert result["daily_loads"][target] == 570.0


def test_training_load_rest_days_are_zero_inside_calendar_window() -> None:
    anchor = date(2026, 9, 14)
    rows = calendar_load_history(anchor)
    training_dates = {"2026-09-07", "2026-09-09", "2026-09-11", "2026-09-13"}
    for row in rows:
        if row["date"] in training_dates:
            row["session_load"] = 350
    result = training_load_domain(rows, anchor)
    recent = {key: value for key, value in result["daily_loads"].items() if "2026-09-07" <= key <= "2026-09-13"}
    assert len(recent) == 7
    assert sum(value == 0 for value in recent.values()) == 3
    assert result["recent_7d_mean"] == 200.0


def test_training_load_sparse_history_does_not_invent_rest_days() -> None:
    anchor = date(2026, 9, 14)
    five_days = training_load_domain(calendar_load_history(anchor, 5), anchor)
    twenty_days = training_load_domain(calendar_load_history(anchor, 20), anchor)
    assert five_days["status"] == INSUFFICIENT and five_days["data_sufficiency"] == "INSUFFICIENT"
    assert twenty_days["status"] == INSUFFICIENT and twenty_days["data_sufficiency"] == "LIMITED"
    assert five_days["daily_loads"] is None and twenty_days["daily_loads"] is None
    assert "unknown" in twenty_days["detail"]


def test_training_load_near_zero_reference_guard() -> None:
    anchor = date(2026, 9, 14)
    rows = calendar_load_history(anchor)
    rows[-1]["session_load"] = 500
    result = training_load_domain(rows, anchor)
    assert result["status"] == INSUFFICIENT
    assert result["reference_21d_mean"] == 0.0
    assert result["z_score"] is None and result["load_change"] is None
    assert "near zero" in result["detail"]


def test_unknown_exercise_fallback_through_real_log_path() -> None:
    _, profile = local_runtime()
    logged = log_training_session(profile, {"date": date.today().isoformat(), "primary_focus": "Chest", "muscle_groups": ["Chest"], "duration_min": 40, "session_rpe": 6, "actual_sets": 10, "exercises": [{"name": "Machine Chest Press", "working_sets": 10}]})
    assert logged["muscle_set_contributions"] == {"Chest": 10.0}
    assert weekly_training_exposure(profile["training_history"])["Chest"] == 10.0


def test_mixed_known_and_unknown_exercises_both_contribute() -> None:
    _, profile = local_runtime()
    logged = log_training_session(profile, {"date": date.today().isoformat(), "primary_focus": "Chest", "muscle_groups": ["Chest"], "duration_min": 45, "session_rpe": 7, "actual_sets": 6, "exercises": [{"name": "Bench Press", "working_sets": 3}, {"name": "Unknown Cable Fly", "working_sets": 3}]})
    assert logged["muscle_set_contributions"]["Chest"] == 6.0
    assert weekly_training_exposure(profile["training_history"])["Chest"] == 6.0


def test_multiple_unknown_exercises_do_not_double_count_session_total() -> None:
    _, profile = local_runtime()
    logged = log_training_session(profile, {"date": date.today().isoformat(), "primary_focus": "Chest", "muscle_groups": ["Chest"], "duration_min": 50, "session_rpe": 7, "actual_sets": 10, "exercises": [{"name": "Unknown Press", "working_sets": 5}, {"name": "Unknown Fly", "working_sets": 5}]})
    assert logged["muscle_set_contributions"]["Chest"] == 10.0
    assert weekly_training_exposure(profile["training_history"])["Chest"] == 10.0


def test_chat_submission_queues_local_persistence() -> None:
    import inspect
    import app
    source = inspect.getsource(app._submit_question)
    assert "_queue_chat_save(profile)" in source
    queue_source = inspect.getsource(app._queue_chat_save)
    assert "_queue_browser_save()" in queue_source
    assert "except Exception" in queue_source


def test_chat_storage_failure_does_not_raise(monkeypatch) -> None:
    import app
    fake_streamlit = type("FakeStreamlit", (), {"session_state": Runtime()})()
    monkeypatch.setattr(app, "st", fake_streamlit)
    monkeypatch.setattr(app, "_queue_browser_save", lambda: (_ for _ in ()).throw(RuntimeError("storage offline")))
    app._queue_chat_save({"user_id": "user-local", "is_demo": False})
    assert "current answer is still available" in fake_streamlit.session_state.storage_error


def test_chat_history_survives_serialization_and_hydration() -> None:
    runtime, profile = local_runtime()
    runtime.chat_histories[profile["user_id"]] = [{"role": "user", "content": "What is RIR?"}, {"role": "assistant", "content": "RIR means repetitions in reserve."}]
    document = serialize_runtime_state(runtime.profiles, profile["user_id"], runtime.local_preferences, runtime.chat_histories)
    restored = Runtime()
    hydrate_runtime_state(restored, document)
    assert restored.chat_histories[profile["user_id"]] == runtime.chat_histories[profile["user_id"]]
    runtime.chat_histories[profile["user_id"]] = [{"role": "user", "content": str(index)} for index in range(35)]
    capped = serialize_runtime_state(runtime.profiles, profile["user_id"], runtime.local_preferences, runtime.chat_histories)
    assert len(capped["chat_history"]) == 30
    oversized = dict(capped)
    oversized["chat_history"] = [{"profile_id": profile["user_id"], "role": "user", "content": str(index)} for index in range(35)]
    assert [row["content"] for row in validate_local_state(oversized)["chat_history"]] == [str(index) for index in range(5, 35)]
    invalid = dict(capped)
    invalid["chat_history"] = [{"profile_id": "unknown-profile", "role": "user", "content": "orphan"}]
    try:
        validate_local_state(invalid)
        assert False, "orphan chat messages must be rejected"
    except LocalDataError:
        pass


def test_full_body_has_no_unmapped_core_target() -> None:
    full_body = next(workout for workout in WORKOUTS if workout["name"] == "Full Body Strength")
    assert "Core" not in full_body["muscle_groups"]
    assert "Core" not in fractional_set_contributions(full_body["exercises"])


def test_all_workout_candidate_groups_are_achievable_by_prescription() -> None:
    for workout in WORKOUTS:
        achievable = set(fractional_set_contributions(workout["exercises"]))
        assert set(workout["muscle_groups"]).issubset(achievable), workout["name"]


def test_coach_copy_matches_context_aware_architecture() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    assert "Context-aware Training Coach" in source
    assert "answer general training and recovery questions" in source
    # the composer still tells the user what the Coach covers
    assert "Ask about your training or recovery" in source
    assert "only explains the approved result" not in source
    assert "Approved workout:" not in source


def test_general_chest_frequency_and_contextual_leg_alternative_answers() -> None:
    profile = ethan()
    rec = recommend_training(profile, assessment(GREEN), profile["training_history"])
    general, _, _ = get_instant_response("Is training chest twice per week okay?", profile, assessment(GREEN), rec)
    rir, _, _ = get_instant_response("What is RIR?", profile, assessment(GREEN), rec)
    alternative, _, _ = get_instant_response("Can I train legs instead?", profile, assessment(GREEN), rec)
    assert "twice per week" in general and rec["primary"]["name"] not in general
    assert "repetitions in reserve" in rir.casefold() and rec["primary"]["name"] not in rir
    assert rec["primary"]["name"] in alternative and "primary recommendation" in alternative.casefold()


def test_mobile_shell_spacing_contract_is_centralised() -> None:
    """The shell band is one contract: tokens -> viewport reservation -> navigation."""
    import styles

    css = styles.SHELL_CSS
    for token in styles.SHELL_TOKENS:
        assert f"{token}:" in css, token
    # the scrolling viewport reserves the navigation band instead of the page
    # adding document-end padding
    assert 'height: calc(100dvh - var(--ara-shell-bottom)) !important' in css
    assert '[data-testid="stMain"]' in css and '[data-testid="stAppScrollToBottomContainer"]' in css
    # safe area is read from the browser, with a non-zero floor for browsers
    # that report no inset at all
    assert "env(safe-area-inset-bottom, 0px)" in css
    assert "max(var(--ara-safe-bottom), var(--ara-shell-floor))" in css
    # the legacy hard-coded document-end offset must not come back
    assert "6.6rem" not in css and "5.2rem" not in css
    assert styles.SHELL_TOKENS["--ara-nav-h"] == "calc(var(--ara-nav-content-h) + var(--ara-shell-inset))"


def test_mobile_shell_hides_chrome_with_installed_streamlit_testids() -> None:
    """Streamlit 1.56 renamed the collapse control; the hide list must track it."""
    import styles

    css = styles.SHELL_CSS
    for selector in styles.MOBILE_HIDDEN_CHROME_SELECTORS:
        assert selector in css, selector
    assert '[data-testid="stExpandSidebarButton"]' in styles.MOBILE_HIDDEN_CHROME_SELECTORS
    assert '[data-testid="stSidebarCollapsedControl"]' in styles.MOBILE_HIDDEN_CHROME_SELECTORS
    assert '[data-testid="stAppDeployButton"]' in styles.MOBILE_HIDDEN_CHROME_SELECTORS
    assert '[data-testid="stMainMenu"]' in styles.MOBILE_HIDDEN_CHROME_SELECTORS
    # the compact navigation is hidden outside the mobile shell, so desktop
    # keeps the sidebar-only layout
    hidden_by_default = css.split("@media")[0]
    assert ".st-key-mobile_bottom_nav, .st-key-mobile_utility_nav { display: none; }" in hidden_by_default
    # internal plumbing (stylesheet + storage bridge + shell bridge) is hidden
    assert ".st-key-ara_stylesheet" in css
    assert ".st-key-browser_storage_bridge" in css
    assert ".st-key-mobile_shell_viewport" in css


def test_mobile_bottom_navigation_renders_primary_destinations_and_navigates() -> None:
    from streamlit.testing.v1 import AppTest

    dashboard = AppTest.from_file("app.py").run(timeout=30)
    assert not dashboard.exception
    keys = {button.key for button in dashboard.button}
    for page in ("Today", "Check-in", "Train", "Trends", "Coach"):
        assert f"mobile_nav_{page}" in keys
    assert dashboard.button(key="mobile_nav_Today").proto.type == "primary"
    dashboard.button(key="mobile_nav_Train").click().run()
    assert dashboard.session_state["current_page"] == "Train"
    assert dashboard.button(key="mobile_nav_Train").proto.type == "primary"
    assert dashboard.button(key="mobile_nav_Today").proto.type == "secondary"


def test_mobile_shell_viewport_bridge_cannot_trigger_reruns() -> None:
    """The bridge only adjusts browser-level shell concerns and returns nothing."""
    import mobile_shell

    script = Path("mobile_shell/frontend/shell.js").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in script
    assert "visualViewport" in script and "ara-keyboard-open" in script
    assert "streamlit:setFrameHeight" in script
    assert "streamlit:setComponentValue" not in script
    assert mobile_shell.SHELL_ELEMENT_KEY == "mobile_shell_viewport"
    component_dir = Path(mobile_shell.__file__).parent / "frontend"
    assert (component_dir / "index.html").exists() and (component_dir / "shell.js").exists()
    source = Path("app.py").read_text(encoding="utf-8")
    assert "mobile_shell_bridge()" in source


def test_browser_storage_bridge_has_no_visible_surface() -> None:
    """IndexedDB sync must stay functional but visually invisible."""
    storage_js = Path("browser_storage/frontend/storage.js").read_text(encoding="utf-8")
    index_html = Path("browser_storage/frontend/index.html").read_text(encoding="utf-8")
    assert '"streamlit:setFrameHeight", {height: 0}' in storage_js
    assert "height: 24" not in storage_js
    assert "indexedDB.open" in storage_js  # semantics untouched
    assert 'id="status"' in index_html
    assert "clip:rect(0 0 0 0)" in index_html
    assert "font:12px sans-serif" not in index_html


def test_design_tokens_are_emitted_and_used() -> None:
    """Tokens are the single source of truth; component CSS must not re-invent values."""
    import re

    import styles

    assert styles.DESIGN_TOKENS
    for token in styles.DESIGN_TOKENS:
        assert f"{token}:" in styles.DESIGN_TOKEN_CSS, token
    assert "--ara-status-green" in styles.COLOR_TOKENS
    assert "--ara-radius-lg" in styles.RADIUS_TOKENS
    assert "--ara-space-md" in styles.SPACE_TOKENS
    assert "--ara-font-body" in styles.TYPE_TOKENS
    # component CSS consumes tokens instead of hard-coded colours
    assert re.search(r"#[0-9a-fA-F]{3,6}", styles.APP_CSS) is None
    assert "var(--ara-surface)" in styles.APP_CSS and "var(--ara-font-body)" in styles.APP_CSS
    # the mobile shell layer keeps its own contract and still uses tokens
    assert "var(--ara-nav-bg)" in styles.SHELL_CSS and "var(--ara-radius-sm)" in styles.SHELL_CSS


def test_status_colour_has_exactly_one_source() -> None:
    """One status -> one colour token, shared by Python and CSS."""
    import re

    import styles
    import ui_components

    for status, token in styles.STATUS_TONE_TOKENS.items():
        assert token in styles.COLOR_TOKENS, status
        assert ui_components.status_tone(status) == f"var({token})"
    for status in (GREEN, AMBER, RED, STOP, INSUFFICIENT):
        tone, _, _ = ui_components.status_meta(status)
        assert tone.startswith("var(--ara-status-")
    # no colour literal may exist in the component layer
    source = Path("ui_components.py").read_text(encoding="utf-8")
    assert re.search(r"#[0-9a-fA-F]{3,6}", source) is None


def test_status_badge_pairs_colour_with_text_label() -> None:
    import ui_components

    for status in (GREEN, AMBER, RED, STOP, INSUFFICIENT):
        badge = ui_components.status_badge(status)
        assert f"var({ui_components.status_tone(status)})".replace("var(var(", "var(") in badge or "var(--ara-status-" in badge
        assert status in badge  # the label is always present, never colour alone
        assert "ara-badge--status" in badge
    explicit = ui_components.status_badge(GREEN, label="Ready")
    assert ">Ready<" in explicit


def test_metric_tile_recommendation_and_trace_row_render_labelled_content() -> None:
    import ui_components

    tile = ui_components.metric_tile("HRV", "-0.6", unit="SD", context="vs 28-day baseline", status=AMBER)
    assert "HRV" in tile and "-0.6" in tile and "SD" in tile and "vs 28-day baseline" in tile
    assert "AMBER" in tile and "ara-metric__label" in tile
    card = ui_components.recommendation_card("Back + Biceps", ("Normal", "50-65 min"), "Why", variant="avoid")
    assert "ara-recommendation--avoid" in card and "Back + Biceps" in card and "ara-chip" in card
    row = ui_components.decision_trace_row("Weekly exposure", "Back 9 / 12 sets", note="Last 7 days", status=GREEN)
    assert "ara-trace-row__label" in row and "Back 9 / 12 sets" in row and "Last 7 days" in row
    # untrusted text is escaped
    assert "<script>" not in ui_components.insight_card("<script>alert(1)</script>", "body")


def test_cta_hierarchy_renders_primary_and_secondary() -> None:
    from streamlit.testing.v1 import AppTest

    script = (
        "import ui_components\n"
        "ui_components.primary_cta('View workout', 'cta_primary')\n"
        "ui_components.secondary_cta('View details', 'cta_secondary')\n"
    )
    app = AppTest.from_string(script).run(timeout=30)
    assert not app.exception
    assert app.button(key="cta_primary").proto.type == "primary"
    assert app.button(key="cta_secondary").proto.type == "secondary"


def test_design_system_has_no_new_runtime_dependency() -> None:
    """The design system stays on Streamlit + custom CSS.

    ``streamlit-shadcn-ui`` 1.4.0 requires Streamlit >= 1.60 while this project is
    verified on 1.56, so it was evaluated and rejected in PHASE 3. This guard keeps
    a half-finished migration from slipping in unnoticed.
    """
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "shadcn" not in requirements.casefold()
    for module in ("app.py", "styles.py", "ui_components.py"):
        source = Path(module).read_text(encoding="utf-8")
        assert "streamlit_shadcn_ui" not in source, module
        assert "shadcn" not in source.casefold(), module
    preview = Path("scripts/design_system_preview.py")
    assert preview.exists()
    app_source = Path("app.py").read_text(encoding="utf-8")
    assert "design_system_preview" not in app_source


# --------------------------------------------------------------------------- #
# PHASE 3.5 — AI Coach factual grounding (bug AI-01)
# --------------------------------------------------------------------------- #


def _coach_fixture(index: int = 0):
    """A demo profile with its real assessment and recommendation."""
    profile = build_demo_profiles()[index]
    draft = json.loads(json.dumps(profile["history"][-1], default=str))
    draft["date"] = date.today().isoformat()
    real_assessment = assess_readiness(draft, profile["history"], profile["personal_sleep_need"], profile["assessments"])
    rec = recommend_training(profile, real_assessment, profile["training_history"])
    return profile, real_assessment, rec


def _ask(question: str, profile, real_assessment, rec, history=()):
    answer, provider, _ = get_ai_response(question, profile, real_assessment, rec, history, {})
    return answer, provider


def test_ai_router_classifies_personal_fact_versus_other_intents() -> None:
    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)

    assert ai_facts.route_question("How much have I trained back this week?", (), facts).kind == "PERSONAL_FACT"
    assert ai_facts.route_question("What's my readiness today?", (), facts).metric == "readiness"
    assert ai_facts.route_question("What's my training load today?", (), facts).metric == "training_load"
    assert ai_facts.route_question("How many days have I trained back this week?", (), facts).metric == "weekly_training_days"
    assert ai_facts.route_question("Why am I training back today?", (), facts).kind == "EXPLANATION"
    assert ai_facts.route_question("What is RIR?", (), facts).kind == "GENERAL"
    assert ai_facts.route_question("What is the capital of Japan?", (), facts).kind == "SCOPE"
    assert ai_facts.route_question("How is my left knee feeling overall?", (), facts).kind == "UNRESOLVED_PERSONAL"

    history = [{"role": "user", "content": "How much have I trained back this week?"},
               {"role": "assistant", "content": "Ethan has trained back for 12 days this week."}]
    correction = ai_facts.route_question("but one week has only 7 days", history, facts)
    assert correction.kind == "CORRECTION"
    assert correction.previous_question == "How much have I trained back this week?"
    # a challenge without a previous assistant turn is not a correction
    assert ai_facts.route_question("but one week has only 7 days", (), facts).kind != "CORRECTION"


def test_ai_case_1_and_2_weekly_exposure_uses_real_unit() -> None:
    import re

    profile, real_assessment, rec = _coach_fixture()
    back = rec["weekly_exposure"]["Back"]
    for question in ("How much have I trained back this week?", "How many sets have I done for back this week?"):
        answer, provider = _ask(question, profile, real_assessment, rec)
        assert provider == "Verified data"
        assert f"{back:g}" in answer
        assert "weighted working set" in answer.casefold()
        assert re.search(r"\d+(\.\d+)?\s*(day|days)\b", answer.casefold()) is None
        assert re.search(r"\bdays?\b", answer.casefold()) is None or "not days" in answer.casefold()


def test_ai_case_3_training_days_is_not_exposure() -> None:
    import re

    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    answer, provider = _ask("How many days have I trained back this week?", profile, real_assessment, rec)
    assert provider == "Verified data"
    exposure = rec["weekly_exposure"]["Back"]
    # the set count must never be reported as days
    assert re.search(rf"{exposure:g}\s*days?", answer.casefold()) is None
    days = facts["weekly_training_days"]["value"]
    if days:
        assert str(days) in answer and "training day" in answer.casefold()
    else:
        assert "no completed sessions" in answer.casefold()


def test_ai_case_4_and_5_training_load_versus_session_duration() -> None:
    profile, real_assessment, rec = _coach_fixture()
    load_answer, _ = _ask("What's my training load today?", profile, real_assessment, rec)
    load = real_assessment["measurements"]["training_load"]["recent_7d_mean"]
    assert f"{load:g}" in load_answer
    # V1.3 consumer terminology: the same metric is shown as Training Load Points.
    assert "pts" in load_answer.casefold()
    assert "duration x session rpe" in load_answer.casefold()
    assert rec["duration"] not in load_answer

    duration_answer, _ = _ask("How long should I train today?", profile, real_assessment, rec)
    assert rec["duration"] in duration_answer
    assert "not training load" in duration_answer.casefold()


def test_ai_case_6_and_7_readiness_and_recommendation() -> None:
    profile, real_assessment, rec = _coach_fixture()
    readiness_answer, _ = _ask("What's my readiness today?", profile, real_assessment, rec)
    assert real_assessment["overall_readiness"] in readiness_answer
    assert str(real_assessment["readiness_index"]) in readiness_answer
    assert real_assessment["assessment_confidence"] in readiness_answer

    workout_answer, _ = _ask("What am I training today?", profile, real_assessment, rec)
    assert rec["primary"]["name"] in workout_answer
    assert rec["intensity"] in workout_answer


def test_ai_case_8_local_soreness_is_reported_or_declared_unavailable() -> None:
    profile, real_assessment, rec = _coach_fixture()
    answer, _ = _ask("How sore is my back today?", profile, real_assessment, rec)
    recorded = (real_assessment.get("today_data") or {}).get("local_soreness") or {}
    if "Back" in recorded:
        assert f"{recorded['Back']}/5" in answer
    else:
        assert "no" in answer.casefold() and "recorded" in answer.casefold()
        assert rec["primary"]["name"] not in answer  # must not fall back to the workout script


def test_ai_case_9_correction_re_reads_source_of_truth() -> None:
    profile, real_assessment, rec = _coach_fixture()
    history = [{"role": "user", "content": "How much have I trained back this week?"},
               {"role": "assistant", "content": "Ethan has trained back for 12 days this week."}]
    answer, provider = _ask("but one week has only 7 days", profile, real_assessment, rec, history)
    assert provider == "Verified data"
    assert "you're right" in answer.casefold()
    assert f"{rec['weekly_exposure']['Back']:g}" in answer
    assert "weighted working set" in answer.casefold()
    assert rec["duration"] not in answer          # never jump to 35-55 min
    assert "training load" not in answer.casefold()  # never switch topic


def test_ai_case_10_challenge_reconfirms_without_new_numbers() -> None:
    import re

    profile, real_assessment, rec = _coach_fixture()
    history = [{"role": "user", "content": "How much have I trained back this week?"},
               {"role": "assistant", "content": f"You have logged {rec['weekly_exposure']['Back']:g} weighted working sets for back this week."}]
    answer, provider = _ask("Are you sure?", profile, real_assessment, rec, history)
    assert provider == "Verified data"
    assert "re-checked" in answer.casefold()
    numbers = set(re.findall(r"\d+(?:\.\d+)?", answer))
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    assert numbers <= ai_facts.facts_numbers(facts)


def test_ai_correction_of_a_correct_answer_does_not_claim_an_error() -> None:
    """A negation ("not minutes") is not unit contamination."""
    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    load_route = ai_facts.Route("PERSONAL_FACT", metric="training_load")
    correct = ai_facts.grounded_answer(load_route, facts)
    answer = ai_facts.correction_answer(load_route, facts, correct)
    assert "re-checked" in answer.casefold()
    assert "you're right" not in answer.casefold()
    assert "wrong unit" not in answer.casefold()

    exposure_route = ai_facts.Route("PERSONAL_FACT", metric="weekly_exposure", groups=("Back",))
    wrong = "Ethan has trained back for 12 days this week."
    corrected = ai_facts.correction_answer(exposure_route, facts, wrong)
    assert "you're right" in corrected.casefold()
    assert "weighted working set" in corrected.casefold()


def test_ai_case_11_missing_data_is_declared_not_invented() -> None:
    profile = create_profile(Runtime(profiles=[], active_profile_id="", chat_notice=None), {"name": "Empty Local"})
    empty_assessment = assessment(GREEN, today_data={"soreness": None, "local_soreness": {}})
    rec = recommend_training(profile, empty_assessment, profile["training_history"])
    assert not profile["training_history"]
    answer, provider = _ask("How much have I trained back this week?", profile, empty_assessment, rec)
    assert provider == "Verified data"
    assert "don't have enough recorded" in answer.casefold()
    assert "12" not in answer


def test_ai_case_12_unit_contamination_is_blocked_by_the_guard() -> None:
    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    exposure_route = ai_facts.Route("PERSONAL_FACT", metric="weekly_exposure")
    days_route = ai_facts.Route("PERSONAL_FACT", metric="weekly_training_days")
    duration_route = ai_facts.Route("PERSONAL_FACT", metric="session_duration")
    load_route = ai_facts.Route("PERSONAL_FACT", metric="training_load")
    explanation_route = ai_facts.Route("EXPLANATION")
    # sets expressed as days, days expressed as sets
    assert not ai_facts.guard_llm_response("You trained back for 9.5 days this week.", facts, "", exposure_route)[0]
    assert not ai_facts.guard_llm_response("You completed 4 sets of training this week.", facts, "", days_route)[0]
    # duration expressed as training load and the reverse
    assert not ai_facts.guard_llm_response("Your training load is 35-55 minutes.", facts, "", duration_route)[0]
    assert not ai_facts.guard_llm_response("Your training load today is 45 minutes.", facts, "", load_route)[0]
    # invented number in an explanation
    assert not ai_facts.guard_llm_response("Your readiness index is 99 today.", facts, "", explanation_route)[0]
    # period shift
    assert not ai_facts.guard_llm_response("Your average load over the last month is fine.", facts, "", explanation_route)[0]
    # a supported paraphrase is still accepted
    assert ai_facts.guard_llm_response("Your back exposure this week is a weighted working-set estimate.", facts, "", exposure_route)[0]


def test_ai_case_13_multiple_muscles_read_their_own_source_values() -> None:
    profile, real_assessment, rec = _coach_fixture()
    for muscle in ("Back", "Chest", "Quads"):
        answer, _ = _ask(f"How many sets have I done for {muscle.lower()} this week?", profile, real_assessment, rec)
        assert f"{rec['weekly_exposure'][muscle]:g}" in answer


def test_ai_case_14_profile_isolation_has_no_stale_context() -> None:
    first_profile, first_assessment, first_rec = _coach_fixture(0)
    second_profile, second_assessment, second_rec = _coach_fixture(1)
    assert first_rec["weekly_exposure"]["Back"] != second_rec["weekly_exposure"]["Back"] or first_profile["name"] != second_profile["name"]
    first_answer, _ = _ask("How much have I trained back this week?", first_profile, first_assessment, first_rec)
    second_answer, _ = _ask("How much have I trained back this week?", second_profile, second_assessment, second_rec)
    assert f"{first_rec['weekly_exposure']['Back']:g}" in first_answer
    assert f"{second_rec['weekly_exposure']['Back']:g}" in second_answer
    assert first_answer != second_answer


def test_ai_case_15_factual_query_survives_provider_failure_and_never_calls_it(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()

    def explode(*args, **kwargs):
        raise AssertionError("The AI provider must not be called for a personal factual query")

    monkeypatch.setattr(ai_engine, "_generate", explode)
    for question in ("How much have I trained back this week?", "What's my training load today?",
                     "What's my readiness today?", "What am I training today?"):
        answer, provider, _ = get_ai_response(question, profile, real_assessment, rec, [], {})
        assert provider == "Verified data"
        assert answer

    # the same queries also work when the deployment disables the explanation layer
    answer, provider, _ = get_ai_response("How much have I trained back this week?", profile, real_assessment, rec, [], {"DISABLE_EMBEDDED_LLM": "true"})
    assert provider == "Verified data"
    assert f"{rec['weekly_exposure']['Back']:g}" in answer


def test_ai_fact_prompt_never_exposes_bare_numbers() -> None:
    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    prompt = ai_facts.facts_for_prompt(facts)
    # every exposure number carries its unit
    for group, entry in facts["weekly_exposure"]["groups"].items():
        assert f"{group}: {entry['value']:g} weighted working sets" in prompt
    # the ambiguous legacy line is gone and the units are called out explicitly
    assert "Current seven-day exposure:" not in prompt
    assert "NOT days and NOT sessions" in prompt
    assert "training days" in prompt and "completed sessions" in prompt
    # V1.3 consumer terminology: the user-facing unit is "pts" (Training Load
    # Points). The metric itself is unchanged (duration × session RPE).
    assert "pts" in prompt and "Training load is NOT session duration" in prompt


def test_ai_explanation_grounding_guard_rejects_invented_rationale() -> None:
    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    invented = "Ethan is training back because he wants to build up his core muscles, which helps with balance."
    accepted, reason = ai_facts.guard_explanation_grounding(invented, facts)
    assert not accepted and "rationale" in reason
    grounded = f"{rec['primary']['name']} stays primary because readiness is {real_assessment['overall_readiness']} and weekly exposure drives the split."
    assert ai_facts.guard_explanation_grounding(grounded, facts)[0]


# --------------------------------------------------------------------------- #
# PHASE 4 — Today experience
# --------------------------------------------------------------------------- #


_TODAY_SCRIPT = """
import json
import streamlit as st
import ai_facts
from app import current_assessment, current_recommendation, get_draft, render_today
from profile_store import get_profile, initialise_store

initialise_store(st.session_state)
profile = get_profile(st.session_state)
assessment = current_assessment(profile)
recommendation = current_recommendation(profile, assessment)
render_today(profile, assessment)
facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
payload = {
    "primary": recommendation["primary"]["name"],
    "training_type": recommendation["primary"]["training_type"],
    "session_demand": recommendation["intensity"],
    "duration": recommendation["duration"],
    "decision_trace": {entry["step"]: entry["value"] for entry in recommendation["decision_trace"]},
    "index": facts["readiness"]["index"],
    "status": facts["readiness"]["status"],
    "confidence": facts["readiness"]["confidence"],
    "hrv": facts["signals"]["hrv"]["value"],
    "rhr": facts["signals"]["resting_hr"]["value"],
    "sleep": facts["signals"]["sleep"]["value"],
    "load": facts["training_load"]["value"],
    "profile": profile["name"],
}
st.markdown("EXPECTEDPAYLOAD" + json.dumps(payload))
"""


def _today_run():
    """The real Today page plus the engine values it was rendered from."""
    from streamlit.testing.v1 import AppTest

    dashboard = AppTest.from_string(_TODAY_SCRIPT).run(timeout=60)
    assert not dashboard.exception
    blocks = [str(element.value) for element in dashboard.markdown]
    payload_line = next(block for block in blocks if block.startswith("EXPECTEDPAYLOAD"))
    payload = json.loads(payload_line.replace("EXPECTEDPAYLOAD", "", 1))
    html = "\n".join(block for block in blocks if not block.startswith("EXPECTEDPAYLOAD"))
    headings = [str(element.value) for element in dashboard.subheader]
    return html, headings, payload


def test_today_renders_primary_recommendation_and_session_demand() -> None:
    html, headings, payload = _today_run()
    assert "TODAY'S TRAINING" in html
    assert "WHAT TO TRAIN" in html and "HOW HARD" in html
    assert payload["primary"] in html
    assert payload["duration"] in html
    assert payload["session_demand"] in html
    assert ai_engine._diag["request_attempted"] is False   # opening Today must not call the AI provider


def test_today_shows_engine_session_demand_not_a_guess() -> None:
    html, _, payload = _today_run()
    assert payload["session_demand"] in html
    assert payload["training_type"] in html
    assert "HOW HARD" in html


def test_today_factual_values_match_structured_facts() -> None:
    html, _, payload = _today_run()
    assert str(payload["index"]) in html
    assert payload["status"] in html
    assert payload["confidence"] in html
    assert f"{payload['hrv']:.0f}" in html
    assert f"{payload['rhr']:.0f}" in html
    assert f"{payload['sleep']:.1f}" in html
    assert f"{payload['load']:.0f}" in html
    # no technical jargon on the main screen
    for jargon in ("z-score", "LnRMSSD", "rolling SD", "21-day"):
        assert jargon.casefold() not in html.casefold()


def test_today_why_today_uses_deterministic_decision_trace() -> None:
    html, headings, payload = _today_run()
    assert "WHY TODAY?" in headings and "KEY SIGNALS" in headings
    assert "TRAINING DIRECTION" in html and "SESSION DEMAND" in html
    trace = payload["decision_trace"]
    for step in ("WEEKLY EXPOSURE", "RECENT TRAINING", "PROGRAMME", "READINESS", "SESSION DEMAND"):
        assert trace[step] in html, step


def test_today_limited_and_missing_data_do_not_break_the_layout() -> None:
    from streamlit.testing.v1 import AppTest

    script = (
        "import streamlit as st\n"
        "from ui_components import mobile_readiness_hero, metric_tile, why_today\n"
        "assessment = {'overall_readiness': 'INSUFFICIENT DATA', 'readiness_index': None,"
        " 'assessment_confidence': 'INSUFFICIENT', 'domains': {'autonomic': 'INSUFFICIENT DATA'},"
        " 'measurements': {'hrv': {'status': 'INSUFFICIENT DATA'}, 'rhr': {'status': 'INSUFFICIENT DATA'},"
        " 'sleep_duration': {'status': 'INSUFFICIENT DATA'}, 'training_load': {'status': 'INSUFFICIENT DATA'}},"
        " 'today_data': {}, 'key_contributors': [], 'safety_flags': [], 'why_this_status': []}\n"
        "mobile_readiness_hero({'name': 'Fresh'}, assessment)\n"
        "st.markdown(metric_tile('HRV', '—', context='Not recorded today'))\n"
        "why_today([], [])\n"
    )
    app = AppTest.from_string(script).run(timeout=30)
    assert not app.exception
    html = "\n".join(str(element.value) for element in app.markdown)
    assert "INSUFFICIENT" in html and "INDEX" in html   # badge + empty index, no fake value
    assert "Not recorded today" in html


def test_today_empty_local_profile_shows_onboarding_without_demo_values() -> None:
    from streamlit.testing.v1 import AppTest

    script = (
        "import streamlit as st\n"
        "from app import render_today\n"
        "from profile_store import create_profile\n"
        "state = type('S', (), {'profiles': [], 'active_profile_id': '', 'chat_notice': None})()\n"
        "profile = create_profile(state, {'name': 'Fresh Local'})\n"
        "render_today(profile, {'overall_readiness': 'INSUFFICIENT DATA', 'readiness_index': None})\n"
    )
    app = AppTest.from_string(script).run(timeout=30)
    assert not app.exception
    html = "\n".join(str(element.value) for element in app.markdown)
    assert "Start with today" in html
    assert any(button.label == "Complete your first check-in" for button in app.button)
    assert "Back + Biceps" not in html     # no demo recommendation for a local profile
    assert "90" not in html


# --------------------------------------------------------------------------- #
# FINAL FAST-TRACK SPRINT — Train / Coach / Profile / Check-in / Trends
# --------------------------------------------------------------------------- #


def _page_render(page: str):
    """Render one product page and return its markdown, subheaders and elements."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file("app.py")
    app.session_state["current_page"] = page
    app.run(timeout=60)
    assert not app.exception, app.exception
    html = "\n".join(str(element.value) for element in app.markdown)
    headings = [str(element.value) for element in app.subheader]
    captions = [str(element.value) for element in app.caption]
    return app, html, headings, captions


_PAGE_SCRIPT = """
import json
import streamlit as st
from app import current_assessment, current_recommendation, render_{page}
from profile_store import get_profile, initialise_store

initialise_store(st.session_state)
profile = get_profile(st.session_state)
assessment = current_assessment(profile)
recommendation = current_recommendation(profile, assessment)
render_{page}(profile, assessment)
st.markdown("EXPECTEDPAYLOAD" + json.dumps({
    "primary": recommendation["primary"]["name"],
    "intensity": recommendation["intensity"],
    "duration": recommendation["duration"],
    "training_type": recommendation["primary"]["training_type"],
    "alternatives": [item["name"] for item in recommendation["alternatives"]],
    "avoid": list(recommendation["avoid"]),
    "decision_trace": {entry["step"]: entry["value"] for entry in recommendation["decision_trace"]},
    "profile": profile["name"],
    "is_demo": bool(profile.get("is_demo")),
}))
"""


def _page_run(page: str):
    """Render a page and return its blocks plus the engine values it used."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(_PAGE_SCRIPT.replace("{page}", page)).run(timeout=60)
    assert not app.exception, app.exception
    blocks = [str(element.value) for element in app.markdown]
    payload_line = next(block for block in blocks if block.startswith("EXPECTEDPAYLOAD"))
    payload = json.loads(payload_line.replace("EXPECTEDPAYLOAD", "", 1))
    html = "\n".join(block for block in blocks if not block.startswith("EXPECTEDPAYLOAD"))
    headings = [str(element.value) for element in app.subheader]
    captions = [str(element.value) for element in app.caption]
    return app, html, headings, captions, payload


def test_train_shows_primary_hierarchy_alternatives_and_avoid() -> None:
    _, html, headings, captions, payload = _page_run("train")
    assert "PRIMARY RECOMMENDATION" in html
    assert "WHAT TO TRAIN" in html and "HOW HARD" in html
    assert payload["primary"] in html                     # engine output, not a copy
    assert payload["intensity"] in html and payload["duration"] in html
    assert "ALTERNATIVES" in headings
    assert any("never overwrites the primary" in caption for caption in captions)
    assert "HOW TO EXECUTE IT" in headings and "DECISION TRACE" in headings and "LOG WORKOUT" in headings


def test_train_decision_trace_rows_cover_every_step() -> None:
    _, html, _, _, payload = _page_run("train")
    for label in ("Goal", "Programme / split", "7-day exposure", "Recent training",
                  "Local soreness", "Readiness", "Session demand", "Recommendation"):
        assert label in html, label
    assert "Weighted working sets" in html          # unit clarity on the exposure row
    for value in payload["decision_trace"].values():
        assert str(value) in html


def test_train_rir_guidance_comes_from_the_prescription() -> None:
    from app import rir_guidance

    profile, real_assessment, rec = _coach_fixture()
    guidance = rir_guidance(rec["primary"])
    assert guidance and guidance.upper().endswith("RIR")
    assert rir_guidance({"exercises": []}) is None


def test_coach_quick_questions_and_touch_targets() -> None:
    from app import COACH_QUICK_QUESTIONS
    import styles

    assert len(COACH_QUICK_QUESTIONS) == 4
    css = styles.SHELL_CSS
    assert '[data-testid="stChatInput"] button { min-width: 44px !important; min-height: 44px !important; }' in css
    assert '.st-key-coach_quick_questions [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]' in css
    general = css.index('[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex: 1 1 100%; min-width: 100%; }')
    assert css.index('.st-key-coach_quick_questions [data-testid="stHorizontalBlock"]') > general
    assert "resetCoachScrollWhenEmpty" in Path("mobile_shell/frontend/shell.js").read_text(encoding="utf-8")


def test_more_page_switches_profiles_and_labels_identity() -> None:
    app, html, _, _ = _page_render("More")
    assert "ACTIVE PROFILE" in html
    assert "DEMO PROFILE" in html or "LOCAL PROFILE" in html
    assert any(select.label == "Change profile" for select in app.selectbox)
    options = next(select.options for select in app.selectbox if select.label == "Change profile")
    assert len(options) >= 2                     # demo profiles plus any local profile
    assert all(option.startswith(("DEMO · ", "LOCAL · ")) for option in options)


def test_profile_switching_sets_active_profile_and_keeps_data_separated() -> None:
    from app import profile_label, switch_active_profile
    from profile_store import get_profile, initialise_store

    state = Runtime(profiles=[], active_profile_id="", chat_notice=None, local_preferences={})
    del state["profiles"]
    initialise_store(state)
    first = get_profile(state)
    profiles = [item for item in state["profiles"]]
    labels = [("DEMO · " if item.get("is_demo") else "LOCAL · ") + item["name"] for item in profiles]
    assert profile_label(first) == labels[profiles.index(first)]
    target = next(item for item in profiles if item["user_id"] != first["user_id"])
    assert switch_active_profile(state, profiles, labels, profile_label(target), first["user_id"])
    assert state["active_profile_id"] == target["user_id"]
    assert get_profile(state)["user_id"] == target["user_id"]
    assert not switch_active_profile(state, profiles, labels, profile_label(target), target["user_id"])  # no rerun loop
    # isolation: the demo profile never gains the other profile's history object
    assert first["training_history"] is not target["training_history"]


def test_checkin_scales_state_direction_explicitly() -> None:
    from app import SUBJECTIVE_SCALE_GUIDANCE, scale_guidance

    assert set(SUBJECTIVE_SCALE_GUIDANCE) == {"Sleep quality", "Fatigue", "Soreness", "Stress", "Motivation"}
    assert "higher is better" in scale_guidance("Motivation").casefold()
    assert "more fatigue" in scale_guidance("Fatigue").casefold()
    assert "more soreness" in scale_guidance("Soreness").casefold()
    assert "more stress" in scale_guidance("Stress").casefold()
    assert "higher is better" in scale_guidance("Sleep quality").casefold()
    _, _, headings, captions = _page_render("Check-in")
    for section in ("Recovery", "How do you feel?", "Local soreness (optional)", "Safety check"):
        assert section in headings
    assert any("higher is better only for motivation" in caption.casefold() for caption in captions)
    assert any("more fatigue" in caption.casefold() for caption in captions)


def test_trend_dates_and_chart_helpers() -> None:
    import pandas as pd

    from app import build_trend_chart, format_trend_date

    assert format_trend_date("2026-09-16") == "16 Sep"
    assert "00:00:00" not in format_trend_date("2026-09-16 00:00:00")
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-12"]),
        "value": [3.9, 4.0, 4.1], "mean": [3.95, 3.98, 4.0],
    })
    chart = build_trend_chart(frame, "value", "mean", "LnRMSSD", 4.02, "#171717")
    spec = json.dumps(chart.to_dict())
    assert '"zero": false' in spec.lower()          # axis is not forced to zero
    assert '"mark": {"type": "rule"' in spec        # personal baseline reference
    assert build_trend_chart(frame[frame["value"] > 99], "value", "mean", "LnRMSSD", None, "#171717") is None


def test_cross_page_terminology_is_consistent() -> None:
    sources = "\n".join(Path(name).read_text(encoding="utf-8") for name in ("app.py", "ui_components.py", "ai_facts.py"))
    for banned in ("calendar week", "Last 7 days", "Last 28 days", "Weekly total"):
        assert banned not in sources, banned
    # the product states what it is not, explicitly
    assert "not a recovery percentage" in sources
    assert "weighted working sets" in sources
    assert "7-day exposure" in sources
    assert "Session duration is not training load" in sources or "not training load" in sources
    trends_source = Path("app.py").read_text(encoding="utf-8")
    assert "check-ins" in trends_source and "duration × session RPE" in trends_source


# --------------------------------------------------------------------------- #
# PHASE 5 — DeepSeek explanation layer
# --------------------------------------------------------------------------- #


class FakeResponse:
    """Minimal stand-in for a ``requests`` response object."""

    def __init__(self, payload=None, status_code: int = 200, unreadable: bool = False) -> None:
        self._payload = payload
        self.status_code = status_code
        self._unreadable = unreadable

    def json(self):
        if self._unreadable:
            raise ValueError("response body is not JSON")
        return self._payload


def _install_transport(monkeypatch, payload=None, status_code: int = 200, unreadable: bool = False, raises=None):
    """Fake the HTTPS transport and return the recorded calls. No network is used."""
    calls: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        if raises is not None:
            raise raises
        return FakeResponse(payload, status_code, unreadable)

    monkeypatch.setattr(ai_engine.requests, "post", fake_post)
    return calls


def _provider_payload(text: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 812, "completion_tokens": 96}}


def _reset_diagnostics() -> None:
    ai_engine._diag.update({"request_attempted": False, "response_received": False, "generation_completed": False,
                            "validation_accepted": False, "provider_used": ai_engine.PROVIDER_FALLBACK,
                            "stage": None, "last_validation_reason": "Not requested",
                            "prompt_tokens": None, "completion_tokens": None})


@pytest.fixture(autouse=True)
def _clean_ai_diagnostics():
    """AI diagnostics are process-wide; keep one test's provider call out of the next."""
    _reset_diagnostics()
    ai_engine._last_model_error = None
    yield
    _reset_diagnostics()
    ai_engine._last_model_error = None


def _grounded_draft(rec, real_assessment) -> str:
    """A draft that satisfies every guard, so a test can isolate the provider layer."""
    return (f"{rec['primary']['name']} stays primary because readiness is {real_assessment['overall_readiness']} "
            "and weekly exposure plus recent training drive the split.")


def test_deepseek_request_is_openai_compatible_and_disables_thinking(monkeypatch) -> None:
    _reset_diagnostics()
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload(_grounded_draft(rec, real_assessment)))

    answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)

    assert provider == ai_engine.AI_PROVIDER_LABEL and notice is None
    assert answer.startswith(rec["primary"]["name"])
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://api.deepseek.com/chat/completions"
    assert call["timeout"] == ai_engine.REQUEST_TIMEOUT_SECONDS
    assert call["headers"]["Authorization"] == f"Bearer {_FAKE_KEY_VALUE}"
    payload = call["payload"]
    assert payload["model"] == "deepseek-flash"
    assert payload["stream"] is False
    assert payload["max_tokens"] == ai_engine.MAX_OUTPUT_TOKENS
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][-1]["role"] == "user"
    diagnostics = ai_engine.ai_diagnostics(_CONFIGURED)
    assert diagnostics["Active provider"] == "DeepSeek"
    assert diagnostics["Prompt tokens"] == 812 and diagnostics["Completion tokens"] == 96


def test_deepseek_context_is_minimised_and_profile_scoped(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture(0)
    calls = _install_transport(monkeypatch, _provider_payload(_grounded_draft(rec, real_assessment)))

    get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)

    payload = calls[0]["payload"]
    serialised = json.dumps(payload, ensure_ascii=False)
    assert [message["role"] for message in payload["messages"]] == ["system", "user"]   # no history, no full database
    assert _FAKE_KEY_VALUE not in serialised                                            # the key never travels in the body
    for other_profile in ("Alex", "Jessica"):
        assert other_profile not in serialised
    for forbidden in ("user_id", "schema_version", "daily_checkins", "storage_revision", "backup"):
        assert forbidden not in serialised
    assert "weighted working sets" in serialised
    assert "NOT days and NOT sessions" in serialised
    assert "Training load is NOT session duration" in serialised


def test_deepseek_history_is_bounded_and_truncated(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload(_grounded_draft(rec, real_assessment)))

    history = []
    for index in range(14):
        history.append({"role": "user", "content": f"user turn {index}"})
        history.append({"role": "assistant", "content": "x" * 900})
    get_ai_response("Why this workout?", profile, real_assessment, rec, history, _CONFIGURED)

    messages = calls[0]["payload"]["messages"]
    assert len(messages) == 2 + ai_engine.MAX_HISTORY_MESSAGES
    assert messages[0]["role"] == "system" and messages[-1]["role"] == "user"
    assert all(len(message["content"]) <= ai_engine.MAX_HISTORY_MESSAGE_CHARS for message in messages[1:-1])
    serialised = json.dumps(messages)
    assert "user turn 13" in serialised      # the newest turns survive
    assert "user turn 0" not in serialised   # the oldest turns are dropped


def test_deepseek_missing_key_degrades_without_calling_the_provider(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload("unused"))

    answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], {})

    assert calls == []
    assert provider == "Instant explanation"
    assert notice == ai_engine.AI_UNAVAILABLE_NOTICE
    assert rec["primary"]["name"] in answer


def test_deepseek_disabled_deployment_never_calls_the_provider(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload("unused"))

    for setting in ("DISABLE_AI_COACH", "DISABLE_EMBEDDED_LLM"):
        answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [],
                                                   {**_CONFIGURED, setting: "true"})
        assert provider == "Instant explanation" and "disabled" in str(notice)
        assert rec["primary"]["name"] in answer
    assert calls == []
    assert "disabled" in ai_engine.ai_engine_status({**_CONFIGURED, "DISABLE_AI_COACH": "true"})


def test_deepseek_timeout_degrades_to_the_deterministic_answer(monkeypatch) -> None:
    _reset_diagnostics()
    profile, real_assessment, rec = _coach_fixture()
    _install_transport(monkeypatch, raises=ai_engine.requests.exceptions.Timeout("provider too slow"))

    answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)

    assert provider == "Instant explanation" and notice == ai_engine.AI_UNAVAILABLE_NOTICE
    assert rec["primary"]["name"] in answer
    assert ai_engine._diag["request_attempted"] is True
    assert ai_engine._diag["generation_completed"] is False
    assert "Traceback" not in answer and _FAKE_KEY_VALUE not in notice
    assert "sk-" not in str(ai_engine._last_model_error)


def test_deepseek_network_and_provider_errors_never_crash_the_coach(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    scenarios = [
        ("network error", {"raises": ai_engine.requests.exceptions.ConnectionError("dns failure")}),
        ("authentication error", {"status_code": 401}),
        ("rate limit", {"status_code": 429}),
        ("provider error", {"status_code": 500}),
        ("invalid response", {"payload": None}),
        ("empty choices", {"payload": {"choices": []}}),
        ("empty content", {"payload": {"choices": [{"message": {"content": "   "}}]}}),
        ("unreadable body", {"payload": None, "unreadable": True}),
    ]
    for label, kwargs in scenarios:
        _reset_diagnostics()
        _install_transport(monkeypatch, **kwargs)
        answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)
        assert provider == "Instant explanation", label
        assert notice == ai_engine.AI_UNAVAILABLE_NOTICE, label
        assert rec["primary"]["name"] in answer, label


def test_personal_factual_questions_never_call_the_ai_provider(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload("unused"))

    for question in ("How much have I trained back this week?", "How many days have I trained back?",
                     "What's my training load today?", "How long should I train today?",
                     "What's my readiness today?", "How sore is my back?"):
        answer, provider, _ = get_ai_response(question, profile, real_assessment, rec, [], _CONFIGURED)
        assert provider == "Verified data", question
        assert answer, question
    assert calls == []


def test_personal_factual_corrections_never_call_the_ai_provider(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload("unused"))
    back = rec["weekly_exposure"]["Back"]
    history = [{"role": "user", "content": "How much have I trained back this week?"},
               {"role": "assistant", "content": f"You have logged {back:g} weighted working sets of back work."}]

    answer, provider, _ = get_ai_response("But one week has only 7 days, so is that right?", profile, real_assessment, rec, history, _CONFIGURED)
    assert provider == "Verified data"
    assert re.search(r"12 days", answer.casefold()) is None

    answer, provider, _ = get_ai_response("Are you sure?", profile, real_assessment, rec, history, _CONFIGURED)
    assert provider == "Verified data" and answer
    assert calls == []


def test_ai_hallucinations_are_rejected_and_replaced_by_the_verified_answer(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    primary = rec["primary"]["name"]
    actual_status = str(real_assessment["overall_readiness"]).upper()
    wrong_status = "Red" if actual_status != "RED" else "Green"
    bad_drafts = {
        "unit drift to days": f"You have trained back for 47 days this week, so {primary} stays primary.",
        "unsupported readiness": f"Your overall readiness is {wrong_status}, so {primary} stays primary.",
        "replaced recommendation": "Your primary recommendation is Legs today.",
        "invented HRV": f"Your HRV is 118 ms today, which is why {primary} stays primary.",
        "invented duration": f"Train for 145 minutes, because {primary} stays primary.",
        "invented rationale": "You are training back to build your core muscles, which improves balance.",
    }
    for label, draft in bad_drafts.items():
        _reset_diagnostics()
        _install_transport(monkeypatch, _provider_payload(draft))
        answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)
        assert provider == "Instant explanation", label
        assert draft not in answer, label
        assert primary in answer, label
        assert ai_engine._diag["validation_accepted"] is False, label


def test_explanation_layer_cannot_invent_missing_personal_data(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload(
        "Your HRV is 118 ms today, so you have excellent recovery capacity and should train legs."))

    answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)

    assert len(calls) == 1                                  # the draft really was requested
    assert provider == "Instant explanation"                # and then rejected by the guards
    assert notice == ai_engine.AI_REJECTED_NOTICE
    assert "118" not in answer and "excellent recovery capacity" not in answer
    verified, verified_provider, _ = get_ai_response("What's my readiness today?", profile, real_assessment, rec, [], {})
    assert verified_provider == "Verified data" and verified


def test_deepseek_provider_labels_and_fallbacks_are_provider_neutral(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    calls = _install_transport(monkeypatch, _provider_payload(_grounded_draft(rec, real_assessment)))
    _, provider, _ = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)
    assert provider == ai_engine.AI_PROVIDER_LABEL
    source = Path("app.py").read_text(encoding="utf-8")
    assert "AI_PROVIDER_LABEL" in source
    for retired in ("Qwen", "qwen", "Built-in AI", "embedded model", "transformers", "torch"):
        assert retired not in source, retired
    for module in ("ai_engine.py", "requirements.txt", "README.md", ".streamlit/secrets.toml.example", "run_demo.command"):
        text = Path(module).read_text(encoding="utf-8")
        assert "Qwen" not in text and "qwen" not in text, module
        assert "torch" not in text and "transformers" not in text, module


def test_about_page_discloses_the_real_provider_and_privacy_boundary() -> None:
    _, html, headings, captions = _page_render("About")
    disclosure = "\n".join([html, *captions])
    assert "AI architecture" in headings and "Data & Privacy" in headings
    assert "DeepSeek" in disclosure
    assert "summarised context" in disclosure.casefold()
    for stale in ("Qwen", "no commercial AI API", "Commercial AI API: none",
                  "All data stays on device", "all AI runs locally",
                  "Your data stays local", "YOUR DATA STAYS LOCAL"):
        assert stale not in disclosure, stale


# --------------------------------------------------------------------------- #
# PHASE 5.1 — readiness index scale (guard false positive)
# --------------------------------------------------------------------------- #


_NOT_GENERAL = ai_facts.Route("EXPLANATION")


def _facts_with_index(index) -> dict:
    """Real structured facts with a pinned readiness index, so the scale cases are exact."""
    profile, real_assessment, rec = _coach_fixture()
    facts = ai_facts.build_personal_facts(profile, real_assessment, rec)
    facts["readiness"]["index"] = index
    return facts


def test_readiness_index_scale_metadata_lives_in_the_facts() -> None:
    facts = _facts_with_index(71)
    assert facts["readiness"]["index_scale"] == ai_facts.READINESS_INDEX_SCALE
    assert ai_facts.READINESS_INDEX_SCALE == {"min": 0, "max": 100}
    prompt = ai_facts.facts_for_prompt(facts)
    assert "readiness index 71 on a 0–100 scale" in prompt
    # the documented scale maximum is never a free-standing allowed personal number
    assert "100" not in ai_facts.facts_numbers(facts)


def test_readiness_scale_is_accepted_next_to_the_verified_index() -> None:
    facts = _facts_with_index(71)
    for draft in ("Your readiness is AMBER (71/100).",
                  "Your readiness index is 71 on a 0–100 scale.",
                  "Your readiness index is 71 / 100 today.",
                  "Your readiness index is 71 out of 100."):
        accepted, reason = ai_facts.guard_llm_response(draft, facts, "", _NOT_GENERAL)
        assert accepted, f"{draft} -> {reason}"


def test_readiness_scale_does_not_license_unrelated_personal_numbers() -> None:
    facts = _facts_with_index(71)
    for draft in ("You should train for 100 minutes.",
                  "You completed 100 weighted working sets.",
                  "Your resting heart rate is 100 bpm.",
                  "Your HRV is 100 ms today."):
        accepted, reason = ai_facts.guard_llm_response(draft, facts, "", _NOT_GENERAL)
        assert not accepted, draft
        assert "100" in reason, f"{draft} -> {reason}"


def test_readiness_scale_does_not_license_a_new_index_value() -> None:
    facts = _facts_with_index(71)
    accepted, reason = ai_facts.guard_llm_response("Your readiness is 83/100.", facts, "", _NOT_GENERAL)
    assert not accepted and "83" in reason, reason
    # an invented index is still rejected when the real index is absent
    empty = _facts_with_index(None)
    accepted, reason = ai_facts.guard_llm_response("Your readiness index is 71 on a 0–100 scale.", empty, "", _NOT_GENERAL)
    assert not accepted and "71" in reason, reason


def test_missing_readiness_index_never_renders_a_misleading_ratio() -> None:
    facts = _facts_with_index(None)
    prompt = ai_facts.facts_for_prompt(facts)
    assert "readiness index not available" in prompt
    assert "100" not in prompt
    for metric in ("readiness", "readiness_index"):
        answer = ai_facts.grounded_answer(ai_facts.Route("PERSONAL_FACT", metric=metric), facts)
        assert "not available" in answer, metric
        assert "/ 100" not in answer and "/100" not in answer, metric


def test_grounded_readiness_ratio_draft_is_accepted_end_to_end(monkeypatch) -> None:
    profile, real_assessment, rec = _coach_fixture()
    index = real_assessment.get("readiness_index")
    assert index is not None      # the demo check-in classifies at least three domains
    draft = (f"{rec['primary']['name']} stays primary because your readiness is "
             f"{real_assessment['overall_readiness']} ({index:g}/100) and weekly exposure drives the split.")
    _reset_diagnostics()
    _install_transport(monkeypatch, _provider_payload(draft))

    answer, provider, notice = get_ai_response("Why this workout?", profile, real_assessment, rec, [], _CONFIGURED)

    assert provider == ai_engine.AI_PROVIDER_LABEL, notice
    assert notice is None
    assert answer == draft


# --------------------------------------------------------------------------- #
# PHASE 6 — Science & references audit
# --------------------------------------------------------------------------- #


def test_reference_bibliography_is_complete_and_consistent() -> None:
    from science_content import REFERENCES

    assert len(REFERENCES) == 13
    seen: set[str] = set()
    for reference in REFERENCES:
        for field in ("authors", "title", "journal", "citation", "pmid", "doi"):
            assert reference.get(field), f"PMID {reference.get('pmid')} is missing {field}"
        assert " et al" not in reference["authors"], reference["pmid"]     # one author style only
        assert not reference["title"].endswith(".")                         # no duplicated terminal punctuation
        assert reference["doi"].startswith("10."), reference["pmid"]
        assert str(reference["year"]).isdigit(), reference["pmid"]
        assert reference["pmid"] not in seen
        seen.add(reference["pmid"])


def test_reference_corrections_from_the_audit_are_present() -> None:
    from science_content import REFERENCES

    by_pmid = {reference["pmid"]: reference for reference in REFERENCES}
    # Schoenfeld 2019 carried a truncated title; the official full title is now used
    assert by_pmid["30558493"]["title"] == (
        "How many times per week should a muscle be trained to maximize muscle hypertrophy? "
        "A systematic review and meta-analysis of studies examining the effects of resistance training frequency")
    # Buchheit 2014 was added, with the verified Frontiers volume/article and DOI
    buchheit = by_pmid["24578692"]
    assert buchheit["authors"] == "Buchheit M"
    assert buchheit["journal"] == "Frontiers in Physiology"
    assert buchheit["year"] == 2014 and buchheit["citation"] == "5:73"
    assert buchheit["doi"] == "10.3389/fphys.2014.00073"
    # a longer author list replaced a truncated "et al." entry
    assert by_pmid["32813181"]["authors"].startswith("Greig L, Stephens Hemingway BH")
    assert by_pmid["38970765"]["authors"].startswith("Robinson ZP, Pelland JC")


def test_reference_pmids_and_dois_are_paired() -> None:
    from science_content import REFERENCES

    paired = {reference["pmid"]: reference["doi"] for reference in REFERENCES}
    assert paired == {
        "26423706": "10.1136/bjsports-2015-094758",
        "28463642": "10.1123/IJSPP.2017-0208",
        "29163016": "10.3389/fnins.2017.00612",
        "27433992": "10.1080/02640414.2016.1210197",
        "30558493": "10.1080/02640414.2018.1555906",
        "41343037": "10.1007/s40279-025-02344-w",
        "32813181": "10.1007/s40279-020-01330-8",
        "33776802": "10.3389/fphys.2021.651112",
        "36334240": "10.1007/s40279-022-01784-y",
        "38970765": "10.1007/s40279-024-02069-2",
        "34489178": "10.1016/j.jsams.2021.04.012",
        "34639599": "10.3390/ijerph181910299",
        "24578692": "10.3389/fphys.2014.00073",
    }


def test_science_page_renders_evidence_boundaries_and_verified_references() -> None:
    _, html, headings, captions = _page_render("Science & Logic")
    assert "Evidence boundaries" in headings
    assert "References" in headings
    body = "\n".join([html, *captions])
    assert "not clinically validated" in body
    assert "have not been prospectively validated" in body
    assert "Buchheit M" in body                       # the added reference renders
    assert "pubmed.ncbi.nlm.nih.gov/24578692" in body
    assert "doi.org/10.3389/fphys.2014.00073" in body
    assert "Rome?." not in body and "?." not in body and ".." not in body   # no doubled punctuation
    # the corrected full title is what the page shows, not the truncated version
    assert "of studies examining the effects of resistance training frequency" in body


_NEGATION_MARKERS = ("not ", "never", "no ", "cannot", "without", "does not")


def _assert_never_asserted(phrase: str, text: str, where: str) -> None:
    """The phrase may only appear inside a negating sentence."""
    lowered, needle = text.casefold(), phrase.casefold()
    start = lowered.find(needle)
    while start != -1:
        window = lowered[max(0, start - 48):start]
        assert any(marker in window for marker in _NEGATION_MARKERS), f"{where} asserts '{phrase}'"
        start = lowered.find(needle, start + 1)


def test_science_copy_never_overclaims() -> None:
    from science_content import EVIDENCE_MAP, LIMITATIONS

    source = Path("app.py").read_text(encoding="utf-8")
    science = source.split("def render_science_logic", 1)[1].split("def render_about", 1)[0]
    corpus = {
        "Science & Logic page": science,
        "limitations": " ".join(LIMITATIONS),
        "evidence map": " ".join(f"{item['concept']} {item['evidence']} {item['implementation']}"
                                 for item in EVIDENCE_MAP.values()),
        "README": Path("README.md").read_text(encoding="utf-8"),
    }
    banned = ("validated threshold", "scientifically proven", "proven cutoff", "predicts injury",
              "prevents injury", "injury risk is low", "fatigue probability", "100% recovered",
              "fully recovered", "safe to train", "clinically validated prescription",
              "optimal weekly sets", "HRV determines", "guaranteed recovery", "medical device")
    for phrase in banned:
        for where, text in corpus.items():
            _assert_never_asserted(phrase, text, where)
    # the guard itself must not be vacuous
    with pytest.raises(AssertionError):
        _assert_never_asserted("predicts injury", "This app predicts injury for you.", "self-check")


def test_every_evidence_row_declares_its_support_level() -> None:
    from science_content import EVIDENCE_LABELS, EVIDENCE_MAP, REFERENCES

    pmids = {reference["pmid"] for reference in REFERENCES}
    for key, item in EVIDENCE_MAP.items():
        assert item["label"] in set(EVIDENCE_LABELS.values()), key
        assert item["concept"] and item["evidence"] and item["implementation"], key
        for pmid in item["pmids"]:
            assert pmid in pmids, f"{key} cites PMID {pmid}, which is not in REFERENCES"
    # rule-level rows stay explicitly heuristic
    for key in ("hrv_thresholds", "overall_rule", "sleep_recovery", "fractional_sets", "local_soreness"):
        assert EVIDENCE_MAP[key]["label"] == EVIDENCE_LABELS["heuristic"], key
