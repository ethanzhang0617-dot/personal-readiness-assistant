"""API contracts.

Every personal value carries its own unit, source and confidence so the frontend
never has to infer semantics. Numeric truth comes from the engines; these models
only describe the transport shape.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base model: unknown engine fields are allowed but never required."""

    model_config = ConfigDict(extra="allow")


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    service: str = "personal-readiness-assistant-api"
    api_version: str
    reference_implementation: str
    ai_provider: str
    ai_explanations_enabled: bool
    ai_credential_configured: bool
    engines: list[str]


class ProfileSummary(ApiModel):
    user_id: str
    name: str
    is_demo: bool
    age: int | None = None
    sex: str | None = None
    primary_activity: str | None = None
    training_goal: str | None = None
    training_level: str | None = None
    training_split_preference: str | None = None
    personal_sleep_need: float | None = None
    target_sessions_per_week: int | None = None
    weekly_set_targets: dict[str, float] = Field(default_factory=dict)
    default_scenario: str | None = None
    scenarios: list[str] = Field(default_factory=list)


class ReadinessDomain(ApiModel):
    key: str
    label: str
    status: str


class ReadinessSummary(ApiModel):
    status: str
    status_label: str
    index: int | None = None
    index_scale: dict[str, int]
    confidence: str | None = None
    confidence_note: str | None = None
    domains: list[ReadinessDomain]
    contributors: list[str] = Field(default_factory=list)
    explanation: str | None = None
    why_this_status: list[str] = Field(default_factory=list)
    decision_support: list[str] = Field(default_factory=list)
    safety_active: bool
    safety_flags: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    measurements: dict[str, Any] = Field(default_factory=dict)
    baseline: dict[str, Any] = Field(default_factory=dict)
    check_in: dict[str, Any] = Field(default_factory=dict)
    assessment_date: str
    source: str = "readiness_engine.assess_readiness"


class PrescriptionItem(ApiModel):
    name: str
    sets: int | None = None
    reps: str | None = None
    rir: str | None = None


class TrainingAlternative(ApiModel):
    name: str
    training_type: str | None = None
    focus: str | None = None
    muscle_groups: list[str] = Field(default_factory=list)
    intensity: str | None = None
    duration: str | None = None
    reason: str | None = None


class TrainingRecommendationSummary(ApiModel):
    primary_name: str
    training_type: str | None = None
    focus: str | None = None
    split: str | None = None
    muscle_groups: list[str] = Field(default_factory=list)
    session_demand: str
    duration: str
    estimated_duration_min_range: list[int] | None = None
    rir_guidance: str | None = None
    exercises: list[PrescriptionItem] = Field(default_factory=list)
    alternatives: list[TrainingAlternative] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    priority: dict[str, list[str]] = Field(default_factory=dict)
    volume_modifier: Any = None
    target_source: str | None = None
    source: str = "training_recommendation_engine.recommend_training"


class ExposureGroup(ApiModel):
    group: str
    value: float
    target: float | None = None
    unit: str = "weighted working sets"
    status: str | None = None


class WeeklyExposure(ApiModel):
    period: str
    unit: str = "weighted working sets"
    target_source: str | None = None
    groups: list[ExposureGroup] = Field(default_factory=list)
    note: str
    source: str = "training_recommendation_engine.weekly_training_exposure"


class RecentSession(ApiModel):
    date: str
    focus: str | None = None
    training_type: str | None = None
    session_rpe: float | None = None
    duration_min: float | None = None
    working_sets: float | None = None


class DecisionTraceStep(ApiModel):
    index: int
    step: str
    value: str
    source: str = "deterministic"


class TodayWhy(ApiModel):
    headline: str
    rationale: list[str] = Field(default_factory=list)
    decision_factors: list[str] = Field(default_factory=list)
    note: str = "Decision Trace is a deterministic explanation, not model chain-of-thought."


class TodayTraining(ApiModel):
    recommendation: TrainingRecommendationSummary
    decision_trace: list[DecisionTraceStep]


class TodayResponse(ApiModel):
    profile: ProfileSummary
    readiness: ReadinessSummary
    training: TodayTraining
    why: TodayWhy
    generated_at: str
    source: str = "backend.services.readiness_service + training_service"


class CheckInRequest(ApiModel):
    profile_id: str | None = None
    rmssd_ms: float | None = None
    resting_hr_bpm: float | None = None
    sleep_hours: float | None = None
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    fatigue: int | None = Field(default=None, ge=1, le=5)
    soreness: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    motivation: int | None = Field(default=None, ge=1, le=5)
    local_soreness: dict[str, int] = Field(default_factory=dict)
    safety_flags: list[str] = Field(default_factory=list)
    scenario: str | None = None


class CoachTurn(ApiModel):
    role: Literal["user", "assistant"]
    content: str


class CoachMessageRequest(ApiModel):
    question: str = Field(min_length=1, max_length=1000)
    profile_id: str | None = None
    history: list[CoachTurn] = Field(default_factory=list)


class CoachMessageResponse(ApiModel):
    answer: str
    provider: str
    kind: Literal["verified_data", "ai_explanation", "deterministic_fallback", "safety"]
    ai_used: bool
    verified_data: bool
    notice: str | None = None
    contract: dict[str, str]


class ScienceReference(ApiModel):
    authors: str
    year: int
    title: str
    journal: str
    citation: str
    pmid: str
    doi: str | None = None
    pubmed_url: str
    doi_url: str | None = None


class ScienceReferencesResponse(ApiModel):
    evidence_boundaries: list[str]
    labels: dict[str, str]
    evidence_map: list[dict[str, Any]]
    references: list[ScienceReference]
    limitations: list[str]
    verification: str
