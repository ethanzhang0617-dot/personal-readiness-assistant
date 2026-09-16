# V1.2 — Streamlit vs Next.js Functional Parity

**Compared:** Streamlit V1.1 (`app.py`, the reference implementation, still runnable) against the
Next.js client (`frontend/`) on branch `v1.2-nextjs-migration`.
**Legend:** PARITY · PARTIAL · NOT MIGRATED · INTENTIONALLY DEFERRED

## 1. User-facing functions

| # | Function | Streamlit V1.1 | Next.js V1.2 | Status |
|---|---|---|---|---|
| 1 | Today: readiness status, index, domains, confidence | Yes | Yes | **PARITY** |
| 2 | Today: What to train + How hard + session length | Yes | Yes | **PARITY** |
| 3 | Today: primary CTA | Yes | Yes (visible above the fold at 390×844) | **PARITY** |
| 4 | Today: Why / Decision Trace (8 deterministic steps) | Yes | Yes (expandable) | **PARITY** |
| 5 | Today: key-signal tiles (HRV, resting HR, sleep, load) | Yes, on Today | Yes, on Insights | **PARITY** (placement differs) |
| 6 | Morning check-in: HRV, resting HR, sleep hours/quality, fatigue, soreness, stress, motivation | Yes | Yes | **PARITY** |
| 7 | Morning check-in: local soreness per muscle group | Yes | Yes | **PARITY** |
| 8 | Morning check-in: safety screen | Yes | Yes | **PARITY** |
| 9 | Morning check-in: validation and direction hints | Yes | Yes (range validation, units, direction hints) | **PARITY** |
| 10 | Train: primary recommendation, prescription, RIR | Yes | Yes | **PARITY** |
| 11 | Train: alternative preview (never replaces primary) | Yes | Yes (session switcher) | **PARITY** |
| 12 | Train: How to execute it (workout template) | Yes | Yes (engine template) | **PARITY** |
| 13 | Train: avoid-today guidance | Yes | Yes | **PARITY** |
| 14 | Train: weekly exposure with targets and unit note | Yes | Yes | **PARITY** |
| 15 | Train: recent completed sessions | Yes | Yes | **PARITY** |
| 16 | Log completed workout: duration, session RPE, per-exercise actual sets, completion, notes | Yes | Yes | **PARITY** |
| 17 | Logged session immediately affects load, exposure and the next recommendation | Yes | Yes (verified end to end) | **PARITY** |
| 18 | Trends: window selector | Yes (by check-ins) | Yes (7 / 28 / all check-ins) | **PARITY** |
| 19 | Trends: HRV, resting HR, sleep, training-load charts | Yes (Altair) | Yes (dependency-free SVG, same columns and rolling mean) | **PARTIAL** — no hover tooltips; simpler chart chrome |
| 20 | Trends: "sessions in the last 14 days" metric | Yes | No | **PARTIAL** |
| 21 | Trends: training history list | Yes | Yes | **PARITY** |
| 22 | Trends: readiness history | Yes | Yes (populated once check-ins are saved) | **PARITY** |
| 23 | Coach: conversation, context strip, starters, provenance labels | Yes | Yes | **PARITY** |
| 24 | Coach: factual questions answered deterministically with zero provider calls | Yes | Yes (asserted in backend tests and in the browser flow) | **PARITY** |
| 25 | Coach: explanation questions via the provider with guards and fallback | Yes | Yes | **PARITY** |
| 26 | Coach: conversation persistence | Local profiles only | All profiles, per profile | **PARITY** (broader than V1.1; documented as an improvement) |
| 27 | Profile: edit name, age, sex, activity, goal, level, split, sleep need, target sessions | Yes | Yes | **PARITY** |
| 28 | Profile: weekly set targets | Yes | Yes | **PARITY** |
| 29 | Profile: baseline panel | Yes | Yes | **PARITY** |
| 30 | Profile: create / delete a local profile | Yes | No | **NOT MIGRATED** — single active profile; local multi-account profiles remain Streamlit-only |
| 31 | Profile: regenerate simulated readiness history (demo tool) | Yes | No | **NOT MIGRATED** — demo tooling |
| 32 | Demo scenario switching (3 scenarios) | Yes | Yes (Profile page; refreshes readiness, training, exposure, trace, Coach and Insights) | **PARITY** |
| 33 | Demo profile switching (Ethan, Alex, Jessica) | Yes | Yes (per-profile local state) | **PARITY** |
| 34 | Science & Logic: evidence boundaries | Yes | Yes (identical copy) | **PARITY** |
| 35 | Science & Logic: system overview, inputs, threshold table, overall rule, decision order, evidence map, example decision, limitations | Yes | Yes | **PARITY** |
| 36 | References: 13 entries with PMID, DOI, PubMed and DOI links | Yes | Yes (mobile-readable cards) | **PARITY** |
| 37 | Data & privacy disclosure (local storage + AI provider boundary) | Yes | Yes | **PARITY** |
| 38 | Data sources, with future wearables marked as not connected | Partial | Yes (explicit "not connected" chips) | **PARITY** |
| 39 | About this prototype | Yes (own page) | Yes (section on Profile → Data) | **PARTIAL** — no separate About route |
| 40 | Export / import local data | Yes (validate, then confirm replace) | Yes (single-file export; import replaces) | **PARTIAL** — Streamlit's two-step confirmation is simplified |
| 41 | Clear local data | Yes | Yes (per browser, resets to the seeded demo profile) | **PARITY** |
| 42 | Mobile shell: bottom navigation, safe area, no hidden controls | Yes | Yes (73 px bar, safe-area floor, verified at 390×844) | **PARITY** |
| 43 | Desktop layout | Sidebar | Sidebar (content capped at 54 rem) | **PARITY** |
| 44 | Developer diagnostics panel (AI provider diagnostics) | Yes | No | **INTENTIONALLY DEFERRED** — developer-only tool |
| 45 | More / settings hub destination | Yes | Folded into Profile and Profile → Data | **PARTIAL** — navigation grouping differs |

## 2. Deliberately out of scope for Phase 2

| Area | State |
|---|---|
| Adaptive Decision Loop, Personal Response Profile, Recommendation Confidence, In-session Calibration, what-if explorer | **INTENTIONALLY DEFERRED** (no such feature exists in V1.1 either) |
| Wearable integrations (Apple Health, Garmin, WHOOP, Oura) | **INTENTIONALLY DEFERRED** — shown as "not connected" |
| Authentication, accounts, permissions | **INTENTIONALLY DEFERRED** |
| Remote database, cloud sync, social features, notifications | **INTENTIONALLY DEFERRED** |
| Final UI polish (motion, brand, dark mode, pixel work) | **INTENTIONALLY DEFERRED** to the polish phase |

## 3. Normal product demo — does it still need Streamlit?

**No.** The full user journey runs in the Next.js client against the FastAPI layer:
open Today → review readiness and the recommendation → complete the morning check-in → Today
recalculates → open Train → review exposure and history → log a completed session → history, load
and exposure update → open Insights → read the updated trends → ask the Coach a factual question
(deterministic) and an explanation question (provider or fallback) → edit a profile field →
reload the browser and confirm the data persisted.

All 20 automated checks of that journey passed at 390 × 844 (see the migration doc for the exact
list). Remaining Streamlit-only surfaces are developer/diagnostic tooling plus the local
multi-profile account management described above.

## 4. Contract checks

* The deterministic engines, thresholds, aggregation, training load, exposure, Decision Trace,
  safety routing, AI router, grounding guards and the DeepSeek integration are unchanged
  (`git diff` shows no modification to `readiness_engine.py`, `training_recommendation_engine.py`,
  `ai_facts.py`, `ai_engine.py`, `demo_data.py`, `profile_store.py`, `local_data.py`, `styles.py`,
  `requirements.txt`).
* Two pure-data extractions were made so the API does not import the Streamlit app:
  `scenario_data.py` (SCENARIOS + `scenario_values`) and `product_options.py` (goal / level /
  split / activity / sex lists). `app.py` now imports both; its behaviour is unchanged.
* `science_content.EVIDENCE_BOUNDARIES` remains the single source of the boundary copy, shared by
  the Streamlit page and the API.
* Coach contract preserved: personal factual and correction turns make **0** provider calls, and a
  rejected or unavailable draft still degrades to the deterministic answer.
