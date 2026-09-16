import type {
  CoachMessageResponse,
  CoachTurn,
  DecisionTraceStep,
  HealthResponse,
  ProfileSummary,
  ReadinessSummary,
  RecentSession,
  ScienceReferencesResponse,
  TodayResponse,
  TrainingRecommendation,
  WeeklyExposure,
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
  coachMessage: (question: string, history: CoachTurn[], profileId?: string) =>
    request<CoachMessageResponse>("/api/coach/message", {
      method: "POST",
      body: JSON.stringify({ question, history, profile_id: profileId ?? null }),
    }),
};
