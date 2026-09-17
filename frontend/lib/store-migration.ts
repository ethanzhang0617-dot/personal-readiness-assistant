/**
 * Storage schema migration for the browser-owned state.
 *
 * | Version | Shape |
 * |---|---|
 * | 1 | `{ version: 1, state, chat }` — one profile, no per-profile maps |
 * | 2 | `{ version: 2, active_profile_id, states, chats }` |
 * | 3 | same as 2, with every session row normalised to carry the optional V1.3 |
 * |   | `response_context` / `response_feedback` keys (default `null`) |
 * | 3 | and every profile carrying the V1.3 Phase 2 `adaptation_log` |
 * |   | (default `[]`). A purely additive field, so no version bump or reset. |
 * | 3 | and the V1.3 final-sprint `active_session` (default `null`) plus the |
 * |   | per-session `response_calibration` key (default `null`). Additive again. |
 *
 * Rules: never discard user data, never silently reset. An envelope from a *newer*
 * version than this build understands is refused (returns null) so a downgrade
 * cannot corrupt newer data; unknown shapes are refused too.
 */

import type { UserState } from "@/types/api";

export const STORAGE_VERSION = 3;

export interface StoredEnvelope {
  version: number;
  updated_at: string;
  active_profile_id: string;
  states: Record<string, UserState>;
  chats: Record<string, unknown[]>;
}

export interface MigrationReport {
  from: number | null;
  to: number;
  migrated: boolean;
  reason?: string;
}

const DEFAULT_PROFILE_ID = "demo-ethan";

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function normaliseState(raw: unknown): UserState | null {
  const state = asRecord(raw);
  if (!state || typeof state.profile_id !== "string") return null;
  const sessions = Array.isArray(state.training_history) ? state.training_history : [];
  // V1.3 Phase 2 adds the adaptation log. Missing (older) data becomes an empty
  // history rather than a reset: the user's check-ins and sessions are untouched.
  const adaptationLog = Array.isArray(state.adaptation_log)
    ? (state.adaptation_log as UserState["adaptation_log"])
    : [];
  const activeSession = asRecord(state.active_session);
  return {
    profile_id: state.profile_id,
    scenario: (state.scenario as string | null) ?? null,
    edits: asRecord(state.edits) ?? {},
    check_in: (state.check_in as UserState["check_in"]) ?? null,
    daily_history: Array.isArray(state.daily_history) ? (state.daily_history as UserState["daily_history"]) : [],
    adaptation_log: adaptationLog,
    // V1.3 final sprint: an unfinished session survives a reload, and older
    // envelopes simply have none.
    active_session: (activeSession as UserState["active_session"]) ?? null,
    training_history: sessions.map((row) => {
      const session = asRecord(row) ?? {};
      // V1.3 keys are added explicitly so the response layer can rely on them.
      return {
        ...session,
        response_context: asRecord(session.response_context) ?? null,
        response_feedback: asRecord(session.response_feedback) ?? null,
        response_calibration: asRecord(session.response_calibration) ?? null,
      } as UserState["training_history"][number];
    }),
  };
}

/** Migrate any supported stored envelope to the current schema. */
export function migrateEnvelope(raw: unknown): { envelope: StoredEnvelope; report: MigrationReport } | null {
  const source = asRecord(raw);
  if (!source) return null;
  const version = typeof source.version === "number" ? source.version : null;
  if (version === null || version > STORAGE_VERSION) return null;

  const chats = (asRecord(source.chats) ?? {}) as Record<string, unknown[]>;

  if (version <= 1) {
    const state = normaliseState(source.state);
    if (!state) return null;
    const active = state.profile_id || DEFAULT_PROFILE_ID;
    return {
      envelope: {
        version: STORAGE_VERSION,
        updated_at: typeof source.updated_at === "string" ? source.updated_at : new Date().toISOString(),
        active_profile_id: active,
        states: { [active]: state },
        chats: (Array.isArray(source.chat) ? { [active]: source.chat as unknown[] } : chats),
      },
      report: { from: 1, to: STORAGE_VERSION, migrated: true, reason: "v1 single-profile envelope" },
    };
  }

  const statesSource = asRecord(source.states);
  if (!statesSource) return null;
  const states: Record<string, UserState> = {};
  for (const [key, value] of Object.entries(statesSource)) {
    const state = normaliseState(value);
    if (state) states[key] = state;
  }
  if (Object.keys(states).length === 0) return null;
  const active = typeof source.active_profile_id === "string" && states[source.active_profile_id]
    ? source.active_profile_id
    : Object.keys(states)[0];

  return {
    envelope: {
      version: STORAGE_VERSION,
      updated_at: typeof source.updated_at === "string" ? source.updated_at : new Date().toISOString(),
      active_profile_id: active,
      states,
      chats,
    },
    report: {
      from: version,
      to: STORAGE_VERSION,
      migrated: version !== STORAGE_VERSION,
      reason: version === STORAGE_VERSION ? "already current" : `v${version} envelope normalised`,
    },
  };
}
