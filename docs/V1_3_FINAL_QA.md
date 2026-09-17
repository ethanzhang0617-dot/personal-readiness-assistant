# V1.3 Final QA

**Branch:** `v1.3-adaptive-decision-loop`
**Result:** V1.3 FINAL PORTFOLIO BUILD
**Scope of this record:** the finalisation sprint (in-session calibration, what-if /
decision explorer, loop integration) plus full regression of V1.1 → V1.3.

## 1. Automated tests

| Suite | Result |
|---|---|
| `python3 -m compileall .` | PASS |
| `python3 -m pytest -v` | **246 / 246 PASS** (`test_app` 139 · `test_adaptive` 31 · `test_api` 39 · `test_calibration` 37) |
| `pnpm lint` | PASS (0 errors, 0 warnings) |
| `pnpm typecheck` | PASS |
| `pnpm build` | PASS |
| `pnpm check:store` | 17 / 17 |

FastAPI was exercised through `fastapi.testclient` (the whole `test_api` +
`test_calibration` surface) with the real application object.

## 2. Browser QA

Every run used the real production build (`next build --webpack` → `next start`) against
the real FastAPI server on `127.0.0.1:8000`.

| Suite | Chromium | WebKit | Notes |
|---|---|---|---|
| Final V1.3 journey (calibration + explorer) | 38 / 38 | — | `web_e2e_v13_final.py` |
| V1.3 Phase 1 journey | 19 / 19 | — | `web_e2e_v13.py` |
| V1.3 Phase 2 journey | 31 / 31 | — | `web_e2e_v13_phase2.py` |
| V1.2 functional parity | 20 / 20 | — | `web_e2e_phase2.py` |
| Cross-engine responsive sweep | 27 / 27 | 27 / 27 | `web_cross_engine_qa.py`, 54/54 combined |
| Route × viewport sweep | 45 / 45 | — | `web_visual_qa.py` |
| Final V1.3 surfaces × 5 viewports | 45 / 45 | — | `web_responsive_v13_final.py` |
| Import / export | 10 / 10 | — | `web_release_qa.py import` |
| API unavailable | 6 / 6 | — | `web_release_qa.py api-down` |
| API recovered | 2 / 2 | — | `web_release_qa.py api-up` |

**Console blocking errors: NONE.** No uncaught page errors in any run.

### Viewports

375 × 812 · 390 × 844 · 430 × 932 · 768 × 1024 · 1440 × 900 — all five passed
horizontal-overflow checks on Today (with the explorer open and compared), the active
session with a recorded checkpoint, Insights and Coach. Mobile touch targets stay at or
above 40px; the denser desktop controls above the `md` breakpoint are the documented
design-system choice and are not asserted as touch targets.

**Firefox: UNAVAILABLE in this environment.** Playwright cannot launch it here
(`plugin-container` is denied by the macOS sandbox, 45 s launch timeout). This is an
environment limitation, not a product result, and it is unchanged from V1.2.

**Physical iOS / Android devices: NOT TESTED.** No claim is made about them; the mobile
evidence above is Chromium and WebKit at mobile viewports.

## 3. End-to-end journeys exercised

1. Today → readiness → recommendation → Decision Trace.
2. Decision explorer (levers, one-factor comparison, read-only confirmation, current
   decision preserved).
3. Train → Start session → active session with starting guidance and session trace.
4. In-session checkpoint → HOLD, EASE and OPTIONAL PUSH all reproduced in the browser.
5. Reload → active session and its checkpoint survive.
6. Complete session → post-session feedback → session history persists.
7. Reload → the completed session carries the checkpoint into the Response Episode.
8. Next-day check-in → episode closes → Personal Response Profile and Recommendation
   Confidence update.
9. Coach → calibration facts, Personal Response facts and confidence answers, all
   deterministic with zero provider calls.
10. Insights → profile, coverage, episodes, adaptation history, in-session calibration.
11. Import / export, scenario switching, profile switching, API-unavailable behaviour.

## 4. Real bugs found and fixed during the final sprint

1. **`"RPE 3–4 / 10"` was parsed as a `3–4 RIR` range.** The calibration rule would have
   compared an aerobically prescribed session against a reps-in-reserve range that was
   never prescribed. Fixed by making the RIR unit mandatory in the parser, with a
   regression test.
2. **The calibration reason text flattened the product's own "RIR" wording.**
   `str.capitalize()` lower-cased the remainder of the sentence
   (`0 rir is below the prescribed 1–3 rir range`). Fixed by capitalising only the first
   character.
3. **`"increase"` was matched as the keyword `"ease"`.** The deterministic calibration
   router intercepted *"Why didn't you increase today's training…"* and answered it as a
   calibration question, breaking an existing Personal Response answer. Fixed with
   word-boundary matching for Latin keywords (CJK keywords still match as substrings) and
   covered by a regression test.
4. **`calibration_service.history()` assumed the state's session rows were dicts.** They
   are pydantic `SessionRow` objects, so every state endpoint that touched the history
   raised `AttributeError`. Fixed by normalising through `model_dump()`; 14 API tests
   caught this immediately.

Earlier V1.3 phases recorded two further real defects (the demo seeds that could show an
evidence state the real rules would not produce, and `refreshToday` discarding the state
returned by `/state/today` so the adaptation history never reached storage). Both remain
fixed and are covered by tests.

## 5. Core-engine protection (final diff)

| Area | Changed? |
|---|---|
| `readiness_engine.py` | NO |
| `training_recommendation_engine.py` | NO |
| Training load / weekly exposure | NO |
| Science content and references | NO |
| `ai_engine.py` / `ai_facts.py` grounding and guard contracts | NO |
| Personal Response Phase 2 rules | NO (additive episode field only) |
| Recommendation Confidence semantics | NO |
| `adaptive_response.py` | additive only: episodes gained a `calibrated` field |

`adaptive_response.py` is the one shared file touched: the change adds an optional
`calibrated` key to each episode and does not alter any Phase 1/2 rule, threshold or
decision.

## 6. Performance and accessibility

* No new heavy dependency, no background job and no additional engine run on Today: the
  session trace is built from the decision that page already computes. Calibration and
  what-if each run the engines once per explicit user action.
* Bundle: no unexpected growth (one small client component plus one new static list).
* Touch targets: ≥ 40px on mobile viewports across the new surfaces.
* Focus visibility, labels (`aria-label` on every segmented group and input), keyboard use
  and the `<details>` disclosures were exercised during the sweeps.
* Empty states exist for "no checkpoint yet" and "no active session".

## 7. Honest remaining limitations

* Physical iOS Safari and Android Chrome were not tested.
* Firefox could not be launched in this environment.
* Calibration is manual input, not device-measured; it is one checkpoint, not continuous
  monitoring.
* The adaptive layer covers the strength-style demand ladder; aerobic prescriptions
  (`RPE 3–4 / 10`) sit outside it.
* The decision explorer is a rule explorer with three levers, not a forecasting tool.
* No wearable, no cloud account, no authentication, no remote database, no machine
  learning.
