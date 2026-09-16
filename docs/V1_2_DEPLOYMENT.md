# V1.2 — Deployment Guide

The product is two processes:

```text
Next.js frontend  ──HTTPS──►  FastAPI backend  ──HTTPS──►  DeepSeek API (optional)
   (browser)                     (your server)               (explanation questions only)
```

* The **frontend** is a static/dynamic Next.js app. It holds no secrets.
* The **backend** is stateless: the browser owns check-ins, sessions, profile edits and Coach
  history, and sends them with each compute request. Nothing is written to a server database.
* The **DeepSeek credential lives only on the backend**. It is never bundled into the frontend.

The Streamlit V1.1 app in the repository is the reference implementation and is **not** part of this
deployment.

## 1. Environment variables

### Frontend

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Recommended | Absolute URL of the backend, e.g. `https://api.example.com`. Defaults to `http://127.0.0.1:8000` when unset. |

`NEXT_PUBLIC_*` values are **inlined into the browser bundle at build time**, so set this variable
before `pnpm build`, not only before `pnpm start`. Never place a secret in a `NEXT_PUBLIC_*`
variable.

Copy `frontend/.env.example` to `frontend/.env.local` for local development. Real env files are
gitignored.

### Backend

| Variable | Required | Purpose |
|---|---|---|
| `DEEPSEEK_API_KEY` | Optional | Enables AI explanations. Without it everything works and explanation questions return the deterministic answer. |
| `DEEPSEEK_MODEL` | Optional | Defaults to `deepseek-flash`. |
| `DEEPSEEK_BASE_URL` | Optional | Defaults to `https://api.deepseek.com`. |
| `DISABLE_AI_COACH` | Optional | `"true"` turns the explanation layer off explicitly. |
| `ARA_FRONTEND_ORIGINS` | Recommended in production | Comma-separated list of exact browser origins allowed by CORS, e.g. `https://app.example.com`. |

The backend also reads `.streamlit/secrets.toml` if present (so the existing local setup keeps
working); a `DEEPSEEK_API_KEY` environment variable takes effect when no secret file supplies one.

## 2. CORS

Allowed origins are an explicit list, never `*`:

* Unset `ARA_FRONTEND_ORIGINS` → only `http://localhost:3000` and `http://127.0.0.1:3000` are allowed.
* Production → set the exact origin(s) of the deployed frontend, for example
  `ARA_FRONTEND_ORIGINS=https://app.example.com,https://staging.example.com`.

Requests are limited to `GET`, `POST` and `OPTIONS`, and to the `Content-Type` header. Credentials
are not used, so no cookie or `allow_credentials` configuration is needed.

## 3. Local production run

```bash
# Terminal 1 — backend (from the repository root)
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend
pnpm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm build
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm start --port 3000
```

Open <http://localhost:3000>. The current build pipeline uses webpack (`next build --webpack`)
because Turbopack's PostCSS worker cannot bind its local IPC port in the development container; the
resulting bundle is a standard Next.js build.

## 4. Testing from a phone on the same network

```bash
# Backend on all interfaces
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend reachable from the LAN, with the API pointing at this machine's LAN IP
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://192.168.1.20:8000 pnpm dev --hostname 0.0.0.0 --port 3000

# Let that origin talk to the API (add the phone's origin, not a wildcard)
ARA_FRONTEND_ORIGINS=http://192.168.1.20:3000 python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Then open `http://192.168.1.20:3000` on the phone. Replace `192.168.1.20` with your machine's LAN
address. This is a temporary testing configuration — do not ship `0.0.0.0` binding together with an
unrestricted CORS list.

**Physical-device verification status:** the current release candidate was validated with browser
engines (Chromium and WebKit) at mobile viewports. It has **not** been verified on a physical iOS or
Android device — see `docs/V1_2_RELEASE_QA.md`.

## 5. Production topology (provider-neutral)

```text
                 ┌──────────────────────────┐
  browser ──────►│ Next.js host             │  static/SSR output, no secrets
        │        └──────────────────────────┘
        │
        └───────►┌──────────────────────────┐
                 │ FastAPI host             │  holds DEEPSEEK_API_KEY
                 │  uvicorn/gunicorn        │  stateless
                 └──────────────────────────┘
                            │
                            └──► DeepSeek API (only for explanation questions)
```

Requirements for any host:

1. **Python 3.11+** with the repository requirements installed (`streamlit`, `pandas`, `numpy`,
   `requests`; FastAPI/uvicorn are used by the API layer).
2. **Node 20.9+** and pnpm for the frontend build.
3. The API process needs outbound HTTPS to the provider endpoint when AI explanations are enabled,
   and no inbound access other than the frontend.
4. The frontend must be built with `NEXT_PUBLIC_API_BASE_URL` pointing at the public API URL.
5. The API must list the frontend origin in `ARA_FRONTEND_ORIGINS`.

Example commands (any PaaS, container, or VM):

```bash
# Backend
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2

# Frontend
cd frontend && pnpm install --frozen-lockfile
NEXT_PUBLIC_API_BASE_URL=https://api.example.com pnpm build
pnpm start --port 3000
```

These host names are examples only; no provider is required by the codebase.

## 6. Release checklist

1. `python3 -m compileall .` and `python3 -m pytest -v` → all green.
2. `cd frontend && pnpm lint && pnpm typecheck && pnpm build` → all green.
3. Backend smoke: `GET /api/health` returns `200` and reports whether a credential is configured
   (never the value).
4. Frontend smoke: Today loads and shows readiness and a recommendation.
5. Confirm `.streamlit/secrets.toml`, `.env`, `.env.local` are **not** tracked:
   `git status --ignored --short | grep -E "secrets|\.env"`.
6. Confirm the browser bundle contains no key: search the built output for `sk-`.
7. Decide the two CORS values (frontend origin) before exposing the API publicly.

## 7. What is intentionally not included

No database, no accounts, no authentication, no wearable integrations, no cloud sync and no
server-side persistence of personal data. Adding any of those is a product decision, not a
deployment detail.
