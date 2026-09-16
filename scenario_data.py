"""Demo scenario definitions — shared by Streamlit and the FastAPI layer.

These helpers are presentation/demo conveniences only. They never change a
readiness threshold, an aggregation rule or a recommendation: they only produce
the simulated morning check-in the fixed demo profiles start from. Extracted
from ``app.py`` so the API no longer has to import the Streamlit app.
"""

from __future__ import annotations

from typing import Any, Mapping


SCENARIOS: tuple[str, ...] = ("Well Recovered Day", "Moderate Fatigue Day", "High Load / Poor Sleep Day")

#: The check-in fields a scenario fills in. Kept explicit so the API and the
#: frontend validate against the same list the product already used.
SCENARIO_FIELDS: tuple[str, ...] = ("rmssd_ms", "resting_hr_bpm", "sleep_hours", "sleep_quality",
                                   "fatigue", "soreness", "stress", "motivation", "safety_flags")


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def default_scenario(profile: Mapping[str, Any]) -> str:
    scenario = str(profile.get("default_scenario") or "").strip()
    return scenario if scenario in SCENARIOS else SCENARIOS[0]


def scenario_values(profile: Mapping[str, Any], scenario: str) -> dict[str, Any]:
    """Simulated morning check-in for a named demo scenario."""
    history = list(profile.get("history") or [])[-28:]

    def average(field: str, fallback: float) -> float:
        values = [float(row[field]) for row in history if row.get(field) is not None]
        return _mean(values) or fallback

    hrv, rhr = average("rmssd_ms", 55.0), average("resting_hr_bpm", 58.0)
    sleep_need = float(profile["personal_sleep_need"])
    if scenario == "High Load / Poor Sleep Day":
        return {"rmssd_ms": round(hrv * .82, 1), "resting_hr_bpm": round(rhr + 5), "sleep_hours": round(sleep_need * .72, 1), "sleep_quality": 2, "fatigue": 4, "soreness": 4, "stress": 4, "motivation": 2, "safety_flags": []}
    if scenario == "Moderate Fatigue Day":
        return {"rmssd_ms": round(hrv * .94, 1), "resting_hr_bpm": round(rhr + 1), "sleep_hours": round(sleep_need * .95, 1), "sleep_quality": 4, "fatigue": 2, "soreness": 2, "stress": 2, "motivation": 4, "safety_flags": []}
    return {"rmssd_ms": round(hrv * 1.04, 1), "resting_hr_bpm": round(max(35, rhr - 1)), "sleep_hours": round(sleep_need * 1.01, 1), "sleep_quality": 5, "fatigue": 1, "soreness": 1, "stress": 2, "motivation": 5, "safety_flags": []}
