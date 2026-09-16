"""Coach orchestration over ``ai_engine`` / ``ai_facts``.

The deterministic-first contract is unchanged: personal factual questions and
corrections never reach the provider, and every model draft still has to pass
the existing guards before it is shown. The DeepSeek credential is read on the
server only and is never returned to the frontend.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

import ai_engine

from backend import REPO_ROOT


_CONTRACT = {
    "personal_factual": "deterministic answer, zero provider calls",
    "correction": "deterministic re-check, zero provider calls",
    "safety": "deterministic safety routing, zero provider calls",
    "explanation": "provider allowed, then contradiction check and grounding guards",
    "fallback": "deterministic answer whenever the provider is unavailable or a draft is rejected",
}


def server_secrets() -> dict[str, Any]:
    """Server-side credentials. Mirrors Streamlit's priority without Streamlit.

    The value is used by ``ai_engine`` inside the API process only. It is never
    serialised into a response body or a Next.js bundle.
    """
    secrets: dict[str, Any] = {}
    path = REPO_ROOT / ".streamlit" / "secrets.toml"
    if path.exists():
        try:
            import tomllib

            secrets.update(tomllib.loads(path.read_text(encoding="utf-8")))
        except Exception:
            # A malformed secrets file must never take the API down.
            secrets = {}
    if os.getenv("DEEPSEEK_API_KEY") and not secrets.get("DEEPSEEK_API_KEY"):
        secrets["DEEPSEEK_API_KEY"] = os.environ["DEEPSEEK_API_KEY"]
    return secrets


def credential_configured() -> bool:
    return bool(ai_engine.deepseek_api_key(server_secrets()))


def _classify(provider: str) -> tuple[str, bool, bool]:
    if provider == ai_engine.PROVIDER_VERIFIED:
        return "verified_data", False, True
    if provider == ai_engine.PROVIDER_SAFETY:
        return "safety", False, False
    if provider == ai_engine.AI_PROVIDER_LABEL:
        return "ai_explanation", True, False
    return "deterministic_fallback", False, False


def verified_answer(text: str, notice: str | None = None) -> dict[str, Any]:
    """A deterministic answer produced outside the router but inside its contract."""
    return {"answer": text, "provider": ai_engine.PROVIDER_VERIFIED, "kind": "verified_data",
            "ai_used": False, "verified_data": True, "notice": notice, "contract": dict(_CONTRACT)}


def answer(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any],
           recommendation: Mapping[str, Any], history: Sequence[Mapping[str, str]] = (),
           secrets: Mapping[str, Any] | None = None) -> dict[str, Any]:
    text, provider, notice = ai_engine.get_ai_response(
        question, dict(profile), assessment, recommendation, list(history), secrets if secrets is not None else server_secrets())
    kind, ai_used, verified = _classify(provider)
    return {"answer": text, "provider": provider, "kind": kind, "ai_used": ai_used,
            "verified_data": verified, "notice": notice, "contract": dict(_CONTRACT)}
