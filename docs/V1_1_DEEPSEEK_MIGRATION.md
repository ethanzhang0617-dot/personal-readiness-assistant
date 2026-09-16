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

## Live QA — verified

Run against the real API with a locally configured key (key never printed). Three pre-patch passes
plus the post-patch re-run, **18 provider calls in total** (3 + 7 + 1 + 7), all to
`https://api.deepseek.com/chat/completions`:

| Item | Result |
|---|---|
| Authentication | PASS |
| Base URL | PASS |
| Model alias `deepseek-flash` | **verified** (accepted by the live endpoint) |
| Non-thinking mode | **verified** — the endpoint accepts `"thinking": {"type": "disabled"}` |
| Latency | median **2.9 s**, range **2.36 s – 3.85 s** |
| Token usage | prompt 812–1019 / completion 96–195 per call |
| Provider errors | none observed (no 401 / 429 / 5xx / timeout) |
| Personal factual + correction turns | **0 provider calls**, measured with a counting transport |

For context, the previous embedded Qwen model was measured at 3.9 s – 7.2 s per answer on CPU.

## Readiness-scale guard false positive (found by live QA, fixed)

**Root cause.** The product renders the readiness index as `index 71 / 100`, and DeepSeek naturally
wrote `Readiness is AMBER (71/100)`. The generic numeric guard allow-lists only numbers present in
the structured facts. The index *value* (71) was present, but the scale maximum (100) was not, so a
fully grounded draft was rejected with
`The draft introduced a number that is not in the verified facts: 100`.

**Fix.** The documented scale was promoted into the facts layer
(`readiness.index_scale = {"min": 0, "max": 100}`, single source `ai_facts.READINESS_INDEX_SCALE`) and
the guard now removes readiness-index + scale *spans* before the allow-list scan. The span must start
with the **verified** index value, so `71/100`, `71 / 100`, `71 out of 100` and `71 on a 0–100 scale`
are licensed while `100 minutes`, `100 weighted working sets`, `100 bpm`, `100 ms` and a new index
value such as `83/100` remain rejected. `facts_numbers` explicitly skips `index_scale`, so there is
**no global `100` whitelist**. `facts_for_prompt` now emits
`readiness index 71 on a 0–100 scale`, and the missing-index copy no longer renders
`index not available / 100`.

**Effect (same question set, live):**

| Route | Before patch | After patch |
|---|---|---|
| EXPLANATION | 0 / 5 accepted | **4 / 5 accepted** |
| GENERAL | 2 / 2 accepted | 2 / 2 accepted |

The single remaining EXPLANATION rejection is a *different*, pre-existing rule (see below). Post-patch
DeepSeek also stopped writing the bare `/100` ratio and followed the new prompt semantics
("readiness is AMBER (index 71)").

## Remaining observed issues (recorded, not changed)

1. **Alternative / swap guard.** `Can I swap the cable row for a machine row?` was rejected by
   `validate_llm_response` with *"The response did not distinguish the primary recommendation from an
   alternative."* Only one live sample exists; behaviour deliberately unchanged.
2. **Router: hypothetical advice phrased with a symptom word.** `Should I reduce volume if my back is
   still sore tomorrow?` routes to `PERSONAL_FACT` (the word "sore" maps to local soreness), so an
   advice question receives a factual answer about today's soreness. Pre-existing design; a future
   fix would separate hypothetical/future advice from current personal factual queries.
3. **Cost guard.** Still only bounded history, bounded output, context minimisation and the
   zero-call factual path. There is no server-side quota or counter.

## Still unverified

* No before/after measurement of dependency size or startup time was taken.
* Streamlit Cloud deployment with a configured secret has not been exercised.
* Real-device iOS / Android behaviour is unchanged from the earlier audits.

## Rollback

The migration is contained in the provider layer. Rolling back means restoring the previous
`ai_engine.py`, `requirements.txt`, `run_demo.command` and the Qwen-specific test assertions;
`ai_facts.py`, both statistical engines and the app's page structure are untouched by this phase.
