# V1.4 Agent — UI Acceptance Evidence

| Field | Value |
|---|---|
| Date | 2026-09-19 |
| Product | Adaptive Training Decision System V1.4 (Agent layer) — formerly Personal Readiness Assistant |
| Code under test | `v1.4-agent-layer` @ `4ee8d49` (the Agent UI itself is unchanged by the release-hardening changes) |
| Environment | Next.js 16 dev server on `http://localhost:3000`, FastAPI on `http://127.0.0.1:8000`, real local provider credential configured |
| Browser | Codex in-app browser (Chromium engine) |
| Evidence directory | `docs/evidence/v1.4-agent/` |
| Capture method | Real application UI captured through browser automation. No mockups, no fabricated screens, no edited pixels. |

## Scenario

The Coach was opened at the canonical demo profile, the conversation was cleared, and one genuine
Agent turn was run through the real UI:

> **"Why is today's recommendation lighter than usual?"**

That question requires several verified sources, so it exercises the whole V1.4 path: routing →
structured planner → read-only tools → verified results → grounded synthesis → guards, and then the
tool-trace disclosure in the answer.

Observed answer (real provider output, 6 verified sources):

> "Today's recommendation isn't actually lighter — it's a Normal-demand Back + Biceps session of
> 50–65 min at 1–3 RIR, the same demand as the engine's base. Readiness is GREEN (index 90/100),
> though your autonomic domain is AMBER, with LnRMSSD 0.6 SD below baseline and resting heart rate
> above baseline. Back is at 9.5 of 12 weekly sets, so it stays the priority."

Every number in that answer is licensed by the deterministic facts or by a tool result from the same
turn; the demand tier is the tier the engine produced.

## Evidence

| Evidence | Viewport | Theme | Scenario | Expected behaviour | Result |
|---|---|---|---|---|---|
| `01_coach_mobile_light.png` | 390 × 844 | Light | Coach home, Agent UI initial state | Four main suggestions, three secondary topics, fixed input, restrained "AI Coach" labelling | PASS |
| `02_coach_mobile_dark_agent_answer.png` | 390 × 844 | Dark | Genuine Agent answer visible | Answer plus "Checked N verified sources"; no reasoning trace, no raw JSON | PASS |
| `03_coach_mobile_dark_tool_trace_open.png` | 390 × 844 | Dark | Verified-sources disclosure expanded | Human-readable labels only (Today's session, Readiness, Personal Response, Recommendation Confidence, Recent training, Decision Trace) | PASS |
| `04_coach_desktop_light_agent_answer.png` | 1440 × 900 | Light | Agent answer and tool trace | Trace legible, layout intact, sidebar navigation unaffected | PASS |
| `05_coach_desktop_dark.png` | 1440 × 900 | Dark | Coach Agent experience | Dual-theme parity; no contrast or overflow defects | PASS |

## What was verified during capture

| Check | Result |
|---|---|
| Four main suggestions remain (`Why this workout?`, `Explain my readiness.`, `Can I train harder today?`, `How much have I trained this week?`) | PASS (4/4, inside the collapsed library once a conversation exists) |
| Three secondary categories remain (Personal Response, In-session Calibration, Training History & Evidence) | PASS (3/3) |
| Conversation-first IA and the fixed input remain usable | PASS (message sent and answered from the UI) |
| Tool trace expands and collapses | PASS (both states exercised) |
| Light theme | PASS |
| Dark theme | PASS |
| System theme | PASS (System resolves to the platform preference; verified on this machine as light, matching the reported `prefers-color-scheme`) |
| 390 × 844 horizontal overflow | PASS (`scrollWidth` 390 = viewport 390) |
| 1440 × 900 layout collision | PASS (`scrollWidth` 1440 = viewport 1440) |
| No chain-of-thought, no planner prompt, no raw JSON, no tool names, no secrets in the UI | PASS (scanned the rendered text: no `chain-of-thought`, `system prompt`, `tool planner`, `"tool":`, `sk-`) |
| No devtools, console overlay, loading skeleton or broken API state in any frame | PASS |

### About the "Checked N verified sources" line

That line is a **tool-execution trace**, not chain-of-thought. It names the verified product sources
the Agent consulted for this answer, in product language, and nothing else. It contains no internal
planner prompt, no tool names, no arguments, no step-by-step reasoning and no model deliberation.
The separate "See reasoning" line is the V1.3 provenance note about who wrote the wording; it is also
not chain-of-thought.

## Reproducing the capture

```bash
# terminal 1 — API (with a provider credential if a live-provider answer is wanted)
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# terminal 2 — web
cd frontend && pnpm dev --port 3000
```

Open <http://localhost:3000/coach>, clear the conversation, and ask
"Why is today's recommendation lighter than usual?".

With no credential configured the same path still runs: the Agent consults the same tools, shows the
same tool trace and answers from the verified results, with the product notice that AI explanation is
temporarily unavailable. Neither the UI nor the tool trace depends on the provider being present.
