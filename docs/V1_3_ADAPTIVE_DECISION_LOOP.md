# V1.3 — Adaptive Decision Loop, Phase 1: Personal Response Foundation

**Branch:** `v1.3-adaptive-decision-loop` (from the V1.2 RC `7d21568`)
**Status:** Phase 1, local, not pushed. No machine learning, no new data sources.

## 1. Product goal

The loop the product has always described:

```text
Understand today → Recommend → Perform → Observe actual response → Learn personal response → Improve next decision
```

V1.2 answered the first two steps. Phase 1 closes the rest with a **transparent,
bounded, deterministic** layer that learns how *this* user tends to respond to the demand
levels they actually trained at. The shift is **Personal Baseline → Personal Response**.

Nothing here is a black box: every adaptation names the observations behind it, and the
base recommendation is always shown next to the final one.

## 2. What adaptation may and may not change

| May change | Never changes |
|---|---|
| HOW HARD: session demand (one band), effort/RIR guidance, adjustment wording | WHAT TO TRAIN, safety routing, injury/soreness exclusions, goal/programme structure, weekly exposure logic |

Priority order, unchanged except for the new step:

```text
Safety → Goal / Programme → Exposure / Recent training → Local soreness → Readiness
       → Personal Response → Session Demand → Recommendation
```

Personal Response sits **after** readiness and can never override it.

## 3. Response episode model

One episode is a compact, inspectable record:

| Part | Source |
|---|---|
| **Before** — readiness status, index, baseline confidence, local soreness | captured when the session is logged |
| **Recommendation** — base demand, final demand, band, adjustment, duration, RIR, exposure note | captured at the same moment |
| **Performed** — duration, session RPE, working sets, completion | the existing completed-session record |
| **Feedback** — perceived difficulty (1–5), performance feeling (1–5), completion, optional note | the short post-session flow (it deliberately does **not** repeat session RPE) |
| **After** — the next morning check-in (fatigue, soreness, motivation, stress, sleep, HRV, resting HR) | existing check-in data |

An episode is **complete** when it has feedback, a classified demand band and a linked
next check-in. No separate schema, no extra survey, no wearable.

**Linking.** Each check-in links to the most recent completed session before it, within
3 days (`MAX_LINK_GAP_DAYS`). A session whose check-in is already claimed by a closer
session is left unlinked rather than double-linked. Sessions logged before this phase
have no pre-session snapshot, so they stay unclassified and never contribute a pattern.

## 4. Demand bands

The engine's own vocabulary, ordered:

| Band | Engine wording |
|---|---|
| Low | `Rest or lower-demand` (RED) |
| Moderate | `Reduced / autoregulated`, `Reduced strength` (AMBER) |
| High | `Normal` (GREEN) |

Effort guidance is drawn from the product's existing published prototype ranges
(`1–3 RIR` at normal demand, `2–4 RIR; avoid unnecessary failure` when reduced). Phase 1
moves **at most one band**.

## 5. Response interpretation

Deterministic and readable: each episode compares the observation with the user's own
recent context (the mean of the previous up-to-7 check-ins) and counts plain signals.

| Negative signals | Positive signals |
|---|---|
| Next-day fatigue at least 1 point above recent usual | Next-day fatigue at least 1 point below recent usual |
| Next-day soreness at least 1 point above recent usual | Next-day soreness at least 1 point below recent usual |
| Session stopped early or modified | Low perceived difficulty, completed as planned |
| High perceived difficulty (≥4) with low performance feeling (≤2) | Performance feeling ≥4 |

Verdict: negative signals outweighing positive → `poorer_than_usual`; positive outweighing
negative → `better_than_usual`; otherwise `as_usual`.

## 6. Evidence sufficiency

Simple, transparent counts of **complete** episodes (product heuristics):

| Complete episodes | Evidence state |
|---|---|
| 0–2 | Insufficient — no adaptation |
| 3–5 | Emerging |
| 6+ | Established |

Per band the same counts produce a tolerance pattern: `Usually harder to recover from`
(≥60% poorer with ≥3 observations), `Generally tolerated better than expected` (≥60%
better), `Generally tolerated as expected`, or `Insufficient evidence`.

## 7. The adaptation rule (bounded)

```
base recommendation (engine)
  → Personal Response: 0 or ±1 band
  → final recommendation (product)
```

* **Downward (reduce one band)** when the *current* band has ≥3 complete episodes and at
  least 60% of them read as poorer than usual. Example: `High → Moderate`.
* **Upward (raise one band)** requires much stronger evidence: the band being moved *into*
  must be **Established** (≥6 complete episodes) with at least 80% tolerated as usual or
  better, **and** today's readiness must be Green. Tolerating the current band well is
  explicitly not enough.
* **Safety precedence:** RED, STOP, insufficient data and the Low band never adapt. The
  layer only ever changes a demand the readiness layer already permitted, and never by
  more than one band.

**Reachability note (honest).** With the current engine, demand is always the band that
readiness permits (GREEN → High, AMBER → Moderate), so the upward branch has no headroom
to act on in practice and is covered by unit tests with synthetic inputs. It is kept
because the rule is part of the design and Phase 2 expects to introduce an explicit
"unmet capacity" signal. Downward adaptation is reachable today.

## 8. Transparency in the product

* **Today** shows a subtle label — *Adjusted from your recent response* — only when a real
  adjustment happened, plus `High → Moderate demand`. With no adaptation the page is not
  decorated at all.
* **Decision Trace** gains one step, `PERSONAL RESPONSE`, between `READINESS` and
  `SESSION DEMAND`, reading `Reduced one step · High → Moderate`, `No adjustment`, or
  `Not enough history yet`.
* **Train** gains a response history and the short post-session feedback flow.
* **Insights** gains a Personal Response section: complete episodes, episodes awaiting a
  check-in, evidence state, per-band tolerance and an expandable episode detail
  (Before / Recommended / Performed / After).
* **Coach** answers these deterministically, with **zero** AI-provider calls:
  *How do I usually respond to high-demand sessions?*, *How many response episodes do I
  have?*, *Why was today's session adjusted?*, *What happened after my last session?*

## 9. Storage

Schema **v2 → v3**. The envelope shape is unchanged; v3 normalises every session row to
carry the optional `response_context` / `response_feedback` keys, and the reader now
**migrates** older envelopes instead of discarding them:

| From | Behaviour |
|---|---|
| v1 (single-profile envelope) | wrapped into per-profile maps; the state and chat are preserved |
| v2 | profiles, check-ins, training history, profile edits, chats preserved; sessions normalised |
| v3 | returned unchanged |
| newer than v3, or unusable | refused (returns `null`) so a downgrade cannot corrupt newer data — never a silent reset |

`pnpm check:store` runs 11 migration assertions (data preserved, normalisation, refusal
paths, partially damaged input).

## 10. API

| Endpoint | Purpose |
|---|---|
| `POST /api/state/feedback` | store the short post-session feedback on a session |
| `POST /api/state/personal-response` | Personal Response payload for the client's own state |
| `GET /api/personal-response` | read-only payload for a demo profile (`response_demo=` selects a case) |
| `GET /api/state/base?response_demo=` | seeds one of the four documented demo response histories |

Today's payload now carries `base_session_demand`, the final `session_demand`, the
`personal_response` block and the 9-step Decision Trace.

## 11. Demo cases

Available from **Profile → Demo controls** (never in the daily workflow):

| Case | Shows |
|---|---|
| Not enough history yet | Insufficient evidence, no adjustment |
| Emerging pattern | 4 episodes, Emerging, no adjustment |
| Poor tolerance to high demand | 3 High-demand episodes with poorer responses → **High → Moderate** adjustment |
| Established good tolerance | 6 tolerated episodes → Established |

The third case is the portfolio demonstration required by the phase brief: open **Today**
with the *Well Recovered Day* scenario after loading it and the base High recommendation
is reduced to Moderate, with the Decision Trace explaining exactly why.

## 12. Science boundaries

These rules are **transparent product heuristics**. No published study validates this
exact algorithm, its thresholds, its three evidence states or its one-step bound. The
existing evidence boundaries on the Science & Logic page continue to apply, and the
following claims remain out of scope: recovery percentage, training-tolerance percentage,
injury or fatigue probability, "your body needs X hours", and anything resembling a
physiological prediction. Response patterns describe how *this user's own sessions were
followed by their own next check-ins*, nothing more.

## 13. Known limitations (Phase 1)

1. Upward adaptation is implemented but cannot fire with the current engine vocabulary
   (see the reachability note).
2. The 3-day linking window and the 7-check-in context window are product choices, not
   validated monitoring windows.
3. Episodes need feedback plus a following check-in; a user who logs sessions without
   feedback accumulates no evidence, and the UI says so rather than inventing a pattern.
4. Interpretation uses simple signal counting, not a weighted model — deliberately.
5. Sessions logged before this phase stay unclassified and never contribute evidence.
6. No wearable, no cloud sync, no accounts, no machine learning, no numeric confidence
   score (evidence stays qualitative: Insufficient / Emerging / Established).
