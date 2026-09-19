"""V1.4 — Intent + tool selection for the Agent layer.

Strategy: **strict structured planner**, not native function calling.

Why, stated plainly: the production integration in this repository is a minimal
OpenAI-compatible ``/chat/completions`` client (``ai_engine.DeepSeekCoachProvider``)
that sends ``messages`` only. It declares no tool-calling capability, the
deployed model alias cannot be probed for reliable function calling from the test
suite, and a hidden capability assumption would be exactly the kind of
"pretend native tool calling exists" the architecture forbids. The planner
therefore asks the model for one strictly validated JSON object and executes
nothing until that object passes this module's schema checks.

Either strategy keeps the same guarantees, because the guarantees live in the
planner's output validation and in ``agent_tools``, not in the transport:

* a tool name that is not in the registry is never executed,
* an argument set that is not declared by the tool is never executed,
* at most ``MAX_TOOLS_PER_PLAN`` tools are chosen in one plan,
* if the model is unavailable, malformed, or picks nothing usable, a
  deterministic heuristic plan is used instead, so the Agent degrades to verified
  data rather than to general knowledge.

The planner only chooses *which verified facts to load*. It cannot answer the
user, and it cannot produce a training decision.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import agent_tools
import ai_facts
from decision_explorer import DEFAULT_SORENESS_LEVEL


#: Documented strategy for this version. See the module docstring.
PLANNER_STRATEGY = "structured_planner"

#: Native tool calling is deliberately *not* claimed. The value is reported by
#: ``capability_report`` so the architecture document and the API stay honest.
NATIVE_TOOL_CALLING_SUPPORTED = False
NATIVE_TOOL_CALLING_REASON = (
    "The production client is a minimal OpenAI-compatible chat-completions client that declares no tool/function "
    "support, and the deployed model alias cannot be capability-probed without a live provider call. V1.4 therefore "
    "uses a strictly validated structured planner and documents it instead of assuming native tool calling."
)

MAX_TOOLS_PER_PLAN = 5
MAX_PLAN_CHARS = 1200
MAX_HISTORY_MESSAGES = 4
MAX_HISTORY_MESSAGE_CHARS = 320

#: Intents the planner may report. Anything else is normalised rather than trusted.
INTENTS: tuple[str, ...] = (
    "explain_recommendation",
    "explain_readiness",
    "what_if",
    "response_history",
    "in_session_guidance",
    "training_load",
    "general_explanation",
)
DEFAULT_INTENT = "general_explanation"

#: The smallest useful default: what is today, and why. Deliberately cheap.
_DEFAULT_TOOLS: tuple[str, ...] = ("get_readiness", "get_current_recommendation")

#: Deterministic keyword -> tool coverage. Used when the planner is unavailable
#: and to complete a plan that is clearly missing a facet the question raised.
FACET_TOOLS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("harder than expected", "feels harder", "easier than expected", "checkpoint", "calibration", "ease", "hold on"),
     ("get_session_calibration_context",)),
    (("what if", "instead", "still want", "swap", "change what", "would change", "what changes"),
     ("run_decision_explorer",)),
    (("sore", "soreness", "tired", "fatigue", "heavy legs", "yesterday", "last few days"),
     ("get_recent_training", "get_training_exposure")),
    (("usually respond", "used to respond", "respond to", "response", "tolerance", "tolerate", "recently",
      "pattern", "how have i"),
     ("get_personal_response", "get_recommendation_confidence")),
    (("training load", "load", "how much work"), ("get_training_load",)),
    # "Why is today lighter / why this workout": the comparison the user is
    # asking about is recent training beside their own response pattern, so the
    # trace alone is not enough evidence.
    (("lighter", "easier than usual", "reduced", "why is today", "why did", "why is my", "why this"),
     ("get_decision_trace", "get_recent_training", "get_personal_response")),
    (("my goal", "programme", "program", "split", "target", "how many sessions do i", "plan"),
     ("get_personal_context",)),
)

#: A question about how the *current* session feels is answered by the in-session
#: calibration rules, not by a what-if simulation of a different input.
_IN_SESSION_PHRASES = ("harder than expected", "easier than expected", "feels harder", "feels easier",
                       "during the session", "mid-session", "checkpoint", "calibration")


def matched_facets(question: str) -> list[tuple[str, ...]]:
    """The deterministic facets a question raises, in the order they are covered."""
    lowered = str(question or "").casefold()
    in_session = any(phrase in lowered for phrase in _IN_SESSION_PHRASES)
    matched: list[tuple[str, ...]] = []
    for keywords, tools in FACET_TOOLS:
        if not any(keyword in lowered for keyword in keywords):
            continue
        if tools == ("run_decision_explorer",) and in_session:
            continue
        matched.append(tools)
    return matched


@dataclass(frozen=True)
class ToolRequest:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": dict(self.arguments)}


@dataclass(frozen=True)
class AgentPlan:
    """A validated plan. ``requests`` only ever contains whitelisted tools."""

    intent: str
    requests: tuple[ToolRequest, ...] = ()
    rejected: tuple[dict[str, str], ...] = ()
    source: str = "heuristic"
    error: str | None = None

    @property
    def usable(self) -> bool:
        return bool(self.requests)

    def as_trace(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "intent": self.intent,
            "tools": [request.name for request in self.requests],
            "rejected": [dict(row) for row in self.rejected],
            "error": self.error,
        }


# --------------------------------------------------------------------------- #
# Planner prompt
# --------------------------------------------------------------------------- #


_PLANNER_SYSTEM = (
    "You are the tool planner inside a training Coach. You never answer the user and you never decide training. "
    "Your only job is to choose which read-only verified product tools must be consulted before the answer is written. "
    "Rules: reply with a single JSON object and nothing else; use only the listed tool names; never invent a tool name, "
    "argument or value; use an empty argument object when a tool takes none; choose at most five tools; prefer the "
    "smallest set that covers the question; never include a tool for a fact the question does not need. "
    'JSON shape: {"intent": "<one of the listed intents>", "tools": [{"name": "<tool>", "arguments": {}}]}'
)


def build_planner_messages(question: str, context_digest: str,
                           history: Sequence[Mapping[str, str]] = ()) -> list[dict[str, str]]:
    catalogue = json.dumps(agent_tools.catalogue(), ensure_ascii=False, separators=(",", ":"))
    messages: list[dict[str, str]] = [{"role": "system", "content": _PLANNER_SYSTEM}]
    for message in history[-MAX_HISTORY_MESSAGES:]:
        if message.get("role") in {"user", "assistant"}:
            messages.append({"role": str(message["role"]),
                             "content": str(message.get("content", ""))[:MAX_HISTORY_MESSAGE_CHARS]})
    messages.append({
        "role": "user",
        "content": (
            f"Available tools (whitelist, read-only): {catalogue}\n"
            f"Allowed intents: {', '.join(INTENTS)}\n"
            f"Current verified product snapshot:\n{context_digest}\n"
            f"Question: {question}\n"
            "Reply with the JSON plan only."
        ),
    })
    return messages


# --------------------------------------------------------------------------- #
# Parsing and validation
# --------------------------------------------------------------------------- #


def _extract_json(text: str) -> Any:
    """The first JSON object in a draft, tolerating a fenced code block."""
    stripped = str(text or "").strip()
    if not stripped:
        return None
    stripped = re.sub(r"^```(?:json)?|```$", "", stripped, flags=re.MULTILINE).strip()
    try:
        return json.loads(stripped)
    except ValueError:
        pass
    start = stripped.find("{")
    while start != -1:
        try:
            value, _end = json.JSONDecoder().raw_decode(stripped[start:])
            return value
        except ValueError:
            start = stripped.find("{", start + 1)
    return None


def parse_plan(text: str, source: str = "planner") -> AgentPlan:
    """Validate a model draft against the registry. Nothing here is trusted."""
    raw = _extract_json(text)
    if not isinstance(raw, Mapping):
        return AgentPlan(intent=DEFAULT_INTENT, source=source, error="The plan was not a JSON object.")
    intent = str(raw.get("intent") or DEFAULT_INTENT)
    if intent not in INTENTS:
        intent = DEFAULT_INTENT
    entries = raw.get("tools")
    if not isinstance(entries, (list, tuple)):
        return AgentPlan(intent=intent, source=source, error="The plan contained no tool list.")

    requests: list[ToolRequest] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in list(entries)[:MAX_TOOLS_PER_PLAN + 4]:
        if not isinstance(entry, Mapping):
            rejected.append({"name": str(entry), "reason": "not_a_tool_request"})
            continue
        name = str(entry.get("name") or "")
        spec = agent_tools.get_spec(name)
        if spec is None:
            rejected.append({"name": name or "(empty)", "reason": "unknown_tool"})
            continue
        if spec.name in seen:
            continue
        if len(requests) >= MAX_TOOLS_PER_PLAN:
            rejected.append({"name": spec.name, "reason": "over_plan_limit"})
            continue
        valid, resolved = agent_tools.validate_arguments(spec, entry.get("arguments") or {})
        if not valid:
            rejected.append({"name": spec.name, "reason": f"invalid_arguments: {resolved}"})
            continue
        seen.add(spec.name)
        requests.append(ToolRequest(spec.name, dict(resolved)))
    return AgentPlan(intent=intent, requests=tuple(requests), rejected=tuple(rejected), source=source)


def request_plan(question: str, context_digest: str, history: Sequence[Mapping[str, str]] = (),
                 provider: Any | None = None) -> AgentPlan | None:
    """One planning call. Returns None when the provider cannot be used at all."""
    if provider is None or not getattr(provider, "configured", False):
        return None
    messages = build_planner_messages(question, context_digest, history)
    try:
        draft = provider.complete(messages)
    except Exception as exc:  # noqa: BLE001 - a planner failure must degrade, never break
        return AgentPlan(intent=DEFAULT_INTENT, source="planner",
                         error=f"planner_unavailable: {type(exc).__name__}")
    plan = parse_plan(draft, source="planner")
    if plan.error and not plan.requests:
        return plan
    return plan


# --------------------------------------------------------------------------- #
# Deterministic plan
# --------------------------------------------------------------------------- #


def heuristic_plan(question: str, intent: str | None = None) -> AgentPlan:
    """Deterministic tool selection: the Agent still uses verified tools offline."""
    selected = list(_DEFAULT_TOOLS)
    matched_intent = intent or DEFAULT_INTENT
    for tools in matched_facets(question):
        for tool in tools:
            if tool not in selected and len(selected) < MAX_TOOLS_PER_PLAN:
                selected.append(tool)
        if matched_intent == DEFAULT_INTENT:
            matched_intent = _INTENT_BY_TOOL.get(tools[0], DEFAULT_INTENT)
    requests = tuple(ToolRequest(name, default_arguments(name, question))
                     for name in selected if agent_tools.is_registered(name))
    return AgentPlan(intent=matched_intent, requests=requests, source="heuristic")


def default_arguments(name: str, question: str) -> dict[str, Any]:
    """Declared arguments for a deterministically selected tool.

    A deterministic choice must still be a *valid* choice, so the arguments are
    built from the product's own vocabulary: the soreness lever uses the
    product's default soreness level and the muscle group the question named, and
    the recent-training limit stays inside the tool's declared range.
    """
    lowered = str(question or "").casefold()
    groups, _note = ai_facts.muscle_groups_from_text(lowered)
    if name == "run_decision_explorer":
        if any(term in lowered for term in ("respond", "response", "pattern", "tolerate", "tolerance", "history")):
            return {"lever": "personal_response"}
        if groups or any(term in lowered for term in ("sore", "soreness", "heavy", "tired", "fatigue")):
            arguments: dict[str, Any] = {"lever": "soreness", "level": DEFAULT_SORENESS_LEVEL}
            if groups:
                arguments["group"] = groups[0]
            return arguments
        return {"lever": "recovery"}
    if name == "get_recent_training":
        arguments = {"limit": 5}
        if groups:
            arguments["group"] = groups[0]
        return arguments
    if name == "get_training_exposure" and groups:
        return {"group": groups[0]}
    return {}


_INTENT_BY_TOOL: dict[str, str] = {
    "run_decision_explorer": "what_if",
    "get_session_calibration_context": "in_session_guidance",
    "get_personal_response": "response_history",
    "get_recommendation_confidence": "response_history",
    "get_training_load": "training_load",
    "get_readiness": "explain_readiness",
    "get_current_recommendation": "explain_recommendation",
}


def coverage_tools(question: str, already: Sequence[str]) -> list[ToolRequest]:
    """Facets the question raised that the first step did not consult.

    Deterministic and bounded: this is the second (and last) retrieval step, so a
    multi-source question is covered without a second model call and without
    unbounded recursion.
    """
    seen = set(already)
    extra: list[ToolRequest] = []
    for tools in matched_facets(question):
        for tool in tools:
            if tool in seen or not agent_tools.is_registered(tool):
                continue
            seen.add(tool)
            extra.append(ToolRequest(tool, default_arguments(tool, question)))
            if len(extra) >= MAX_TOOLS_PER_PLAN:
                return extra
    return extra


def plan(question: str, context_digest: str, history: Sequence[Mapping[str, str]] = (),
         provider: Any | None = None) -> AgentPlan:
    """The planner entry point: model plan when possible, deterministic otherwise."""
    planned = request_plan(question, context_digest, history, provider)
    if planned is not None and planned.usable:
        return planned
    fallback = heuristic_plan(question)
    if planned is not None and planned.error:
        fallback = AgentPlan(intent=fallback.intent, requests=fallback.requests, source="heuristic",
                             rejected=planned.rejected, error=planned.error)
    return fallback


def capability_report() -> dict[str, Any]:
    """What this version actually does, published instead of assumed."""
    return {
        "strategy": PLANNER_STRATEGY,
        "native_tool_calling": NATIVE_TOOL_CALLING_SUPPORTED,
        "reason": NATIVE_TOOL_CALLING_REASON,
        "max_tools_per_plan": MAX_TOOLS_PER_PLAN,
        "validation": "closed JSON schema per tool; unknown names and undeclared arguments are refused",
    }
