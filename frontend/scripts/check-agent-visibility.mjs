/**
 * Agent visibility checks.
 *
 * Run with `pnpm check:agent`. Node 24 imports the TypeScript module directly via
 * type stripping, so no build step and no new dependency are needed.
 *
 * These checks cover the adapter and the copy rules that decide what the Coach
 * may claim: which execution surface an answer earns, how many sources it says
 * were checked, how an unknown source degrades, and that no reasoning surface is
 * ever rendered. Visual rendering at both viewports is covered by the browser QA
 * record in docs/V1_4_2_AGENT_VISIBILITY_EVIDENCE.md.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  DETERMINISTIC_AUTHORITY_LINE,
  UNKNOWN_SOURCE_DESCRIPTION,
  deriveAgentRun,
  sourceDescription,
  sourceLabel,
} from "../lib/agent-sources.ts";

const results = [];
function check(label, run) {
  try {
    run();
    results.push([label, true]);
    console.log(`PASS | ${label}`);
  } catch (error) {
    results.push([label, false]);
    console.log(`FAIL | ${label} | ${error.message}`);
  }
}

const trace = (tool) => ({ tool, label: "" });
const agentTrace = [
  trace("get_readiness"),
  trace("get_current_recommendation"),
  trace("get_recent_training"),
  trace("get_personal_response"),
  trace("get_decision_trace"),
  trace("get_recommendation_confidence"),
];

check("an AI explanation with grounded=true earns AGENT RUN · GROUNDED", () => {
  const run = deriveAgentRun({ kind: "ai_explanation", grounded: true, toolTrace: agentTrace });
  assert.equal(run.mode, "agent");
  assert.equal(run.pill, "AGENT RUN · GROUNDED");
  assert.equal(run.grounded, true);
});

check("the grounded badge uses the actual grounded field", () => {
  const run = deriveAgentRun({ kind: "ai_explanation", grounded: false, toolTrace: agentTrace });
  assert.equal(run.pill, "AGENT RUN");
  assert.equal(run.grounded, false);
});

check("the source count comes from the actual tool trace", () => {
  assert.equal(deriveAgentRun({ kind: "ai_explanation", grounded: true, toolTrace: agentTrace }).headline,
    "Checked 6 verified sources");
  assert.equal(deriveAgentRun({ kind: "verified_data", grounded: true, toolTrace: [trace("get_readiness")] }).headline,
    "Checked 1 verified source");
});

check("source labels map to consumer language", () => {
  assert.equal(sourceLabel("get_readiness"), "Readiness");
  assert.equal(sourceLabel("get_current_recommendation"), "Today's Session");
  assert.equal(sourceLabel("run_decision_explorer"), "Decision Explorer");
  assert.equal(sourceLabel("get_session_calibration_context"), "In-session Calibration");
  assert.equal(sourceLabel("get_training_exposure"), "Weekly Exposure");
});

check("Decision Explorer appears when it was actually used", () => {
  const run = deriveAgentRun({
    kind: "ai_explanation",
    grounded: true,
    toolTrace: [trace("get_current_recommendation"), trace("run_decision_explorer")],
  });
  assert.deepEqual(run.sources.map((source) => source.label), ["Today's Session", "Decision Explorer"]);
  assert.equal(run.sources[1].description, "Compared a verified what-if scenario");
});

check("In-session Calibration appears when it was actually used", () => {
  const run = deriveAgentRun({
    kind: "ai_explanation",
    grounded: true,
    toolTrace: [trace("get_session_calibration_context")],
  });
  assert.equal(run.sources[0].label, "In-session Calibration");
  assert.equal(run.sources[0].description, "Checked current session adjustment guidance");
});

check("a deterministic fast-path fact is never labelled as an Agent run", () => {
  const run = deriveAgentRun({ kind: "verified_data", grounded: true, toolTrace: [trace("get_readiness")] });
  assert.equal(run.mode, "recorded");
  assert.equal(run.pill, "RECORDED DATA");
  assert.ok(!run.pill.includes("AGENT RUN"));
});

check("the rule-based fallback is labelled truthfully", () => {
  const run = deriveAgentRun({ kind: "deterministic_fallback", grounded: true, toolTrace: [trace("get_readiness")] });
  assert.equal(run.mode, "rule_based");
  assert.equal(run.pill, "RULE-BASED ANSWER");
});

check("an answer with no verified source renders nothing", () => {
  assert.equal(deriveAgentRun({ kind: "ai_explanation", grounded: true, toolTrace: [] }), null);
  assert.equal(deriveAgentRun({ kind: "verified_data", grounded: true }), null);
});

check("tools_used is used when a trace is unavailable, and duplicates collapse", () => {
  const run = deriveAgentRun({
    kind: "ai_explanation",
    grounded: true,
    toolsUsed: ["get_readiness", "get_readiness", "get_training_load"],
  });
  assert.deepEqual(run.sources.map((source) => source.label), ["Readiness", "Training Load"]);
});

check("an unknown tool degrades gracefully instead of inventing a source", () => {
  assert.equal(sourceLabel("future_tool", "Future capability"), "Future capability");
  assert.equal(sourceLabel("future_tool"), "Verified source");
  assert.equal(sourceDescription("future_tool"), UNKNOWN_SOURCE_DESCRIPTION);
  const run = deriveAgentRun({ kind: "ai_explanation", grounded: true, toolTrace: [{ tool: "future_tool" }] });
  assert.equal(run.sources[0].label, "Verified source");
});

check("every mapped source carries a description", () => {
  for (const tool of ["get_readiness", "get_current_recommendation", "get_recent_training", "get_training_exposure",
    "get_personal_response", "get_recommendation_confidence", "get_decision_trace", "run_decision_explorer",
    "get_session_calibration_context", "get_training_load", "get_personal_context"]) {
    assert.ok(sourceDescription(tool).length > 10, tool);
  }
});

check("labels never expose raw backend tool names", () => {
  const run = deriveAgentRun({ kind: "ai_explanation", grounded: true, toolTrace: agentTrace });
  for (const source of run.sources) {
    assert.ok(!source.label.startsWith("get_"), source.label);
    assert.ok(!source.label.includes("_"), source.label);
  }
});

check("the deterministic authority line uses the approved wording", () => {
  assert.equal(DETERMINISTIC_AUTHORITY_LINE, "AI orchestrates verified tools. Training decisions remain deterministic.");
});

check("the Agent Run component renders no reasoning surface", () => {
  // Comments may explain the rule; only rendered code and copy are scanned.
  const component = readFileSync(new URL("../components/agent-run-summary.tsx", import.meta.url), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  for (const forbidden of ["chain-of-thought", "chain of thought", "system prompt", "planner output", "JSON.stringify",
    "Calling tool", "Reasoning…"]) {
    assert.ok(!component.includes(forbidden), forbidden);
  }
  assert.ok(component.includes("DETERMINISTIC_AUTHORITY_LINE"));
  assert.ok(component.includes("How this answer was built"));
});

check("the Coach loading state stays truthful", () => {
  const view = readFileSync(new URL("../features/coach/coach-view.tsx", import.meta.url), "utf8");
  assert.ok(view.includes("Agent is checking verified training context"));
  for (const fake of ["Calling tool", "Planning...", "Planning…", "Comparing", "Reasoning...", "Reasoning…",
    "Readiness checked", "Thinking"]) {
    assert.ok(!view.includes(fake), fake);
  }
});

check("the Coach identity names the tool-using Agent", () => {
  const view = readFileSync(new URL("../features/coach/coach-view.tsx", import.meta.url), "utf8");
  assert.ok(view.includes("Tool-Using Training Agent"));
  assert.ok(view.includes("Plans what to check, uses verified training tools, then explains the result."));
});

const failed = results.filter(([, ok]) => !ok);
console.log(`\n${results.length - failed.length}/${results.length} agent visibility checks passed`);
if (failed.length > 0) process.exitCode = 1;
