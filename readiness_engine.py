"""Transparent, individual-baseline readiness rules for V2.1.

This is a scientifically informed decision-support prototype.  It deliberately
contains transparent product heuristics; it is not a diagnostic or validated
fatigue-prediction algorithm.  No function in this module calls an LLM.
"""
from __future__ import annotations

from datetime import date, timedelta
import math
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"
INSUFFICIENT, STOP = "INSUFFICIENT DATA", "STOP / PROFESSIONAL REVIEW"
SEVERITY_TO_STATUS = {0: GREEN, 1: AMBER, 2: RED}
STATUS_TO_SEVERITY = {GREEN: 0, AMBER: 1, RED: 2}
INDEX_BY_STATUS = {GREEN: 100, AMBER: 60, RED: 25}
EPSILON = 1e-6
# Numerical-stability guard only: it is not a physiological threshold.
MIN_NUMERICAL_SD = 0.01
MIN_REFERENCE_LOAD_AU = 1.0

HRV_GREEN_MIN_Z, HRV_AMBER_MIN_Z = -0.5, -1.0
RHR_GREEN_MAX_Z, RHR_AMBER_MAX_Z = 0.5, 1.0
SLEEP_GREEN_RATIO, SLEEP_AMBER_RATIO = 0.90, 0.80
SLEEP_QUALITY_GREEN_MIN, SLEEP_QUALITY_AMBER_MIN = 4, 3
SUBJECTIVE_GREEN_MAX, SUBJECTIVE_AMBER_MAX = 0.33, 0.66
BASELINE_NORMAL_DAYS, BASELINE_LIMITED_DAYS = 28, 14
LOAD_RECENT_DAYS, LOAD_REFERENCE_DAYS = 7, 21
LOAD_HISTORY_DAYS = LOAD_RECENT_DAYS + LOAD_REFERENCE_DAYS
LOAD_GREEN_MAX_Z, LOAD_AMBER_MAX_Z = 0.5, 1.0
LOAD_GREEN_MAX_CHANGE, LOAD_AMBER_MAX_CHANGE = 0.10, 0.25
HEURISTIC_VERSION = "V2.1"

SAFETY_FLAGS = (
    "Chest pain", "Fainting / near fainting", "Fever / acute illness",
    "Acute injury preventing normal training", "Unusual shortness of breath",
)

# Science & Logic reads this object directly so documented thresholds and the
# executable engine cannot silently drift apart.
READINESS_RULE_METADATA = {
    "heuristic_version": HEURISTIC_VERSION,
    "baseline": {"normal_valid_observations": BASELINE_NORMAL_DAYS, "limited_valid_observations": BASELINE_LIMITED_DAYS, "transform": "LnRMSSD = ln(RMSSD)", "comparison": "z = (today - personal mean) / personal SD"},
    "thresholds": {
        "hrv_z": {GREEN: f">= {HRV_GREEN_MIN_Z}", AMBER: f"{HRV_AMBER_MIN_Z} to < {HRV_GREEN_MIN_Z}", RED: f"< {HRV_AMBER_MIN_Z}"},
        "rhr_z": {GREEN: f"<= {RHR_GREEN_MAX_Z}", AMBER: f"> {RHR_GREEN_MAX_Z} to <= {RHR_AMBER_MAX_Z}", RED: f"> {RHR_AMBER_MAX_Z}"},
        "sleep_ratio": {GREEN: f">= {SLEEP_GREEN_RATIO}", AMBER: f"{SLEEP_AMBER_RATIO} to < {SLEEP_GREEN_RATIO}", RED: f"< {SLEEP_AMBER_RATIO}"},
        "sleep_quality": {GREEN: f">= {SLEEP_QUALITY_GREEN_MIN}", AMBER: f">= {SLEEP_QUALITY_AMBER_MIN} and < {SLEEP_QUALITY_GREEN_MIN}", RED: f"< {SLEEP_QUALITY_AMBER_MIN}"},
        "subjective_badness": {GREEN: f"< {SUBJECTIVE_GREEN_MAX}", AMBER: f"{SUBJECTIVE_GREEN_MAX} to < {SUBJECTIVE_AMBER_MAX}", RED: f">= {SUBJECTIVE_AMBER_MAX}"},
    },
    "overall_rule": [
        "STOP when a listed safety concern is selected.",
        "INSUFFICIENT DATA when fewer than three domains are classifiable.",
        "RED when at least two domains are Red, or one is Red and at least two are Amber.",
        "AMBER when one domain is Red, or at least two domains are Amber.",
        "GREEN otherwise.",
    ],
    "readiness_index": dict(INDEX_BY_STATUS),
    "training_load": {"recent_days": LOAD_RECENT_DAYS, "reference_days": LOAD_REFERENCE_DAYS, "window_basis": "calendar days", "recent_window": "assessment date - 7 days through assessment date - 1 day", "reference_window": "assessment date - 28 days through assessment date - 8 days", "daily_aggregation": "sum all completed session loads by profile and calendar date; a covered date with no completed session contributes 0 AU", "full_coverage_days": LOAD_HISTORY_DAYS, "limited_coverage_days": BASELINE_LIMITED_DAYS, "minimum_reference_load_au": MIN_REFERENCE_LOAD_AU, "z_green_max": LOAD_GREEN_MAX_Z, "z_amber_max": LOAD_AMBER_MAX_Z, "flat_baseline_change_green_max": LOAD_GREEN_MAX_CHANGE, "flat_baseline_change_amber_max": LOAD_AMBER_MAX_CHANGE},
    "labels": {"thresholds": "PROTOTYPE HEURISTIC", "clinical": "NOT A CLINICAL THRESHOLD"},
}


def session_load(duration_min: float | int | None, rpe: float | int | None) -> float | None:
    if duration_min is None or rpe is None:
        return None
    return round(float(duration_min) * float(rpe), 2)


def ln_rmssd(rmssd_ms: float | int | None) -> float | None:
    if rmssd_ms is None or float(rmssd_ms) <= 0:
        return None
    return math.log(float(rmssd_ms))


def mean_sd(values: Iterable[float | int | None]) -> tuple[float | None, float | None, int]:
    cleaned = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return (None, None, 0) if not cleaned else (mean(cleaned), pstdev(cleaned) if len(cleaned) > 1 else 0.0, len(cleaned))


def safe_z(value: float | None, baseline_mean: float | None, baseline_sd: float | None) -> float | None:
    """Return None for flat/nearly-flat baselines instead of pseudo-precise z scores."""
    if value is None or baseline_mean is None or baseline_sd is None:
        return None
    if not all(math.isfinite(float(v)) for v in (value, baseline_mean, baseline_sd)):
        return None
    if abs(float(baseline_sd)) <= MIN_NUMERICAL_SD:
        return None
    return (float(value) - float(baseline_mean)) / float(baseline_sd)


def hrv_status(z_score: float | None) -> str:
    if z_score is None: return INSUFFICIENT
    return GREEN if z_score >= HRV_GREEN_MIN_Z else AMBER if z_score >= HRV_AMBER_MIN_Z else RED


def rhr_status(z_score: float | None) -> str:
    if z_score is None: return INSUFFICIENT
    return GREEN if z_score <= RHR_GREEN_MAX_Z else AMBER if z_score <= RHR_AMBER_MAX_Z else RED


def sleep_duration_status(sleep_hours: float | None, personal_sleep_need: float) -> tuple[str, float | None]:
    if sleep_hours is None or personal_sleep_need <= 0: return INSUFFICIENT, None
    ratio = float(sleep_hours) / float(personal_sleep_need)
    return (GREEN if ratio >= SLEEP_GREEN_RATIO else AMBER if ratio >= SLEEP_AMBER_RATIO else RED), ratio


def sleep_quality_status(quality: float | int | None) -> str:
    if quality is None: return INSUFFICIENT
    return GREEN if float(quality) >= SLEEP_QUALITY_GREEN_MIN else AMBER if float(quality) >= SLEEP_QUALITY_AMBER_MIN else RED


def subjective_item_badness(row: Mapping[str, Any]) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for field, transform in (("fatigue", lambda x: (x - 1) / 4), ("soreness", lambda x: (x - 1) / 4), ("stress", lambda x: (x - 1) / 4), ("motivation", lambda x: (5 - x) / 4)):
        try: values[field] = transform(float(row[field])) if row.get(field) is not None else None
        except (TypeError, ValueError): values[field] = None
    return values


def subjective_badness(row: Mapping[str, Any]) -> float | None:
    values = subjective_item_badness(row)
    return None if any(v is None for v in values.values()) else mean(v for v in values.values() if v is not None)


def subjective_status(badness: float | None) -> str:
    if badness is None: return INSUFFICIENT
    return GREEN if badness < SUBJECTIVE_GREEN_MAX else AMBER if badness < SUBJECTIVE_AMBER_MAX else RED


def baseline_confidence(history: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    valid = sum(1 for r in history if ln_rmssd(r.get("rmssd_ms")) is not None and r.get("resting_hr_bpm") is not None)
    return ("NORMAL" if valid >= BASELINE_NORMAL_DAYS else "LIMITED" if valid >= BASELINE_LIMITED_DAYS else "INSUFFICIENT"), valid


def _as_date(row: Mapping[str, Any]) -> date:
    value = row.get("date")
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _sorted(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(r) for r in sorted(rows, key=_as_date)]


def _baseline(past: list[dict[str, Any]]) -> dict[str, Any]:
    window = past[-BASELINE_NORMAL_DAYS:]
    ln_mean, ln_sd, ln_count = mean_sd(ln_rmssd(r.get("rmssd_ms")) for r in window)
    rhr_mean, rhr_sd, rhr_count = mean_sd(r.get("resting_hr_bpm") for r in window)
    sleep_mean, _, sleep_count = mean_sd(r.get("sleep_hours") for r in window)
    return {"valid_days": min(ln_count, rhr_count), "lnrmssd_mean": ln_mean, "lnrmssd_sd": ln_sd, "rhr_mean": rhr_mean, "rhr_sd": rhr_sd, "sleep_mean": sleep_mean, "sleep_valid_days": sleep_count, "window_days": len(window)}


def _domain_from_statuses(*statuses: str) -> str:
    known = [STATUS_TO_SEVERITY[s] for s in statuses if s in STATUS_TO_SEVERITY]
    return INSUFFICIENT if not known else SEVERITY_TO_STATUS[max(known)]


def training_load_domain(completed_rows: list[dict[str, Any]], assessment_date: date | None = None) -> dict[str, Any]:
    """Compare fixed calendar windows without treating untracked dates as rest.

    A dated row establishes tracking coverage for that calendar date. Within a
    fully covered window, a date with no completed-session load is a rest day
    (0 AU). Missing dates remain unknown and prevent a full comparison.
    """
    anchor = assessment_date or date.today()
    window_start = anchor - timedelta(days=LOAD_HISTORY_DAYS)
    recent_start = anchor - timedelta(days=LOAD_RECENT_DAYS)
    window_end = anchor - timedelta(days=1)
    daily_totals: dict[date, float] = {}
    covered_dates: set[date] = set()
    valid_load_observations = 0
    for row in completed_rows:
        try:
            day = _as_date(row)
        except (TypeError, ValueError):
            continue
        if not window_start <= day <= window_end:
            continue
        covered_dates.add(day)
        if row.get("completed", True) is False or row.get("session_load") is None:
            continue
        try:
            load = float(row["session_load"])
        except (TypeError, ValueError):
            continue
        if math.isfinite(load) and load >= 0:
            daily_totals[day] = daily_totals.get(day, 0.0) + load
            valid_load_observations += 1

    coverage_days = len(covered_dates)
    sufficiency = "FULL" if coverage_days == LOAD_HISTORY_DAYS else "LIMITED" if coverage_days >= BASELINE_LIMITED_DAYS else "INSUFFICIENT"
    base = {
        "recent_window_start": recent_start.isoformat(), "recent_window_end": window_end.isoformat(),
        "reference_window_start": window_start.isoformat(), "reference_window_end": (recent_start - timedelta(days=1)).isoformat(),
        "calendar_days_covered": coverage_days, "calendar_days_required": LOAD_HISTORY_DAYS,
        "data_sufficiency": sufficiency, "completed_observations": valid_load_observations,
    }
    if sufficiency != "FULL":
        return {**base, "status": INSUFFICIENT, "recent_7d_mean": None, "reference_21d_mean": None, "reference_21d_sd": None, "z_score": None, "load_change": None, "daily_loads": None, "detail": f"Insufficient calendar coverage ({coverage_days}/{LOAD_HISTORY_DAYS} complete dates tracked; missing dates remain unknown rather than being treated as rest)."}

    days = [window_start + timedelta(days=offset) for offset in range(LOAD_HISTORY_DAYS)]
    loads_by_day = {day: daily_totals.get(day, 0.0) for day in days}
    reference = [loads_by_day[day] for day in days[:LOAD_REFERENCE_DAYS]]
    recent = [loads_by_day[day] for day in days[LOAD_REFERENCE_DAYS:]]
    recent_mean = mean(recent)
    ref_mean, ref_sd, _ = mean_sd(reference)
    assert ref_mean is not None and ref_sd is not None
    z_score = load_change = None
    if ref_mean < MIN_REFERENCE_LOAD_AU:
        status = INSUFFICIENT
        detail = "Reference daily load is near zero, so a stable relative comparison is not reported."
    elif ref_sd > MIN_NUMERICAL_SD:
        z_score = (recent_mean - ref_mean) / ref_sd
        status = GREEN if z_score <= LOAD_GREEN_MAX_Z else AMBER if z_score <= LOAD_AMBER_MAX_Z else RED
        detail = "Mean daily load across the last 7 complete calendar days compared with the preceding 21 complete calendar days."
    else:
        load_change = (recent_mean - ref_mean) / ref_mean
        status = GREEN if load_change <= LOAD_GREEN_MAX_CHANGE else AMBER if load_change <= LOAD_AMBER_MAX_CHANGE else RED
        detail = "Calendar-based 7-day versus preceding 21-day daily-load comparison using the low-variance percentage fallback."
    return {**base, "status": status, "recent_7d_mean": round(recent_mean, 1), "reference_21d_mean": round(ref_mean, 1), "reference_21d_sd": round(ref_sd, 1), "z_score": round(z_score, 2) if z_score is not None else None, "load_change": round(load_change, 3) if load_change is not None else None, "daily_loads": {day.isoformat(): round(value, 1) for day, value in loads_by_day.items()}, "detail": detail}


def overall_status(domain_statuses: Mapping[str, str], safety_flags: Iterable[str]) -> str:
    if any(flag in SAFETY_FLAGS for flag in safety_flags): return STOP
    known = [s for s in domain_statuses.values() if s in STATUS_TO_SEVERITY]
    if len(known) < 3: return INSUFFICIENT
    red, amber = known.count(RED), known.count(AMBER)
    return RED if red >= 2 or (red == 1 and amber >= 2) else AMBER if red == 1 or amber >= 2 else GREEN


def autonomic_context(hrv_z: float | None, rhr_z: float | None) -> tuple[str, str]:
    hrv_low = hrv_z is not None and hrv_z < HRV_GREEN_MIN_Z
    rhr_high = rhr_z is not None and rhr_z > RHR_GREEN_MAX_Z
    rhr_low = rhr_z is not None and rhr_z < -RHR_GREEN_MAX_Z
    if hrv_low and rhr_high: return "CONCORDANT_UNFAVOURABLE", "HRV is below baseline while resting HR is above baseline. These two autonomic signals move in the same unfavourable direction and should be considered alongside sleep, training load and subjective wellness."
    if hrv_low and rhr_low: return "MIXED_LOW", "HRV and resting HR are both below baseline. This mixed autonomic pattern should be interpreted with training context and the other readiness domains."
    if hrv_low: return "ISOLATED_HRV_DEVIATION", "HRV is below baseline, while resting HR remains within its usual range."
    if hrv_z is not None and rhr_z is not None: return "BROADLY_USUAL", "Autonomic measures are broadly within your usual range."
    return "INCOMPLETE", "Autonomic context is incomplete because a stable standardized deviation estimate is not available for both signals."


def assessment_confidence(baseline_days: int, domains: Mapping[str, str], load: Mapping[str, Any], measures: Mapping[str, Any]) -> str:
    available = sum(s in STATUS_TO_SEVERITY for s in domains.values())
    important_missing = measures["hrv"]["status"] == INSUFFICIENT or measures["rhr"]["status"] == INSUFFICIENT or measures["sleep_duration"]["status"] == INSUFFICIENT or measures["sleep_quality"]["status"] == INSUFFICIENT or measures["subjective_badness"] is None
    if baseline_days < BASELINE_LIMITED_DAYS or available < 3: return "INSUFFICIENT"
    if baseline_days < BASELINE_NORMAL_DAYS or available < 4 or load["status"] == INSUFFICIENT or important_missing: return "LIMITED"
    return "NORMAL"


def _contributors(today: Mapping[str, Any], measurements: Mapping[str, Any], item_statuses: Mapping[str, str]) -> list[str]:
    items: list[str] = []
    hrv = measurements["hrv"]
    if hrv["status"] in {AMBER, RED} and hrv["z_score"] is not None: items.append(f"LnRMSSD is {abs(hrv['z_score']):.1f} SD below your personal baseline")
    if measurements["rhr"]["status"] in {AMBER, RED}: items.append("Resting heart rate is above your personal baseline")
    if measurements["sleep_duration"]["status"] in {AMBER, RED}: items.append("Sleep duration is below your personal sleep need")
    if measurements["sleep_quality"]["status"] in {AMBER, RED}: items.append("Sleep quality is lower than usual recovery support")
    labels = {"fatigue": "High self-reported fatigue", "soreness": "High self-reported soreness", "stress": "High self-reported stress", "motivation": "Low motivation"}
    items.extend(labels[k] for k, status in item_statuses.items() if status == RED)
    if measurements["training_load"]["status"] in {AMBER, RED}: items.append("Recent completed training load is elevated relative to your own history")
    return items[:5]


def build_status_explanation(overall: str, autonomic: str, contributors: list[str], domains: Mapping[str, str], confidence: str) -> list[str]:
    if overall == STOP: return ["Safety mode is active because a current safety concern was selected. The normal readiness recommendation has been overridden."]
    if overall == INSUFFICIENT: return ["There is not enough current and historical information for a complete readiness decision. Continue collecting morning signals and completed-session load data."]
    drivers = "; ".join(contributors[:2]) if contributors else "no material adverse contributors were detected"
    stable = [name.replace("_", " ") for name, status in domains.items() if status == GREEN]
    tail = f" Stable areas: {', '.join(stable[:2])}." if stable else ""
    return [f"Your readiness is {overall.title()} today. Main context: {drivers}.{tail}", autonomic, f"Assessment confidence is {confidence}; it describes data availability and baseline quality, not physiological certainty."]


def decision_support(status: str) -> list[str]:
    if status == STOP: return ["Pause demanding training and do not use this tool as a substitute for symptom assessment.", "Acute or concerning symptoms should be assessed by an appropriate healthcare professional."]
    if status == RED: return ["Avoid maximal or unnecessary high-intensity training today.", "Prioritise recovery and consider discussing training modification with a coach or qualified professional.", "Reassess readiness before demanding training."]
    if status == AMBER: return ["Consider reducing training volume and/or intensity.", "Avoid unnecessary additional high-intensity work.", "Prioritise sleep, hydration and recovery; reassess if symptoms worsen."]
    if status == GREEN: return ["Planned training can generally proceed, subject to your warm-up response and context.", "Maintain normal recovery habits and continue monitoring your trends."]
    return ["There is not yet enough longitudinal data for a complete readiness decision.", "Continue collecting check-ins to build an individual baseline and use training judgement conservatively."]


def _trend_summary(past: list[dict[str, Any]], today: Mapping[str, Any], baseline: Mapping[str, Any], load: Mapping[str, Any], readiness_history: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    recent = past[-7:]
    ln_today = ln_rmssd(today.get("rmssd_ms"))
    ln7, _, _ = mean_sd(ln_rmssd(r.get("rmssd_ms")) for r in recent)
    rhr7, _, _ = mean_sd(r.get("resting_hr_bpm") for r in recent)
    sleep7, _, _ = mean_sd(r.get("sleep_hours") for r in recent)
    readiness = [r.get("overall_readiness") for r in list(readiness_history)[-7:] if r.get("overall_readiness")]
    return {"lnrmssd_today": round(ln_today, 3) if ln_today is not None else None, "lnrmssd_7d_mean": round(ln7, 3) if ln7 is not None else None, "lnrmssd_baseline": baseline["lnrmssd_mean"], "rhr_today": today.get("resting_hr_bpm"), "rhr_7d_mean": round(rhr7, 1) if rhr7 is not None else None, "rhr_baseline": baseline["rhr_mean"], "sleep_today": today.get("sleep_hours"), "sleep_7d_mean": round(sleep7, 1) if sleep7 is not None else None, "sleep_target": today.get("personal_sleep_need"), "training_load_recent_7d": load["recent_7d_mean"], "training_load_reference": load["reference_21d_mean"], "readiness_last_7d": readiness}


def assess_readiness(today_data: Mapping[str, Any], history: Iterable[Mapping[str, Any]], personal_sleep_need: float = 8.0, readiness_history: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Assess morning data against history of sessions completed before today."""
    today = dict(today_data); today["date"] = str(today.get("date") or date.today().isoformat()); today["personal_sleep_need"] = personal_sleep_need
    # Never manufacture a same-day planned-session load for a morning readiness decision.
    today["session_load"] = None
    all_history = _sorted(history); assessment_date = _as_date(today)
    past = [row for row in all_history if _as_date(row) < assessment_date]
    baseline = _baseline(past); _, valid_days = baseline_confidence(past); baseline["valid_days"] = valid_days
    ln_today = ln_rmssd(today.get("rmssd_ms")); hrv_z = safe_z(ln_today, baseline["lnrmssd_mean"], baseline["lnrmssd_sd"]); rhr_z = safe_z(today.get("resting_hr_bpm"), baseline["rhr_mean"], baseline["rhr_sd"])
    hrv_measure = {"value": ln_today, "z_score": round(hrv_z, 2) if hrv_z is not None else None, "status": hrv_status(hrv_z), "variability_guard": hrv_z is None and baseline["lnrmssd_sd"] is not None}
    rhr_measure = {"value": today.get("resting_hr_bpm"), "z_score": round(rhr_z, 2) if rhr_z is not None else None, "status": rhr_status(rhr_z), "variability_guard": rhr_z is None and baseline["rhr_sd"] is not None}
    duration_status, ratio = sleep_duration_status(today.get("sleep_hours"), personal_sleep_need); quality_status = sleep_quality_status(today.get("sleep_quality"))
    item_badness = subjective_item_badness(today); item_statuses = {key: subjective_status(value) for key, value in item_badness.items()}; composite = subjective_badness(today); composite_status = subjective_status(composite)
    subjective_domain = AMBER if composite_status == GREEN and any(v == RED for v in item_statuses.values()) else composite_status
    load = training_load_domain(past, assessment_date)
    domains = {"autonomic": _domain_from_statuses(hrv_measure["status"], rhr_measure["status"]), "sleep": _domain_from_statuses(duration_status, quality_status), "subjective": subjective_domain, "training_load": load["status"]}
    flags = [f for f in today.get("safety_flags", []) if f in SAFETY_FLAGS]
    available = sum(v in STATUS_TO_SEVERITY for v in domains.values())
    overall = overall_status(domains, flags); confidence = assessment_confidence(valid_days, domains, load, {"hrv": hrv_measure, "rhr": rhr_measure, "sleep_duration": {"status": duration_status}, "sleep_quality": {"status": quality_status}, "subjective_badness": composite})
    baseline["confidence"] = confidence
    pattern, interpretation = autonomic_context(hrv_z, rhr_z)
    measurements = {"hrv": hrv_measure, "rhr": rhr_measure, "sleep_duration": {"status": duration_status, "ratio": round(ratio, 2) if ratio is not None else None}, "sleep_quality": {"status": quality_status}, "subjective_badness": round(composite, 2) if composite is not None else None, "subjective_item_badness": item_badness, "subjective_item_statuses": item_statuses, "training_load": load}
    contributors = _contributors(today, measurements, item_statuses)
    return {"assessment_version": "V2.1", "heuristic_version": HEURISTIC_VERSION, "assessment_date": today["date"], "today_data": today, "baseline": baseline, "measurements": measurements, "domains": domains, "overall_readiness": overall, "available_domain_count": available, "data_sufficiency": "SUFFICIENT" if available >= 3 else INSUFFICIENT, "readiness_index": round(mean(INDEX_BY_STATUS[s] for s in domains.values() if s in INDEX_BY_STATUS)) if available >= 3 else None, "assessment_confidence": confidence, "autonomic_pattern": pattern, "autonomic_interpretation": interpretation, "subjective_item_statuses": item_statuses, "individual_red_flags": [k for k, v in item_statuses.items() if v == RED], "key_contributors": contributors, "why_this_status": build_status_explanation(overall, interpretation, contributors, domains, confidence), "decision_support": decision_support(overall), "safety_flags": flags, "trend_summary": _trend_summary(past, today, baseline, load, readiness_history), "limitations": ["Scientifically informed, individual-baseline-driven, explainable readiness decision-support prototype; not a medical diagnostic or fatigue/injury prediction system.", "Specific thresholds, aggregation, index, confidence and time windows are transparent prototype heuristics and have not been prospectively validated."]}
