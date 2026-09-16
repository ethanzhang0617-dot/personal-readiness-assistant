"""Insights series built from the same columns the Streamlit Trends page uses.

No new analytics: the rolling mean is the same "mean of the most recent 7
check-ins, ignoring missing values" that the reference implementation shows, and
missing days stay missing rather than becoming zero.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

from readiness_engine import ln_rmssd

from backend.services import training_service


def _rolling(values: list[float | None], size: int = 7) -> list[float | None]:
    """Mean of the most recent ``size`` recorded values, skipping missing ones."""
    result: list[float | None] = []
    for index in range(len(values)):
        window = [value for value in values[max(0, index - size + 1):index + 1] if value is not None]
        result.append(round(sum(window) / len(window), 2) if window else None)
    return result


def _series(key: str, label: str, unit: str, dates: list[str], values: list[float | None],
            baseline: float | None, note: str) -> dict[str, Any]:
    rolling = _rolling(values)
    latest = next((value for value in reversed(values) if value is not None), None)
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "points": [{"date": day, "value": value, "rolling_mean": roll}
                   for day, value, roll in zip(dates, values, rolling)],
        "baseline": baseline,
        "latest": latest,
        "note": note,
    }


def build(profile: Mapping[str, Any], assessment: Mapping[str, Any],
          recommendation: Mapping[str, Any], window: int | None = None) -> dict[str, Any]:
    rows = sorted((profile.get("history") or []), key=lambda row: str(row.get("date")))
    if window is None or window <= 0 or window > len(rows):
        window = len(rows)
    shown = rows[-window:] if rows else []
    dates = [str(row.get("date")) for row in shown]
    baseline = dict(assessment.get("baseline") or {})

    def column(field: str, transform=None) -> list[float | None]:
        out: list[float | None] = []
        for row in shown:
            raw = row.get(field)
            if raw is None:
                out.append(None)
                continue
            try:
                value = transform(float(raw)) if transform else float(raw)
            except (TypeError, ValueError):
                value = None
            out.append(None if value is None else round(float(value), 2))
        return out

    note = "Mean of the most recent 7 recorded check-ins; missing days stay missing."
    series = [
        _series("ln_rmssd", "HRV", "lnRMSSD", dates, column("rmssd_ms", ln_rmssd),
                baseline.get("lnrmssd_mean"), note),
        _series("resting_hr_bpm", "Resting HR", "bpm", dates, column("resting_hr_bpm"),
                baseline.get("rhr_mean"), note),
        _series("sleep_hours", "Sleep", "hours", dates, column("sleep_hours"),
                baseline.get("sleep_mean"), note),
        _series("session_load", "Training load", "AU", dates, column("session_load"),
                None, "Duration × session RPE per day. Not minutes and not sets."),
    ]

    measurements = dict(assessment.get("measurements") or {})
    load = dict(measurements.get("training_load") or {})
    load.pop("daily_loads", None)  # the client already has the daily series above

    readiness_history = [
        {"date": str(row.get("assessment_date")),
         "status": row.get("overall_readiness"),
         "index": row.get("readiness_index"),
         "confidence": row.get("assessment_confidence")}
        for row in sorted((profile.get("assessments") or []), key=lambda row: str(row.get("assessment_date")), reverse=True)
    ]

    missing = ("Charts only plot recorded check-ins. Days without a check-in are shown as gaps, not as zero, "
               "and a metric without a recorded value is not plotted.")

    # Same metric the reference implementation shows on its Trends page: completed
    # sessions with a date inside the last 14 days (today minus 13 days onwards).
    cutoff = (date.today() - timedelta(days=13)).isoformat()
    sessions_14d = sum(1 for row in (profile.get("training_history") or [])
                       if row.get("completed") and str(row.get("date")) >= cutoff)

    return {
        "window": window,
        "available_check_ins": len(rows),
        "sessions_last_14_days": sessions_14d,
        "series": series,
        "load": load,
        "exposure": training_service.exposure(profile, assessment, recommendation),
        "readiness_history": readiness_history,
        "missing_data_note": missing,
    }
