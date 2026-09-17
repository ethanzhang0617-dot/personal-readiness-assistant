"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { clearEnvelope, readEnvelope, writeEnvelope } from "@/lib/store";
import type {
  Calibration,
  CoachKind,
  CoachTurn,
  InsightsResponse,
  PersonalResponse,
  ProfileEdits,
  ProfileSummary,
  TodayResponse,
  UserState,
  WhatIfResponse,
} from "@/types/api";

export const DEFAULT_PROFILE_ID = "demo-ethan";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider?: string;
  kind?: CoachKind;
  notice?: string | null;
  failed?: boolean;
}

export interface ActionResult {
  ok: boolean;
  error?: string;
  message?: string;
  /** Set by logSession so the UI can immediately ask for post-session feedback. */
  sessionId?: string;
}

interface UserStateContextValue {
  ready: boolean;
  busy: boolean;
  /** The free-tier API may be waking; the UI shows a calm state, not an error. */
  waking: boolean;
  error: string | null;
  storageAvailable: boolean;
  state: UserState | null;
  today: TodayResponse | null;
  chat: ChatMessage[];
  profileId: string;
  scenario: string | null;
  profiles: ProfileSummary[];
  switchProfile: (profileId: string) => Promise<ActionResult>;
  setScenario: (scenario: string) => Promise<ActionResult>;
  submitCheckIn: (values: Record<string, unknown>) => Promise<ActionResult>;
  saveProfile: (edits: ProfileEdits) => Promise<ActionResult>;
  logSession: (details: Record<string, unknown>) => Promise<ActionResult>;
  submitFeedback: (
    sessionId: string,
    feedback: { difficulty: number; performance: number; completion: string; note?: string },
  ) => Promise<ActionResult>;
  loadPersonalResponse: () => Promise<{ ok: boolean; data?: PersonalResponse; error?: string }>;
  seedResponseDemo: (caseName: string) => Promise<ActionResult>;
  startSession: (prescriptionId: string | null) => Promise<ActionResult>;
  cancelSession: () => Promise<ActionResult>;
  submitCalibration: (
    observation: { effort: string; performance: string; actual_rir: number | null },
  ) => Promise<{ ok: boolean; calibration?: Calibration; error?: string }>;
  runWhatIf: (
    lever: string,
    options?: { group?: string | null; level?: number | null },
  ) => Promise<{ ok: boolean; data?: WhatIfResponse; error?: string }>;
  askCoach: (question: string) => Promise<ActionResult>;
  clearChat: () => Promise<void>;
  loadInsights: (window?: number) => Promise<{ ok: boolean; data?: InsightsResponse; error?: string }>;
  exportState: () => string | null;
  importState: (json: string) => Promise<ActionResult>;
  resetLocal: () => Promise<ActionResult>;
  reload: () => Promise<void>;
}

const UserStateContext = createContext<UserStateContextValue | null>(null);

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

// A check-in belongs to one day. Yesterday's entry stays in the history for the
// baseline, but today's readiness falls back to the selected demo scenario until
// the user checks in again — the rule the reference app also applies.
function forToday(state: UserState | null): UserState | null {
  if (!state) return null;
  return state.check_in && state.check_in.date === todayIso() ? state : { ...state, check_in: null };
}

export function UserStateProvider({ children }: { children: ReactNode }) {
  const [states, setStates] = useState<Record<string, UserState>>({});
  const [chats, setChats] = useState<Record<string, ChatMessage[]>>({});
  const [activeId, setActiveId] = useState<string>(DEFAULT_PROFILE_ID);
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [today, setToday] = useState<TodayResponse | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [storageAvailable, setStorageAvailable] = useState(false);
  const bootstrapped = useRef(false);

  const state = states[activeId] ?? null;
  const chat = useMemo(() => chats[activeId] ?? [], [activeId, chats]);
  const effective = useMemo(() => forToday(state), [state]);

  const persist = useCallback(
    async (nextStates: Record<string, UserState>, nextChats: Record<string, ChatMessage[]>, profileId: string) => {
      const ok = await writeEnvelope(profileId, nextStates, nextChats);
      setStorageAvailable(ok);
      return ok;
    },
    [],
  );

  // `/state/today` is a compute endpoint that also returns the state it computed
  // from, with today's adaptation-history entry appended. Persisting that copy is
  // what makes the Adaptation History in Insights real rather than decorative, so
  // the caller passes the state map and chat list it already knows.
  const refreshToday = useCallback(
    async (
      target: UserState | null,
      currentStates: Record<string, UserState>,
      currentChats: Record<string, ChatMessage[]>,
    ) => {
      if (!target) return null;
      const result = await api.stateToday(target);
      if (!result.ok) {
        setError(result.error);
        return null;
      }
      setError(null);
      setToday(result.data.today);
      const profileId = result.data.state.profile_id;
      // The request carries a *display* copy of the state, where yesterday's
      // check-in is hidden so today's readiness falls back to the scenario. Never
      // let that round trip erase a check-in the browser is still holding.
      const previous = currentStates[profileId];
      const computed = result.data.state;
      const nextStates = {
        ...currentStates,
        [profileId]: previous?.check_in && !computed.check_in
          ? { ...computed, check_in: previous.check_in }
          : computed,
      };
      setStates(nextStates);
      await persist(nextStates, currentChats, profileId);
      return result.data.today;
    },
    [persist],
  );

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;

    (async () => {
      api.profiles().then((result) => {
        if (result.ok) setProfiles(result.data);
      });

      const stored = await readEnvelope();
      if (stored) {
        setStates(stored.states);
        setChats((stored.chats as Record<string, ChatMessage[]>) ?? {});
        setActiveId(stored.active_profile_id || DEFAULT_PROFILE_ID);
        setStorageAvailable(true);
        await refreshToday(
          forToday(stored.states[stored.active_profile_id] ?? stored.states[DEFAULT_PROFILE_ID] ?? null),
          stored.states,
          (stored.chats as Record<string, ChatMessage[]>) ?? {},
        );
        setWaking(false);
        setReady(true);
        return;
      }

      // A free-tier backend can take a while to wake up. Retry quietly before
      // showing anything that looks like a failure.
      let base = await api.stateBase(DEFAULT_PROFILE_ID);
      for (let attempt = 0; attempt < 4 && !base.ok; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        base = await api.stateBase(DEFAULT_PROFILE_ID);
      }
      setWaking(false);
      if (!base.ok) {
        setError(base.error);
        setReady(true);
        return;
      }
      const seeded = { [base.data.state.profile_id]: base.data.state };
      setStates(seeded);
      setChats({});
      setActiveId(base.data.state.profile_id);
      await persist(seeded, {}, base.data.state.profile_id);
      await refreshToday(forToday(base.data.state), seeded, {});
      setReady(true);
    })();
  }, [persist, refreshToday]);

  const mutate = useCallback(
    async (
      run: (current: UserState) => Promise<
        { state: UserState; today?: TodayResponse; message?: string; sessionId?: string } | { error: string }
      >,
    ) => {
      if (!state) return { ok: false, error: "The local profile is still loading." };
      setBusy(true);
      try {
        const outcome = await run(state);
        if ("error" in outcome) return { ok: false, error: outcome.error };
        const nextStates = { ...states, [activeId]: outcome.state };
        setStates(nextStates);
        if (outcome.today) setToday(outcome.today);
        await persist(nextStates, chats, activeId);
        setError(null);
        return {
          ok: true,
          message: outcome.message,
          sessionId: "sessionId" in outcome ? (outcome.sessionId as string | undefined) : undefined,
        };
      } finally {
        setBusy(false);
      }
    },
    [activeId, chats, persist, state, states],
  );

  const switchProfile = useCallback(
    async (profileId: string) => {
      setBusy(true);
      try {
        let nextStates = states;
        let target = states[profileId];
        if (!target) {
          const base = await api.stateBase(profileId);
          if (!base.ok) return { ok: false, error: base.error };
          target = base.data.state;
          nextStates = { ...states, [profileId]: target };
          setStates(nextStates);
        }
        setActiveId(profileId);
        setError(null);
        await persist(nextStates, chats, profileId);
        await refreshToday(forToday(target), nextStates, chats);
        return { ok: true, message: `Active profile: ${profileId}` };
      } finally {
        setBusy(false);
      }
    },
    [chats, persist, refreshToday, states],
  );

  const setScenario = useCallback(
    (scenario: string) =>
      mutate(async (current) => {
        const result = await api.stateToday({ ...current, scenario });
        if (!result.ok) return { error: result.error };
        return { state: result.data.state, today: result.data.today, message: `Scenario set to ${scenario}.` };
      }),
    [mutate],
  );

  const submitCheckIn = useCallback(
    (values: Record<string, unknown>) =>
      mutate(async (current) => {
        const result = await api.stateCheckIn(current, { ...values, date: todayIso() });
        if (!result.ok) return { error: result.error };
        return { state: result.data.state, today: result.data.today, message: "Check-in saved. Readiness recalculated." };
      }),
    [mutate],
  );

  const saveProfile = useCallback(
    (edits: ProfileEdits) =>
      mutate(async (current) => {
        const result = await api.stateProfile(current, edits);
        if (!result.ok) return { error: result.error };
        return { state: result.data.state, today: result.data.today, message: "Profile saved." };
      }),
    [mutate],
  );

  const logSession = useCallback(
    (details: Record<string, unknown>) =>
      mutate(async (current) => {
        const result = await api.stateSession(current, details);
        if (!result.ok) return { error: result.error };
        return {
          state: result.data.state,
          today: result.data.today,
          // Consumer unit: Training Load Points (the metric is unchanged).
          message: `Logged ${result.data.session.primary_focus} · ${result.data.session.session_load} pts.`,
          sessionId: String(result.data.session.session_id),
        };
      }),
    [mutate],
  );

  const submitFeedback = useCallback(
    (sessionId: string, feedback: { difficulty: number; performance: number; completion: string; note?: string }) =>
      mutate(async (current) => {
        const result = await api.stateFeedback(current, sessionId, feedback);
        if (!result.ok) return { error: result.error };
        return {
          state: result.data.state,
          today: result.data.today,
          message: "Response saved. We'll compare it with your next check-in.",
        };
      }),
    [mutate],
  );

  const loadPersonalResponse = useCallback(async () => {
    if (!effective) return { ok: false as const, error: "The local profile is still loading." };
    const result = await api.statePersonalResponse(effective);
    if (!result.ok) return { ok: false as const, error: result.error };
    return { ok: true as const, data: result.data };
  }, [effective]);

  /** Demo control: seed a Personal Response history case into this browser. */
  const seedResponseDemo = useCallback(
    async (caseName: string) => {
      const result = await api.stateBaseWithDemo(activeId, state?.scenario ?? undefined, caseName);
      if (!result.ok) return { ok: false, error: result.error };
      const nextStates = { ...states, [activeId]: result.data.state };
      setStates(nextStates);
      await persist(nextStates, chats, activeId);
      await refreshToday(forToday(result.data.state), nextStates, chats);
      return { ok: true, message: `Demo response history loaded: ${caseName}` };
    },
    [activeId, chats, persist, refreshToday, state?.scenario, states],
  );

  /** V1.3: open the active session with the guidance the product prescribes now. */
  const startSession = useCallback(
    async (prescriptionId: string | null) => {
      if (!state) return { ok: false, error: "The local profile is still loading." };
      setBusy(true);
      try {
        const result = await api.stateSessionStart(state, prescriptionId);
        if (!result.ok) return { ok: false, error: result.error };
        const nextStates = { ...states, [activeId]: result.data.state };
        setStates(nextStates);
        setToday(result.data.today);
        await persist(nextStates, chats, activeId);
        return { ok: true, message: "Session started. Guidance is on screen until you complete it." };
      } finally {
        setBusy(false);
      }
    },
    [activeId, chats, persist, state, states],
  );

  const cancelSession = useCallback(async () => {
    if (!state) return { ok: false, error: "The local profile is still loading." };
    setBusy(true);
    try {
      const result = await api.stateSessionCancel(state);
      if (!result.ok) return { ok: false, error: result.error };
      const nextStates = { ...states, [activeId]: result.data.state };
      setStates(nextStates);
      setToday(result.data.today);
      await persist(nextStates, chats, activeId);
      return { ok: true, message: "Active session discarded. Nothing was logged." };
    } finally {
      setBusy(false);
    }
  }, [activeId, chats, persist, state, states]);

  /**
   * One optional in-session checkpoint. It only ever resolves to HOLD, EASE or
   * OPTIONAL PUSH, and it is stored on the active session so a reload keeps it.
   */
  const submitCalibration = useCallback(
    async (observation: { effort: string; performance: string; actual_rir: number | null }) => {
      if (!state) return { ok: false as const, error: "The local profile is still loading." };
      setBusy(true);
      try {
        const result = await api.stateCalibration(state, observation);
        if (!result.ok) return { ok: false as const, error: result.error };
        const nextStates = { ...states, [activeId]: result.data.state };
        setStates(nextStates);
        await persist(nextStates, chats, activeId);
        await refreshToday(forToday(result.data.state), nextStates, chats);
        return { ok: true as const, calibration: result.data.calibration };
      } finally {
        setBusy(false);
      }
    },
    [activeId, chats, persist, refreshToday, state, states],
  );

  /** What-if is a read-only simulation: the returned state is deliberately ignored. */
  const runWhatIf = useCallback(
    async (lever: string, options?: { group?: string | null; level?: number | null }) => {
      if (!effective) return { ok: false as const, error: "The local profile is still loading." };
      const result = await api.stateWhatIf(effective, lever, options);
      if (!result.ok) return { ok: false as const, error: result.error };
      return { ok: true as const, data: result.data };
    },
    [effective],
  );

  const askCoach = useCallback(
    async (question: string) => {
      if (!effective) return { ok: false, error: "The local profile is still loading." };
      const trimmed = question.trim();
      if (!trimmed) return { ok: false, error: "Enter a question first." };

      const history: CoachTurn[] = chat
        .filter((message) => !message.failed)
        .map((message) => ({ role: message.role, content: message.content }));
      const pending: ChatMessage[] = [...chat, { id: `user-${Date.now()}`, role: "user", content: trimmed }];
      setChats({ ...chats, [activeId]: pending });
      setBusy(true);
      const result = await api.stateCoach(effective, trimmed, history);
      setBusy(false);

      if (!result.ok) {
        const nextChat = [
          ...pending,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant" as const,
            content: "The Coach is unavailable right now. Your question was not sent to the AI provider.",
            kind: "deterministic_fallback" as const,
            failed: true,
          },
        ];
        const nextChats = { ...chats, [activeId]: nextChat };
        setChats(nextChats);
        await persist(states, nextChats, activeId);
        return { ok: false, error: result.error };
      }

      const appended: ChatMessage[] = [
        ...pending,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.data.answer,
          provider: result.data.provider,
          kind: result.data.kind,
          notice: result.data.notice,
        },
      ];
      const nextChat = appended.slice(-30);
      const nextChats = { ...chats, [activeId]: nextChat };
      setChats(nextChats);
      await persist(states, nextChats, activeId);
      return { ok: true };
    },
    [activeId, chat, chats, effective, persist, states],
  );

  const clearChat = useCallback(async () => {
    const nextChats = { ...chats, [activeId]: [] };
    setChats(nextChats);
    await persist(states, nextChats, activeId);
  }, [activeId, chats, persist, states]);

  const loadInsights = useCallback(
    async (window?: number) => {
      if (!effective) return { ok: false as const, error: "The local profile is still loading." };
      const result = await api.stateInsights(effective, window);
      if (!result.ok) return { ok: false as const, error: result.error };
      return { ok: true as const, data: result.data };
    },
    [effective],
  );

  const exportState = useCallback(() => {
    if (!state) return null;
    return JSON.stringify(
      {
        product: "personal-readiness-assistant",
        version: 2,
        exported_at: new Date().toISOString(),
        active_profile_id: activeId,
        states,
        chats,
      },
      null,
      2,
    );
  }, [activeId, chats, state, states]);

  const importState = useCallback(
    async (json: string) => {
      try {
        const parsed = JSON.parse(json) as {
          states?: Record<string, UserState>;
          chats?: Record<string, ChatMessage[]>;
          active_profile_id?: string;
          state?: UserState;
        };
        // Accept both the current multi-profile envelope and the single-profile file.
        const importedStates = parsed.states ?? (parsed.state ? { [parsed.state.profile_id]: parsed.state } : null);
        if (!importedStates || Object.keys(importedStates).length === 0) {
          return { ok: false, error: "This file does not contain Personal Readiness data." };
        }
        const importedChats = parsed.chats ?? {};
        const nextActive = parsed.active_profile_id ?? Object.keys(importedStates)[0];
        setStates(importedStates);
        setChats(importedChats);
        setActiveId(nextActive);
        await persist(importedStates, importedChats, nextActive);
        await refreshToday(forToday(importedStates[nextActive]), importedStates, importedChats);
        return { ok: true, message: "Backup imported into this browser." };
      } catch {
        return { ok: false, error: "That file is not valid JSON." };
      }
    },
    [persist, refreshToday],
  );

  const resetLocal = useCallback(async () => {
    await clearEnvelope();
    const base = await api.stateBase(DEFAULT_PROFILE_ID);
    if (!base.ok) return { ok: false, error: base.error };
    const seeded = { [base.data.state.profile_id]: base.data.state };
    setStates(seeded);
    setChats({});
    setActiveId(base.data.state.profile_id);
    await persist(seeded, {}, base.data.state.profile_id);
    await refreshToday(forToday(base.data.state), seeded, {});
    return { ok: true, message: "Local data cleared and reset to the seeded demo profile." };
  }, [persist, refreshToday]);

  const reload = useCallback(async () => {
    setReady(false);
    const stored = await readEnvelope();
    if (stored) {
      setStates(stored.states);
      setChats((stored.chats as Record<string, ChatMessage[]>) ?? {});
      setActiveId(stored.active_profile_id || DEFAULT_PROFILE_ID);
      await refreshToday(
        forToday(stored.states[stored.active_profile_id]),
        stored.states,
        (stored.chats as Record<string, ChatMessage[]>) ?? {},
      );
    }
    setWaking(false);
    setReady(true);
  }, [refreshToday]);

  const value: UserStateContextValue = {
    ready,
    busy,
    waking,
    error,
    storageAvailable,
    state,
    today,
    chat,
    profileId: activeId,
    scenario: state?.scenario ?? null,
    profiles,
    switchProfile,
    setScenario,
    submitCheckIn,
    saveProfile,
    logSession,
    submitFeedback,
    loadPersonalResponse,
    seedResponseDemo,
    startSession,
    cancelSession,
    submitCalibration,
    runWhatIf,
    askCoach,
    clearChat,
    loadInsights,
    exportState,
    importState,
    resetLocal,
    reload,
  };

  return <UserStateContext.Provider value={value}>{children}</UserStateContext.Provider>;
}

export function useUserState(): UserStateContextValue {
  const context = useContext(UserStateContext);
  if (!context) throw new Error("useUserState must be used inside UserStateProvider");
  return context;
}
