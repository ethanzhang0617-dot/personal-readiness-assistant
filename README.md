# Personal Readiness Assistant

**Release candidate: Personal Readiness Assistant V1.0 — Portfolio Release**

An English-only Streamlit web prototype for two daily questions:

1. **How ready am I today?**
2. **What should I train today?**

It combines a personal readiness baseline, morning recovery signals, completed training history, goals and preferred training split to generate an explainable workout direction. The default public profiles are fixed, simulated examples for Ethan, Alex and Jessica.

## Mobile-first experience

The portfolio release uses a mobile-first information hierarchy while keeping the same deterministic readiness and recommendation logic. At phone widths, the primary daily flow is **Today → Check-in → Train → Trends → Coach**, with a fixed five-item bottom navigation and secondary destinations grouped under **More**. Desktop widths retain the sidebar navigation.

- **Today:** readiness status, primary training direction, brief explanation and inspectable Decision Trace.
- **Check-in:** daily recovery inputs with explicit 1–5 scale labels and safety prompts.
- **Train:** selected workout, alternatives, rationale and completed-session logging.
- **Trends:** historical readiness and training context.
- **Coach:** deterministic factual answers, with an optional DeepSeek explanation layer and a rule-based fallback.

The English-only product copy, browser-local data model, safety boundary, readiness engine and training recommendation engine are unchanged. The AI explanation layer now runs on the DeepSeek API instead of a locally embedded model.

## Product loop

```text
Profile → Morning Check-in → Readiness → Recent Training History
        → Deterministic Workout Recommendation → Workout Template
        → Explicit Training Log → Next Day's Context
```

The product never logs a proposed workout automatically. A completed session is added only after the user selects **Log completed workout**. The selected `WorkoutPrescription` is the single source for the displayed exercises, prescribed sets and log defaults; actual completed sets are stored separately and drive weekly exposure.

Each completed session stores `session_id`, `profile_id`, `date`, `training_type`, `primary_focus`, `prescription_id`, `exercises`, `prescribed_sets`, `actual_sets`, `duration_min`, `session_rpe`, `session_load`, `muscle_set_contributions`, `completed`, `completion_status` and `notes`. Two sessions on one date remain separate because `session_id`, not date, is unique.

## Local-first browser data

My Local Data uses browser **IndexedDB** as the persistent source of truth and `st.session_state` as the active runtime cache. A small dependency-free Streamlit custom component provides the Python ↔ browser bridge:

```text
Streamlit UI → Python application logic → browser-storage bridge → IndexedDB
```

At startup, the bridge loads the versioned local document and hydrates the runtime cache. Profile changes, check-ins, readiness assessments, deterministic recommendations and completed training sessions queue an automatic save back to IndexedDB. Daily check-ins are unique by `profile_id + date` and update the existing date; local soreness remains part of that dated check-in, never a permanent profile field.

The stored document includes `schema_version`, `updated_at`, profiles, daily check-ins, readiness history, training sessions, recommendation history, browser preferences and an optional bounded recent chat history. **Export My Data** creates `personal-readiness-backup.json`. **Import Backup** validates the schema and references before a confirmed replace. **Clear Local Data** requires confirmation and removes personal browser data while retaining fixed demo profiles.

Demo profiles (Ethan, Alex and Jessica) are seeded separately and are never serialized into My Local Data. The app does not use a remote personal-history database, GitHub commits, cloud sync or automatic remote backup. Data needed for readiness and recommendations is temporarily processed by the running application. Saved personal history stays in the browser; when a user asks the AI Coach an explanation question, a summarised context and the recent Coach messages are sent to the configured AI provider (see **AI architecture** below). Local history does not automatically follow the user to another browser/device and may be lost if browser site data is cleared; exports are the manual backup/transfer mechanism.

## Training recommendation architecture

`training_recommendation_engine.py` is a pure deterministic module. It receives:

- approved Green / Amber / Red / STOP readiness result and four domains;
- reported fatigue and soreness;
- profile goal, activity, level and preferred training split;
- completed session dates, focuses, muscle groups, duration and session-RPE load.

It returns one primary workout, two rule-generated alternatives, a duration and intensity context, avoid-today guidance, a workout template, recent-training facts, and an inspectable decision rationale. It does **not** estimate recovery percentages or make clinical claims.

### Decision rules in plain language

- **Green:** normal planned training can be selected. The engine favours the goal and split pattern while deprioritising muscle groups trained on the same or previous day.
- **Amber:** elevated load or high soreness selects easy aerobic work plus mobility. With an isolated sleep-driven Amber result and low soreness, a reduced strength session can remain available: shorter duration, 2–3 sets and no failure sets.
- **Red:** recovery / rest direction only. No heavy strength, HIIT or maximal testing.
- **STOP:** no normal training recommendation. A safety concern overrides the workout flow and directs the user to appropriate professional assessment for acute or concerning symptoms.

The rotation logic is a transparent scheduling heuristic, not proof of a fixed 48-hour recovery requirement. It looks at actual logged muscles and avoids a consecutive high-intensity repeat when another appropriate option exists.

### Calendar-based training load

Training Load uses completed calendar days, not the last 7 or 28 sessions. Session load remains `duration_min × session_RPE`; all completed sessions on the same date are summed into one daily load. The recent window is assessment date minus 7 days through assessment date minus 1 day. The reference window is assessment date minus 28 days through assessment date minus 8 days. Means therefore cover exactly 7 and 21 calendar days, including tracked rest days as 0 AU.

A dated daily record establishes tracking coverage. Missing dates are unknown and are never silently converted to rest days. The full comparison requires all 28 dates; 14–27 covered dates are labelled limited but remain insufficient for a full 7-versus-21 comparison. When the reference mean is near zero, the load domain reports insufficient data instead of dividing by a tiny value. These windows and thresholds are transparent prototype heuristics.

## AI architecture — deterministic facts, optional DeepSeek explanations

The readiness result and workout recommendation are always generated by deterministic rules. The AI layer can only explain them.

```text
question → deterministic router
             ├── personal factual  → structured fact resolver → verified answer   (no model, no API call)
             ├── correction        → verified re-check                            (no model, no API call)
             ├── safety            → safety rule                                  (no model, no API call)
             └── explanation / general → DeepSeek (non-thinking) → guards → fallback
```

- **Personal factual questions never call the provider.** "How much have I trained back this week?", "What's my training load today?" and similar questions are answered from structured facts that carry their own unit, period and source, and are labelled **VERIFIED DATA**.
- **Explanation, discussion and general training questions** may be sent to the DeepSeek API (`deepseek-flash`, non-thinking mode) and are shown only after passing the contradiction check and the grounding guards.
- The provider is **not required** for Today, Train, Check-in, Trends, Profile or the deterministic Coach. No AI client is created and no request is made unless a user asks an explanation question.
- The model receives a **minimised structured context**: goal, level, split, today's readiness, today's recommendation, weekly exposure summary, recent sessions, local soreness and a bounded recent conversation. It never receives the full local database, the browser backup or another profile's data.
- Output is bounded (`max_tokens` 400) and requests time out after 20 seconds. Any failure — missing key, authentication, rate limit, timeout, network, invalid or empty response, or a rejected draft — degrades to the deterministic answer instead of crashing.
- API usage is a small internal token count in the developer diagnostics panel; prompts are not persisted.

### Configuring the provider

The key is read from Streamlit secrets first, then from the `DEEPSEEK_API_KEY` environment variable. It is never hardcoded, logged, committed, written to browser storage or sent to the frontend.

```toml
# .streamlit/secrets.toml  (gitignored — never commit a real key)
DEEPSEEK_API_KEY = "..."
```

`.streamlit/secrets.toml.example` contains placeholder values only. `DEEPSEEK_MODEL` and `DEEPSEEK_BASE_URL` are optional overrides; the defaults are `deepseek-flash` and `https://api.deepseek.com`. `DISABLE_AI_COACH = "true"` turns the explanation layer off while keeping the deterministic Coach.

Without a key the product is fully usable: explanation questions show *AI explanation is temporarily unavailable* alongside the deterministic answer.

### Privacy boundary

Saved readiness, check-in and training-history data remain in the browser's IndexedDB. When a user asks an explanation question, a summarised context and the recent Coach messages are sent to the configured AI provider to generate that reply. Personal factual answers are produced without any provider call.

## Deploy to Streamlit Community Cloud

This is the primary deployment path.

1. Create a GitHub repository and upload this project, with `app.py` at the repository root.
2. Commit and push to branch `main`.
3. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
4. Select **Create app**, then select the repository and branch `main`.
5. Set **Main file path** to `app.py`.
6. Choose **Deploy** and share the resulting `https://...streamlit.app` URL.

No Streamlit secrets are required for the default app: without a `DEEPSEEK_API_KEY` every product feature works and the Coach falls back to deterministic answers. To enable AI explanations, add `DEEPSEEK_API_KEY` to the app's Streamlit secrets (Settings → Secrets). `DISABLE_AI_COACH = "true"` disables the explanation layer explicitly.

## Run locally

```bash
cd personal-readiness-assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt pytest
python -m pytest -q
python -m streamlit run app.py
```

Open the local URL Streamlit prints. The full app works with no API key. Add `DEEPSEEK_API_KEY` to `.streamlit/secrets.toml` when you want to test the live explanation path, or run `python scripts/deepseek_smoke.py` for a manual live check.

## Files to upload to GitHub

```text
app.py
ai_engine.py
ai_facts.py
local_data.py
science_content.py
training_recommendation_engine.py
readiness_engine.py
profile_store.py
demo_data.py
ui_components.py
styles.py
requirements.txt
test_app.py
README.md
run_demo.command
scripts/deepseek_smoke.py
.gitignore
.streamlit/secrets.toml.example
.streamlit/config.toml
browser_storage/__init__.py
browser_storage/frontend/index.html
browser_storage/frontend/storage.js
mobile_shell/__init__.py
mobile_shell/frontend/index.html
mobile_shell/frontend/shell.js
```

Do not upload `.venv/`, `__pycache__/`, local model cache directories, a real `.streamlit/secrets.toml`, or real personal/health exports.

## Science & Logic and evidence boundary

The first-level **Science & Logic** page documents evidence boundaries, system inputs, personal baseline handling, the four domains, exact overall-readiness rules, recommendation order, evidence labels, an example decision, limitations and linked PubMed / DOI references. It imports rule metadata directly from `readiness_engine.py` and `training_recommendation_engine.py`, which prevents documentation thresholds from silently drifting away from executable code.

The monitoring concepts are informed by Saw et al. (2016, PMID 26423706) for subjective measures; Bourdon et al. (2017, PMID 28463642) and Haddad et al. (2017, PMID 29163016) for training-load and session-RPE monitoring; Buchheit (2014, PMID 24578692) for within-athlete HR/HRV interpretation and measurement variability; Schoenfeld et al. (2017, PMID 27433992), Schoenfeld et al. (2019, PMID 30558493) and Pelland et al. (2026, PMID 41343037) for resistance-training volume and frequency context; Greig et al. (2020, PMID 32813181) and Zhang et al. (2021, PMID 33776802) for autoregulation as a broader concept; Refalo et al. (2023, PMID 36334240) and Robinson et al. (2024, PMID 38970765) for proximity-to-failure context; and HRV-guided training reviews (PMID 34489178, PMID 34639599), which come from endurance/aerobic research, for using autonomic status as one intensity modifier.

**Evidence boundaries:** these sources support the broader monitoring concepts and training principles. They do not validate this application's exact thresholds, aggregation weights, Readiness Index scale, 7-versus-21-day training-load windows, session-demand mapping, RIR ranges or recommendation order — those are documented product heuristics, listed concept by concept on the Science & Logic page. Bibliographic details for every reference were verified against PubMed, Europe PMC and Crossref; the per-reference evidence is recorded in `docs/V1_1_SCIENCE_REFERENCE_AUDIT.md`.

Direct sets are counted as 1.0 and mapped secondary sets as 0.5. This is a transparent productized estimate, not a precise physiological contribution ratio. Weekly targets are user-entered where available, then descriptive from recent logs, then a labelled demo heuristic; no universal optimal sets/week is claimed.

For an exercise absent from the mapping table, exposure falls back once per exercise to an explicit primary muscle group, then to a clearly mappable session focus. Known and unknown exercises are added from their own actual completed sets; the session total is never applied repeatedly to multiple unknown exercises. `Full Body Strength` declares only the muscle groups its current Squat, Bench Press and Chest-Supported Row prescription can actually contribute to; Core is not declared by that candidate.

## Safety, privacy and product boundary

This is an educational product prototype. It is not a clinically validated fatigue prediction system, injury prediction tool, medical diagnostic system or training prescription. Workout recommendations are heuristic decision-support suggestions based on readiness, recent training history, reported soreness and goals. Acute or concerning symptoms, illness, injury, persistent deterioration, or unusual symptoms require appropriate professional assessment.

The readiness engine uses personal baseline comparisons and transparent prototype heuristics. The specific thresholds, aggregation rules and time windows have not been prospectively validated. Readiness Index is a communication score, not a recovery percentage, fatigue probability or injury probability. The interface exposes **Decision factors**, **Decision Trace** and **Recommendation Rationale**, not a model's private chain-of-thought.
