"""FastAPI entry point for the V1.2 frontend migration.

Run from the repository root:

    python3 -m uvicorn backend.main:app --reload --port 8000

The Streamlit app is untouched and remains the reference implementation.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import API_VERSION, router

DEFAULT_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def allowed_origins() -> list[str]:
    """Local development origins only, unless a deployment sets them explicitly."""
    configured = os.getenv("ARA_FRONTEND_ORIGINS", "").strip()
    if not configured:
        return list(DEFAULT_FRONTEND_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


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
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)
    return app


app = create_app()
