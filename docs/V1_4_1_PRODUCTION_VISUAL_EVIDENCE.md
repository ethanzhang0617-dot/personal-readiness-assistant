# V1.4.1 — Public Production Visual Evidence

| Field | Value |
|---|---|
| Commit | `bd934eb` (the V1.4.1 identity release commit) |
| Tag | `v1.4.1` |
| Public URL | https://personal-readiness-assistant.vercel.app |
| Backend | https://personal-readiness-assistant-api.onrender.com |
| Capture date | 2026-09-19 |
| Browser | Codex in-app browser (Chromium engine) |
| Capture method | Real public production pages captured with browser automation. No mockups, no edited pixels, no localhost. |
| Evidence directory | `docs/evidence/v1.4.1-production/` |

## Captures

| Evidence | Viewport | Theme | Route | Scenario | Result |
|---|---|---|---|---|---|
| `01_today_mobile_light.png` | 390 × 844 | Light | `/` | Today with the new mobile identity "Adaptive Training" | PASS |
| `02_train_mobile_dark.png` | 390 × 844 | Dark | `/train` | Today's session with the MuscleMap front/back body visual | PASS |
| `03_coach_agent_mobile_dark.png` | 390 × 844 | Dark | `/coach` | Real Agent answer plus the collapsed "Checked N verified sources" line | PASS |
| `04_coach_agent_sources_open.png` | 390 × 844 | Dark | `/coach` | Expanded verified-source trace in product language | PASS |
| `05_insights_mobile_light.png` | 390 × 844 | Light | `/insights` | Insights surface | PASS |
| `06_desktop_today_light.png` | 1440 × 900 | Light | `/` | Desktop lockup: AT / Adaptive Training / Decision System | PASS |
| `07_desktop_coach_dark.png` | 1440 × 900 | Dark | `/coach` | Coach with the Agent response and the new identity | PASS |
| `08_about_identity.png` | 1440 × 900 | Light | `/profile/about` | Official English and Chinese project names plus the historical naming note | PASS |

## Acceptance checks

| Check | Result |
|---|---|
| New current identity visible | PASS (mobile header "Adaptive Training"; desktop lockup "AT / Adaptive Training / Decision System"; document title "Adaptive Training Decision System"; About shows the official English and Chinese names) |
| Old name not presented as current brand | PASS (0 accidental current-facing uses of "Personal Readiness Assistant" in the captured screens) |
| Historical naming | PASS (About shows "Former project name: Personal Readiness Assistant" and the V1.0 → V1.4 evolution, explicitly marked historical) |
| Agent functionality visible | PASS (real Agent answer with "Checked N verified sources"; expanded trace lists Today's session, Personal Response, Recommendation Confidence, Decision Trace, Recent training) |
| Chain-of-thought | NONE (no prompt, no planner output, no raw tool names, no JSON, no internal reasoning) |
| Secrets | NONE (no credential, token or personal sensitive data appears in any frame) |
| Horizontal overflow | NONE (390 × 844 and 1440 × 900 both report scrollWidth = viewport width) |
| Navigation collision | NONE (desktop sidebar and content stay separate; mobile bottom bar unchanged) |
| Themes | PASS (Light and Dark captured on production; System remains the default preference and resolves through the same CSS-variable swap) |

## Notes

The Coach conversation in the captures is the browser-local history of this demo profile, produced by the
live production Agent (DeepSeek orchestration over the 11 read-only tools), not a staged transcript. The
product version label stays `V1.4` because V1.4.1 is a patch-level identity release: `product_version` and
`api_version` remain `1.4`, matching `GET /api/health`.
