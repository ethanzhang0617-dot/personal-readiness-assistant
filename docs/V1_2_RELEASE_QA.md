# V1.2 Release Candidate — QA Record

**Branch:** `v1.2-nextjs-migration`
**Build under test:** production build (`pnpm build` + `pnpm start`) with a live FastAPI backend.
**Product:** Next.js frontend + FastAPI backend. The Streamlit V1.1 app is a reference
implementation and was not part of this QA.

## 1. What was tested, and how

| Area | Method | Result |
|---|---|---|
| Types and lint | `pnpm typecheck`, `pnpm lint` | PASS (no findings) |
| Production build | `next build --webpack` | PASS (10 routes) |
| Production server | `next start` on 3000 + uvicorn on 8000 | PASS |
| Frontend ↔ backend | Live API used by the production server | PASS |
| Python suite | `python3 -m compileall .`, `python3 -m pytest -v` | PASS, 161/161 |
| Backend smoke | `/api/health`, `/api/scenarios`, `/api/profile/options`, `/api/science/logic`, `/api/state/base` | PASS, all 200 |
| Cross-engine UI | Chromium 141+, WebKit 26.5 × 3 mobile viewports × 9 routes | **54/54 PASS**, 0 console errors |
| Functional regression | Full user journey, Chromium and WebKit, on the production server | **20/20 PASS** each |
| Import / export | Export → validate → summary → confirm → reload, plus malformed and incompatible files | 10/10 PASS |
| API unavailable | Backend stopped deliberately | 6/6 PASS (product-level error, recovery after restart) |
| AI unavailable | Backend started with `DISABLE_AI_COACH=true` | 7/7 PASS |

## 2. Browsers and engines

| Engine | Coverage | Result |
|---|---|---|
| Chromium (Playwright 1.62, headless) | 3 viewports × 9 routes + full functional journey | **PASS** |
| WebKit 26.5 (Safari-compatible engine) | 3 viewports × 9 routes + full functional journey | **PASS** |
| Firefox 153 | Engine could not launch in this environment | **NOT TESTED** |
| Physical iOS Safari | No device available | **NOT TESTED** |
| Physical Android Chrome | No device available | **NOT TESTED** |

**Physical-device verification is pending.** WebKit is a Safari-compatible engine, not Safari on
iOS; the browser-emulation results above must not be reported as real-device verification.

Firefox was installed but fails to launch here: macOS denies the sandbox extension its
`plugin-container` needs (`sandbox_extension_issue_file_to_process ... Operation not permitted`).
This is an environment limitation, not an application finding.

## 3. Viewports

| Viewport | Routes checked | Result |
|---|---|---|
| 375 × 812 | 9 routes × 2 engines | PASS |
| 390 × 844 | 9 routes × 2 engines | PASS |
| 430 × 932 | 9 routes × 2 engines | PASS |
| 768 × 1024 | 9 routes (Phase 3 pass) | PASS |
| 1440 × 900 | 9 routes (Phase 3 pass) | PASS |

Checks per combination: horizontal overflow, bottom-navigation presence and position, form-control
font size, and touch-target size.

* Horizontal overflow: **0px** everywhere.
* Bottom navigation: present, 73px, flush with the viewport bottom, no control resting under it.
* Form controls: **no control below 16px** (the iOS focus-zoom threshold).
* Touch targets: every primary control ≥44px. Two documented exceptions: a checkbox inside a 44px
  label, and inline citation links (PMID/DOI) inside prose or list items, which are ~24px and meet
  the WCAG 2.5.8 target-size rule.

## 4. Mobile-specific behaviour

| Item | Finding |
|---|---|
| Safe-area insets | Bottom navigation uses `max(env(safe-area-inset-bottom), 8px)`; the viewport meta uses `viewport-fit=cover`. |
| Keyboard overlap | The Coach composer and the check-in action bar are sticky above the navigation; no control is hidden behind it. |
| Input zoom (iOS) | Fixed in this phase: all form controls render at 16px on small screens. |
| Native select sizing | Fixed in this phase: WebKit ignores `min-height` on a native `<select>`, so selects now use a fixed height (they were 23px in WebKit, now 44px). |
| Sticky positioning | Coach composer and check-in action bar verified in both engines. |
| File import | Native file picker, then an in-page validation step; verified in both engines. |
| `100vh` behaviour | The shell uses `min-h-dvh` rather than `100vh`. |

## 5. Functional regression (production server)

Verified end to end in Chromium **and** WebKit (20 checks each):

Today renders readiness and the recommendation → morning check-in saves and Today recalculates →
Train shows exposure, prescription and history → a completed session logs and updates
history/exposure → Insights renders charts → Coach answers a factual question deterministically and
an explanation question through the provider or its fallback → a profile edit saves → a browser
reload preserves the check-in, the logged session and the profile edit.

Additional verified behaviour:

* **Coach contract:** factual questions are answered from recorded data with **zero** provider calls
  (asserted in the Python suite and observed in the browser); explanation questions either return an
  AI explanation or degrade to a rule-based answer with a notice.
* **AI unavailable** (`DISABLE_AI_COACH=true`): Today, Train, Insights, Profile and the deterministic
  Coach all keep working; the explanation request degrades to a rule-based answer with a notice; no
  crash.
* **API unavailable:** Today shows "Today is unavailable right now" with actionable copy, no raw
  exception text, navigation still works, and the page recovers once the API is back.
* **Import:** malformed JSON and a structurally incompatible file both produce product-level
  messages, and selecting a file never overwrites local data before confirmation.

## 6. Console, network and performance sanity

* Console errors across 54 engine/viewport/route combinations: **0**. No hydration errors, no React
  warnings, no uncaught page errors in any functional run.
* No repeated API loops observed; each page performs one state computation per interaction.
* No secret values in any payload; `/api/health` reports only whether a credential is configured.
* Build output: 10 routes, all client components are small; the only runtime dependency added in the
  migration is `requests` on the backend. No chart library, no UI framework beyond the design tokens.

## 7. Accessibility sanity

* Keyboard: navigation, expandable Decision Trace (`<details>`), sliders, segmented controls and all
  form controls are reachable and operable; one consistent `:focus-visible` outline.
* Labels: every input has an accessible name (`aria-label` or a wrapping label); icon-only buttons
  carry `aria-label`.
* Status semantics: colour is always paired with a written status word.
* Reduced motion: `prefers-reduced-motion` disables transitions and animations.
* Touch targets: see section 3.

## 8. Known release limitations

1. **Physical devices not verified** (see section 2). This is the main outstanding QA gap.
2. Firefox could not be launched in this environment.
3. Charts are hand-rolled SVG: no zoom/pan and single-value tooltips.
4. The check-in action bar and Coach composer are sticky; on very short viewports they occupy part
   of the screen by design.
5. Local data lives in one browser profile; there is no cloud sync, account or export automation.
6. If a deployment explicitly disables the AI layer, the notice still uses configuration language
   ("disabled for this deployment"). The wording lives in the protected `ai_engine.py` and was
   deliberately left unchanged in this phase.
7. The production build uses the webpack pipeline because Turbopack's PostCSS worker cannot bind its
   local IPC port in the development container.
