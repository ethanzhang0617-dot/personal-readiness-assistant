"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { clearEnvelope, readEnvelope, writeEnvelope } from "@/lib/store";
import type {
  CoachKind,
  CoachTurn,
  InsightsResponse,
  PersonalResponse,
  ProfileEdits,
  ProfileSummary,
  TodayResponse,
  UserState,
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

  const refreshToday = useCallback(async (target: UserState | null) => {
    if (!target) return null;
    const result = await api.stateToday(target);
    if (!result.ok) {
      setError(result.error);
      return null;
    }
    setError(null);
    setToday(result.data.today);
    return result.data.today;
  }, []);

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
        await refreshToday(forToday(stored.states[stored.active_profile_id] ?? stored.states[DEFAULT_PROFILE_ID] ?? null));
        setReady(true);
        return;
      }

      const base = await api.stateBase(DEFAULT_PROFILE_ID);
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
      await refreshToday(forToday(base.data.state));
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
        await refreshToday(forToday(target));
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
          message: `Logged ${result.data.session.primary_focus} · ${result.data.session.session_load} AU.`,
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
      await refreshToday(forToday(result.data.state));
      return { ok: true, message: `Demo response history loaded: ${caseName}` };
    },
    [activeId, chats, persist, refreshToday, state?.scenario, states],
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
        await refreshToday(forToday(importedStates[nextActive]));
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
    await refreshToday(forToday(base.data.state));
    return { ok: true, message: "Local data cleared and reset to the seeded demo profile." };
  }, [persist, refreshToday]);

  const reload = useCallback(async () => {
    setReady(false);
    const stored = await readEnvelope();
    if (stored) {
      setStates(stored.states);
      setChats((stored.chats as Record<string, ChatMessage[]>) ?? {});
      setActiveId(stored.active_profile_id || DEFAULT_PROFILE_ID);
      await refreshToday(forToday(stored.states[stored.active_profile_id]));
    }
    setReady(true);
  }, [refreshToday]);

  const value: UserStateContextValue = {
    ready,
    busy,
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
