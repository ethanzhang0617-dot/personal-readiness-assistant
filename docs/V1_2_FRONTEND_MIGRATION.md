# V1.2 — Frontend Architecture Migration (Phase 1)

**Branch:** `v1.2-nextjs-migration` (created from `v1.1-productization` at `0c42048`)
**Status:** Phase 1 scaffold complete, local only, **not pushed**

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

1. Extract `SCENARIOS` / `scenario_values` / `rir_guidance` into a Streamlit-free module so the API
   no longer imports `app.py`.
2. Add history endpoints (per-day HRV, resting HR, sleep, load) to reach Insights parity.
3. Add check-in submission and completed-session logging to the web client, with an explicit
   decision about where user data lives after the migration.
4. Reach Train/Profile functional parity, then run a deliberate UI polish pass on the new client.
5. Only after parity: decide the long-term status of the Streamlit app (retire or keep as a
   diagnostic surface).
