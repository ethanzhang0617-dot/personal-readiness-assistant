# V1.4.2 — Agent Visibility Production Evidence

| Field | Value |
|---|---|
| Public URL | https://personal-readiness-assistant.vercel.app |
| Backend | https://personal-readiness-assistant-api.onrender.com |
| Capture date | 2026-09-19 |
| Browser | Codex in-app browser (Chromium engine) |
| Capture method | Real public production pages captured with browser automation. No mockups, no edited pixels, no localhost. |
| Evidence directory | `docs/evidence/v1.4.2-agent-visibility/` |
| Frontend package version | `1.4.2` (product/API version stays `1.4`, a patch-level UX release) |

## Captures

| Evidence | Viewport | Theme | Route | Scenario | Result |
|---|---|---|---|---|---|
| `01_coach_home_mobile_light.png` | 390 × 844 | Light | `/coach` | Coach home: AI Coach, "Tool-Using Training Agent", the consumer explanation, four questions, three categories, input reachable | PASS |
| `02_agent_loading_mobile_dark.png` | 390 × 844 | Dark | `/coach` | Truthful generic loading state while an Agent question is in flight | PASS |
| `03_agent_answer_mobile_dark.png` | 390 × 844 | Dark | `/coach` | Real Agent answer with "AGENT RUN · GROUNDED", the real source count and the source preview | PASS |
| `04_agent_run_expanded_mobile_dark.png` | 390 × 844 | Dark | `/coach` | "How this answer was built" expanded: one consumer sentence per verified source plus the deterministic authority line | PASS |
| `05_fast_path_mobile_light.png` | 390 × 844 | Light | `/coach` | Deterministic fast path: "RECORDED DATA", "Checked 1 verified source", Readiness | PASS |
| `06_decision_explorer_agent_trace.png` | 390 × 844 | Dark | `/coach` | What-if question: Decision Explorer appears in the real source trace ("Compared a verified what-if scenario") | PASS |
| `07_coach_desktop_light.png` | 1440 × 900 | Light | `/coach` | Desktop: product lockup plus Agent Run surface on an Agent answer | PASS |
| `08_about_agent_architecture.png` | 1440 × 900 | Light | `/profile/about` | About: "How the Agent works" flow, tool groups and the core principle | PASS |

## Acceptance checks

| Check | Result |
|---|---|
| A first-time reviewer can tell this is an Agent without reading GitHub | PASS ("AI Coach" + "Tool-Using Training Agent" + the one-line explanation on the Coach home) |
| The Agent visibly checks multiple verified sources | PASS ("Checked 6 verified sources" with the source preview and the expanded list) |
| The sources shown are the ones actually used | PASS (labels come from the response `tool_trace`; the fast path shows exactly one source) |
| An Agent answer is distinguishable from deterministic data | PASS ("AGENT RUN · GROUNDED" versus "RECORDED DATA") |
| The LLM does not own the training decision | PASS (expanded card closes with "AI orchestrates verified tools. Training decisions remain deterministic."; the About page states the principle and the DeepSeek boundary) |
| The architecture is understandable from About | PASS (question → Agent planner → verified training tools → deterministic results → DeepSeek explanation → grounded answer) |
| No fake Agent theatre | PASS (the loading state is one truthful generic line with `role="status"`; no simulated steps and no source list before the response exists) |
| Chain-of-thought hidden | PASS (no prompt, planner output, raw tool name, argument, JSON or traceback anywhere in the captured screens) |
| Decision Explorer and Calibration visibility | PASS (Decision Explorer visible in capture 06 when it actually ran; Calibration uses the same real-trace path) |
| Still a consumer sports-tech product | PASS (existing design system, no neon or chatbot styling, mobile layout unchanged) |
| No horizontal overflow / navigation collision | PASS (390 × 844 and 1440 × 900 both report scrollWidth = viewport width) |
| Light / Dark / System | PASS (both themes captured; System remains the default and resolves through the same CSS-variable swap) |

## Coverage note

The deterministic adapter is covered by `frontend/scripts/check-agent-visibility.mjs`
(`pnpm check:agent`, 17 checks: real counts, grounded flag, label mapping, Decision Explorer and Calibration
visibility, fast-path distinction, unknown-tool fallback, no reasoning surface, truthful loading copy). The
rendered result at both viewports and themes is covered by this capture set.
