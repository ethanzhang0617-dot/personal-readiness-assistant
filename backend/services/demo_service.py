"""Demo profile access for the API.

Phase 1 exposes the fixed demo profiles only. Local browser profiles keep living
in Streamlit + IndexedDB; the API does not add a database or a second store.

``scenario_values`` and ``SCENARIOS`` are reused from ``app.py`` on purpose: the
API must return the same demo numbers the Streamlit reference implementation
shows. Extracting them into a Streamlit-free module is a later migration step,
not a Phase 1 change to the stable app.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from demo_data import build_demo_profiles


class UnknownProfileError(LookupError):
    """Raised when a requested demo profile id does not exist."""


def scenarios() -> tuple[str, ...]:
    from app import SCENARIOS

    return tuple(SCENARIOS)


def demo_profiles() -> list[dict[str, Any]]:
    return build_demo_profiles()


def get_profile(profile_id: str | None = None) -> dict[str, Any]:
    profiles = demo_profiles()
    if not profile_id:
        return profiles[0]
    for profile in profiles:
        if profile.get("user_id") == profile_id:
            return profile
    raise UnknownProfileError(profile_id)


def scenario_values(profile: Mapping[str, Any], scenario: str) -> dict[str, Any]:
    from app import scenario_values as _scenario_values

    return deepcopy(_scenario_values(dict(profile), scenario))


def default_check_in(profile: Mapping[str, Any]) -> dict[str, Any]:
    """The demo check-in the Streamlit reference implementation starts from."""
    scenario = str(profile.get("default_scenario") or scenarios()[0])
    return scenario_values(profile, scenario)
