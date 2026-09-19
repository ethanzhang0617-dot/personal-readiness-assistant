"""FastAPI entry point for the V1.2 frontend migration.

Run from the repository root:

    python3 -m uvicorn backend.main:app --reload --port 8000

The Streamlit app is untouched and remains the reference implementation.
"""

from __future__ import annotations

import os
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import API_VERSION, router

DEFAULT_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

#: Every Vercel deployment of THIS project uses the project name as its host
#: prefix, and the preview hosts end with the account slug, for example
#: ``personal-readiness-assistant-git-main-ethanzhang0617-dot.vercel.app``.
#: Preview deployments change hostname on every push, so an exact-origin list
#: alone cannot cover QA. This pattern is deliberately project-scoped: it never
#: matches an unrelated ``.vercel.app`` site, and the API uses no cookies or
#: credentials, so it is not a wildcard for the platform.
VERCEL_ACCOUNT_SLUG = os.getenv("ARA_VERCEL_ACCOUNT_SLUG", "ethanzhang0617-dot")
PROJECT_SLUG = "personal-readiness-assistant"


def allowed_origins() -> list[str]:
    """Local development origins only, unless a deployment sets them explicitly."""
    configured = os.getenv("ARA_FRONTEND_ORIGINS", "").strip()
    if not configured:
        return list(DEFAULT_FRONTEND_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def preview_origin_pattern() -> str:
    """Project-scoped regex for this project's Vercel production and preview hosts.

    Matches ``personal-readiness-assistant.vercel.app`` and preview hosts such as
    ``personal-readiness-assistant-<deployment-or-branch>-<account>.vercel.app``.
    Any other ``.vercel.app`` site, including one that merely reuses the project
    name with a different account slug, stays blocked.
    """
    project = re.escape(PROJECT_SLUG)
    account = re.escape(VERCEL_ACCOUNT_SLUG)
    return rf"^https://{project}(-[a-z0-9-]+)?-{account}\.vercel\.app$|^https://{project}(-git-[a-z0-9-]+)?\.vercel\.app$"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Personal Readiness Assistant API",
        version=API_VERSION,
        description="Read-only adapter over the existing deterministic engines plus the Coach endpoint. "
                    "Personal facts are answered deterministically; only explanation questions may reach the "
                    "configured AI provider, and the credential stays server-side.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        # Vercel production and preview hosts for this project only. The explicit
        # allowed_origins list above stays authoritative for every other origin.
        allow_origin_regex=preview_origin_pattern(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)
    return app


app = create_app()
