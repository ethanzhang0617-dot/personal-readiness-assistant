"""Manual live smoke test for the DeepSeek explanation layer.

Not part of pytest: this is the only place that may spend real API calls. Run it
with a configured key:

    DEEPSEEK_API_KEY=... python3 scripts/deepseek_smoke.py

Without a key the script reports that nothing was called and exits cleanly. The
key value is never printed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import os
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ai_engine
from demo_data import build_demo_profiles
from readiness_engine import GREEN
from training_recommendation_engine import recommend_training


#: Explanation questions are the only ones allowed to reach the provider.
EXPLANATION_QUESTIONS = (
    "Why this workout?",
    "Can I train harder today?",
    "Explain my readiness.",
    "What should I adjust in my recent training?",
    "Why is my sleep affecting today's recommendation?",
    "What does RIR mean?",
)

#: Personal factual questions must be answered without any provider call.
FACTUAL_QUESTIONS = (
    "How much have I trained back this week?",
    "How many days have I trained back?",
    "What's my training load today?",
    "How long should I train today?",
    "What's my readiness today?",
    "How sore is my back?",
)


def _demo_context():
    profile = build_demo_profiles()[0]
    assessment = {
        "assessment_date": date.today().isoformat(), "overall_readiness": GREEN,
        "domains": {"autonomic": GREEN, "sleep": GREEN, "subjective": GREEN, "training_load": GREEN},
        "today_data": {"soreness": 1, "local_soreness": {}}, "key_contributors": [], "assessment_confidence": "NORMAL",
        "safety_flags": [], "decision_support": ["Use context."],
    }
    return profile, assessment, recommend_training(profile, assessment, profile["training_history"])


def main() -> int:
    secrets = {"DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", "")}
    if not ai_engine.ai_coach_enabled(secrets):
        print("No DEEPSEEK_API_KEY available: nothing was called.")
        print("Factual questions still work; explanation questions use the deterministic answer.")
        return 0

    profile, assessment, recommendation = _demo_context()
    print(f"Provider: {ai_engine.AI_PROVIDER_LABEL} · model: {ai_engine.deepseek_model_name(secrets)}")
    print(f"Thinking: disabled · max output: {ai_engine.MAX_OUTPUT_TOKENS} tokens\n")

    latencies: list[float] = []
    for question in EXPLANATION_QUESTIONS:
        started = time.monotonic()
        answer, provider, notice = ai_engine.get_ai_response(question, profile, assessment, recommendation, [], secrets)
        elapsed = time.monotonic() - started
        if provider == ai_engine.AI_PROVIDER_LABEL:
            latencies.append(elapsed)
        print(f"QUESTION: {question}\nPROVIDER: {provider}  ({elapsed:.2f}s)\nNOTICE: {notice or 'None'}\nANSWER: {answer}\n")

    print("--- factual regression (must not call the provider) ---")
    for question in FACTUAL_QUESTIONS:
        answer, provider, _ = ai_engine.get_ai_response(question, profile, assessment, recommendation, [], secrets)
        print(f"QUESTION: {question}\nPROVIDER: {provider}\nANSWER: {answer}\n")

    if latencies:
        print(f"Latency: median {statistics.median(latencies):.2f}s · range "
              f"{min(latencies):.2f}s–{max(latencies):.2f}s over {len(latencies)} provider answers")
    print(f"Diagnostics: {ai_engine.ai_diagnostics(secrets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
