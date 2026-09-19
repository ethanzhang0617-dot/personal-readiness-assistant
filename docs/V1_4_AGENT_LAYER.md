# V1.4 — Agent Layer

**Project:** Agentic Sports-Science Adaptive Training Decision System
（中文：基于运动科学与 Agent 的自适应训练决策系统）— formerly Personal Readiness Assistant,
which remains the name used through the V1.3/V1.4 release records below.

**Branch:** `v1.4-agent-layer` (created from the V1.3 HEAD `55f05d4`)
**Status:** implemented, tested, documented. No new chatbot, no second DeepSeek
integration, no autonomous LLM training decisions.

```
USER
 ↓
AI COACH
 ↓
AGENT ORCHESTRATOR            agent_orchestrator.py
 ↓
INTENT + TOOL SELECTION       agent_planner.py  (strict structured planner)
 ↓
DETERMINISTIC TOOLS           agent_tools.py    (whitelist, read-only)
 ↓
VERIFIED STRUCTURED RESULTS   agent_context.py  (structured context + memory)
 ↓
DEEPSEEK                      ai_engine.py      (the existing provider)
 ↓
GROUNDED FINAL RESPONSE       agent_guard.py    (grounding + safety + authority)
```

The Agent decides **which verified product information to consult**. The
deterministic engines still decide the training.

---

## 1. Audit of the existing product (what V1.4 reuses)

Nothing was rebuilt. The layers below already existed and are called unchanged:

| Existing capability | Entry point reused by V1.4 |
|---|---|
| DeepSeek provider | `ai_engine.DeepSeekCoachProvider` (`/chat/completions`, non-thinking) |
| Grounding prompt | `ai_engine.system_prompt()` (new accessor over the V1.1 `_SYSTEM_PROMPT`) |
| Coaching entry | `ai_engine.get_ai_response()` (routing, notices, deterministic answers) |
| Deterministic answers | `ai_engine.rule_based_answer()`, `ai_facts.grounded_answer()` |
| Personal facts | `ai_facts.build_personal_facts()` |
| Intent router | `ai_facts.route_question()` |
| Fact guards | `ai_facts.guard_llm_response()`, `guard_explanation_grounding()` |
| Readiness | `backend.services.readiness_service` → `readiness_engine.assess_readiness` |
| Recommendation | `backend.services.training_service` → `training_recommendation_engine.recommend_training` |
| Weekly exposure | `training_recommendation_engine.weekly_training_exposure` |
| Recent training | stored `profile.training_history` completed rows |
| Personal Response | `backend.services.response_service` → `adaptive_response.evaluate` |
| Recommendation Confidence | `adaptive_response.recommendation_confidence` |
| Decision Trace | `training_recommendation_engine` trace + `response_service.apply_to_trace` |
| Decision Explorer | `decision_explorer` + `backend.services.explorer_service` (simulation only) |
| Session Calibration | `session_calibration` + `backend.services.calibration_service` |
| Client-owned state | `backend.services.state_service` (`UserState`, browser-owned) |
| Coach API | `POST /api/state/coach` (upgraded internally), new `POST /api/state/coach/agent` |
| Response contract | `backend.services.coach_service.classify_provider()` (new public accessor) |

---

## 2. Agent Tool Registry (`agent_tools.py`)

Eleven tools, each an explicit wrapper around a capability the product already
ships. There is no generic dispatcher: a name that is not in the registry cannot
be executed, and an argument set that is not declared by the tool cannot be
passed on.

| Tool | Source engine | Operation |
|---|---|---|
| `get_readiness` | `readiness_engine.assess_readiness` | read-only |
| `get_current_recommendation` | `training_recommendation_engine.recommend_training` | read-only |
| `get_recent_training` | stored completed sessions | read-only |
| `get_training_exposure` | `weekly_training_exposure` | read-only |
| `get_personal_response` | `adaptive_response.evaluate` | read-only |
| `get_recommendation_confidence` | `adaptive_response.recommendation_confidence` | read-only |
| `get_decision_trace` | deterministic trace + Personal Response step | read-only |
| `run_decision_explorer` | `decision_explorer` (one input changed, nothing saved) | read-only |
| `get_session_calibration_context` | `session_calibration` | read-only |
| `get_training_load` | readiness engine, training-load domain | read-only |
| `get_personal_context` | stored profile settings | read-only |

Every tool declares five things: `name`, `description`, a typed `input_schema`,
a typed `output_schema`, and its `source` engine. The error behaviour is one
shared contract: a structured `{ok: false, error: unknown_tool |
invalid_arguments | tool_failure}` object, never an exception.

### Tool safety

No tool can change readiness, override a recommendation, change Personal
Response rules, change Recommendation Confidence, change Training Load, change
weekly exposure, modify a scientific threshold or a safety rule, execute
arbitrary code, read an arbitrary file, call an arbitrary URL or run a shell
command. There is no write tool in V1.4: tool **use** is the feature.

Two mechanical guarantees back this up:

* `validate_arguments()` is a closed schema — unknown keys, wrong types,
  undeclared enum values and out-of-range numbers are refused before the handler
  runs (enum matching is case-insensitive but always resolves to a declared
  value);
* a tool result is size-bounded (`MAX_TOOL_OUTPUT_CHARS = 3200`) and always
  JSON-compatible; a raw engine object never reaches the model.

---

## 3. Planner: structured planner, not native tool calling (`agent_planner.py`)

**Strategy used: strict structured planner.** This is deliberate and published
at `GET /api/health` → `agent.strategy`, with `native_tool_calling: false`.

Why: the production integration is a minimal OpenAI-compatible
`/chat/completions` client that sends `messages` only. It declares no
tool-calling capability, and the deployed model alias cannot be capability-probed
from the test suite without a live provider call. Assuming native function
calling would be exactly the "pretend it exists" failure the architecture
forbids, so V1.4 asks for one strictly validated JSON object instead:

```json
{"intent": "explain_recommendation",
 "tools": [{"name": "get_readiness", "arguments": {}},
           {"name": "get_current_recommendation", "arguments": {}}]}
```

`parse_plan()` validates that object against the registry: unknown tool names are
recorded as `rejected` and dropped, undeclared or invalid arguments are recorded
and dropped, duplicates are collapsed, and at most `MAX_TOOLS_PER_PLAN = 5`
tools survive. A tool name that is not in the registry is never executed,
whatever the model writes.

If the provider is unavailable, or the draft is not a usable plan, the
deterministic `heuristic_plan()` takes over: the same facets are covered from
keyword evidence, with declared arguments built from the product's own
vocabulary. The Agent therefore degrades to verified tools rather than to
general knowledge. A follow-up `native tool calling` implementation can replace
`request_plan()` without touching the registry, the guards or the orchestrator.

---

## 4. Orchestrator (`agent_orchestrator.py`)

```
receive user message
 → route (ai_facts router)
 → deterministic fast path?  ── yes ─▶ verified answer, zero provider calls
 → build structured context
 → plan (structured planner, or deterministic plan)
 → execute tools in parallel (whitelisted, read-only, ≤ MAX_TOOLS_PER_STEP)
 → complete the coverage the question raised (deterministic, one extra step)
 → build grounded context (tool results + structured digest)
 → DeepSeek wording (existing provider, existing grounding prompt)
 → grounding / safety / decision-authority validation
 → answer + tool-use metadata
```

* `MAX_TOOL_STEPS = 4` — a hard cap on tool iterations per user turn. A plan that
  still has work left when the cap is reached is reported as
  `agent.limit_reached = true` and answered from what was already verified.
* Independent read-only tools in one batch run in parallel
  (`ThreadPoolExecutor`, max 4 workers).
* **Cost:** one user question costs at most one planning call plus one answer
  call. No call is made per tool, and the fast path costs nothing.

### Deterministic fast path

`SAFETY`, `PERSONAL_FACT`, `UNRESOLVED_PERSONAL`, `CORRECTION` and out-of-scope
questions are answered by the existing deterministic layers, exactly as before.
The Agent adds no latency and no provider call; the response reports
`agent.strategy = "deterministic_fast_path"`, `steps = 0` and the single verified
source that produced the answer. The routing difference is invisible to the user.

---

## 5. Structured Agent Context and conservative memory (`agent_context.py`)

The context is a bounded, read-only projection of state the product already
stores: readiness (status, index, scale, confidence, domains, contributors,
safety flags), the recommendation (primary, training type, demand, base demand,
duration, RIR guidance, alternatives, avoid list, rationale), recent completed
sessions, weekly exposure in weighted working sets, Training Load in points,
local soreness, Personal Response, Recommendation Confidence, recorded
calibrations, the active session, profile settings and the programme split.

`context_digest()` renders that structure as a short, unit-bearing summary for
the planner and the answer prompt.

**Memory is the product's own persisted history**, summarised with counts and
dates: recorded sessions and check-ins, adaptation events, calibration events and
recent post-session feedback. There is no model-written memory and no field with
the shape of an inferred trait: the module cannot produce "the user seems lazy",
"the user prefers pain" or "the user probably recovers badly" because no such
field exists, and the model never writes to memory.

---

## 6. Decision authority and safety precedence (`agent_guard.py`)

After DeepSeek writes the wording, the draft is accepted only if all of these
hold:

1. **No contradiction** — the existing `ai_engine.validate_llm_response()`.
2. **No invented number** — the existing `ai_facts.guard_llm_response()` runs over
   the verified facts *plus this turn's tool results*, so a number is licensed
   only if a tool or the deterministic facts produced it. That covers the
   readiness index, set counts, load values, durations and periods.
3. **No invented rationale** — the existing `guard_explanation_grounding()`.
4. **Safety precedence** — when the deterministic system reports a safety
   restriction, the answer must preserve it. Safety turns never reach the model
   at all; this is the second line of defence.
5. **Decision authority** — an asserted session-demand tier must be the tier the
   deterministic engine produced. The model explains the recorded demand; it
   cannot replace it.

A rejected draft falls back to the deterministic answer with the product notice
"The AI draft did not pass factual validation…". The model cannot produce a
readiness score, an intensity tier, a training focus, a RIR range, a load value,
a calibration state or a safety classification.

---

## 7. Failure behaviour

| Failure | Behaviour |
|---|---|
| DeepSeek unavailable or erroring | deterministic answer from `rule_based_answer()` plus tool-derived evidence; `notice = AI_UNAVAILABLE_NOTICE` |
| Planner unusable | deterministic plan; the turn continues with tools |
| A tool raises | structured `tool_failure`; the other tools still answer, the failing tool is dropped from the trace |
| Tool arguments fail validation | the tool is refused and recorded in `agent.rejected` |
| The model names an unknown tool | the name is refused before execution and recorded in `agent.rejected` |
| Iteration limit reached | the answer uses what was verified; `agent.limit_reached = true` |
| Draft fails grounding/safety/authority | fallback answer; `notice = AI_REJECTED_NOTICE` |

The Coach never fails a turn because one Agent step failed.

---

## 8. API

```
POST /api/state/coach          # upgraded internally: same contract, Agent routing
POST /api/state/coach/agent    # explicit Agent endpoint, identical behaviour
POST /api/coach/message        # demo-profile path, now routed through the Agent
GET  /api/health               # publishes agent.strategy, native_tool_calling and the tool list
```

The response keeps the five V1.1 fields (`answer`, `provider`, `kind`, `ai_used`,
`verified_data`, `notice`, `contract`) and adds, additively:

```json
{
  "tools_used": ["get_readiness", "get_current_recommendation"],
  "tool_trace": [{"tool": "get_readiness", "label": "Readiness",
                  "source": "readiness_engine.assess_readiness", "operation": "read_only"}],
  "grounded": true,
  "fallback_used": false,
  "agent": {"strategy": "structured_planner", "intent": "explain_recommendation",
            "plan_source": "planner", "steps": 1, "rejected": [],
            "planner_error": null, "limit_reached": false, "provider_seconds": 0.83}
}
```

No prompt, no chain-of-thought and no credential is ever returned.

---

## 9. Transparency UI

The Coach answer gains one small, collapsed line:

```
Checked 5 verified sources  ›
  • Readiness
  • Today's session
  • Decision Trace
  • Recent training
  • Personal Response
```

It is a **tool trace, not a reasoning trace**: product-language labels only, no
internal planner prompt, no tool names, no step-by-step reasoning. The Coach
information architecture is unchanged (four suggested questions, three
secondary topics, Personal Response / Calibration / History, conversation-first
layout, fixed input, existing navigation). The only other change is a quiet
label: the Coach eyebrow reads **AI Coach**, with "Powered by verified training
tools." under the empty state.

---

## 10. Logging

`personal_readiness_assistant.agent` logs one structured line per Agent turn:
event, strategy, intent, plan source, selected tool names, tool failures, number
of tool steps, fallback use, provider latency and total latency. It never logs
the API key, the prompt, the user's question text or their personal values.

---

## 11. Tests

`test_agent.py` adds 33 tests to the 246-test V1.3 baseline (**279 passing**),
covering: registry contents, unknown tool refusal, invalid argument refusal, each
wrapper's agreement with its source engine, the read-only Decision Explorer,
planner validation, planner fallback, the deterministic fast path, multi-tool
turns, the tool-step cap, provider failure, planner failure, tool failure,
grounding protection, safety precedence, decision-authority protection, tool
trace metadata, bounded conversation context, context/memory structure, and the
six acceptance scenarios A–F. No test performs a live provider call; the
provider is replaced by a fake that records its messages.

Frontend verification: `tsc --noEmit`, `eslint .`, `next build` and
`scripts/check-store-migration.mjs` (17/17) all pass; the Coach screen was
rendered at 390×844 and 1440×900 in both light and dark appearance with no
horizontal overflow, no navigation collision and no literal Markdown artifacts.
The captured acceptance evidence lives in `docs/evidence/v1.4-agent/` and is
documented in `docs/V1_4_AGENT_UI_ACCEPTANCE.md`.

**Live-provider observation (2026-09-19, `deepseek-flash`).** Across five live
drafts of the mandatory question, three were accepted and two were rejected by
the existing V1.3 rule that an explanation of the user's own plan must name the
recorded primary recommendation (`ai_engine.validate_llm_response`). The
rejections were correct behaviour — the wording omitted the session name — and
the product answered from the verified deterministic result instead. This is a
wording-quality issue in the provider prompt, not a defect in the Agent layer;
the release report records it as a known observation for the next prompt review.

### 11.1 Real provider smoke test (manual)

The automated suite **mocks** the provider on purpose: no test may spend a real
API call, and the normal test count must stay reproducible offline. The live
provider is validated separately, by hand:

```bash
DEEPSEEK_API_KEY=... python3 scripts/smoke_agent_deepseek.py          # one case
DEEPSEEK_API_KEY=... python3 scripts/smoke_agent_deepseek.py --all     # + what-if case
```

`--attempts N` (default 2) exists because provider wording is stochastic and the
existing V1.3 grounding guard rejects a draft that does not identify the recorded
primary recommendation. When a draft is rejected the product shows the verified
deterministic answer — a correct, documented outcome that says nothing about
whether the provider worked. The script therefore retries the case, prints every
attempt and the retry explicitly, and only reports PASS once a live draft passed
the guards. The flakiness stays visible; it is never hidden.

`scripts/smoke_agent_deepseek.py` reads the project's existing configuration
(`.streamlit/secrets.toml`, then `DEEPSEEK_API_KEY`) - no new secret name is
introduced - and runs the real V1.4 stack end to end: structured planner →
read-only tools → grounded synthesis → guards. It asserts that the provider was
actually called, that the strategy is `structured_planner`, that at least two
verified tools were used, that the answer is grounded, non-empty and not a
fallback, and that no tool name or argument set was rejected. It prints only
public metadata (provider, strategy, tool names, grounding, fallback, latency)
and a redacted answer preview; it never prints the key, the Authorization header,
the system prompt or any chain-of-thought.

Behaviour without a credential: it prints `SKIPPED - DEEPSEEK_API_KEY not
configured` and exits `0`, so it can never fail a build. `--strict` exits `3`
instead when a hard failure is wanted. The script is never invoked by pytest, the
frontend build, a Vercel build, a Render build or CI: nothing imports it and
nothing calls it automatically. Its result is evidence, not part of the 279-test
count.

---

## 12. Defects found and fixed while building V1.4

| Defect | Fix |
|---|---|
| Advice / what-if questions that mention a metric ("I trained legs yesterday… what should I do today?") were routed to a single factual metric instead of an explanation | `ai_facts.ADVICE_PATTERNS` routes advice and counterfactual questions to the explanation path, where the Agent answers from several verified sources |
| "How have I responded to **hard** sessions recently?" was answered as if the user had asked about **low-demand** sessions (the band lookup only recognised "high" and "moderate") | the band lookup maps "hard session(s)" to the High band and no longer guesses a band the question never named |
| A deterministically selected `run_decision_explorer` had no `lever` argument, so the what-if step failed validation and never ran | deterministic plans now supply declared arguments (`default_arguments()`), including the product's own default soreness level and the muscle group the question named |
| "What if today's session feels much harder than expected?" also triggered a what-if simulation of an unrelated input | in-session questions are answered by the calibration rules; the decision explorer is not selected for them |

## 13. What V1.4 deliberately does not do

* It does not add a second model, a second provider or a second integration.
* It does not let the model decide training; it does not expose any write tool.
* It does not add free-form or self-written memory, and it makes no health,
  personality or recovery inference.
* It does not rebuild the Coach information architecture or the broader app.
* It does not claim native tool calling, and it does not hide the strategy it
  actually uses.
