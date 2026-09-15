"""Browser-level shell bridge for the mobile product shell.

Streamlit does not expose two things the mobile shell needs:

* the document ``viewport`` meta tag (Streamlit always writes
  ``width=device-width, initial-scale=1, shrink-to-fit=no``, which makes
  ``env(safe-area-inset-*)`` permanently report 0 on iOS);
* a dynamic-viewport / on-screen-keyboard signal.

This component carries **no application data**. It never writes a value back to
Python (so it can never trigger a rerun) and it degrades gracefully: if the
script cannot run, the shell still works because ``styles.py`` owns a complete
CSS-only fallback contract.
"""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


SHELL_COMPONENT_NAME = "personal_readiness_mobile_shell"
SHELL_ELEMENT_KEY = "mobile_shell_viewport"

_component = components.declare_component(
    SHELL_COMPONENT_NAME,
    path=str(Path(__file__).parent / "frontend"),
)


def mobile_shell_bridge(key: str = SHELL_ELEMENT_KEY) -> None:
    """Mount the (visually hidden) shell bridge for this page render."""
    _component(key=key, default=None)
