/**
 * Types for the FastAPI layer. Personal values always carry their unit, source
 * and confidence so the UI never has to infer semantics.
 */

export type ReadinessStatus = "GREEN" | "AMBER" | "RED" | "INSUFFICIENT DATA" | "STOP / PROFESSIONAL REVIEW";

export interface ReadinessDomain {
  key: string;
  label: string;
  status: ReadinessStatus;
}

export interface ReadinessSummary {
  status: ReadinessStatus;
  status_label: string;
  index: number | null;
  index_scale: { min: number; max: number };
  confidence: string | null;
  confidence_note: string | null;
  domains: ReadinessDomain[];
  contributors: string[];
  explanation: string | null;
  why_this_status: string[];
  decision_support: string[];
  safety_active: boolean;
  safety_flags: string[];
  limitations: string[];
  measurements: Record<string, unknown>;
  baseline: Record<string, unknown>;
  check_in: Record<string, unknown>;
  assessment_date: string;
  source: string;
}

export interface PrescriptionItem {
  name: string;
  sets: number | null;
  reps: string | null;
  rir: string | null;
}

export interface TrainingAlternative {
  name: string;
  prescription_id: string | null;
  training_type: string | null;
  focus: string | null;
  muscle_groups: string[];
  intensity: string | null;
  duration: string | null;
  reason: string | null;
  template: WorkoutTemplate;
  log_defaults: SessionLogDefaults;
}

export interface WorkoutTemplate {
  title?: string;
  duration?: string;
  intensity?: string;
  items?: string[];
  note?: string;
}

export interface SessionLogDefaults {
  exercises?: Array<{ name: string; prescribed_sets: number }>;
  prescribed_sets?: number;
}

export interface TrainingRecommendation {
  primary_name: string;
  prescription_id: string | null;
  training_type: string | null;
  focus: string | null;
  split: string | null;
  muscle_groups: string[];
  session_demand: string;
  /** V1.3: the engine's own demand is kept next to the final, adapted one. */
  base_session_demand?: string | null;
  personal_response?: PersonalResponse | null;
  adaptation?: PersonalResponseAdaptation | null;
  duration: string;
  estimated_duration_min_range: number[] | null;
  rir_guidance: string | null;
  exercises: PrescriptionItem[];
  alternatives: TrainingAlternative[];
  avoid: string[];
  rationale: string[];
  priority: Record<string, string[]>;
  volume_modifier: unknown;
  target_source: string | null;
  template: WorkoutTemplate;
  log_defaults: SessionLogDefaults;
  source: string;
}

export interface ExposureGroup {
  group: string;
  value: number;
  target: number | null;
  unit: string;
  status: string | null;
}

export interface WeeklyExposure {
  period: string;
  unit: string;
  target_source: string | null;
  groups: ExposureGroup[];
  note: string;
  source: string;
}

export interface RecentSession {
  date: string;
  focus: string | null;
  training_type: string | null;
  session_rpe: number | null;
  duration_min: number | null;
  working_sets: number | null;
}

export interface DecisionTraceStep {
  index: number;
  step: string;
  value: string;
  source: string;
}

export interface ProfileSummary {
  user_id: string;
  name: string;
  is_demo: boolean;
  age: number | null;
  sex: string | null;
  primary_activity: string | null;
  training_goal: string | null;
  training_level: string | null;
  training_split_preference: string | null;
  personal_sleep_need: number | null;
  target_sessions_per_week: number | null;
  weekly_set_targets: Record<string, number>;
  default_scenario: string | null;
  scenarios: string[];
}

export interface TodayWhy {
  headline: string;
  rationale: string[];
  decision_factors: string[];
  note: string;
}

export interface TodayResponse {
  profile: ProfileSummary;
  readiness: ReadinessSummary;
  training: {
    recommendation: TrainingRecommendation;
    decision_trace: DecisionTraceStep[];
    exposure: WeeklyExposure;
    history: RecentSession[];
  };
  why: TodayWhy;
  personal_response?: PersonalResponse;
  generated_at: string;
  source: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  api_version: string;
  reference_implementation: string;
  ai_provider: string;
  ai_explanations_enabled: boolean;
  ai_credential_configured: boolean;
  engines: string[];
}

export type CoachKind = "verified_data" | "ai_explanation" | "deterministic_fallback" | "safety";

export interface CoachTurn {
  role: "user" | "assistant";
  content: string;
}

export interface CoachMessageResponse {
  answer: string;
  provider: string;
  kind: CoachKind;
  ai_used: boolean;
  verified_data: boolean;
  notice: string | null;
  contract: Record<string, string>;
}

export interface ScienceReference {
  authors: string;
  year: number;
  title: string;
  journal: string;
  citation: string;
  pmid: string;
  doi: string | null;
  pubmed_url: string;
  doi_url: string | null;
}

export interface ScienceEvidenceRow {
  key: string;
  concept: string;
  evidence: string;
  implementation: string;
  label: string;
  pmids: string[];
}

export interface ScienceReferencesResponse {
  evidence_boundaries: string[];
  labels: Record<string, string>;
  evidence_map: ScienceEvidenceRow[];
  references: ScienceReference[];
  limitations: string[];
  verification: string;
}

export interface ScienceThreshold {
  key: string;
  label: string;
  green: string;
  amber: string;
  red: string;
  label_text: string;
}

export interface ScienceLogicResponse {
  baseline: Record<string, unknown>;
  thresholds: ScienceThreshold[];
  threshold_caveat: string;
  overall_rule: string[];
  readiness_index: Record<string, number>;
  readiness_index_caveat: string;
  training_load: Record<string, unknown>;
  decision_order: string[];
  session_demand_mapping: string;
  fractional_sets: Record<string, unknown>;
  rir_guidance: string;
  safety_override: string;
  example_decision: Record<string, string>;
  example_note: string;
  system_steps: string[];
  inputs: Record<string, string>;
}

/* ------------------------------------------------------------------ */
/* Phase 2 — client-owned state and the stateless compute endpoints    */
/* ------------------------------------------------------------------ */

export interface ProfileEdits {
  name?: string | null;
  age?: number | null;
  sex?: string | null;
  primary_activity?: string | null;
  training_goal?: string | null;
  training_level?: string | null;
  training_split_preference?: string | null;
  personal_sleep_need?: number | null;
  target_sessions_per_week?: number | null;
  weekly_set_targets?: Record<string, number> | null;
}

export interface DailyRow {
  date: string;
  rmssd_ms?: number | null;
  resting_hr_bpm?: number | null;
  sleep_hours?: number | null;
  sleep_quality?: number | null;
  fatigue?: number | null;
  soreness?: number | null;
  stress?: number | null;
  motivation?: number | null;
  local_soreness?: Record<string, number>;
  safety_flags?: string[];
  session_duration_min?: number | null;
  session_rpe?: number | null;
  session_load?: number | null;
}

export interface SessionRow {
  session_id: string;
  date?: string | null;
  training_type?: string | null;
  primary_focus?: string | null;
  muscle_groups?: string[];
  exercises?: Array<Record<string, unknown>>;
  prescribed_sets?: number | null;
  actual_sets?: number | null;
  duration_min?: number | null;
  session_rpe?: number | null;
  session_load?: number | null;
  working_sets?: number | null;
  notes?: string | null;
  completed?: boolean;
  /** V1.3 response episode data attached to a session. */
  response_context?: ResponseSnapshot | null;
  response_feedback?: ResponseFeedback | null;
}

export interface ResponseSnapshot {
  captured_at?: string;
  readiness_status?: string | null;
  readiness_index?: number | null;
  readiness_confidence?: string | null;
  base_session_demand?: string | null;
  final_session_demand?: string | null;
  adjustment?: number;
  recommended_focus?: string | null;
  recommended_duration?: string | null;
  recommended_rir?: string | null;
  local_soreness?: Record<string, number>;
  exposure_note?: string | null;
}

export interface ResponseFeedback {
  difficulty: number;
  performance: number;
  completion: string;
  note?: string | null;
  submitted_at?: string;
}

export interface PersonalResponseAdaptation {
  label: string;
  direction: string;
  from: string | null;
  to: string | null;
  reason: string;
}

export interface ResponseEpisode {
  session_id: string;
  date: string;
  focus: string | null;
  band: string | null;
  before: {
    readiness_status: string | null;
    readiness_index: number | null;
    confidence: string | null;
    local_soreness: Record<string, number>;
  };
  recommendation: {
    base_demand: string | null;
    final_demand: string | null;
    band: string | null;
    adjustment: number;
    duration: string | null;
    rir: string | null;
    exposure_note: string | null;
  };
  performed: {
    duration_min: number | null;
    session_rpe: number | null;
    working_sets: number | null;
    completion: string | null;
  };
  feedback: ResponseFeedback | null;
  after: {
    date: string;
    fatigue: number | null;
    soreness: number | null;
    motivation: number | null;
    stress: number | null;
    sleep_hours: number | null;
    rmssd_ms: number | null;
    resting_hr_bpm: number | null;
  } | null;
  response: { verdict: string; signals: string[] };
  link: string;
  complete: boolean;
}

export interface PersonalResponseBand {
  band: string;
  demand: string;
  observations: number;
  poorer: number;
  better: number;
  pattern: string;
  evidence: string;
}

export interface PersonalResponse {
  available: boolean;
  base_demand: string | null;
  base_band: string | null;
  final_demand: string | null;
  final_band: string | null;
  adjustment: number;
  direction: string;
  evidence: string | null;
  reason: string | null;
  detail: string | null;
  summary: {
    episodes_total?: number;
    episodes_complete?: number;
    episodes_pending?: number;
    evidence?: string;
    bands?: PersonalResponseBand[];
    note?: string;
  };
  bands: PersonalResponseBand[];
  episodes: ResponseEpisode[];
  note: string | null;
}

export interface UserState {
  profile_id: string;
  scenario: string | null;
  edits: ProfileEdits;
  check_in: DailyRow | null;
  daily_history: DailyRow[];
  training_history: SessionRow[];
}

export interface ScenarioInfo {
  name: string;
  label: string;
  values: Record<string, number | number[] | string[]>;
}

export interface ScenarioListResponse {
  scenarios: ScenarioInfo[];
  fields: string[];
  safety_flags: string[];
  muscle_groups: string[];
  note: string;
}

export interface BaseStateResponse {
  state: UserState;
  profile: ProfileSummary;
  daily_rows: number;
  training_rows: number;
  note: string;
}

export interface ProfileOptionsResponse {
  activities: string[];
  goals: string[];
  levels: string[];
  sexes: string[];
  splits: string[];
  muscle_groups: string[];
}

export interface StateEnvelope {
  state: UserState;
  today: TodayResponse;
}

export interface SessionLogResponse {
  state: UserState;
  session: SessionRow;
  today: TodayResponse;
  exposure: WeeklyExposure;
  history: RecentSession[];
}

export interface InsightPoint {
  date: string;
  value: number | null;
  rolling_mean: number | null;
}

export interface InsightSeries {
  key: string;
  label: string;
  unit: string;
  points: InsightPoint[];
  baseline: number | null;
  latest: number | null;
  note: string;
}

export interface InsightsResponse {
  window: number;
  available_check_ins: number;
  sessions_last_14_days: number;
  series: InsightSeries[];
  load: Record<string, unknown>;
  exposure: WeeklyExposure;
  readiness_history: Array<{ date: string; status: string | null; index: number | null; confidence: string | null }>;
  missing_data_note: string;
}
