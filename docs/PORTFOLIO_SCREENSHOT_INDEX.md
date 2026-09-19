# Portfolio Screenshot Index — V1.4.2

| Field | Value |
|---|---|
| Production URL | https://personal-readiness-assistant.vercel.app |
| Release | `v1.4.2` (Agent Visibility); production commit `6547c77` |
| Identity on screen | Adaptive Training Decision System · AI Coach · Tool-Using Training Agent |
| Capture date | 2026-09-19 |
| Browser | Chromium (in-app automation browser), page content only — no tabs, address bar, devtools or console |
| Demo state | The product's own demo profile (Ethan). No invented data, no edited screenshots, no mock UI. |
| Directory | `docs/evidence/portfolio-v1.4.2/` |

## Screenshots

| File | Route | Viewport | Theme | Product state | Interaction required | Portfolio use | Why it is useful | Result | Limitation |
|---|---|---|---|---|---|---|---|---|---|
| `01_hero_today_desktop_light.png` | `/` | 1440 × 900 | Light | Today, readiness 90 GREEN, recommendation Legs (Normal · 50–65 min · 1–3 RIR), Start Session, morning check-in prompt | none | PAGE 01 HERO / PAGE 05 TODAY | strongest above-the-fold desktop composition; identity + readiness hero + recommendation + primary action | PASS | — |
| `02_today_mobile_light.png` | `/` | 390 × 844 | Light | same Today state, mobile layout with bottom navigation | none | PAGE 01 HERO / PAGE 05 TODAY | consumer mobile quality; readiness, recommendation and action in one frame | PASS | — |
| `03_train_musclemap_mobile_dark.png` | `/train` | 390 × 844 | Dark | Today's session Legs, MuscleMap front/back with Quads and Hamstrings/Glutes highlighted | none | PAGE 06 TRAIN | main visual highlight: photoreal body, highlighted target muscles, demand, duration, RIR, Start Session | PASS | the reachable demo state is Legs, not Back + Biceps; captured the real state rather than fabricating a different focus |
| `04_train_musclemap_desktop_dark.png` | `/train` | 1440 × 900 | Dark | same Train state, desktop composition with the product lockup | none | PAGE 06 TRAIN | desktop version of the training experience with the full session card | PASS | captured after discarding a temporary session so the recommendation view is shown |
| `05_decision_trace_desktop_light.png` | `/decision-trace` | 1440 × 900 | Light | full deterministic path: Goal → Programme → Weekly Exposure → Recent Training → Local Soreness → Readiness → Personal Response → Session Demand → Recommendation | none | PAGE 04 DECISION SYSTEM / PAGE 09 AGENT | "every recommendation can answer why" — nine readable stages in one frame | PASS | — |
| `06_decision_trace_mobile_light.png` | `/decision-trace` | 390 × 844 | Light | same trace, mobile framing | none | PAGE 04 DECISION SYSTEM | editorial mobile crop; the stage list stays readable | PASS | portrait frame shows fewer stages above the fold |
| `07_personal_response_desktop_light.png` | `/personal-response` | 1440 × 900 | Light | Personal Response profile, demand bands, evidence state | none | PAGE 07 ADAPTIVE LOOP | shows adaptive personalisation and the confidence/evidence framing | PASS | the demo profile currently has limited response evidence, which the page states honestly |
| `08_personal_response_mobile_light.png` | `/personal-response` | 390 × 844 | Light | strongest section of the same page | none | PAGE 07 ADAPTIVE LOOP | mobile support crop for the adaptive-loop case study page | PASS | — |
| `09_decision_explorer_desktop_light.png` | `/decision-explorer` | 1440 × 900 | Light | real what-if: current → changed input (more local soreness) → alternative, with the rule conclusion | select "More local soreness" → "Compare with the current decision" | PAGE 08 CALIBRATION & WHAT-IF | shows the real what-if engine with CURRENT / CHANGE / ALTERNATIVE | PASS | values come from the live re-run; no result text was edited |
| `10_decision_explorer_mobile_light.png` | `/decision-explorer` | 390 × 844 | Light | same real comparison, mobile framing | same two clicks | PAGE 08 CALIBRATION & WHAT-IF | mobile support crop for the what-if section | PASS | — |
| `11_calibration_mobile_dark.png` | `/train` (active session) | 390 × 844 | Dark | real in-session checkpoint resolved to **Optional push** with its guidance text | Start Session → effort "Easier than expected", RIR 4, performance "Better than expected" → "Check how it feels" | PAGE 08 CALIBRATION & WHAT-IF | shows genuine in-session adaptation with one of the three real outcomes | PASS | the session was discarded afterwards, so no temporary state was left in the product |
| `12_agent_coach_home_mobile_light.png` | `/coach` | 390 × 844 | Light | Coach home: AI Coach, Tool-Using Training Agent, consumer explanation, 4 questions, 3 categories, input | clear conversation for a clean home | PAGE 09 TOOL-USING AGENT | introduces the Agent and preserves the product IA | PASS | — |
| `13_agent_loading_mobile_dark.png` | `/coach` | 390 × 844 | Dark | real request in flight: "Agent is checking verified training context…" | ask "Why is today's recommendation lighter than usual?" and capture during processing | PAGE 09 TOOL-USING AGENT | proves the loading state is truthful (no simulated steps, no source list before the response) | PASS | timing-sensitive: captured during genuine processing |
| `14_agent_answer_mobile_dark.png` | `/coach` | 390 × 844 | Dark | real grounded Agent answer with **AGENT RUN · GROUNDED**, "Checked 5 verified sources" and the source preview | same question, after the response | PAGE 09 TOOL-USING AGENT | core Agent screenshot: grounded answer plus verified-source evidence | PASS | source count varies with what the planner selected for that answer |
| `15_agent_trace_expanded_mobile_dark.png` | `/coach` | 390 × 844 | Dark | same answer with "How this answer was built" expanded: per-source sentences and the deterministic authority line | expand the disclosure | PAGE 09 TOOL-USING AGENT | shows exactly which verified sources were used, with no chain-of-thought | PASS | — |
| `16_agent_answer_desktop_dark.png` | `/coach` | 1440 × 900 | Dark | Agent identity + grounded answer + Agent Run summary at desktop width | clear conversation, ask the same question | PAGE 01 HERO (Agent) / PAGE 09 TOOL-USING AGENT | desktop Agent hero with the full product lockup | PASS | — |
| `17_agent_decision_explorer_trace.png` | `/coach` | 390 × 844 | Dark | real Agent answer whose expanded trace contains **Decision Explorer — Compared a verified what-if scenario** | ask "I still want to train back. What would change?" and expand the trace | PAGE 09 TOOL-USING AGENT | evidence that the Agent really calls a product tool, not just the language model | PASS | — |
| `18_agent_fast_path_mobile_light.png` | `/coach` | 390 × 844 | Light | deterministic fast path: **RECORDED DATA**, "Checked 1 verified source", Readiness | ask "What is my readiness today?" | PAGE 09 TOOL-USING AGENT | shows simple facts are not dressed up as a full Agent run | PASS | — |
| `19_about_agent_architecture_desktop_light.png` | `/profile/about` | 1440 × 900 | Light | "How the Agent works": question → Agent planner → verified training tools → deterministic results → DeepSeek explanation → grounded answer, plus the tool groups | scroll to the section | PAGE 09 TOOL-USING AGENT | explains the architecture to a recruiter without reading GitHub | PASS | — |
| `20_about_project_identity_desktop_light.png` | `/profile/about` | 1440 × 900 | Light | official English and Chinese project names, one-line positioning, historical naming note | none (top of page) | project identity / case-study cover | gives the portfolio its project name and positioning | PASS | the former name appears only as an explicitly historical note |
| `21_insights_mobile_light.png` | `/insights` | 390 × 844 | Light | readiness and training trends, personal-response entry point | none | PAGE 04 DECISION SYSTEM (support) | trend-first data experience on mobile | PASS | — |
| `22_insights_desktop_light.png` | `/insights` | 1440 × 900 | Light | same Insights surface at desktop width | none | PAGE 04 DECISION SYSTEM (support) | desktop support crop | PASS | — |
| `23_science_desktop_light.png` | `/profile/science` | 1440 × 900 | Light | evidence boundaries, methodology and references | none | PAGE 10 SCIENCE | supports the science & guardrails section without being a wall of text | PASS | the real route is `/profile/science`; `/science` is not a product route |
| `24_profile_theme_mobile.png` | — | — | — | — | — | — | optional profile capture | SKIPPED | not needed for the planned portfolio pages |

## Portfolio page mapping

| Planned page | Screenshots |
|---|---|
| PAGE 01 HERO | 01 · 02 · 16 |
| PAGE 04 DECISION SYSTEM | 05 · 06 · 21 · 22 |
| PAGE 05 TODAY | 01 · 02 |
| PAGE 06 TRAIN | 03 · 04 |
| PAGE 07 ADAPTIVE LOOP | 07 · 08 |
| PAGE 08 CALIBRATION & WHAT-IF | 09 · 10 · 11 |
| PAGE 09 TOOL-USING AGENT | 12 · 13 · 14 · 15 · 16 · 17 · 18 · 19 |
| PAGE 10 SCIENCE | 23 |
| PAGE 12 OUTCOME | strongest desktop production image: 01 (Today) with 16 (Agent) |

## Capture notes and limitations

* **Device pixel ratio:** the automation surface exposes only a viewport override, not `deviceScaleFactor`, so every
  image is captured at 1× in native pixels (1440 × 900 desktop, 390 × 844 mobile). No upscaling or post-processing was
  applied; crop and resize are still available for layout.
* **Authenticity:** every frame is the real public production application. No mockups, generated images, painted-over
  content, fabricated metrics or fabricated Agent states.
* **Temporary state:** the only temporary browser-local state was the in-session calibration run for screenshot 11; the
  session was discarded through the product UI afterwards, leaving no artificial production data.
* **Honesty of the Agent UI:** screenshot 13 is a real in-flight state; screenshots 14–17 read their sources from the
  actual response metadata, and screenshot 18 shows the deterministic fast path rather than a fake Agent run.
* **No product change:** this task produced screenshots and this index only; the product code was not modified.
