"""Optional local language layer. Product decisions remain deterministic."""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Any, Mapping, Sequence

import streamlit as st

import ai_facts
from readiness_engine import STOP


DEFAULT_EMBEDDED_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
MAX_NEW_TOKENS = 110
_loaded_model_id: str | None = None
_last_model_error: str | None = None
_last_generation_seconds: float | None = None
_model_load_seconds: float | None = None
_generation_lock = threading.Lock()
_diag: dict[str, Any] = {"model_requested": False, "model_downloaded": False, "tokenizer_loaded": False, "model_loaded": False, "generation_attempted": False, "generation_completed": False, "validation_accepted": False, "provider_used": "Rule-based fallback", "stage": None, "last_validation_reason": "Not requested"}

#: The model may explain verified facts, never decide them. Personal factual
#: questions never reach the model at all (see ai_facts.route_question).
_SYSTEM_PROMPT = (
    "You are a concise, context-aware training coach. You explain and discuss; the deterministic engines and the "
    "verified structured personal facts decide. Rules you must follow: never invent personal metrics; never change a "
    "recorded number; never change a unit; weekly exposure represents training-set exposure (weighted working sets), "
    "not days trained and not sessions; session duration is not training load; training load and session duration are "
    "different concepts; if a personal fact is not provided, say it is unavailable; do not infer missing personal "
    "history; do not override or replace the deterministic primary recommendation; clearly distinguish a primary "
    "recommendation from a rule-generated alternative. You may answer general training and recovery questions with "
    "general sports-science knowledge when the question is not about the user's own recorded data. Do not diagnose "
    "medical conditions, predict injury, or reveal hidden chain-of-thought."
)


def _setting(secrets: Mapping[str, Any] | None, name: str) -> str:
    try:
        secret = secrets.get(name, "") if secrets is not None else ""
    except Exception:
        secret = ""
    return str(secret or os.getenv(name, "")).strip()


def _is_true(value: str) -> bool:
    return value.casefold() in {"1", "true", "yes", "on"}


def embedded_model_name(secrets: Mapping[str, Any] | None = None) -> str:
    return _setting(secrets, "EMBEDDED_LLM_MODEL") or DEFAULT_EMBEDDED_MODEL


def ai_diagnostics(secrets: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"Model": embedded_model_name(secrets), "Architecture": "Embedded local inference", "API": "None", "API key": "None", "Device": "CPU", "Model requested": "Yes" if _diag["model_requested"] else "No", "Model downloaded": "Yes" if _diag["model_downloaded"] else "No", "Tokenizer loaded": "Yes" if _diag["tokenizer_loaded"] else "No", "Model loaded": "Yes" if _diag["model_loaded"] else "No", "Generation attempted": "Yes" if _diag["generation_attempted"] else "No", "Generation completed": "Yes" if _diag["generation_completed"] else "No", "Validation accepted": "Yes" if _diag["validation_accepted"] else "No", "Provider": _diag["provider_used"], "Model load time": f"{_model_load_seconds:.2f}s" if _model_load_seconds is not None else "—", "Generation time": f"{_last_generation_seconds:.2f}s" if _last_generation_seconds is not None else "—", "Last error stage": _diag.get("stage") or "—", "Last validation reason": _diag.get("last_validation_reason", "Not requested"), "Last exception": _last_model_error or "None"}


@st.cache_resource(show_spinner=False)
def load_embedded_model(model_id: str) -> tuple[Any, Any]:
    """Lazy-load the small public model on the first explicit enhancement."""
    global _loaded_model_id, _model_load_seconds
    started = time.monotonic()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    _diag["stage"] = "TOKENIZER LOAD"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    _diag["tokenizer_loaded"] = True
    _diag["stage"] = "MODEL LOAD"
    # Keep dependencies minimal for Streamlit Cloud; ``torch_dtype=auto`` uses
    # the checkpoint dtype without requiring accelerate or a quantisation stack.
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto")
    model.to("cpu")
    model.eval()
    _loaded_model_id = model_id
    _diag["model_downloaded"] = True
    _diag["model_loaded"] = True
    _model_load_seconds = time.monotonic() - started
    return tokenizer, model


def _recommendation_facts(recommendation: Mapping[str, Any] | None) -> str:
    if not recommendation:
        return "No workout recommendation has been generated yet."
    primary = recommendation["primary"]
    alternatives = ", ".join(item["name"] for item in recommendation.get("alternatives", [])) or "None"
    avoid = ", ".join(recommendation.get("avoid", [])) or "None"
    exposure = ", ".join(f"{key} {value:g}" for key, value in recommendation.get("weekly_exposure", {}).items())
    targets = ", ".join(f"{key} {value:g}" for key, value in recommendation.get("weekly_targets", {}).items())
    recent = "; ".join(f"{item.get('date')}: {item.get('primary_focus', item.get('training_type'))} (RPE {item.get('session_rpe', 'not recorded')})" for item in recommendation.get("recent_training", [])[:7]) or "None"
    return (f"Primary recommendation: {primary['name']}. Session demand: {recommendation['intensity']}. Duration: {recommendation['duration']}. "
            f"Alternatives: {alternatives}. Avoid today: {avoid}. Rationale: {'; '.join(recommendation.get('rationale', []))}. "
            f"Recent training: {recent}. Current seven-day exposure: {exposure}. Weekly targets: {targets}.")


def validate_llm_response(text: str, readiness_status: str, primary_workout: str | None = None, question: str = "", recommendation: Mapping[str, Any] | None = None) -> tuple[bool, str]:
    """Reject only an explicit contradiction of the overall status."""
    found = re.findall(r"(?:overall\s+)?readiness\s+(?:status\s+)?(?:is|:)?\s*(green|amber|red)", text.casefold())
    contradictory = [value.upper() for value in found if value.upper() != readiness_status.upper()]
    if contradictory:
        return False, f"Explicit overall readiness contradiction: {contradictory[0]}"
    if primary_workout:
        claims = re.findall(r"(?:primary recommendation|today'?s (?:approved )?workout)\s+(?:is|:)\s*([^\n.]+)", text, flags=re.IGNORECASE)
        if claims and all(primary_workout.casefold() not in claim.casefold() for claim in claims):
            return False, "The response replaced the recorded primary recommendation."
    q = question.casefold()
    if "what is rir" in q and "repetitions in reserve" not in text.casefold():
        return False, "The response did not correctly define RIR."
    if recommendation and any(term in q for term in ("sets this week", "how many back sets", "how many chest sets", "how many leg sets")):
        mentioned = [group for group in recommendation.get("weekly_exposure", {}) if group.casefold() in q]
        for group in mentioned:
            expected = f"{float(recommendation['weekly_exposure'][group]):g}"
            if expected not in text:
                return False, f"The response did not preserve the recorded {group} exposure."
    if primary_workout and ("why" in q and any(term in q for term in ("recommend", "workout", primary_workout.casefold()))) and primary_workout.casefold() not in text.casefold():
        return False, "The contextual explanation did not identify the recorded primary recommendation."
    if primary_workout and any(term in q for term in ("instead", "alternative", "swap")):
        lower = text.casefold()
        if primary_workout.casefold() not in lower or "alternative" not in lower:
            return False, "The response did not distinguish the primary recommendation from an alternative."
    return True, "No explicit overall readiness contradiction"


def rule_based_answer(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any], recommendation: Mapping[str, Any] | None = None) -> str:
    q = question.casefold()
    status = assessment["overall_readiness"]
    contributors = "; ".join(assessment.get("key_contributors", [])[:3]) or "no material adverse contributors were detected"
    if status == STOP:
        flags = ", ".join(assessment.get("safety_flags", [])) or "a current safety concern"
        return f"Safety mode is active because you selected {flags}. Normal workout guidance is disabled: pause demanding training and seek appropriate assessment for acute or concerning symptoms."
    if any(term in q for term in ("chest pain", "fainting", "severe shortness", "acute injury", "fever", "neurological")):
        return "This Coach cannot assess serious symptoms. Stop demanding training and seek appropriate medical assessment; seek urgent local help if symptoms are severe or worsening."
    # Personal facts are answered from the structured fact layer, never from keywords
    # or model output (hotfix AI-01).
    facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
    route = ai_facts.route_question(question, (), facts)
    if route.kind == "PERSONAL_FACT":
        return ai_facts.grounded_answer(route, facts)
    if route.kind == "UNRESOLVED_PERSONAL":
        return ai_facts.CLARIFICATION
    if route.kind == "CORRECTION":
        return ai_facts.correction_answer(None, facts, None)
    if "capital of japan" in q or "capital of" in q:
        return "This Coach is designed for training, readiness and recovery questions."
    if q.strip() in {"what is rir", "what's rir", "define rir"} or "what is rir" in q:
        return "RIR means repetitions in reserve: how many good repetitions you estimate you could still perform at the end of a set. For example, 2 RIR means stopping when you believe about two quality repetitions remain."
    if "what is rpe" in q or "what's rpe" in q:
        return "RPE is a perceived-effort scale. Session-RPE is commonly recorded from 1 to 10 after training and can be combined with duration to estimate internal load. It is a practical monitoring measure, not a diagnosis."
    if "failure" in q:
        return "You do not need to take every set to failure. Leaving repetitions in reserve can preserve technique and manage fatigue; the appropriate effort depends on the exercise, goal and today's readiness."
    if "chest twice" in q or "twice a week" in q:
        return "Training chest twice per week can be a reasonable way to distribute weekly volume when total sets, exercise quality and recovery are managed. Your current weekly exposure and today's recommendation should guide whether another chest session is useful today."
    if "deload" in q:
        return "A deload is a planned period of lower training demand, often used when fatigue is accumulating or performance and motivation are persistently affected. The exact format should fit the person's context rather than a fixed universal schedule."
    if recommendation and any(term in q for term in ("how many", "sets this week", "trained this week", "this week")):
        exposure = recommendation.get("weekly_exposure", {})
        for group, value in exposure.items():
            if group.casefold() in q or (group == "Hamstrings / Glutes" and any(term in q for term in ("hamstring", "glute"))):
                return f"You have logged **{value:g} effective {group.lower()} sets** in the current seven-day window. Direct sets count as 1.0 and mapped indirect sets as 0.5, so this is a transparent exposure estimate rather than an exact stimulus measure."
    if any(term in q for term in ("workout", "train today", "back", "legs", "cardio", "swap", "recommend", "recent training", "rest")) and recommendation:
        primary = recommendation["primary"]
        rationale = " ".join(recommendation.get("rationale", [])[:3])
        alternatives = {item["name"]: item for item in recommendation.get("alternatives", [])}
        if "cardio" in q and primary.get("training_type") != "Aerobic":
            aerobic = next((item for item in recommendation.get("alternatives", []) if item.get("training_type") == "Aerobic"), None)
            if aerobic:
                return f"**{primary['name']} remains the primary recommendation.** {aerobic['name']} is a listed rule-generated alternative at {aerobic['intensity']}; choose it only as an alternative, not as a silent replacement. {rationale}"
            return f"**{primary['name']} remains the primary recommendation.** Cardio is not one of today's two listed alternatives. If you independently choose easy aerobic work, treat it as a lower-demand substitute and respect the current avoid-today and safety guidance."
        if "leg" in q and primary["name"] != "Legs":
            permitted = alternatives.get("Legs")
            if permitted:
                return f"**{primary['name']} remains the primary recommendation.** Legs are available as a rule-generated alternative, but consider today's local soreness, recent lower-body work and the listed avoid-today guidance. {rationale}"
            return f"**{primary['name']} remains the primary recommendation.** Legs are not a current rule-generated alternative. {rationale} Check the avoid-today list and choose a lower-conflict option."
        return f"Today's primary recommendation is **{primary['name']}** ({recommendation['intensity']}, {recommendation['duration']}). {rationale} Alternatives remain clearly labelled and do not replace the primary recommendation."
    if any(term in q for term in ("why", "amber", "red", "green", "baseline", "hrv")):
        return f"Your readiness is **{status}**. The main context is {contributors}. This comparison uses {profile['name']}'s own history rather than universal HRV or resting-heart-rate cut-offs."
    if any(term in q for term in ("hard", "intensity", "session")):
        return f"For the current **{status}** status: " + " ".join(assessment["decision_support"][:2])
    return "Ask me about readiness, training volume, RIR/RPE, recent completed sessions, today's recommendation or recovery."


def get_instant_response(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any], recommendation: Mapping[str, Any] | None = None) -> tuple[str, str, None]:
    provider = "Safety rule" if assessment["overall_readiness"] == STOP else "Instant explanation"
    return rule_based_answer(question, profile, assessment, recommendation), provider, None


def _generate(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any], recommendation: Mapping[str, Any], model_id: str, history: Sequence[Mapping[str, str]] = ()) -> str:
    tokenizer, model = load_embedded_model(model_id)
    facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
    context = (f"Profile: {profile['name']}; goal: {profile.get('training_goal', 'General Fitness')}; "
               f"training level: {profile.get('training_level', 'Not recorded')}; "
               f"preferred split: {profile.get('training_split_preference', 'No Preference')}.\n"
               + ai_facts.facts_for_prompt(facts))
    system_prompt = _SYSTEM_PROMPT
    messages = [{"role": "system", "content": system_prompt}]
    for message in list(history)[-8:]:
        if message.get("role") in {"user", "assistant"}:
            messages.append({"role": message["role"], "content": str(message.get("content", ""))[:500]})
    messages.append({"role": "user", "content": f"Verified structured personal facts (the only permitted source of personal numbers):\n{context}\nQuestion: {question}"})
    if hasattr(tokenizer, "apply_chat_template"):
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
    else:
        inputs = tokenizer(messages[-1]["content"], return_tensors="pt", truncation=True, max_length=480)
    _diag["stage"] = "GENERATION"
    with _generation_lock:
        output = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    text = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    _diag["generation_completed"] = True
    if not text:
        raise ValueError("The embedded model returned an empty explanation")
    return text


def get_ai_response(question: str, profile: Mapping[str, Any], assessment: Mapping[str, Any], recommendation: Mapping[str, Any], history: Sequence[Mapping[str, str]] = (), secrets: Mapping[str, Any] | None = None) -> tuple[str, str, str | None]:
    """Answer contextually while deterministic engines retain decision authority."""
    facts = ai_facts.build_personal_facts(profile, assessment, recommendation)
    route = ai_facts.route_question(question, history, facts)
    _diag["last_route"] = route.as_trace()
    if assessment["overall_readiness"] == STOP:
        return rule_based_answer(question, profile, assessment, recommendation), "Safety rule", None
    if route.kind == "SAFETY":
        return rule_based_answer(question, profile, assessment, recommendation), "Safety rule", None
    if route.kind == "PERSONAL_FACT":
        # Deterministic layer answers; the model is not consulted, so it cannot
        # invent a number, unit or period for the user's own data.
        return ai_facts.grounded_answer(route, facts), "Verified data", "Answered from your recorded data. No model wording was used."
    if route.kind == "UNRESOLVED_PERSONAL":
        return ai_facts.CLARIFICATION, "Verified data", "The question could not be mapped to a supported personal metric, so no model was used."
    if route.kind == "CORRECTION":
        previous_route = ai_facts.route_question(route.previous_question or "", (), facts)
        if previous_route.kind != "PERSONAL_FACT":
            # A challenge can follow another challenge ("Are you sure?" after a
            # correction, or after a non-factual question). Walk back to the most
            # recent question that asked for a verifiable personal fact.
            for message in reversed(list(history)):
                if message.get("role") != "user":
                    continue
                candidate = ai_facts.route_question(str(message.get("content", "")), (), facts)
                if candidate.kind == "PERSONAL_FACT":
                    previous_route = candidate
                    break
        previous_answer = next((str(message.get("content", "")) for message in reversed(list(history)) if message.get("role") == "assistant"), None)
        answer = ai_facts.correction_answer(previous_route if previous_route.kind == "PERSONAL_FACT" else None, facts, previous_answer)
        return answer, "Verified data", "Your previous answer was re-checked against your recorded data."
    if _is_true(_setting(secrets, "DISABLE_EMBEDDED_LLM")):
        return rule_based_answer(question, profile, assessment, recommendation), "Instant explanation", "The embedded AI is disabled for this deployment."
    try:
        started = time.monotonic()
        _diag["model_requested"] = True
        _diag["generation_attempted"] = True
        _diag["generation_completed"] = False
        _diag["validation_accepted"] = False
        _diag["stage"] = "GENERATION"
        explanation = _generate(question, profile, assessment, recommendation, embedded_model_name(secrets), history[-8:])
        global _last_generation_seconds
        _last_generation_seconds = time.monotonic() - started
        approved = recommendation["primary"]["name"]
        accepted, validation_reason = validate_llm_response(explanation, str(assessment["overall_readiness"]), approved, question, recommendation)
        if accepted:
            accepted, validation_reason = ai_facts.guard_llm_response(explanation, facts, question, route)
        if accepted and route.kind == "EXPLANATION":
            accepted, validation_reason = ai_facts.guard_explanation_grounding(explanation, facts)
        if not accepted:
            _diag["stage"] = "VALIDATION"
            _diag["last_validation_reason"] = validation_reason
            raise ValueError(validation_reason)
        _diag["validation_accepted"] = True
        _diag["provider_used"] = "Built-in AI"
        _diag["last_validation_reason"] = validation_reason
        return explanation, "Built-in AI · Qwen2.5-0.5B", None
    except Exception as exc:
        global _last_model_error
        _last_model_error = f"{type(exc).__name__}: {str(exc)[:280]}"
        _diag["provider_used"] = "Rule-based fallback"
        _diag["stage"] = _diag.get("stage") or "MODEL LOAD"
        if _diag.get("stage") != "VALIDATION":
            _diag["last_validation_reason"] = "Fallback retained the canonical deterministic answer."
        notice = ("The embedded draft did not pass factual validation, so the verified deterministic answer is shown."
                  if _diag.get("stage") == "VALIDATION" else
                  "The embedded model could not load or respond. The deterministic recommendation remains available.")
        return rule_based_answer(question, profile, assessment, recommendation), "Instant explanation", notice


def ai_engine_status(secrets: Mapping[str, Any] | None = None) -> str:
    return "Built-in Qwen AI is ready" if _loaded_model_id else "Deterministic Coach fallback is ready · Qwen loads on first Coach question"
