/**
 * Storage migration check for the browser-owned state.
 *
 * Run with `pnpm check:store` (also exercised by the release checklist). Node 24
 * imports the TypeScript module directly via type stripping, so this needs no
 * build step and adds no dependency.
 */

import assert from "node:assert/strict";

import { migrateEnvelope, STORAGE_VERSION } from "../lib/store-migration.ts";
import { RESPONSE_DEMO_CASES } from "../lib/response.ts";

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

const state = (profileId, sessions = []) => ({
  profile_id: profileId,
  scenario: "Moderate Fatigue Day",
  edits: { training_goal: "Muscle Gain" },
  check_in: { date: "2026-09-16", sleep_hours: 7.4 },
  daily_history: [{ date: "2026-09-16", sleep_hours: 7.4 }],
  training_history: sessions,
});

const v2 = {
  version: 2,
  updated_at: "2026-09-16T00:00:00.000Z",
  active_profile_id: "demo-alex",
  states: {
    "demo-ethan": state("demo-ethan", [{ session_id: "e1", date: "2026-09-14", duration_min: 55 }]),
    "demo-alex": state("demo-alex", [{ session_id: "a1", date: "2026-09-15", session_rpe: 7 }]),
  },
  chats: { "demo-alex": [{ id: "m1", role: "user", content: "hi" }] },
};

check("version constant is 3", () => assert.equal(STORAGE_VERSION, 3));

check("v2 → v3 keeps every profile, check-in, session and chat", () => {
  const result = migrateEnvelope(v2);
  assert.ok(result, "migration returned null");
  assert.equal(result.report.migrated, true);
  assert.equal(result.envelope.version, 3);
  assert.equal(result.envelope.active_profile_id, "demo-alex");
  assert.deepEqual(Object.keys(result.envelope.states).sort(), ["demo-alex", "demo-ethan"]);
  assert.equal(result.envelope.states["demo-ethan"].daily_history.length, 1);
  assert.equal(result.envelope.states["demo-ethan"].edits.training_goal, "Muscle Gain");
  assert.equal(result.envelope.states["demo-ethan"].check_in.sleep_hours, 7.4);
  assert.equal(result.envelope.states["demo-ethan"].training_history[0].duration_min, 55);
  assert.equal(result.envelope.states["demo-alex"].training_history[0].session_rpe, 7);
  assert.equal(result.envelope.chats["demo-alex"].length, 1);
});

check("v2 → v3 normalises session rows with the V1.3 response keys", () => {
  const result = migrateEnvelope(v2);
  for (const item of Object.values(result.envelope.states)) {
    for (const session of item.training_history) {
      assert.equal(session.response_context, null);
      assert.equal(session.response_feedback, null);
    }
  }
});

check("v2 → v3 keeps an existing response snapshot and feedback", () => {
  const withResponse = {
    ...v2,
    states: {
      "demo-ethan": state("demo-ethan", [{
        session_id: "e9", date: "2026-09-15",
        response_context: { base_session_demand: "Normal" },
        response_feedback: { difficulty: 4, performance: 2, completion: "Stopped early" },
      }]),
    },
  };
  const session = migrateEnvelope(withResponse).envelope.states["demo-ethan"].training_history[0];
  assert.equal(session.response_context.base_session_demand, "Normal");
  assert.equal(session.response_feedback.completion, "Stopped early");
});

check("v2 → v3 gives every profile an empty adaptation history", () => {
  const result = migrateEnvelope(v2);
  for (const item of Object.values(result.envelope.states)) {
    assert.deepEqual(item.adaptation_log, []);
  }
});

check("v2 → v3 keeps a recorded adaptation history", () => {
  const withLog = {
    ...v2,
    states: {
      "demo-ethan": {
        ...state("demo-ethan"),
        adaptation_log: [{
          date: "2026-09-15",
          base_demand: "Normal",
          base_band: "High",
          final_demand: "Reduced / autoregulated",
          final_band: "Moderate",
          adjustment: -1,
          result: "reduced",
          confidence: "Developing",
          evidence: "Emerging",
          relevant_episodes: 3,
          reason: "3 of 3 high-demand sessions were followed by a poorer next-day response.",
          recorded_at: "2026-09-15T07:30:00+00:00",
        }],
      },
    },
  };
  const log = migrateEnvelope(withLog).envelope.states["demo-ethan"].adaptation_log;
  assert.equal(log.length, 1);
  assert.equal(log[0].result, "reduced");
  assert.equal(log[0].final_band, "Moderate");
  assert.equal(log[0].reason.includes("poorer next-day response"), true);
});

check("a current envelope missing the adaptation history gains one, not a reset", () => {
  const current = migrateEnvelope(v2).envelope;
  delete current.states["demo-ethan"].adaptation_log;
  const again = migrateEnvelope(current);
  // Adding an optional field is backwards compatible, so the schema stays at V3.
  assert.equal(again.report.migrated, false);
  assert.deepEqual(again.envelope.states["demo-ethan"].adaptation_log, []);
  // The pre-existing user data is untouched by the additive field.
  assert.equal(again.envelope.states["demo-ethan"].training_history.length, 1);
  assert.equal(again.envelope.states["demo-ethan"].daily_history.length, 1);
});

check("v1 → v3 wraps the single-profile envelope instead of discarding it", () => {
  const legacy = {
    version: 1,
    updated_at: "2026-09-10T00:00:00.000Z",
    state: state("local-1", [{ session_id: "l1", date: "2026-09-09" }]),
    chat: [{ id: "c1", role: "user", content: "hello" }],
  };
  const result = migrateEnvelope(legacy);
  assert.ok(result);
  assert.equal(result.report.from, 1);
  assert.deepEqual(Object.keys(result.envelope.states), ["local-1"]);
  assert.equal(result.envelope.active_profile_id, "local-1");
  assert.equal(result.envelope.states["local-1"].training_history.length, 1);
  assert.equal(result.envelope.chats["local-1"].length, 1);
});

check("already-current envelopes are returned unchanged and not re-migrated", () => {
  const current = migrateEnvelope(v2).envelope;
  const again = migrateEnvelope(current);
  assert.equal(again.report.migrated, false);
  assert.equal(again.report.reason, "already current");
  assert.deepEqual(again.envelope.states["demo-ethan"].training_history[0].session_id, "e1");
});

check("a newer schema is refused rather than reset", () => {
  assert.equal(migrateEnvelope({ ...v2, version: 99 }), null);
  assert.equal(migrateEnvelope({ version: null }), null);
});

check("unusable input is refused, never silently reset", () => {
  assert.equal(migrateEnvelope(null), null);
  assert.equal(migrateEnvelope("nonsense"), null);
  assert.equal(migrateEnvelope({ version: 2 }), null);
  assert.equal(migrateEnvelope({ version: 1, state: { nope: true } }), null);
});

check("a partially damaged profile set keeps the profiles it can read", () => {
  const damaged = { ...v2, states: { "demo-ethan": state("demo-ethan"), broken: { profile_id: 42 } }, active_profile_id: "broken" };
  const result = migrateEnvelope(damaged);
  assert.deepEqual(Object.keys(result.envelope.states), ["demo-ethan"]);
  assert.equal(result.envelope.active_profile_id, "demo-ethan");
});

check("first use (no stored envelope) is not a migration", () => {
  assert.equal(migrateEnvelope(undefined), null);
});

check("demo keys are exported for the demo controls", () => {
  assert.deepEqual([...RESPONSE_DEMO_CASES], ["insufficient", "emerging", "poor_high_tolerance", "established_good"]);
});

const failures = results.filter(([, ok]) => !ok);
console.log(`\n${results.length - failures.length}/${results.length} storage migration checks passed`);
process.exit(failures.length === 0 ? 0 : 1);
