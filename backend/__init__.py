"""FastAPI adapter over the existing Python domain modules.

The Streamlit V1.1 app remains the reference implementation. This package adds a
thin HTTP layer that calls the same engines; it never re-implements a formula.
Importing ``backend`` puts the repository root on ``sys.path`` so the existing
top-level modules (``readiness_engine``, ``training_recommendation_engine``,
``ai_facts``, ``ai_engine``, ``demo_data``, ``science_content``) can be reused
where they already live.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

__all__ = ["REPO_ROOT"]
