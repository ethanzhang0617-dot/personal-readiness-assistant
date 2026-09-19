"""V1.4 — Agent layer: the whitelisted, read-only tool registry.

The Agent decides *which* verified product capability to consult. It never
computes a training number itself. Every tool below is a thin wrapper around a
capability the product already ships:

| Tool | Existing capability it wraps |
|---|---|
| ``get_readiness`` | ``readiness_engine.assess_readiness`` (via ``readiness_service``) |
| ``get_current_recommendation`` | ``training_recommendation_engine.recommend_training`` |
| ``get_recent_training`` | stored completed sessions in ``profile.training_history`` |
| ``get_training_exposure`` | ``training_recommendation_engine.weekly_training_exposure`` |
| ``get_personal_response`` | ``adaptive_response.evaluate`` (via ``response_service``) |
| ``get_recommendation_confidence`` | ``adaptive_response.recommendation_confidence`` |
| ``get_decision_trace`` | the deterministic trace + the Personal Response step |
| ``run_decision_explorer`` | ``decision_explorer`` (read-only simulation only) |
| ``get_session_calibration_context`` | ``session_calibration`` |
| ``get_training_load`` | the readiness engine's training-load domain |
| ``get_personal_context`` | stored profile settings, goal, split and weekly targets |

Three rules hold for the whole module:

1. **Read-only.** ``operation`` is ``read_only`` for every tool. No tool can
   change readiness, a recommendation, Personal Response, Recommendation
   Confidence, Training Load, weekly exposure, a safety rule or a threshold, and
   none of them executes arbitrary code, reads arbitrary files, calls an
   arbitrary URL or runs a shell command.
2. **Whitelisted.** Only the names in ``_REGISTRY`` can run. An unknown name is
   refused before anything executes, and arguments are validated against the
   tool's declared schema, so a model can never reach an arbitrary function.
3. **Structured.** A tool returns JSON-compatible data with a bounded size,
   never a raw Python object and never an engine-internal structure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Iterable, Mapping

import ai_facts
import session_calibration
from training_recommendation_engine import MUSCLE_GROUPS
from backend.services import (calibration_service, explorer_service, response_service,
                              state_service, training_service)


# --------------------------------------------------------------------------- #
# Registry primitives
# --------------------------------------------------------------------------- #

AGENT_TOOL_VERSION = "1.4"

#: The only operation kind this version exposes. Agent tool use is read-only.
READ_ONLY = "read_only"

#: One tool result is a structured summary, never a raw history dump. The
#: orchestrator embeds results in the final prompt, so the budget is enforced
#: here rather than at the call site.
MAX_TOOL_OUTPUT_CHARS = 3200

#: Product-language labels for the tool trace the user sees. These are labels,
#: not capability descriptions: the consumer UI never shows a tool name.
TOOL_LABELS: dict[str, str] = {
    "get_readiness": "Readiness",
    "get_current_recommendation": "Today's session",
    "get_recent_training": "Recent training",
    "get_training_exposure": "Weekly exposure",
    "get_personal_response": "Personal Response",
    "get_recommendation_confidence": "Recommendation Confidence",
    "get_decision_trace": "Decision Trace",
    "run_decision_explorer": "Decision Explorer",
    "get_session_calibration_context": "In-session Calibration",
    "get_training_load": "Training Load",
    "get_personal_context": "Profile & programme",
}

ERROR_BEHAVIOUR = ("Returns a structured error object "
                   "({ok: false, error: unknown_tool|invalid_arguments|tool_failure}) and never raises; "
                   "the orchestrator degrades to the deterministic answer.")


@dataclass(frozen=True)
class ToolSpec:
    """One whitelisted capability: name, typed input, typed output, source."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    source: str
    operation: str = READ_ONLY
    errors: str = ERROR_BEHAVIOUR

    def catalogue_entry(self) -> dict[str, Any]:
        """The compact form shown to the planner (never the handler)."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": _compact_arguments(self.input_schema),
            "operation": self.operation,
        }


def _compact_arguments(schema: Mapping[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties") or {}
    keep = {"type", "enum", "description", "minimum", "maximum"}
    return {
        "type": "object",
        "properties": {
            key: {k: v for k, v in dict(value).items() if k in keep}
            for key, value in properties.items()
        },
        "required": list(schema.get("required") or []),
        "additionalProperties": False,
    }


def _object_schema(properties: Mapping[str, Any] | None = None,
                   required: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {key: dict(value) for key, value in (properties or {}).items()},
        "required": list(required),
        "additionalProperties": False,
    }


# --------------------------------------------------------------------------- #
# Argument validation
# --------------------------------------------------------------------------- #

_TYPE_CHECK: dict[str, Callable[[Any], bool]] = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
}


def validate_arguments(spec: ToolSpec, arguments: Any) -> tuple[bool, dict[str, Any] | str]:
    """Strict, closed-schema validation of model-supplied arguments.

    Anything not explicitly declared is refused: unknown keys, wrong types, an
    undeclared enum value or an out-of-range number. A caller never executes a
    partially validated argument set.
    """
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, Mapping):
        return False, "Arguments must be a JSON object."
    schema = spec.input_schema or {}
    properties: Mapping[str, Any] = schema.get("properties") or {}
    unknown = sorted(str(key) for key in arguments if key not in properties)
    if unknown and not schema.get("additionalProperties", False):
        return False, f"Undeclared argument(s): {', '.join(unknown)}."
    cleaned: dict[str, Any] = {}
    for key, expected in properties.items():
        if key not in arguments or arguments.get(key) is None:
            continue
        value = arguments[key]
        kind = str(expected.get("type") or "string")
        check = _TYPE_CHECK.get(kind)
        if check is None or not check(value):
            return False, f"Argument '{key}' must be of type {kind}."
        if "enum" in expected and value not in expected["enum"]:
            # Enum membership is matched case-insensitively so that a natural
            # spelling ("Quads") resolves to the product's own value ("quads")
            # and the tool still receives a declared value only.
            folded = {str(item).casefold(): item for item in expected["enum"]}
            canonical = folded.get(str(value).casefold())
            if canonical is None:
                allowed = ", ".join(str(item) for item in expected["enum"])
                return False, f"Argument '{key}' must be one of: {allowed}."
            value = canonical
        if kind in {"integer", "number"}:
            if "minimum" in expected and float(value) < float(expected["minimum"]):
                return False, f"Argument '{key}' is below the allowed minimum."
            if "maximum" in expected and float(value) > float(expected["maximum"]):
                return False, f"Argument '{key}' is above the allowed maximum."
        cleaned[key] = value
    missing = [str(key) for key in (schema.get("required") or []) if key not in cleaned]
    if missing:
        return False, f"Missing required argument(s): {', '.join(missing)}."
    return True, cleaned


# --------------------------------------------------------------------------- #
# Tool context
# --------------------------------------------------------------------------- #


@dataclass
class AgentToolContext:
    """The verified product state every tool reads from.

    Constructed once per user turn. ``facts`` is the shared read-only projection
    the rest of the product already uses, so a tool cannot disagree with the UI.
    """

    profile: Mapping[str, Any]
    assessment: Mapping[str, Any]
    recommendation: Mapping[str, Any]
    decision: Mapping[str, Any]
    state: Any | None = None
    today: date | None = None
    _facts: dict[str, Any] | None = field(default=None, init=False, repr=False)

    @property
    def facts(self) -> dict[str, Any]:
        if self._facts is None:
            self._facts = ai_facts.build_personal_facts(
                dict(self.profile), dict(self.assessment), dict(self.recommendation), self.today)
        return self._facts

    @property
    def day(self) -> date:
        return self.today or date.today()

    def base_state(self) -> Any:
        """The client state, or the seeded state when the caller sent none."""
        if self.state is not None:
            return self.state
        _, seeded = state_service.base_state(self.profile.get("user_id"))
        return seeded


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


_SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-]{4,}")


def _safe_error(exc: BaseException) -> str:
    """A tool failure is reported by exception type: never a traceback or a secret."""
    return _SECRET_PATTERN.sub("sk-***", f"{type(exc).__name__}")


def resolve_groups(value: Any) -> tuple[str, ...] | None:
    """Resolve a muscle-group phrase the product taxonomy can map reliably."""
    groups, _note = ai_facts.muscle_groups_from_text(str(value or ""))
    return groups or None


def _shrink(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _shrink(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_shrink(item) for item in list(value)[:3]]
    if isinstance(value, str) and len(value) > 240:
        return value[:237] + "…"
    return value


def bound_payload(payload: Mapping[str, Any], max_chars: int = MAX_TOOL_OUTPUT_CHARS) -> dict[str, Any]:
    """Keep one tool result inside the prompt budget without losing its shape."""
    data = dict(payload)
    if len(json.dumps(data, default=str)) <= max_chars:
        return data
    trimmed = dict(_shrink(data))
    trimmed["truncated"] = True
    return trimmed


def _head(value: Any, limit: int = 3) -> list[Any]:
    return list(value or [])[:limit]


# --------------------------------------------------------------------------- #
# Tool handlers
# --------------------------------------------------------------------------- #


def _readiness(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    facts = context.facts["readiness"]
    return {
        "period": "today",
        "status": facts["status"],
        "index": facts["index"],
        "index_scale": dict(facts["index_scale"]),
        "baseline_confidence": facts["confidence"],
        "domains": dict(facts["domains"]),
        "contributors": _head(facts["contributors"]),
        "safety_flags": list(facts["safety_flags"]),
        "why_this_status": _head(context.assessment.get("why_this_status")),
        "limitations": _head(context.assessment.get("limitations")),
    }


def _current_recommendation(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    engine_summary = training_service.summary(context.recommendation)
    final_summary = response_service.apply_to_summary(
        engine_summary, context.decision, engine_summary.get("rir_guidance"))
    adaptation = final_summary.get("adaptation") or None
    return {
        "period": "today",
        "primary": final_summary.get("primary_name"),
        "training_type": final_summary.get("training_type"),
        "session_demand": final_summary.get("session_demand"),
        "base_session_demand": final_summary.get("base_session_demand"),
        "duration": final_summary.get("duration"),
        "rir_guidance": final_summary.get("rir_guidance"),
        "prescription": [
            {"exercise": item.get("name"), "sets": item.get("sets"), "reps": item.get("reps"), "rir": item.get("rir")}
            for item in (final_summary.get("exercises") or [])[:6]
        ],
        "alternatives": [item.get("name") for item in (final_summary.get("alternatives") or [])[:4]],
        "avoid": list(final_summary.get("avoid") or [])[:5],
        "rationale": _head(final_summary.get("rationale"), 4),
        "decision_factors": _head(context.recommendation.get("decision_factors"), 5),
        "personal_response_adjustment": {
            "applied": bool(context.decision.get("adjustment")),
            "label": adaptation.get("label") if adaptation else None,
            "from": context.decision.get("base_band"),
            "to": context.decision.get("final_band"),
        },
        "authority": "session demand and focus come from training_recommendation_engine.recommend_training",
    }


def _recent_training(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    limit = int(arguments.get("limit") or 5)
    rows = training_service.recent_sessions(dict(context.profile), max(1, min(14, limit)))
    result: dict[str, Any] = {
        "period": "most recent completed sessions, newest first",
        "sessions": rows,
        "session_count": len(rows),
    }
    requested = arguments.get("group")
    groups = resolve_groups(requested) if requested else None
    if groups:
        last = context.facts["muscle_last_trained"]
        result["requested_groups"] = list(groups)
        result["last_trained"] = {group: last.get(group) for group in groups}
    return result


def _training_exposure(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    entry = context.facts["weekly_exposure"]
    requested = arguments.get("group")
    groups = resolve_groups(requested) if requested else None
    selected = list(groups or tuple(entry["groups"]))
    return {
        "period": entry["period"],
        "unit": "weighted working sets",
        "weighting": "direct sets count 1.0, mapped secondary sets 0.5; not days and not sessions",
        "target_source": entry.get("target_source"),
        "groups": [
            {"group": group,
             "value": float((entry["groups"].get(group) or {}).get("value") or 0),
             "target": (entry["groups"].get(group) or {}).get("target")}
            for group in selected if group in entry["groups"]
        ],
        "training_days": context.facts["weekly_training_days"]["value"],
        "completed_sessions": context.facts["weekly_sessions"]["value"],
    }


def _personal_response(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    payload = response_service.payload(context.decision)
    summary = dict(payload.get("summary") or {})
    return {
        "available": payload.get("available"),
        "base_demand": payload.get("base_demand"),
        "final_demand": payload.get("final_demand"),
        "adjustment": payload.get("adjustment"),
        "direction": payload.get("direction"),
        "evidence": payload.get("evidence"),
        "reason": payload.get("reason"),
        "detail": payload.get("detail"),
        "confidence_state": payload.get("confidence_state"),
        "relevant_episodes": payload.get("relevant_episodes"),
        "relevant_band": (payload.get("relevant") or {}).get("band"),
        "consistency": {
            "label": (payload.get("consistency") or {}).get("label"),
            "counts": (payload.get("consistency") or {}).get("counts"),
        },
        "bands": [
            {"band": row.get("band"), "observations": row.get("observations"),
             "pattern": row.get("pattern"), "evidence": row.get("evidence")}
            for row in (summary.get("bands") or [])
        ],
        "episodes_complete": summary.get("episodes_complete"),
        "episodes_pending": summary.get("episodes_pending"),
        "note": summary.get("note") or payload.get("note"),
    }


def _recommendation_confidence(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    confidence = dict(context.decision.get("confidence") or {})
    coverage = dict(context.decision.get("coverage") or {})
    relevant = dict(context.decision.get("relevant") or {})
    return {
        "state": confidence.get("state"),
        "label": confidence.get("label"),
        "explanation": confidence.get("explanation"),
        "relevant_episodes": confidence.get("relevant_episodes"),
        "window_days": relevant.get("window_days"),
        "max_recent_episodes": relevant.get("max_episodes"),
        "episodes_complete": coverage.get("episodes_complete"),
        "note": confidence.get("note"),
    }


def _decision_trace(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    base = training_service.decision_trace(context.recommendation)
    rows = response_service.apply_to_trace(base, context.decision)
    return {
        "steps": [{"index": row.get("index"), "step": row.get("step"), "value": row.get("value")}
                  for row in rows[:12]],
        "step_count": len(rows),
        "note": "Deterministic explanation of the recorded decision, not model reasoning.",
    }


def _decision_explorer(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    change: dict[str, Any] = {"key": arguments.get("lever")}
    if arguments.get("group") is not None:
        groups = resolve_groups(arguments.get("group"))
        if groups:
            change["group"] = groups[0]
    if arguments.get("level") is not None:
        change["level"] = int(arguments["level"])
    result = explorer_service.explore(context.base_state(), change)
    return {
        "lever": result.get("lever"),
        "lever_label": result.get("lever_label"),
        "changed_input": result.get("changed_input"),
        "current": dict(result.get("current") or {}),
        "alternative": dict(result.get("alternative") or {}),
        "differences": list(result.get("differences") or [])[:5],
        "conclusion": result.get("conclusion"),
        "note": result.get("note"),
        "read_only_note": result.get("read_only_note"),
    }


def _session_calibration(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    active = dict(getattr(context.state, "active_session", None) or {})
    recorded = active.get("calibration") or {}
    summary = (calibration_service.summary(context.state) if context.state is not None
               else session_calibration.summarise([]))
    return {
        "active_session": {
            "primary_focus": active.get("primary_focus"),
            "session_demand": active.get("session_demand"),
            "planned_rir": active.get("planned_rir"),
        } if active else None,
        "checkpoint_recorded": bool(recorded),
        "latest_checkpoint": (recorded.get("result") if isinstance(recorded, Mapping) else None),
        "summary": summary,
        "outcomes": list(session_calibration.CALIBRATION_RESULTS),
        "scope": session_calibration.SCOPE,
        "meaning": "HOLD keeps the plan, EASE moves to the conservative end of the prescribed range, "
                   "OPTIONAL PUSH points at the harder end. None of them changes demand, focus, exercises or volume.",
    }


def _training_load(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    load = dict(context.facts["training_load"])
    return {
        "value": load.get("value"),
        "unit": "Training Load Points (pts)",
        "period": load.get("period"),
        "reference_value": load.get("reference_value"),
        "comparison": load.get("comparison"),
        "status": load.get("status"),
        "detail": load.get("detail"),
        "definition": load.get("definition"),
    }


def _personal_context(context: AgentToolContext, arguments: Mapping[str, Any]) -> dict[str, Any]:
    profile = dict(context.profile)
    recommendation = dict(context.recommendation)
    primary = dict(recommendation.get("primary") or {})
    facts = context.facts
    history = [row for row in (profile.get("training_history") or []) if row.get("completed", True)]
    return {
        "name": profile.get("name"),
        "goal": profile.get("training_goal"),
        "training_level": profile.get("training_level"),
        "programme_split": profile.get("training_split_preference"),
        "primary_activity": profile.get("primary_activity"),
        "personal_sleep_need": profile.get("personal_sleep_need"),
        "target_sessions_per_week": profile.get("target_sessions_per_week"),
        "weekly_set_targets": {str(key): value for key, value in (profile.get("weekly_set_targets") or {}).items()},
        "target_source": recommendation.get("target_source"),
        "today_programme": {"split": primary.get("split"), "focus": primary.get("focus")},
        "completed_sessions_7d": facts["weekly_sessions"]["value"],
        "recorded_sessions_total": len(history),
    }


# --------------------------------------------------------------------------- #
# The registry
# --------------------------------------------------------------------------- #


#: Both the product's canonical group names and the aliases an athlete uses.
_GROUP_ENUM = list(dict.fromkeys([*MUSCLE_GROUPS, *ai_facts.MUSCLE_ALIASES]))

_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_readiness",
        description=("Today's readiness status, index, baseline confidence, domain statuses, "
                     "main contributors and any safety flags."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "status": {"type": "string"}, "index": {"type": ["integer", "null"]},
            "baseline_confidence": {"type": "string"}, "domains": {"type": "object"},
            "contributors": {"type": "array"}, "safety_flags": {"type": "array"}}},
        source="readiness_engine.assess_readiness",
    ),
    ToolSpec(
        name="get_current_recommendation",
        description=("Today's final session recommendation: primary session, session demand, duration, "
                     "RIR guidance, prescription, alternatives, avoid list and rationale."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "primary": {"type": "string"}, "session_demand": {"type": "string"},
            "duration": {"type": "string"}, "rir_guidance": {"type": "string"},
            "alternatives": {"type": "array"}, "avoid": {"type": "array"}, "rationale": {"type": "array"}}},
        source="training_recommendation_engine.recommend_training",
    ),
    ToolSpec(
        name="get_recent_training",
        description=("Most recent completed sessions, newest first, with focus, session RPE, duration and "
                     "working sets; optionally the last trained date for one muscle group."),
        input_schema=_object_schema({
            "limit": {"type": "integer", "minimum": 1, "maximum": 14,
                      "description": "How many completed sessions to return."},
            "group": {"type": "string", "enum": _GROUP_ENUM,
                      "description": "Optional muscle group to resolve the last trained date for."},
        }),
        output_schema={"type": "object", "properties": {
            "sessions": {"type": "array"}, "session_count": {"type": "integer"},
            "last_trained": {"type": "object"}}},
        source="profile.training_history (completed sessions)",
    ),
    ToolSpec(
        name="get_training_exposure",
        description=("Weekly weighted working-set exposure per muscle group for the last seven days including "
                     "today, with the configured weekly targets."),
        input_schema=_object_schema({
            "group": {"type": "string", "enum": _GROUP_ENUM,
                      "description": "Optional muscle group to narrow the exposure to."},
        }),
        output_schema={"type": "object", "properties": {
            "period": {"type": "string"}, "unit": {"type": "string"}, "groups": {"type": "array"}}},
        source="training_recommendation_engine.weekly_training_exposure",
    ),
    ToolSpec(
        name="get_personal_response",
        description=("The Personal Response layer: whether today's demand was adjusted, the evidence, relevant "
                     "episodes, per-band patterns and the response confidence state."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "available": {"type": "boolean"}, "adjustment": {"type": "integer"},
            "base_demand": {"type": "string"}, "final_demand": {"type": "string"},
            "evidence": {"type": "string"}, "reason": {"type": "string"}, "bands": {"type": "array"}}},
        source="adaptive_response.evaluate",
    ),
    ToolSpec(
        name="get_recommendation_confidence",
        description=("How much recent personal evidence supports today's personalisation, with the recency "
                     "window and the counted episodes."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "state": {"type": "string"}, "label": {"type": "string"},
            "explanation": {"type": "string"}, "relevant_episodes": {"type": "integer"}}},
        source="adaptive_response.recommendation_confidence",
    ),
    ToolSpec(
        name="get_decision_trace",
        description="The recorded deterministic decision trace for today, including the Personal Response step.",
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "steps": {"type": "array"}, "step_count": {"type": "integer"}}},
        source="training_recommendation_engine + response_service.apply_to_trace",
    ),
    ToolSpec(
        name="run_decision_explorer",
        description=("Simulate exactly one changed input through the same deterministic engines and return the "
                     "comparison. Simulation only: nothing is saved."),
        input_schema=_object_schema({
            "lever": {"type": "string", "enum": ["soreness", "recovery", "personal_response"],
                      "description": "The single input to change."},
            "group": {"type": "string", "enum": _GROUP_ENUM,
                      "description": "Muscle group for the soreness lever."},
            "level": {"type": "integer", "minimum": 1, "maximum": 5,
                      "description": "Soreness level for the soreness lever, on the product's own 1-5 scale."},
        }, required=("lever",)),
        output_schema={"type": "object", "properties": {
            "lever": {"type": "string"}, "current": {"type": "object"},
            "alternative": {"type": "object"}, "conclusion": {"type": "string"}}},
        source="decision_explorer (read-only simulation)",
    ),
    ToolSpec(
        name="get_session_calibration_context",
        description=("In-session calibration context: the active session, any recorded checkpoint, the recorded "
                     "checkpoint history and the HOLD / EASE / OPTIONAL PUSH rule vocabulary and scope."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "active_session": {"type": "object"}, "latest_checkpoint": {"type": "string"},
            "summary": {"type": "object"}, "outcomes": {"type": "array"}, "scope": {"type": "string"}}},
        source="session_calibration",
    ),
    ToolSpec(
        name="get_training_load",
        description=("Training Load in points for the last seven complete calendar days against the preceding "
                     "21 days, with the engine's own definition."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "value": {"type": "number"}, "reference_value": {"type": "number"},
            "status": {"type": "string"}, "definition": {"type": "string"}}},
        source="readiness_engine.assess_readiness (training load domain)",
    ),
    ToolSpec(
        name="get_personal_context",
        description=("Stored profile settings: goal, training level, programme split, weekly set targets, target "
                     "sessions per week and recorded session counts."),
        input_schema=_object_schema(),
        output_schema={"type": "object", "properties": {
            "goal": {"type": "string"}, "programme_split": {"type": "string"},
            "weekly_set_targets": {"type": "object"}, "completed_sessions_7d": {"type": "integer"}}},
        source="stored profile settings",
    ),
)

_HANDLERS: dict[str, Callable[[AgentToolContext, Mapping[str, Any]], Mapping[str, Any]]] = {
    "get_readiness": _readiness,
    "get_current_recommendation": _current_recommendation,
    "get_recent_training": _recent_training,
    "get_training_exposure": _training_exposure,
    "get_personal_response": _personal_response,
    "get_recommendation_confidence": _recommendation_confidence,
    "get_decision_trace": _decision_trace,
    "run_decision_explorer": _decision_explorer,
    "get_session_calibration_context": _session_calibration,
    "get_training_load": _training_load,
    "get_personal_context": _personal_context,
}

_REGISTRY: dict[str, ToolSpec] = {spec.name: spec for spec in _SPECS}

#: Tool names in the order the product presents them in the tool trace.
TOOL_ORDER: tuple[str, ...] = tuple(spec.name for spec in _SPECS)


def tool_specs() -> list[ToolSpec]:
    return [spec for spec in _SPECS]


def tool_names() -> tuple[str, ...]:
    return TOOL_ORDER


def get_spec(name: Any) -> ToolSpec | None:
    return _REGISTRY.get(str(name or ""))


def is_registered(name: Any) -> bool:
    return str(name or "") in _REGISTRY


def catalogue() -> list[dict[str, Any]]:
    """The planner-visible view: names, descriptions and allowed arguments."""
    return [spec.catalogue_entry() for spec in _SPECS]


def label(name: str) -> str:
    spec = get_spec(name)
    if spec is None:
        return str(name)
    return TOOL_LABELS.get(spec.name, spec.name)


def trace_entry(name: str) -> dict[str, Any]:
    """One product-language row for the UI tool trace (never a developer view)."""
    spec = get_spec(name)
    return {
        "tool": str(name),
        "label": label(name),
        "source": spec.source if spec else "unknown",
        "operation": spec.operation if spec else READ_ONLY,
    }


def execute(name: Any, arguments: Any, context: AgentToolContext) -> dict[str, Any]:
    """Run one whitelisted tool. Refuses anything that is not in the registry."""
    spec = get_spec(name)
    if spec is None:
        return {"tool": str(name or ""), "ok": False, "error": "unknown_tool",
                "detail": "That tool is not part of the whitelist and was not executed."}
    valid, resolved = validate_arguments(spec, arguments)
    if not valid:
        return {"tool": spec.name, "ok": False, "error": "invalid_arguments", "detail": str(resolved)}
    handler = _HANDLERS.get(spec.name)
    if handler is None:
        return {"tool": spec.name, "ok": False, "error": "unknown_tool",
                "detail": "That tool is not part of the whitelist and was not executed."}
    try:
        payload = handler(context, resolved)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001 - a failing tool must never break the turn
        return {"tool": spec.name, "ok": False, "error": "tool_failure", "detail": _safe_error(exc)}
    return {
        "tool": spec.name,
        "ok": True,
        "operation": spec.operation,
        "source": spec.source,
        "data": bound_payload(dict(payload)),
    }
