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
    #: Human-readable project identity; ``service`` remains the technical id.
    product_name: str | None = None
    product_version: str
    api_version: str
    frontend: str
    backend: str
    ai_provider: str
    ai_explanations_enabled: bool
    ai_credential_configured: bool
    engines: list[str]
    #: V1.4 — what the Agent layer is and is not: strategy, tool whitelist.
    agent: dict[str, Any] | None = None


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
    prescription_id: str | None = None
    training_type: str | None = None
    focus: str | None = None
    muscle_groups: list[str] = Field(default_factory=list)
    intensity: str | None = None
    duration: str | None = None
    reason: str | None = None
    template: dict[str, Any] = Field(default_factory=dict)
    log_defaults: dict[str, Any] = Field(default_factory=dict)


class TrainingRecommendationSummary(ApiModel):
    primary_name: str
    prescription_id: str | None = None
    training_type: str | None = None
    focus: str | None = None
    split: str | None = None
    muscle_groups: list[str] = Field(default_factory=list)
    session_demand: str
    #: V1.3: the engine's own demand is preserved next to the final, adapted one.
    base_session_demand: str | None = None
    personal_response: dict[str, Any] = Field(default_factory=dict)
    recommendation_confidence: dict[str, Any] = Field(default_factory=dict)
    adaptation: dict[str, Any] | None = None
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
    template: dict[str, Any] = Field(default_factory=dict)
    log_defaults: dict[str, Any] = Field(default_factory=dict)
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
    #: V1.3 Phase 2: structured, scannable detail for the PERSONAL RESPONSE step.
    detail: dict[str, Any] | None = None


class TodayWhy(ApiModel):
    headline: str
    rationale: list[str] = Field(default_factory=list)
    decision_factors: list[str] = Field(default_factory=list)
    note: str = "Decision Trace is a deterministic explanation, not model chain-of-thought."


class TodayTraining(ApiModel):
    recommendation: TrainingRecommendationSummary
    decision_trace: list[DecisionTraceStep]
    exposure: WeeklyExposure
    history: list[RecentSession] = Field(default_factory=list)


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


class CoachToolTrace(ApiModel):
    """One verified source a Coach answer used. A tool trace, never a reasoning trace."""

    tool: str
    label: str
    source: str
    operation: str = "read_only"


class CoachAgentMeta(ApiModel):
    """Agent-layer metadata. No prompt, no chain-of-thought, no secret."""

    strategy: str
    intent: str | None = None
    plan_source: str | None = None
    steps: int = 0
    rejected: list[dict[str, Any]] = Field(default_factory=list)
    planner_error: str | None = None
    limit_reached: bool = False
    provider_seconds: float | None = None
    planner: dict[str, Any] | None = None


class CoachMessageResponse(ApiModel):
    answer: str
    provider: str
    kind: Literal["verified_data", "ai_explanation", "deterministic_fallback", "safety"]
    ai_used: bool
    verified_data: bool
    notice: str | None = None
    contract: dict[str, str]
    # V1.4 — additive Agent fields. Older clients keep working: the previous
    # five fields are unchanged, and these all have defaults.
    tools_used: list[str] = Field(default_factory=list)
    tool_trace: list[CoachToolTrace] = Field(default_factory=list)
    grounded: bool = True
    fallback_used: bool = False
    agent: CoachAgentMeta | None = None


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


class ScienceLogicResponse(ApiModel):
    baseline: dict[str, Any]
    thresholds: list[dict[str, Any]]
    threshold_caveat: str
    overall_rule: list[str]
    readiness_index: dict[str, Any]
    readiness_index_caveat: str
    training_load: dict[str, Any]
    decision_order: list[str]
    session_demand_mapping: str
    fractional_sets: dict[str, Any]
    rir_guidance: str
    safety_override: str
    example_decision: dict[str, Any]
    example_note: str
    system_steps: list[str]
    inputs: dict[str, str]


# --------------------------------------------------------------------------- #
# Phase 2 — browser-owned state passed to a stateless compute layer
# --------------------------------------------------------------------------- #


class ProfileEdits(ApiModel):
    """The profile fields the product already allows a user to edit."""

    name: str | None = None
    age: int | None = Field(default=None, ge=16, le=100)
    sex: str | None = None
    primary_activity: str | None = None
    training_goal: str | None = None
    training_level: str | None = None
    training_split_preference: str | None = None
    personal_sleep_need: float | None = Field(default=None, ge=4.0, le=12.0)
    target_sessions_per_week: int | None = Field(default=None, ge=0, le=14)
    weekly_set_targets: dict[str, float] | None = None


class DailyRow(ApiModel):
    """One dated check-in row, in the shape the engines already consume."""

    date: str
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
    session_duration_min: float | None = None
    session_rpe: float | None = None
    session_load: float | None = None


class SessionRow(ApiModel):
    """One completed training session, in the stored product shape.

    A row sent back by the client may be a *patch*: the browser overlay can carry
    just ``session_id`` plus the fields it wants to attach (a pre-session snapshot
    or post-session feedback), and the server merges it onto the seeded session.
    """

    session_id: str
    date: str | None = None
    training_type: str | None = None
    primary_focus: str | None = None
    muscle_groups: list[str] = Field(default_factory=list)
    exercises: list[dict[str, Any]] = Field(default_factory=list)
    prescribed_sets: float | None = None
    actual_sets: float | None = None
    duration_min: float | None = None
    session_rpe: float | None = None
    session_load: float | None = None
    working_sets: float | None = None
    notes: str | None = None
    completed: bool = True
    #: V1.3 final sprint: the in-session checkpoint recorded for this session.
    response_calibration: dict[str, Any] | None = None


class UserState(ApiModel):
    """The browser-owned overlay on top of a seeded demo profile.

    The API never stores this. The client keeps it in IndexedDB and sends it with
    each compute request, which keeps the backend stateless and the personal data
    on the user's device.
    """

    profile_id: str = "demo-ethan"
    scenario: str | None = None
    edits: ProfileEdits = Field(default_factory=ProfileEdits)
    check_in: DailyRow | None = None
    daily_history: list[DailyRow] = Field(default_factory=list)
    training_history: list[SessionRow] = Field(default_factory=list)
    #: V1.3 Phase 2: one meaningful adaptation decision per day (newest last).
    adaptation_log: list[dict[str, Any]] = Field(default_factory=list)
    #: V1.3 final sprint: the session the user started but has not completed.
    active_session: dict[str, Any] | None = None


class ScenarioInfo(ApiModel):
    name: str
    label: str
    values: dict[str, Any]


class ScenarioListResponse(ApiModel):
    scenarios: list[ScenarioInfo]
    fields: list[str]
    safety_flags: list[str] = Field(default_factory=list)
    muscle_groups: list[str] = Field(default_factory=list)
    note: str


class BaseStateResponse(ApiModel):
    state: UserState
    profile: ProfileSummary
    daily_rows: int
    training_rows: int
    note: str


class ProfileOptionsResponse(ApiModel):
    activities: list[str]
    goals: list[str]
    levels: list[str]
    sexes: list[str]
    splits: list[str]
    muscle_groups: list[str]


class CheckInRequest2(ApiModel):
    state: UserState
    check_in: DailyRow


class ProfileEditRequest(ApiModel):
    state: UserState
    edits: ProfileEdits


class SessionLogRequest(ApiModel):
    state: UserState
    prescription_id: str | None = None
    duration_min: float = Field(gt=0, le=600)
    session_rpe: float = Field(gt=0, le=10)
    completion_status: Literal["Completed", "Partial"] = "Completed"
    notes: str | None = None
    date: str | None = None
    #: Optional per-exercise actual completed sets: ``[{name, working_sets}]``.
    #: When omitted, the prescribed sets are logged as completed.
    exercises: list[dict[str, Any]] | None = None


class SessionLogResponse(ApiModel):
    state: UserState
    session: SessionRow
    today: TodayResponse
    exposure: WeeklyExposure
    history: list[RecentSession]


class StateEnvelope(ApiModel):
    state: UserState
    today: TodayResponse


class StateRequest(ApiModel):
    state: UserState


class InsightPoint(ApiModel):
    date: str
    value: float | None = None
    rolling_mean: float | None = None


class InsightSeries(ApiModel):
    key: str
    label: str
    unit: str
    points: list[InsightPoint]
    baseline: float | None = None
    latest: float | None = None
    note: str


class InsightsResponse(ApiModel):
    window: int
    available_check_ins: int
    sessions_last_14_days: int = 0
    series: list[InsightSeries]
    load: dict[str, Any]
    exposure: WeeklyExposure
    readiness_history: list[dict[str, Any]]
    missing_data_note: str


class InsightsRequest(ApiModel):
    state: UserState
    window: int | None = Field(default=None, ge=7, le=365)


class CoachStateRequest(ApiModel):
    state: UserState
    question: str = Field(min_length=1, max_length=1000)
    history: list[CoachTurn] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Phase V1.3 — Personal Response
# --------------------------------------------------------------------------- #


class SessionFeedbackRequest(ApiModel):
    state: UserState
    session_id: str
    difficulty: int = Field(ge=1, le=5)
    performance: int = Field(ge=1, le=5)
    completion: Literal["Completed", "Modified", "Stopped early"] = "Completed"
    note: str | None = Field(default=None, max_length=280)


class PersonalResponseRequest(ApiModel):
    state: UserState


# --------------------------------------------------------------------------- #
# V1.3 final sprint — in-session calibration and the decision explorer
# --------------------------------------------------------------------------- #


class SessionStartRequest(ApiModel):
    state: UserState
    prescription_id: str | None = None


class CalibrationObservation(ApiModel):
    """The optional in-session checkpoint. No sleep/HRV/stress question is repeated."""

    effort: Literal["Easier than expected", "As expected", "Harder than expected"] = "As expected"
    performance: Literal["Better than expected", "As expected", "Worse than expected"] = "As expected"
    actual_rir: int | None = Field(default=None, ge=0, le=10)
    note: str | None = Field(default=None, max_length=280)


class CalibrationRequest(ApiModel):
    state: UserState
    observation: CalibrationObservation


class WhatIfRequest(ApiModel):
    state: UserState
    lever: Literal["soreness", "recovery", "personal_response"]
    group: str | None = None
    level: int | None = Field(default=None, ge=1, le=5)


class ActiveSessionResponse(ApiModel):
    state: UserState
    active_session: dict[str, Any] | None = None
    session_trace: list[dict[str, Any]] = Field(default_factory=list)
    today: dict[str, Any] | None = None


class CalibrationResponse(ApiModel):
    state: UserState
    calibration: dict[str, Any]
    session_trace: list[dict[str, Any]] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ExplorerLeversResponse(ApiModel):
    levers: list[dict[str, Any]]
    compared_fields: list[dict[str, str]] = Field(default_factory=list)
    note: str
    read_only: bool = True


class WhatIfResponse(ApiModel):
    lever: str | None = None
    lever_label: str | None = None
    changed_input: str | None = None
    change: dict[str, Any] = Field(default_factory=dict)
    current: dict[str, Any] = Field(default_factory=dict)
    alternative: dict[str, Any] = Field(default_factory=dict)
    differences: list[dict[str, Any]] = Field(default_factory=list)
    changed: bool = False
    conclusion: str
    why: list[str] = Field(default_factory=list)
    current_view: dict[str, Any] = Field(default_factory=dict)
    alternative_view: dict[str, Any] = Field(default_factory=dict)
    note: str
    read_only_note: str


class PersonalResponseResponse(ApiModel):
    available: bool
    base_demand: str | None = None
    base_band: str | None = None
    final_demand: str | None = None
    final_band: str | None = None
    adjustment: int = 0
    direction: str = "none"
    evidence: str | None = None
    reason: str | None = None
    detail: str | None = None
    no_increase_reason: str | None = None
    confidence: dict[str, Any] = Field(default_factory=dict)
    confidence_state: str | None = None
    coverage: dict[str, Any] = Field(default_factory=dict)
    consistency: dict[str, Any] = Field(default_factory=dict)
    relevant: dict[str, Any] = Field(default_factory=dict)
    relevant_episodes: int = 0
    profile: dict[str, Any] = Field(default_factory=dict)
    bands_profile: list[dict[str, Any]] = Field(default_factory=list)
    focus_profile: list[dict[str, Any]] = Field(default_factory=list)
    within_tier: dict[str, Any] = Field(default_factory=dict)
    adaptation_history: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    bands: list[dict[str, Any]] = Field(default_factory=list)
    episodes: list[dict[str, Any]] = Field(default_factory=list)
    note: str | None = None
