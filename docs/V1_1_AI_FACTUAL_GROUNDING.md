# V1.1 AI Coach — Factual Grounding (hotfix AI-01)

**Phase:** PHASE 3.5 — AI Coach Factual Grounding Hotfix
**Severity:** HIGH — a wrong answer about the user's own recorded data destroys product credibility
**Scope:** the Coach's factual layer. Readiness engine, recommendation engine, training-load
logic, weekly-exposure logic, safety logic and the model provider are unchanged.

## 1. Bug AI-01

**Name:** Personal factual query can hallucinate field semantics and units.

Reported reproduction:

```
User: How much have I trained back this week?
AI:   Ethan has trained back for 12 days this week.
User: but one week has only 7 days
AI:   Today's training load is 50-65 minutes.
```

### 1.1 Reproduction (real pipeline, real Qwen2.5-0.5B, offline cache)

Run against the V1.0 code path with the Ethan demo profile:

```
weekly_exposure: {'Back': 9.5, ...}      weekly_targets: {'Back': 12.0, ...}
duration: 35–55 min

Q: How much have I trained back this week?
A (Built-in AI · Qwen2.5-0.5B, 7.2s): Ethan has trained back for 12 days this week.

Q: but one week has only 7 days
A (Built-in AI · Qwen2.5-0.5B, 3.9s): Today's exposure is limited to 7 days.
```

The reported failure is deterministic, not a one-off: the model took the weekly *target*
(12), reinterpreted it as *days*, and on the follow-up invented another day count instead of
re-reading the source of truth.

## 2. Root cause

| # | Cause | Evidence |
|---|---|---|
| 1 | **Bare numbers with no unit or semantics.** `_recommendation_facts()` produced `Current seven-day exposure: Chest 6, Back 9.5, …` — a number, no unit, and a window description ("seven-day") that invites "days". The real window is *the last seven days including today*, and the unit is *weighted working sets*. | context dump above |
| 2 | **The target and the actual value were both bare.** `Weekly targets: Back 12` sat next to `Back 9.5`; the model merged them into a single "12" claim. | context dump |
| 3 | **Validation could not catch it.** `validate_llm_response()` only rejected readiness contradictions, primary-recommendation replacement, a missing RIR definition and (for three phrasings) a missing exposure number. "12 days" passed. | code review |
| 4 | **No correction/challenge handling.** The previous exchange was in the prompt, but nothing told the system to re-resolve the fact from the source of truth, and `rule_based_answer()` had no correction branch at all. | code review |
| 5 | **Fallback keyword collisions.** With the model disabled, `How many days have I trained back this week?` matched the *sets* branch and answered with `9.5 effective back sets`; `What's my training load today?` matched nothing and returned the generic menu; `How sore is my back today?` matched the workout branch. | fallback run above |

## 3. Architecture change

```
User message
   |
   v
ai_facts.route_question()            <- deterministic router, no model
   |
   +-- PERSONAL_FACT  -> ai_facts.grounded_answer()          -> user        (model not called)
   +-- CORRECTION     -> re-route previous question -> grounded answer / correction
   +-- UNRESOLVED     -> clarification request                              (model not called)
   +-- SAFETY         -> existing deterministic safety handling
   +-- EXPLANATION    -> structured facts -> Qwen -> validate -> grounding guard -> fallback
   +-- GENERAL        -> structured facts -> Qwen -> validate -> unit guard    -> fallback
```

New module `ai_facts.py` owns:

* `UNITS` / `Unit` — the unit registry, including the units each metric must **never** be
  expressed in (`sets != days`, `minutes != training load`, `ms != bpm`, `RPE != RIR`).
* `build_personal_facts()` — a read-only projection of the deterministic engines and the loaded
  history. Every value names its `source`; nothing is invented.
* `facts_for_prompt()` — unit-bearing context for the model. The legacy
  `Current seven-day exposure: Back 9.5` line is gone.
* `route_question()` / `Route` — intent routing plus a `as_trace()` diagnostic (development only,
  never shown to users).
* `grounded_answer()` / `correction_answer()`.
* `guard_llm_response()` / `guard_explanation_grounding()` / `_answer_was_wrong()`.

`ai_engine.get_ai_response()` routes first; only explanation and general questions reach the model.

## 4. Supported factual intents

| Intent | Example question | Source of truth |
|---|---|---|
| Weekly exposure (per muscle group) | How much have I trained back this week? | `weekly_training_exposure` |
| Weekly target | What is my back weekly target? | `recommendation["weekly_targets"]` |
| Completed training days | How many days have I trained back this week? | `profile["training_history"]` (completed rows) |
| Completed sessions | How many sessions have I done this week? | `profile["training_history"]` |
| Training load | What's my training load today? | readiness engine training-load domain (AU) |
| Session duration | How long should I train today? | `recommendation["duration"]` |
| Readiness / index / confidence | What's my readiness today? | `assess_readiness` |
| Recommendation / session demand | What am I training today? | `recommend_training` |
| Local soreness | How sore is my back today? | daily check-in local soreness |
| HRV / resting HR / sleep | What's my HRV today? | today's check-in + measurements |
| Recent training / last trained | When did I last train back? | `profile["training_history"]` |

Unsupported but personal-looking questions return a clarification instead of a guess.

## 5. Unit semantics

| Concept | Unit | Never expressed as |
|---|---|---|
| Weekly exposure / volume | weighted working sets (direct 1.0, mapped secondary 0.5) | days, sessions, minutes |
| Completed training | training days | sets, minutes |
| Completed training | sessions | sets, minutes |
| Session duration | minutes | training load, AU |
| Training load | AU (duration × session RPE, mean daily) | minutes, hours, sets, days |
| HRV | ms | bpm |
| Resting HR | bpm | ms |
| Sleep | hours | sets, score |
| Readiness index | index points / 100 | sets, minutes, AU |
| Effort scales | RPE | RIR |
| Repetitions in reserve | RIR | RPE |

The two reporting windows stay distinct and are named in every answer:
**weekly exposure = the last seven days including today** (the engine's `0 <= age < 7` window);
**training load = the last 7 complete calendar days** compared with the preceding 21.

## 6. Fallback behaviour

* Personal factual queries never call the model, so they work when Qwen is unavailable, disabled
  (`DISABLE_EMBEDDED_LLM`), out of memory or slow.
* Explanation answers still use Qwen, then pass three checks: the existing contradiction
  validator, `guard_llm_response` (invented numbers, unit contamination, period shift) and
  `guard_explanation_grounding` (the explanation must reference a verified rationale element —
  readiness status, primary recommendation name, session demand, or a decision-factor concept).
  A rejected draft is replaced by the deterministic answer and the user sees the normal
  "Rule-based fallback" notice.
* With Qwen2.5-0.5B, the explanation guard rejects a large share of drafts; the deterministic
  rationale is then shown. This is the intended trade-off: grounding over naturalness.

## 7. Chat history and correction handling

* History is still passed as `user`/`assistant` pairs, bounded to the most recent 8 turns for the
  model and 30 stored messages per profile.
* A challenge (`that's wrong`, `are you sure?`, `check again`, `you said …`,
  `one week has only 7 days`, `not 4 sets`) is only treated as a correction when a previous
  assistant turn exists.
* On a correction the previous *question* is re-routed and the fact is re-read; the previous
  model text is never used as evidence. If the earlier answer was wrong (a quantity in a
  forbidden unit, or a number outside the verified facts) the reply states the correction;
  otherwise it re-confirms without inventing anything.
* A negation such as "not minutes and not sets" is **not** treated as unit contamination.

## 8. Known boundaries

* The router is pattern-based. Paraphrases outside its vocabulary return the clarification
  message; it does not cover arbitrary free-form personal questions (no model based extraction
  by design).
* Muscle aliases are limited to the product taxonomy: `biceps`/`triceps` map to the single
  `Arms` group (stated in the answer), `legs` expands to `Quads` + `Hamstrings / Glutes`.
* Local soreness is only available when today's check-in recorded it; demo profiles often have
  none, in which case the Coach says so.
* Qwen wording quality itself is unchanged; a stronger model is a separate, later decision.
* The explanation grounding guard is heuristic: it can reject a correct-but-unusual wording and
  fall back to the deterministic answer.

## 9. Tests

`test_app.py` adds 16 regression tests covering the phase's CASE 1–15 requirements plus the
router, the prompt contract and the explanation guard:

`test_ai_router_classifies_personal_fact_versus_other_intents`,
`test_ai_case_1_and_2_weekly_exposure_uses_real_unit`,
`test_ai_case_3_training_days_is_not_exposure`,
`test_ai_case_4_and_5_training_load_versus_session_duration`,
`test_ai_case_6_and_7_readiness_and_recommendation`,
`test_ai_case_8_local_soreness_is_reported_or_declared_unavailable`,
`test_ai_case_9_correction_re_reads_source_of_truth`,
`test_ai_case_10_challenge_reconfirms_without_new_numbers`,
`test_ai_correction_of_a_correct_answer_does_not_claim_an_error`,
`test_ai_case_11_missing_data_is_declared_not_invented`,
`test_ai_case_12_unit_contamination_is_blocked_by_the_guard`,
`test_ai_case_13_multiple_muscles_read_their_own_source_values`,
`test_ai_case_14_profile_isolation_has_no_stale_context`,
`test_ai_case_15_factual_query_survives_qwen_failure_and_never_calls_it`,
`test_ai_fact_prompt_never_exposes_bare_numbers`,
`test_ai_explanation_grounding_guard_rejects_invented_rationale`.

The one modified existing test (`test_ai_weekly_sets_answer_uses_recorded_exposure`) was
strengthened: it now requires the real unit (`weighted working sets`), forbids a quantity in
days, and keeps the exposure-number assertion.
