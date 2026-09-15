# V1.1 — DeepSeek Explanation Migration

Phase record for replacing the built-in Qwen explanation layer with the DeepSeek
API. The deterministic decision layer was not changed. This document describes
what moved, what stayed, and what is still unverified.

## Scope

Only one responsibility changed: **explanation generation**.

```text
User
  ↓
Router (ai_facts.route_question)
  ├── PERSONAL_FACT     → Deterministic Fact Resolver → verified answer   (no model, no API call)
  ├── CORRECTION        → verified re-check                               (no model, no API call)
  ├── UNRESOLVED_PERSONAL / SAFETY / SCOPE → deterministic answer         (no model, no API call)
  └── EXPLANATION / GENERAL → DeepSeek → validate → guard → else fallback
```

Unchanged, deliberately:

* `readiness_engine.py`, `training_recommendation_engine.py`, training load, weekly exposure,
  safety logic and Decision Trace semantics.
* The three guards: `ai_engine.validate_llm_response`, `ai_facts.guard_llm_response`,
  `ai_facts.guard_explanation_grounding`.
* The router and the structured fact layer in `ai_facts.py`.

## Provider contract

| Item | Value |
|---|---|
| Provider | DeepSeek, OpenAI-compatible chat completions |
| Endpoint | `POST https://api.deepseek.com/chat/completions` |
| Model | `deepseek-flash` (configurable via `DEEPSEEK_MODEL`) |
| Thinking | explicitly disabled — `"thinking": {"type": "disabled"}` |
| Transport | `requests.post` directly; no SDK, no LangChain, no agent framework |
| Output bound | `MAX_OUTPUT_TOKENS = 400` |
| Timeout | `REQUEST_TIMEOUT_SECONDS = 20.0` |
| Conversation bound | last 8 turns, each truncated to 500 characters |
| Temperature | 0.3 |

Only ~4k tokens of input are expected per call: the profile basics plus
`ai_facts.facts_for_prompt(facts)`, which emits unit-bearing context and never a
bare personal number.

## Credentials

* Read order: Streamlit secrets `DEEPSEEK_API_KEY`, then the `DEEPSEEK_API_KEY` environment variable.
* Never hardcoded, committed, printed, written to browser storage or sent to the frontend.
* `ai_diagnostics()` reports **Configured** / **Not configured**, never the value.
* Provider failures are redacted (`_redact()`) before they reach diagnostics, so a key fragment
  cannot leak into an error string.
* `.streamlit/secrets.toml` stays gitignored; `.streamlit/secrets.toml.example` holds placeholders only.

## Context minimisation and privacy

Sent to the provider when, and only when, a user asks an explanation question:

* profile basics: name, goal, training level, preferred split;
* today's readiness status, index, baseline confidence, domain statuses and contributors;
* today's primary recommendation, session demand, duration, prescription, alternatives, avoid list, rationale;
* the 7-day weighted-working-set exposure summary and completed training days/sessions;
* recent completed sessions (bounded) and today's reported local soreness;
* signals (HRV, resting HR, sleep) and training load in AU;
* the last 8 conversation turns.

Never sent: the full 30+ day raw history, the IndexedDB document, the export backup, other
profiles' data, or the API key itself.

Disclosure updated in three places: the Coach "How the Coach works" panel, the About page
**Data & Privacy** section, and the first-use privacy notice.

## Degradation rules

| Condition | Behaviour |
|---|---|
| No API key | deterministic answer + *AI explanation is temporarily unavailable* |
| `DISABLE_AI_COACH` / legacy `DISABLE_EMBEDDED_LLM` | deterministic answer, explanation layer off |
| Timeout, network error | deterministic answer, no crash |
| HTTP 401 / 429 / 5xx | deterministic answer; only the status code is retained |
| Invalid, empty or non-JSON response | deterministic answer |
| Draft rejected by a guard | deterministic answer + *The AI draft did not pass factual validation…* |

There is no second model fallback. The chain is **DeepSeek → deterministic**, never
DeepSeek → Qwen → deterministic.

## File-by-file change

| File | Change |
|---|---|
| `ai_engine.py` | Qwen loading/`st.cache_resource`/torch-transformers removed; `DeepSeekCoachProvider`, request builder, diagnostics, redaction and provider-neutral labels added |
| `app.py` | provider-neutral `kind` detection, DeepSeek metadata, privacy copy, spinner wording |
| `requirements.txt` | `transformers` and `torch` removed; `requests` declared explicitly |
| `run_demo.command` | dependency preflight and console copy updated |
| `.streamlit/secrets.toml.example` | `DEEPSEEK_API_KEY` placeholder, optional overrides |
| `scripts/deepseek_smoke.py` | replaces `scripts/qwen_smoke.py`; the only place allowed to make live calls |
| `test_app.py` | Qwen assertions replaced; DeepSeek request, guard, fallback, privacy and zero-call tests added |
| `README.md` | AI architecture, deployment, privacy and file-list sections rewritten |

## Tests

Unit tests never contact the provider: they inject a fake transport with
`monkeypatch.setattr(ai_engine.requests, "post", ...)`. Covered:

* request construction against the official endpoint, `deepseek-flash`, bounded output, non-thinking flag;
* missing key, disabled deployment, timeout, network error, 401, 429, 500, invalid and empty responses;
* personal factual questions and correction turns make **zero** provider calls;
* context minimisation (no other profile, no `user_id`, no backup keys, no full history) and history bounding;
* hallucination rejection: new number, unit drift to days, replaced primary recommendation, invented HRV,
  invented duration, invented rationale;
* provider metadata and diagnostics without exposing the key.

## Unverified (honest list)

* No live DeepSeek call has been made on this machine: there is no `DEEPSEEK_API_KEY` available.
  Response latency, real token usage, whether the serving endpoint accepts
  `"thinking": {"type": "disabled"}`, and the availability of the `deepseek-flash` alias are
  therefore **not confirmed against the live API**.
* No before/after measurement of dependency size or startup time was taken.
* Streamlit Cloud deployment with a configured secret has not been exercised.

Next verification step: set the key locally and run
`DEEPSEEK_API_KEY=... python scripts/deepseek_smoke.py` (6 explanation questions plus the factual
regression set), then confirm the latency median/range and that factual turns still report
`Verified data` with no provider call.

## Rollback

The migration is contained in the provider layer. Rolling back means restoring the previous
`ai_engine.py`, `requirements.txt`, `run_demo.command` and the Qwen-specific test assertions;
`ai_facts.py`, both statistical engines and the app's page structure are untouched by this phase.
