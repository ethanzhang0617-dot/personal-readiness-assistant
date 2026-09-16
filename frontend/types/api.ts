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
  training_type: string | null;
  focus: string | null;
  muscle_groups: string[];
  intensity: string | null;
  duration: string | null;
  reason: string | null;
}

export interface TrainingRecommendation {
  primary_name: string;
  training_type: string | null;
  focus: string | null;
  split: string | null;
  muscle_groups: string[];
  session_demand: string;
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
  };
  why: TodayWhy;
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
