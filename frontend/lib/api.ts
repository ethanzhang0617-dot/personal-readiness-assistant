import type {
  ActiveSessionResponse,
  BaseStateResponse,
  CalibrationResponse,
  CoachMessageResponse,
  CoachTurn,
  DecisionTraceStep,
  ExplorerLeversResponse,
  HealthResponse,
  InsightsResponse,
  ProfileEdits,
  ProfileOptionsResponse,
  ProfileSummary,
  PersonalResponse,
  ReadinessSummary,
  RecentSession,
  ScienceReferencesResponse,
  ScienceLogicResponse,
  ScenarioListResponse,
  SessionLogResponse,
  StateEnvelope,
  TodayResponse,
  TrainingRecommendation,
  UserState,
  WeeklyExposure,
  WhatIfResponse,
} from "@/types/api";

/**
 * The backend URL is the only public value the frontend needs. The DeepSeek
 * credential lives in the FastAPI process and is never sent to the browser.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string; status?: number };

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!response.ok) {
      return { ok: false, error: `The API responded with ${response.status}.`, status: response.status };
    }
    return { ok: true, data: (await response.json()) as T };
  } catch {
    // Network failure, DNS failure or the API not running: a product state, not a crash.
    return { ok: false, error: "The API is unavailable. Start the FastAPI backend and retry." };
  }
}

const query = (profileId?: string) => (profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "");

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  profiles: () => request<ProfileSummary[]>("/api/profiles"),
  profile: (profileId?: string) => request<ProfileSummary>(`/api/profile${query(profileId)}`),
  today: (profileId?: string) => request<TodayResponse>(`/api/today${query(profileId)}`),
  readiness: (profileId?: string) => request<ReadinessSummary>(`/api/readiness${query(profileId)}`),
  recommendation: (profileId?: string) =>
    request<TrainingRecommendation>(`/api/training/recommendation${query(profileId)}`),
  exposure: (profileId?: string) => request<WeeklyExposure>(`/api/training/exposure${query(profileId)}`),
  history: (profileId?: string, limit = 8) =>
    request<RecentSession[]>(`/api/training/history${query(profileId)}${profileId ? "&" : "?"}limit=${limit}`),
  decisionTrace: (profileId?: string) => request<DecisionTraceStep[]>(`/api/decision-trace${query(profileId)}`),
  science: () => request<ScienceReferencesResponse>("/api/science/references"),
  scienceLogic: () => request<ScienceLogicResponse>("/api/science/logic"),
  coachMessage: (question: string, history: CoachTurn[], profileId?: string) =>
    request<CoachMessageResponse>("/api/coach/message", {
      method: "POST",
      body: JSON.stringify({ question, history, profile_id: profileId ?? null }),
    }),
  // Phase 2 — the browser owns the state and posts it for computation.
  scenarios: () => request<ScenarioListResponse>("/api/scenarios"),
  stateBase: (profileId?: string, scenario?: string) =>
    request<BaseStateResponse>(`/api/state/base${_stateBaseQuery(profileId, scenario)}`),
  stateBaseWithDemo: (profileId: string | undefined, scenario: string | undefined, responseDemo: string) =>
    request<BaseStateResponse>(`/api/state/base${_stateBaseQuery(profileId, scenario, responseDemo)}`),
  stateToday: (state: UserState) =>
    request<StateEnvelope>("/api/state/today", { method: "POST", body: JSON.stringify({ state }) }),
  stateCheckIn: (state: UserState, checkIn: Record<string, unknown>) =>
    request<StateEnvelope>("/api/state/check-in", { method: "POST", body: JSON.stringify({ state, check_in: checkIn }) }),
  stateProfile: (state: UserState, edits: ProfileEdits) =>
    request<StateEnvelope>("/api/state/profile", { method: "POST", body: JSON.stringify({ state, edits }) }),
  stateSession: (state: UserState, details: Record<string, unknown>) =>
    request<SessionLogResponse>("/api/state/session", { method: "POST", body: JSON.stringify({ state, ...details }) }),
  stateCoach: (state: UserState, question: string, history: CoachTurn[]) =>
    request<CoachMessageResponse>("/api/state/coach", { method: "POST", body: JSON.stringify({ state, question, history }) }),
  stateInsights: (state: UserState, window?: number) =>
    request<InsightsResponse>("/api/state/insights", { method: "POST", body: JSON.stringify({ state, window: window ?? null }) }),
  profileOptions: () => request<ProfileOptionsResponse>("/api/profile/options"),
  // V1.3 — Personal Response
  stateFeedback: (state: UserState, sessionId: string, feedback: { difficulty: number; performance: number; completion: string; note?: string }) =>
    request<StateEnvelope>("/api/state/feedback", {
      method: "POST",
      body: JSON.stringify({ state, session_id: sessionId, ...feedback }),
    }),
  statePersonalResponse: (state: UserState) =>
    request<PersonalResponse>("/api/state/personal-response", { method: "POST", body: JSON.stringify({ state }) }),
  personalResponse: (responseDemo?: string) =>
    request<PersonalResponse>(`/api/personal-response${responseDemo ? `?response_demo=${encodeURIComponent(responseDemo)}` : ""}`),
  // V1.3 final sprint — active session, calibration and the decision explorer
  stateSessionStart: (state: UserState, prescriptionId: string | null) =>
    request<ActiveSessionResponse>("/api/state/session/start", {
      method: "POST",
      body: JSON.stringify({ state, prescription_id: prescriptionId }),
    }),
  stateSessionCancel: (state: UserState) =>
    request<StateEnvelope>("/api/state/session/cancel", { method: "POST", body: JSON.stringify({ state }) }),
  stateCalibration: (
    state: UserState,
    observation: { effort: string; performance: string; actual_rir: number | null; note?: string },
  ) =>
    request<CalibrationResponse>("/api/state/session/calibration", {
      method: "POST",
      body: JSON.stringify({ state, observation }),
    }),
  explorerLevers: () => request<ExplorerLeversResponse>("/api/decision-explorer"),
  stateWhatIf: (state: UserState, lever: string, options?: { group?: string | null; level?: number | null }) =>
    request<WhatIfResponse>("/api/state/what-if", {
      method: "POST",
      body: JSON.stringify({ state, lever, group: options?.group ?? null, level: options?.level ?? null }),
    }),
};

function _stateBaseQuery(profileId?: string, scenario?: string, responseDemo?: string): string {
  const parts: string[] = [];
  if (profileId) parts.push(`profile_id=${encodeURIComponent(profileId)}`);
  if (scenario) parts.push(`scenario=${encodeURIComponent(scenario)}`);
  if (responseDemo) parts.push(`response_demo=${encodeURIComponent(responseDemo)}`);
  return parts.length ? `?${parts.join("&")}` : "";
}
