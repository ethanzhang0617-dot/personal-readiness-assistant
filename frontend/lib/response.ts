/**
 * Personal Response vocabulary shared by the UI (labels, demo cases, feedback
 * options). The rules themselves live in the backend layer; this file only names
 * what the product shows.
 */

export const RESPONSE_DEMO_CASES = [
  "insufficient",
  "emerging",
  "poor_high_tolerance",
  "established_good",
] as const;

export type ResponseDemoCase = (typeof RESPONSE_DEMO_CASES)[number];

export const RESPONSE_DEMO_LABELS: Record<ResponseDemoCase, string> = {
  insufficient: "Not enough history yet",
  emerging: "Emerging pattern",
  poor_high_tolerance: "Poor tolerance to high demand (shows an adjustment)",
  established_good: "Established good tolerance",
};

export const COMPLETION_OPTIONS = ["Completed", "Modified", "Stopped early"] as const;
export type CompletionOption = (typeof COMPLETION_OPTIONS)[number];

export const DIFFICULTY_SCALE = [
  { value: 1, label: "1", hint: "Easy" },
  { value: 2, label: "2" },
  { value: 3, label: "3" },
  { value: 4, label: "4" },
  { value: 5, label: "5", hint: "Maximal" },
];

export const PERFORMANCE_SCALE = [
  { value: 1, label: "1", hint: "Poor" },
  { value: 2, label: "2" },
  { value: 3, label: "3" },
  { value: 4, label: "4" },
  { value: 5, label: "5", hint: "Strong" },
];

/** Restrained wording for the evidence states (never a percentage or a model score). */
export const EVIDENCE_LABELS: Record<string, string> = {
  Insufficient: "Not enough history yet",
  Emerging: "Emerging pattern",
  Established: "Established pattern",
};
