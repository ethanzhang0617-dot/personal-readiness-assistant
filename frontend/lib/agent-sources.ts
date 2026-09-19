/**
 * Agent visibility adapter.
 *
 * The Coach API already returns what actually happened: `tools_used`,
 * `tool_trace`, `grounded` and the answer `kind`. This module turns that into
 * consumer language and decides which execution surface an answer earns:
 *
 * * `agent`      — the tool-using Agent ran and the provider wrote the wording
 * * `recorded`   — a deterministic personal fact answered straight from the
 *                  user's recorded data (no Agent planning)
 * * `rule_based` — the deterministic rule answer shown when the provider was
 *                  unavailable or a draft was rejected
 *
 * It never invents execution. No source is listed unless the backend reported
 * it for this answer, and no reasoning, prompt or planner output is exposed.
 */

import type { CoachKind } from "@/types/api";

export type AgentRunMode = "agent" | "recorded" | "rule_based";

export interface AgentSource {
  tool: string;
  label: string;
  description: string;
}

export interface AgentRun {
  mode: AgentRunMode;
  /** Status pill, e.g. "AGENT RUN · GROUNDED". */
  pill: string;
  /** Headline, e.g. "Checked 6 verified sources". */
  headline: string;
  grounded: boolean;
  sources: AgentSource[];
}

/** The shape the Coach response and the stored chat message both provide. */
export interface ToolTraceLike {
  tool: string;
  label?: string | null;
}

/** Consumer labels and one-line explanations, keyed by the product tool name. */
const SOURCE_COPY: Record<string, { label: string; description: string }> = {
  get_readiness: { label: "Readiness", description: "Checked today's readiness state" },
  get_current_recommendation: { label: "Today's Session", description: "Verified the current training recommendation" },
  get_recent_training: { label: "Recent Training", description: "Reviewed completed sessions" },
  get_training_exposure: { label: "Weekly Exposure", description: "Checked recent training exposure" },
  get_personal_response: { label: "Personal Response", description: "Reviewed your recorded response pattern" },
  get_recommendation_confidence: {
    label: "Recommendation Confidence",
    description: "Checked the available personal evidence",
  },
  get_decision_trace: { label: "Decision Trace", description: "Verified the factors behind the recommendation" },
  run_decision_explorer: { label: "Decision Explorer", description: "Compared a verified what-if scenario" },
  get_session_calibration_context: {
    label: "In-session Calibration",
    description: "Checked current session adjustment guidance",
  },
  get_training_load: { label: "Training Load", description: "Reviewed recent training-load data" },
  get_personal_context: { label: "Profile Context", description: "Checked current goal and programme context" },
};

/** Fallback copy keeps an unknown source honest instead of hiding or inventing it. */
export const UNKNOWN_SOURCE_DESCRIPTION = "Checked verified training data";

export function sourceLabel(tool: string, fallbackLabel?: string | null): string {
  return SOURCE_COPY[tool]?.label ?? (fallbackLabel && fallbackLabel.trim()) ?? "Verified source";
}

export function sourceDescription(tool: string): string {
  return SOURCE_COPY[tool]?.description ?? UNKNOWN_SOURCE_DESCRIPTION;
}

export function toAgentSources(traces: ToolTraceLike[]): AgentSource[] {
  const seen = new Set<string>();
  const sources: AgentSource[] = [];
  for (const trace of traces) {
    const tool = String(trace?.tool ?? "");
    if (!tool || seen.has(tool)) continue;
    seen.add(tool);
    sources.push({ tool, label: sourceLabel(tool, trace?.label), description: sourceDescription(tool) });
  }
  return sources;
}

export interface AgentRunInput {
  kind?: CoachKind;
  grounded?: boolean;
  toolTrace?: ToolTraceLike[];
  toolsUsed?: string[];
}

function pillFor(mode: AgentRunMode, grounded: boolean): string {
  if (mode === "agent") return grounded ? "AGENT RUN · GROUNDED" : "AGENT RUN";
  if (mode === "recorded") return "RECORDED DATA";
  return "RULE-BASED ANSWER";
}

/**
 * Everything the summary shows comes from the response metadata for this answer.
 * Returns null when there is no verified source to report.
 */
export function deriveAgentRun(input: AgentRunInput): AgentRun | null {
  const traces = input.toolTrace ?? [];
  const fromTrace = toAgentSources(traces);
  const sources = fromTrace.length > 0
    ? fromTrace
    : toAgentSources((input.toolsUsed ?? []).map((tool) => ({ tool, label: "" })));
  if (sources.length === 0) return null;

  const mode: AgentRunMode = input.kind === "ai_explanation"
    ? "agent"
    : input.kind === "verified_data"
      ? "recorded"
      : "rule_based";
  const grounded = Boolean(input.grounded);
  return {
    mode,
    pill: pillFor(mode, grounded),
    headline: `Checked ${sources.length} verified source${sources.length === 1 ? "" : "s"}`,
    grounded,
    sources,
  };
}

/** The product principle shown at the foot of the expanded card. */
export const DETERMINISTIC_AUTHORITY_LINE =
  "AI orchestrates verified tools. Training decisions remain deterministic.";
