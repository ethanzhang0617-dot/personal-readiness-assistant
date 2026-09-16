# V1.2 — Frontend Architecture Migration (Phase 1)

**Branch:** `v1.2-nextjs-migration` (created from `v1.1-productization` at `0c42048`)
**Status:** Phase 1 pushed (`84fee69`). Phase 2 pushed (`a00c4e2`). Phase 3 UI polish complete
locally, **not pushed**.

> Phase 2 adds the write path: morning check-in, completed-session logging, profile and weekly-target
> editing, demo scenario and profile switching, browser-local persistence with export/import,
> trend charts, and per-profile Coach history. See `docs/V1_2_FUNCTIONAL_PARITY.md` for the
> Streamlit-versus-Next.js checklist.
>
> Phase 3 polishes the presentation into a portfolio-quality product UI without adding features.
> See `docs/V1_2_UI_POLISH.md` for the visual direction, the component changes and the QA.

## 1. Goal

Replace the Streamlit presentation layer with a production-style, mobile-first web client
(Next.js + React + TypeScript + Tailwind CSS + shadcn/ui-style primitives) backed by a thin
FastAPI layer that calls the existing Python engines.

Phase 1 is an **architecture migration**, not a science migration:

* the deterministic engines remain the single source of truth;
* the Streamlit V1.1 app is untouched and stays runnable as the reference implementation;
* no threshold, aggregation, recommendation, router, guard or provider rule was changed.

## 2. Architecture

```text
Next.js (app router, server components)          FastAPI (backend/)
  │  reads JSON only                                │  no formulas
  ▼                                                 ▼
  lib/api.ts ────────── HTTP ──────────►  api/routes.py
                                            │
                                            ▼
                                        services/  (orchestration only)
                                            │
                                            ▼
                    readiness_engine · training_recommendation_engine ·
                    ai_facts · ai_engine (DeepSeek) · science_content · demo_data
```

**Adapter rule:** services orchestrate, they never re-implement. `readiness_service` calls
`assess_readiness`; `training_service` calls `recommend_training` and reads the existing
`ai_facts` projection for exposure; `coach_service` calls `ai_engine.get_ai_response`;
`science_service` serves `science_content` verbatim. The only copy that moved is
`EVIDENCE_BOUNDARIES`, which is now a single constant in `science_content.py` rendered by both
the Streamlit page and the API (identical text, no visible change).

## 3. Folder structure

```text
backend/
  main.py                 FastAPI app, CORS, router wiring
  api/routes.py           all HTTP endpoints
  services/               demo_service, readiness_service, training_service,
                          coach_service, science_service
  schemas/models.py       Pydantic transport contracts
frontend/
  app/                    layout, globals.css, /, /train, /coach, /insights, /profile, /profile/science
  components/             app shell, navigation, readiness hero, training block,
                          decision trace, state panels, ui/ primitives
  features/               today, train, coach, insights, profile, science views
  lib/                    api client, formatting, navigation, measurement readers, cn()
  types/api.ts            TypeScript contract for every endpoint
test_api.py               focused API tests (the existing test_app.py is unchanged)
```

Stable Python modules were **not moved**; the adapter imports them from the repository root
(`backend/__init__.py` puts the root on `sys.path`).

## 4. API endpoints

| Endpoint | Status | Notes |
|---|---|---|
| `GET /api/health` | working | engines, API version, provider, credential *presence* only |
| `GET /api/profiles` | working | three fixed demo profiles |
| `GET /api/profile` | working | `?profile_id=` optional |
| `GET /api/today` | working | readiness + recommendation + decision trace + why |
| `GET /api/readiness` | working | status, index + scale, confidence, domains, measurements, baseline |
| `GET /api/training/recommendation` | working | primary, prescription, alternatives, avoid, rationale, priority |
| `GET /api/training/exposure` | working | weighted working sets, targets, unit note |
| `GET /api/training/history` | working | completed sessions, newest first (`limit` 1–30) |
| `GET /api/decision-trace` | working | 8 deterministic steps, `source: deterministic` |
| `GET /api/science/references` | working | 13 verified references + evidence map + limitations + boundaries |
| `POST /api/check-in` | working | recomputes readiness and recommendation from a submitted check-in |
| `POST /api/coach/message` | working | deterministic-first; provider only for explanation questions |

Every response is structured JSON with `value`/`status`/`unit`/`source` style fields; no HTML and
no pre-rendered Streamlit text.

## 5. Reused vs new

**Reused unchanged:** `readiness_engine`, `training_recommendation_engine`, `ai_facts`,
`ai_engine` (DeepSeek provider + guards), `science_content`, `demo_data`, and the Streamlit
demo helpers `SCENARIOS` / `scenario_values` / `rir_guidance` (imported so the API returns the
same demo numbers as V1.1).

**New:** `backend/` (API + services + schemas), `frontend/` (Next.js client), `test_api.py`,
this document, and one constant (`EVIDENCE_BOUNDARIES`) that removes duplicated science copy.

**Still Streamlit-only:** the morning check-in form and validation UI, completed-session logging
and the workout template editor, profile editing and weekly set targets, IndexedDB persistence
(browser-local history), export/import/clear local data, the trend charts (multi-day HRV, resting
HR, sleep and load), the demo scenario switcher, and the developer diagnostics panel.

## 6. Phase 1 parity status

| Surface | Status |
|---|---|
| Today (readiness hero, training, how hard, why/decision trace, primary CTA) | **parity for reading** |
| Train (recommendation, prescription, alternatives, avoid, exposure, recent sessions, trace) | **partial** — logging still Streamlit-only |
| Coach (chat, starter prompts, context strip, provenance labels, notices) | **partial** — chat works end to end; no persistence of chat history |
| Insights (daily signals, domains, weekly exposure) | **partial** — multi-day trend charts are not exposed by the API yet |
| Profile (goal/split/level, baseline, targets, data sources, AI + privacy) | **partial** — read-only; editing stays in Streamlit |
| Science & Logic (boundaries, evidence map, limitations, 13 references) | **parity for reading** |

## 7. Verification performed

* Python: `python3 -m compileall .` PASS; `python3 -m pytest -v` → **149 / 149 PASS**
  (139 pre-existing + 10 new API tests, existing tests untouched).
* Frontend: `pnpm typecheck` PASS, `pnpm lint` PASS (no warnings), `pnpm build` PASS.
* FastAPI smoke: live `uvicorn` on 127.0.0.1:8000 → `/api/health` 200, `/api/today` 200,
  CORS preflight allows `http://localhost:3000` only.
* Visual QA (Playwright 1.62, headless Chromium, real dev server + real API):
  * 390 × 844: horizontal overflow **0 px** on all six routes; bottom navigation 73 px, flush to
    the viewport bottom; Today fits in a single viewport; `START SESSION` fully visible
    (top 657 px, bottom 709 px) above the navigation.
  * 1440 × 900: sidebar navigation visible, content column 864 px (no stretched layout),
    overflow 0 px.

## 8. Known limitations

1. **Two processes during Phase 1.** The API must run before the frontend can render data; without
   it, every page shows an explicit "API unavailable" state instead of crashing.
2. **No persistence and no auth.** The API serves the fixed demo profiles from memory. IndexedDB,
   local profiles and data export remain in the Streamlit app.
3. **No trend endpoints.** Insights shows today's values plus an explicit limited-state panel.
4. **shadcn/ui primitives were added as source, not via the CLI.** `components/ui/*` follow the
   shadcn/ui conventions (cva variants, `cn()` helper, `components.json` present) and are ready for
   `shadcn add` later; the CLI itself was not run in this environment.
5. **`pnpm`, not `npm`.** Node 24 is available from the Codex runtime, but `npm` is not installed
   in this environment; `pnpm` 11 is the configured package manager and `pnpm-lock.yaml` is
   committed.
6. **The build uses the webpack pipeline** (`next build --webpack`). Turbopack's PostCSS worker was
   unable to bind its local IPC port in this environment, which failed the CSS step. Adding
   `--webpack` is a build-pipeline choice only; it does not change runtime behaviour.
7. **Coach chat history is session-only** and is not written to any store.

## 9. Security

* DeepSeek credentials are read by the FastAPI process from `.streamlit/secrets.toml` or the
  `DEEPSEEK_API_KEY` environment variable. They are never sent to the browser: `/api/health`
  reports only whether a credential is configured.
* No `NEXT_PUBLIC_*` variable may carry a secret; `frontend/env.example` documents that the only
  public value is `NEXT_PUBLIC_API_BASE_URL`.
* `.streamlit/secrets.toml` remains gitignored and untracked.
* CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000` unless a deployment sets
  `ARA_FRONTEND_ORIGINS` explicitly.

## 10. Local development

```bash
# Terminal 1 — API (from the repository root)
python3 -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
pnpm install
pnpm dev            # http://localhost:3000
```

Quality gates: `pnpm typecheck`, `pnpm lint`, `pnpm build`.

## 11. Next migration steps (not started)

1. Add the remaining PARTIAL items listed in `docs/V1_2_FUNCTIONAL_PARITY.md` (chart tooltips,
   "sessions in the last 14 days", two-step import confirmation, a dedicated About route).
2. Decide whether local multi-profile accounts (create/delete a local profile) move to the web
   client or stay Streamlit-only.
3. Run a deliberate UI polish pass on the new client.
4. Only after that: decide the long-term status of the Streamlit app (retire or keep as a
   diagnostic surface).

---

# Phase 2 — Functional Parity (implemented)

## Architecture change: the browser owns the state

Phase 1 read fixed demo profiles from the API. Phase 2 moves the user's own data into the browser
and turns the API into a **stateless compute + explain layer**:

```text
IndexedDB (per profile: check-ins, logged sessions, profile edits, chat)
        │  state sent with every compute request
        ▼
POST /api/state/{today,check-in,profile,session,coach,insights}
        │  materialise → engines → JSON
        ▼
readiness_engine · training_recommendation_engine · ai_facts · ai_engine · profile_store helpers
```

Materialising a request means: seeded demo profile → apply profile edits (`update_profile`) →
upsert the user's daily rows (`upsert_daily_metric`) → append the user's logged session rows (as
produced by `log_training_session`). Nothing is re-implemented, and no server-side database is
introduced.

## New endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/scenarios` | scenario names, their simulated values, safety flags and the muscle taxonomy |
| `GET /api/profile/options` | the product's own goal / level / split / activity / sex lists |
| `GET /api/state/base` | seeded state for a demo profile, ready for the client to own |
| `POST /api/state/today` | readiness + recommendation + exposure + history + decision trace from the supplied state |
| `POST /api/state/check-in` | apply a check-in, recompute, return the updated state |
| `POST /api/state/profile` | apply profile edits and weekly targets, recompute |
| `POST /api/state/session` | log a completed session through the product's logging function |
| `POST /api/state/coach` | Coach answer from the supplied state |
| `POST /api/state/insights` | per-day series, load summary, exposure and readiness history |
| `GET /api/science/logic` | threshold table, overall rule, decision order and example decision |

## Frontend additions

* `/check-in` — the full morning check-in with units, validation, local soreness and the safety screen.
* Train — session switcher (primary + alternatives), engine workout template, weekly exposure,
  recent sessions, and a completed-session form pre-filled from the prescription.
* Insights — window selector, four trend charts (solid value line, dashed 7-check-in mean, dotted
  personal baseline), load summary, exposure and readiness history.
* Profile — editable profile fields and weekly targets, baseline panel, demo scenario and profile
  switchers.
* Profile → Data — data sources (wearables explicitly "not connected"), AI/privacy wording,
  export/import/clear, and the About copy.
* Coach — conversation persisted per profile in IndexedDB; starters reworded so they hit the
  deterministic fact path (the router is a protected contract).
* `lib/store.ts` (IndexedDB envelope v2, per-profile maps) and `lib/state-provider.tsx` (one source
  of truth for every page).

## Phase 2 verification

* Python: `compileall` PASS; `pytest` → **161 / 161 PASS** (149 before + 12 new API tests).
* Frontend: `pnpm typecheck` PASS, `pnpm lint` PASS (no findings), `pnpm build` PASS.
* End-to-end browser flow at 390 × 844: **20 / 20 checks** (Today → check-in → Today update →
  Train → log session → history/exposure update → Insights charts → Coach factual + explanation →
  profile edit → reload persistence), plus a log-button check confirming no control hides under the
  bottom navigation.
* Profile switching: **6 / 6 checks** (switch to Alex, Today follows, survives reload, switch back).
* Visual QA: 8 routes × 2 viewports → **0 px horizontal overflow everywhere**, bottom navigation
  73 px with a safe-area floor, Today CTA above the fold (661–713 px against a 771 px navigation
  top), desktop content column capped at 864 px.

## Phase 2 known limitations

1. Two processes must run (FastAPI + Next.js). Without the API every page shows an explicit
   "API unavailable" state rather than crashing.
2. Import replaces the whole local envelope; the reference app's validate-then-confirm step is not
   reproduced.
3. Charts are dependency-free SVG: correct data and gaps, but no hover tooltips.
4. Local multi-profile account management (create/delete a local profile) and the demo
   "regenerate history" tool remain Streamlit-only.
5. Storage schema version 2 replaced version 1; an older local envelope is discarded and reseeded.

---

# Phase 3 — Product UI Polish (implemented)

Presentation-only pass. No product feature, engine, contract or AI change.

* **Design system:** graphite/off-white neutrals, one elevated surface where it carries meaning,
  status colour reserved for readiness, a four-step type scale, a documented spacing rhythm,
  Lucide-only icons, one focus treatment, reduced-motion support.
* **Section primitive replaces the card wall:** most blocks now use an eyebrow, a title, a
  hairline divider and typographic hierarchy instead of another bordered rectangle. `Card` is
  reserved for the readiness hero, the primary decision, charts and the log form.
* **Today** is rebuilt as a flagship screen: readiness hero (large tabular index, status,
  interpretation, quiet domain strip), the training decision with a three-column stat row, the
  primary CTA, an inline check-in row and a collapsible causal Decision Trace. At 1440×900 the
  whole screen fits without scrolling.
* **Coach** reads as an embedded assistant: avatar + provenance line + full-width answers,
  right-aligned user bubbles, a raised composer, and an empty state that explains the contract.
* **Insights** leads with training load, adds "Sessions, last 14 days", and moves the four charts
  into a responsive 2-column Signals section. Charts gained axis ticks, a current-value readout,
  hover/tap guides and accessible labels while staying dependency-free.
* **Train, Check-in, Profile, Data and Science** were reorganised into sections; Check-in uses
  one-tap segmented scales; import became select → validate → summary → explicit confirm;
  About is its own route.

Verification for this phase: 45/45 route-viewport combinations (five viewports × nine routes) with
zero horizontal overflow and no controls under the bottom navigation; the Phase 2 functional
journey still passes 20/20; Python 161/161; frontend typecheck, lint and build clean.
