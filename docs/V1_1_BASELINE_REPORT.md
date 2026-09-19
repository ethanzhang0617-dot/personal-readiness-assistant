# V1.1 Baseline Report

> **Historical phase record.** This is the Phase 1 snapshot taken before the productization
> changes. Its dependency list still shows `transformers`/`torch`; those were removed from
> `requirements.txt` by the DeepSeek migration (`docs/V1_1_DEEPSEEK_MIGRATION.md`).

**Release under work:** Personal Readiness Assistant V1.1.0 — Productization & Experience Release
**Baseline version:** V1.0.0 (tag `v1.0.0`)
**Report date:** 2026-09-16
**Phase:** PHASE 1 — Repository Audit + V1.0 Baseline (no product code modified)

---

## 1. Repository state

| Item | Value |
|---|---|
| Working copy | `Personal_Readiness_Assistant_Mobile_First_V1.0/` |
| Remote | `https://github.com/ethanzhang0617-dot/personal-readiness-assistant.git` |
| Branch before Phase 1 | `main` (clean, up to date with `origin/main`) |
| Baseline commit | `fe09ab6` — "Release v1.0.0: Mobile-first Personal Readiness Assistant" |
| Previous commit | `f453695` — "Initial commit" |
| Tags | `v1.0.0` (not modified, not moved, not deleted) |
| V1.1 branch created | `v1.1-productization` (branched from `fe09ab6`) |
| `git status` at baseline | `nothing to commit, working tree clean` |

No commit, merge, tag, push or release action was taken in Phase 1. `main` and `v1.0.0` are untouched.

---

## 2. Toolchain actually used for this baseline

| Component | Version |
|---|---|
| OS | macOS (arm64) |
| Python | 3.14.6 |
| Streamlit | 1.56.0 |
| pandas | 2.3.3 |
| numpy | 2.4.4 |
| altair | 6.0.0 |
| pytest | 9.1.1 |
| Playwright (Python) | 1.62.0 (bundled Chromium available) |
| plotly / streamlit-echarts / streamlit-shadcn-ui | not installed |

`requirements.txt` currently declares `streamlit>=1.42,<2`, `pandas>=2.2,<3`, `numpy>=1.26,<3`,
`transformers>=4.45,<6`, `torch>=2.4,<3`.

> Version-drift risk (verified, not theoretical): the app's CSS hides Streamlit chrome through
> `[data-testid="stSidebarCollapsedControl"]`, but Streamlit 1.56 renders that control as
> `[data-testid="stExpandSidebarButton"]`. The hide rule therefore no longer matches and a stray
> sidebar-expand chevron is visible on phones (see `V1_1_UX_AUDIT.md`, section 8). The V1.0 build
> was developed against an older 1.4x/1.5x release, so any V1.1 work must re-verify shell selectors
> against the pinned version.

---

## 3. Compile result

| Command | Result |
|---|---|
| `python3 -m compileall -q .` | PASS — no syntax errors, exit code 0 |

---

## 4. Existing test suite

| Command | Result |
|---|---|
| `python3 -m pytest -v` | **72 / 72 passed** (≈1.7 s) |
| `python3 -m pytest -q` | 72 passed |
| `python3 -m pytest -q -W error::DeprecationWarning` | 72 passed (no deprecation warnings raised as errors) |

`test_app.py` contains 72 test functions and is the project's only test module. There is no separate
QA runner script; `scripts/` contains only `qwen_smoke.py` (a manual Qwen smoke check, not part of pytest).

### 4.1 Coverage by area (from `test_app.py`)

| Area | Representative tests |
|---|---|
| Readiness engine | `test_readiness_still_runs_without_training_recommendation_or_ai`, `test_four_week_baseline_is_not_last_seven_day_only`, `test_low_effort_yesterday_is_available_not_absolute_ban` |
| Training recommendation | `test_upper_lower_rotation_is_respected`, `test_endurance_autonomic_amber_prefers_easy_aerobic`, `test_alternative_and_primary_templates_are_consistent`, `test_all_workout_candidate_groups_are_achievable_by_prescription` |
| Training load / weekly exposure | `test_training_load_uses_calendar_days_not_sessions`, `test_training_load_aggregates_multiple_sessions_same_day`, `test_training_load_rest_days_are_zero_inside_calendar_window`, `test_training_load_sparse_history_does_not_invent_rest_days`, `test_training_load_near_zero_reference_guard`, `test_weekly_exposure_uses_only_completed_last_seven_days`, `test_fractional_set_accounting` |
| Local soreness | `test_daily_local_soreness_does_not_persist_into_next_day`, `test_local_soreness_remains_date_specific_after_round_trip`, `test_unknown_exercise_uses_logged_focus_fallback` |
| Decision trace | `test_decision_trace_uses_explicit_recent_training_summary`, `test_rationale_is_factual_and_has_no_fake_recovery_percentage` |
| AI Coach architecture | `test_ai_instant_uses_recent_training_recommendation`, `test_ai_failure_leaves_deterministic_answer`, `test_ai_does_not_need_api_key_or_load_before_request`, `test_validate_llm_allows_paraphrase_but_rejects_explicit_contradiction`, `test_qwen_success_has_no_forced_recommendation_prefix` |
| Persistence / data model | `test_checkin_and_readiness_can_be_persisted_and_upserted`, `test_export_clear_import_restore_round_trip`, `test_schema_validation_and_corrupt_backup_rejection`, `test_data_restoration_recreates_runtime_and_keeps_demos_isolated`, `test_chat_submission_queues_local_persistence`, `test_chat_history_survives_serialization_and_hydration` |
| Demo / local isolation | `test_local_profile_never_receives_unsaved_demo_today_inputs`, `test_new_local_profile_can_be_serialized_without_demo_data` |
| Product copy / structure | `test_science_page_and_privacy_content_are_present`, `test_english_only_streamlit_cloud_source_has_no_language_selector`, `test_no_remote_personal_database_dependencies_or_tokens` |

### 4.2 Scenario QA

There is no standalone Goal × Split × Readiness scenario script. Scenario coverage lives inside
pytest (`test_scenarios_continue_to_produce_morning_inputs`, plus the endurance/split/readiness
recommendation cases above). No scenario matrix is executed outside pytest today; V1.1 should keep it
that way unless a scenario runner is explicitly added.

---

## 5. Known warnings

| Warning | Severity | Note |
|---|---|---|
| pytest warnings | none | No warnings summary emitted |
| Deprecation warnings in app code | none observed | AppTest runs clean under `-W error::DeprecationWarning` |
| Streamlit runtime advisory | informational | "For better performance, install the Watchdog module" — a local dev-machine message, not an app defect |
| `nice(5) failed: operation not permitted` | environment-only | Sandbox artifact when launching Streamlit from the agent shell; not reproducible in normal terminals |

---

## 6. Known failures and known unverified areas

| Item | Status | Source |
|---|---|---|
| Failing tests at baseline | **NONE** | `pytest` 72/72 |
| IndexedDB bridge end-to-end (save → reload → data present) | **NOT VERIFIED** | Explicitly recorded as not verified in `QA_REPORT.md` |
| App-reload / reopen persistence | **NOT VERIFIED** | Explicitly recorded as not verified in `QA_REPORT.md` |
| Real-device mobile shell behaviour (iOS Safari / Android Chrome) | **NOT VERIFIED** | V1.0 shipped without device QA; Phase 1 browser emulation is documented in `V1_1_UX_AUDIT.md` |
| Automated coverage of the mobile shell (CSS, fixed nav, safe area) | **ABSENT** | `test_app.py` only asserts that the source strings `render_bottom_navigation` / `mobile_bottom_nav` exist (lines ~211–213). No DOM/CSS/layout assertion exists |

No test expectation was modified, skipped, or weakened during this audit.

---

## 7. Repository inventory (V1.0)

| Path | Role |
|---|---|
| `app.py` (~58 KB) | App shell, page renderers (`render_today`, `render_checkin`, `render_train`, `render_trends`, `render_coach`, `render_more`, `render_profile`, `render_science_logic`, `render_about`), sidebar nav, `render_bottom_navigation`, `render_mobile_utility_nav`, `main()` |
| `styles.py` | Single global CSS block (`APP_CSS`), includes the 768 px mobile shell media query and the fixed bottom nav |
| `ui_components.py` | Presentation components only (`readiness_hero`, `mobile_readiness_hero`, `training_summary`, `domain_card`, `callout`, `flow_card`, `detail_row`, `page_intro`) |
| `readiness_engine.py` | Readiness domains, baseline, safety flags |
| `training_recommendation_engine.py` | Split/exposure/soreness-driven session selection, prescriptions, templates |
| `ai_engine.py` | Qwen integration, deterministic fallback, validation |
| `profile_store.py` | Profile store, demo datasets, session logging, weekly targets |
| `local_data.py` | Serialization, hydration, export/import, clear |
| `science_content.py` | Science & Logic content, evidence labels, references |
| `demo_data.py` | Fixed demo datasets (Ethan / Alex / Jessica) |
| `browser_storage/` | IndexedDB bridge (custom Streamlit component: `frontend/index.html`, `frontend/storage.js`) |
| `.streamlit/config.toml` | `headless = true`, usage-stats disabled |
| `scripts/qwen_smoke.py` | Manual Qwen smoke test |
| `test_app.py` | The 72-test suite |
| `QA_REPORT.md` | V1.0 QA gate record |
| `README.md` | V1.0 product/architecture description |
| `docs/` | **did not exist before Phase 1** — created here |

---

## 8. Phase 1 acceptance

| Phase 1 deliverable | Status |
|---|---|
| Repository audit | DONE (section 1, 7) |
| V1.0 baseline compile + tests | DONE (section 3, 4) |
| Real mobile / desktop UX audit | DONE — see `docs/V1_1_UX_AUDIT.md` |
| `docs/V1_1_BASELINE_REPORT.md` | DONE (this file) |
| `docs/V1_1_UX_AUDIT.md` | DONE |
| Mobile bottom navigation occlusion problem confirmed and recorded | DONE — confirmed with measurements; root cause identified |

### Phase 1 verdict

The V1.0 baseline is **stable and green** (compile clean, 72/72 tests passing) and is a safe
foundation for V1.1. The V1.1 risk is not in the engines — it is entirely in the presentation shell:
a real, measured primary-CTA occlusion by the fixed bottom navigation, an active
safe-area mechanism that cannot fire without `viewport-fit=cover`, and a chat-input dock collision
on the Coach page.

No product code was changed in Phase 1. Waiting for review before PHASE 2 — P0 Mobile Shell.
# Historical document (V1.1). The project is now the Agentic Sports-Science Adaptive Training
# Decision System (中文：基于运动科学与 Agent 的自适应训练决策系统); "Personal Readiness Assistant"
# below is the historical name used at the time of that release.
