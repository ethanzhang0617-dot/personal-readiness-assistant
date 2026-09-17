/**
 * In-session calibration vocabulary shared by the UI. The rule itself lives in
 * the backend (`session_calibration.py`); this file only names what the product
 * shows. Calibration never raises the session demand, the focus or the volume.
 */

export const EFFORT_OPTIONS = ["Easier than expected", "As expected", "Harder than expected"] as const;
export type EffortOption = (typeof EFFORT_OPTIONS)[number];

export const PERFORMANCE_OPTIONS = ["Better than expected", "As expected", "Worse than expected"] as const;
export type PerformanceOption = (typeof PERFORMANCE_OPTIONS)[number];

/** Reported reps in reserve: 0 = to failure. */
export const RIR_OPTIONS = [0, 1, 2, 3, 4, 5] as const;

export const CALIBRATION_RESULTS = ["HOLD", "EASE", "OPTIONAL PUSH"] as const;
export type CalibrationResult = (typeof CALIBRATION_RESULTS)[number];

/** Plain product wording — never "AI adjusted", never a physiological claim. */
export const CALIBRATION_LABELS: Record<string, string> = {
  HOLD: "Hold the plan",
  EASE: "Ease off slightly",
  "OPTIONAL PUSH": "Optional push",
};

export const CALIBRATION_HINTS: Record<string, string> = {
  HOLD: "Your checkpoint matched the plan, so nothing changes.",
  EASE: "Make the remainder of this session slightly more conservative.",
  "OPTIONAL PUSH": "Optional: the harder end of the range you already have.",
};

/** Result tone: amber for ease (caution), green for an optional push, neutral for hold. */
export function calibrationTone(result?: string | null): string {
  if (result === "EASE") return "bg-[var(--status-amber-soft)] text-[var(--status-amber)]";
  if (result === "OPTIONAL PUSH") return "bg-[var(--status-green-soft)] text-[var(--status-green)]";
  return "bg-surface-muted text-muted";
}

export function calibrationLabel(result?: string | null): string {
  return CALIBRATION_LABELS[String(result)] ?? "Not recorded";
}
