"""Minimal Streamlit custom-component bridge to browser IndexedDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import streamlit.components.v1 as components


_component = components.declare_component(
    "personal_readiness_indexeddb",
    path=str(Path(__file__).parent / "frontend"),
)


def browser_storage_bridge(
    operation: str,
    command_id: str,
    state: Mapping[str, Any] | None = None,
    key: str = "browser_storage_bridge",
) -> Any:
    """Run one idempotent ``load``, ``save`` or ``clear`` browser command."""
    if operation not in {"load", "save", "clear"}:
        raise ValueError(f"Unsupported browser-storage operation: {operation}")
    return _component(operation=operation, command_id=command_id, state=dict(state or {}), key=key, default=None)

