"""Manual real-model smoke test; no mock and no API key."""

from __future__ import annotations

from pathlib import Path
from datetime import date
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo_data import build_demo_profiles
from readiness_engine import GREEN
from training_recommendation_engine import recommend_training
from ai_engine import DEFAULT_EMBEDDED_MODEL, get_ai_response


profile = build_demo_profiles()[0]
assessment = {
    "assessment_date": date.today().isoformat(), "overall_readiness": GREEN,
    "domains": {"autonomic": GREEN, "sleep": GREEN, "subjective": GREEN, "training_load": GREEN},
    "today_data": {"soreness": 1, "local_soreness": {}}, "key_contributors": [], "assessment_confidence": "NORMAL",
}
recommendation = recommend_training(profile, assessment, profile["training_history"])
questions = (
    "What is RIR?",
    "Why was this workout recommended?",
    "Can I train legs instead?",
    "How many back sets have I done this week?",
    "Is training chest twice per week okay?",
)
for question in questions:
    answer, provider, notice = get_ai_response(question, profile, assessment, recommendation, secrets={"EMBEDDED_LLM_MODEL": DEFAULT_EMBEDDED_MODEL})
    print(f"QUESTION: {question}\nPROVIDER: {provider}\nNOTICE: {notice or 'None'}\nANSWER: {answer}\n")
