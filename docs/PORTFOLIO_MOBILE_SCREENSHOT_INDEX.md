# Portfolio Mobile Screenshot Index — V1.4.2

| Field | Value |
|---|---|
| Production URL | https://personal-readiness-assistant.vercel.app |
| Release | `v1.4.2` (Agent Visibility) · production commit `6547c77` |
| Identity on screen | Adaptive Training Decision System · AI Coach · Tool-Using Training Agent |
| Viewport | 390 × 844 for every capture (mobile only, no desktop layouts) |
| Raw captures | `docs/evidence/portfolio-mobile-v1.4.2/raw/` (13) |
| Framed assets | `docs/evidence/portfolio-mobile-v1.4.2/framed/` (13) — use these in the portfolio |
| Compositions | `docs/evidence/portfolio-mobile-v1.4.2/compositions/` (3) |
| Authenticity record | `docs/evidence/portfolio-mobile-v1.4.2/manifest.json` |

## Phone frame

One frame for every asset: graphite body, thin bezel (14 px sides / 26 px top and bottom), 92 px outer corner
radius, speaker slot and camera in the top bezel, a single subtle shadow and **no brand marks**. The screen is the
raw production capture scaled by one uniform factor to 852 × 1844 and masked to the frame's inner radius, so nothing
is stretched, clipped or covered. Canvas 1000 × 2116 px with a transparent background.

## Framed screens

| Framed file | Raw file | Route | Theme | Product state | Interaction | Portfolio page | Why it is useful | Result |
|---|---|---|---|---|---|---|---|---|
| `01_today_mobile_light_phone.png` | `01_today_mobile_light_raw.png` | `/` | Light | readiness 90 GREEN, recommendation Legs, Start Session, bottom nav | none | HERO / TODAY | decision-first mobile experience in one frame | PASS |
| `02_train_musclemap_dark_phone.png` | `02_train_musclemap_dark_raw.png` | `/train` | Dark | Legs session with the MuscleMap; Quads and Hamstrings/Glutes highlighted; Normal · 50–65 min · 1–3 RIR | none | HERO / TRAIN | the strongest product visual | PASS |
| `03_decision_trace_light_phone.png` | `03_decision_trace_light_raw.png` | `/decision-trace` | Light | multiple decision stages leading to the recommendation | none | DECISION SYSTEM | "every recommendation can answer why" | PASS |
| `04_personal_response_light_phone.png` | `04_personal_response_light_raw.png` | `/personal-response` | Light | demand bands with observed pattern and evidence state | none | ADAPTIVE LOOP | adaptive personalisation | PASS |
| `05_decision_explorer_light_phone.png` | `05_decision_explorer_light_raw.png` | `/decision-explorer` | Light | real what-if with current / changed input / alternative | selected "More local soreness" → "Compare with the current decision" | WHAT-IF | shows the deterministic what-if engine | PASS |
| `06_calibration_dark_phone.png` | `06_calibration_dark_raw.png` | `/train` (active session) | Dark | in-session checkpoint resolved to **OPTIONAL PUSH** | Start Session → Easier than expected / RIR 4 / Better than expected → "Check how it feels" | ADAPTIVE LOOP / WHAT-IF | real in-session adaptation | PASS |
| `07_agent_home_light_phone.png` | `07_agent_home_light_raw.png` | `/coach` | Light | AI Coach · Tool-Using Training Agent · explanation · 4 questions · 3 categories · input | cleared the browser-local conversation | AGENT | introduces the Agent | PASS |
| `08_agent_answer_dark_phone.png` | `08_agent_answer_dark_raw.png` | `/coach` | Dark | real grounded answer, AGENT RUN · GROUNDED, Checked 5 verified sources | asked "Why is today's recommendation lighter than usual?" | AGENT / HERO | core Agent screen | PASS |
| `09_agent_trace_expanded_dark_phone.png` | `09_agent_trace_expanded_dark_raw.png` | `/coach` | Dark | expanded "How this answer was built" with per-source explanations and the deterministic authority line | expanded the disclosure | AGENT PROOF | strongest Agent evidence | PASS |
| `10_agent_decision_explorer_dark_phone.png` | `10_agent_decision_explorer_dark_raw.png` | `/coach` | Dark | trace contains Decision Explorer — Compared a verified what-if scenario | asked "I still want to train back. What would change?" | AGENT PROOF | proves a real tool invocation | PASS |
| `11_agent_fast_path_light_phone.png` | `11_agent_fast_path_light_raw.png` | `/coach` | Light | RECORDED DATA · Checked 1 verified source · Readiness | asked "What is my readiness today?" | AGENT PROOF | truthful Agent vs deterministic distinction | PASS |
| `12_about_agent_architecture_light_phone.png` | `12_about_agent_architecture_light_raw.png` | `/profile/about` | Light | "How the Agent works": question → planner → verified tools → deterministic results → DeepSeek → grounded answer, tool groups, core principle | scrolled to the section | ABOUT / ARCHITECTURE | explains the architecture | PASS |
| `13_insights_light_phone.png` | `13_insights_light_raw.png` | `/insights` | Light | readiness and training trends with the personal-response connection | none | DECISION SYSTEM (support) | trend-first data experience | PASS |

## Grouped compositions

| File | Sources | Purpose |
|---|---|---|
| `portfolio_hero_three_phones.png` | Train (dark, left, 82%) · Today (light, centre, 100%) · Agent answer (dark, right, 82%) | portfolio hero |
| `portfolio_agent_sequence.png` | Coach home → Agent answer → expanded trace | the Agent journey |
| `portfolio_adaptive_pair.png` | Personal Response + Calibration | the adaptive loop |

All three are transparent-background PNGs built only from the framed real captures.

## Portfolio page pairings

| Portfolio page | Assets |
|---|---|
| HERO | `01_today_mobile_light_phone` + `02_train_musclemap_dark_phone` + `08_agent_answer_dark_phone` (or `portfolio_hero_three_phones.png`) |
| DECISION SYSTEM | `03_decision_trace_light_phone` (+ `13_insights_light_phone`) |
| TODAY | `01_today_mobile_light_phone` |
| TRAIN | `02_train_musclemap_dark_phone` |
| ADAPTIVE LOOP | `04_personal_response_light_phone` + `06_calibration_dark_phone` (or `portfolio_adaptive_pair.png`) |
| WHAT-IF | `05_decision_explorer_light_phone` |
| AGENT PAGE | `07_agent_home_light_phone` + `08_agent_answer_dark_phone` + `09_agent_trace_expanded_dark_phone` (or `portfolio_agent_sequence.png`) |
| AGENT PROOF | `10_agent_decision_explorer_dark_phone` + `11_agent_fast_path_light_phone` |
| ABOUT / ARCHITECTURE | `12_about_agent_architecture_light_phone` |

## Notes and limitations

* **Raw captures preserved:** every framed asset keeps its raw 390 × 844 source next to it in `raw/`, and
  `manifest.json` links the two with the route, theme, viewport, capture time, interaction and real product state.
* **No full-page screenshots:** each frame is one real 390 × 844 viewport, exactly what a phone user sees.
* **Device pixel ratio:** the automation surface exposes a viewport override only, so the raw captures are 1×
  (390 × 844 px). The framed canvas upscales them uniformly to 852 × 1844 for a high-resolution asset — the UI is
  scaled, never redrawn, cropped differently per asset, or edited.
* **The real Train state is Legs:** the reachable demo state was captured as-is; no training focus was fabricated.
* **Temporary state:** the calibration screenshot came from a real in-session checkpoint; the session was discarded
  through the product UI afterwards.
* **No product change:** this task produced assets and documentation only.
