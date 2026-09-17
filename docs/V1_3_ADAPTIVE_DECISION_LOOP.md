# V1.3 — Adaptive Decision Loop

**Branch:** `v1.3-adaptive-decision-loop` (from the V1.2 RC `7d21568`)
**Status:** Phase 1 pushed (`673010f`). Phase 2 local, not pushed. No machine learning,
no new data sources, no numeric confidence score.

* Phase 1 — Personal Response foundation: episodes, evidence states, bounded adjustment.
* Phase 2 — Personal Response Profile, Recommendation Confidence, evidence coverage,
  consistency, recency, adaptation history and an honest resolution of the previously
  unreachable upward-adaptation path.

The Phase 1 sections below are kept because Phase 2 builds on them rather than
replacing them; where Phase 2 changed a rule, the change is stated explicitly.

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

* **Downward (reduce one band)** when the *current* band has ≥3 complete episodes, at
  least 60% of them read as poorer than usual, **and** those episodes are a consistent
  pattern (Phase 2 added the consistency condition). Example: `High → Moderate`.
* **Within-tier personalisation** (Phase 2) replaces the removed `Moderate → High` rule —
  see §18.
* **Safety precedence:** RED, STOP, insufficient data and the Low band never adapt. The
  layer only ever changes a demand the readiness layer already permitted, and never by
  more than one band.

**Phase 1's honest reachability note.** Phase 1 implemented an "upward" rule that raised
the demand *tier* by one band when the band being moved into was Established. With the
real engine, demand **is** the band readiness permits (GREEN → High, AMBER → Moderate),
so that rule could only ever fire with synthetic inputs: raising `Moderate → High` on a
day the engine already decided readiness permits `Normal` contradicts the readiness
decision the layer sits on top of. It was therefore **unreachable in the real product
path**. Phase 2 removes it rather than advertising a capability the product cannot
deliver (see §18 and §19).

## 8. Transparency in the product

* **Today** shows a subtle label only when Personal Response actually affected the
  decision: *Adjusted from your recent response* with `High → Moderate demand` for a tier
  change, or *Personalized from recent response* with the within-tier guidance. Either
  way it adds one compact `Recommendation confidence` line (§15). With no personalisation
  the page is not decorated at all — no confidence card, no badge.
* **Decision Trace** gains one step, `PERSONAL RESPONSE`, between `READINESS` and
  `SESSION DEMAND`, reading `Reduced one step · High → Moderate`, `No adjustment`, or
  `Not enough history yet`. Phase 2 adds structured, scannable `Evidence` / `Pattern` /
  `Confidence` / `Adjustment` lines underneath it.
* **Train** gains a response history and the short post-session feedback flow.
* **Insights** gains, inside one Personal Response section, the **Personal Response
  Profile**, **Recommendation Confidence**, **Evidence Coverage**, **Recent Response
  Episodes** and **Adaptation History** (§14–§17).
* **Coach** answers the Personal Response questions deterministically, with **zero**
  AI-provider calls (§19).

## 9. Storage

Schema **v3**, unchanged by Phase 2. The envelope shape is unchanged; v3 normalises every
session row to carry the optional `response_context` / `response_feedback` keys and (Phase
2) every profile to carry `adaptation_log`, and the reader **migrates** older envelopes
instead of discarding them:

| From | Behaviour |
|---|---|
| v1 (single-profile envelope) | wrapped into per-profile maps; the state and chat are preserved |
| v2 | profiles, check-ins, training history, profile edits, chats preserved; sessions normalised |
| v3 | returned unchanged (a missing `adaptation_log` is defaulted to `[]` on read) |
| newer than v3, or unusable | refused (returns `null`) so a downgrade cannot corrupt newer data — never a silent reset |

**Phase 2 decision:** `adaptation_log` is a purely additive, optional field, so the schema
version is deliberately **not** bumped. Bumping it would force a rewrite of every stored
envelope for no benefit, and a version bump is the one change that can make an older build
refuse a newer envelope. Adding the field with a `[]` default is lossless in both
directions: an older build ignores it, a newer build defaults it. V1.2 and V1.3 Phase 1
data survive untouched.

`pnpm check:store` runs 14 migration assertions (data preserved, normalisation, the
adaptation-log defaults, refusal paths, partially damaged input).

## 10. API

| Endpoint | Purpose |
|---|---|
| `POST /api/state/feedback` | store the short post-session feedback on a session |
| `POST /api/state/personal-response` | Personal Response payload for the client's own state |
| `GET /api/personal-response` | read-only payload for a demo profile (`response_demo=` selects a case) |
| `GET /api/state/base?response_demo=` | seeds one of the four documented demo response histories |

Today's payload now carries `base_session_demand`, the final `session_demand`, the
`personal_response` block, `recommendation_confidence` on the recommendation, a
`detail` object on the `PERSONAL RESPONSE` trace step, and the 9-step Decision Trace.

The Personal Response payload exposes `confidence`, `coverage`, `consistency`,
`relevant` (count, band, window), `profile` (by demand and by focus), `within_tier`,
`no_increase_reason`, `base_demand` / `final_demand` and `adaptation_history`.

| Phase 2 field | Meaning |
|---|---|
| `confidence` | Limited / Developing / Strong, with the evidence counts behind it |
| `coverage` | how much personalised history exists, and how recent it is |
| `consistency` | how much the relevant episodes point the same way |
| `relevant` | the episodes that may drive today: same demand, inside the recency window |
| `profile` | the Personal Response Profile |
| `within_tier` | the optional in-range guidance, or the reason it was withheld |
| `adaptation_history` | the stored decision events, newest first |

## 11. Demo cases

Available from **Profile → Demo controls** (never in the daily workflow):

| Case | Shows |
|---|---|
| Not enough history yet | 1 episode → Limited confidence, no adjustment |
| Emerging pattern | 4 High-demand episodes, mixed → Developing confidence, no adjustment |
| Poor tolerance to high demand | 3 High-demand episodes with poorer responses → **High → Moderate** adjustment (Developing confidence) |
| Established good tolerance | 6 High-demand episodes tolerated better than expected → **Strong** confidence → within-tier guidance, demand unchanged |

Phase 2 changed the seeding: the demo episodes are recorded at the demand the product
**actually prescribes** for that profile and scenario (`demo_seed(profile, case,
base_demand)`), chosen from the live recommendation when the demo is loaded. Phase 1 seeded
some cases at `Reduced / autoregulated`, which meant the current `High` recommendation had
zero relevant episodes and the demo displayed "Limited evidence" while claiming to show an
established pattern. A demo must not be able to demonstrate a state the real rules would
not produce.

The third case is the downward portfolio demonstration: load it and the base High
recommendation is reduced to Moderate, with the Decision Trace explaining exactly why. The
fourth is the honest good-tolerance demonstration: the demand stays High and the product
offers bounded extra effort inside the range it already prescribed.

## 14. Personal Response Profile (Phase 2)

The profile is the plain-language answer to *"what has the system learned about me?"*:

| Field | Meaning |
|---|---|
| by demand band | observations, evidence state, `poorer / as expected / good` counts, pattern, recent pattern |
| by training focus | shown **only** once that focus has ≥3 complete episodes, so the product never presents a category its data cannot support |

Patterns are the same three transparent readings as Phase 1, computed both over all
complete episodes and over the recent ones, so "usually harder to recover from" is never
reported from stale history alone.

## 15. Recommendation Confidence (Phase 2)

A single qualitative state describing **how much personal evidence supports the
personalisation**. It is deliberately not a probability, not a recovery score and not a
percentage:

| State | Rule |
|---|---|
| **Limited** | fewer than 3 relevant episodes at today's demand |
| **Developing** | 3–5 relevant episodes, or 6+ whose pattern is not yet consistent |
| **Strong** | 6+ relevant episodes with a consistent pattern |

Inputs are only: the number of eligible episodes, how many match today's demand, how many
are recent enough, whether the next-day observation is complete, and whether the pattern
is consistent. No weighted model, no hidden factors.

**It never affects readiness.** Confidence describes the *evidence for the
personalisation*. It cannot change the readiness index, the GREEN / AMBER / RED state or
safety routing, and the note attached to every payload says so.

## 16. Evidence coverage, consistency and recency (Phase 2)

* **Coverage** reports complete episodes, episodes awaiting a check-in, the last complete
  episode, and how many observations exist per demand band. No invented precision.
* **Consistency** is the share of relevant episodes pointing the same way: consistent at
  ≥3 relevant episodes with ≥60% agreement, otherwise *Mixed*. The tie-break order
  (`poorer → as usual → better`) is deterministic so two identical runs report the same
  leader.
* **Recency** is a documented product heuristic, not exponential decay: only episodes
  inside `RECENT_WINDOW_DAYS = 56` drive personalisation, capped at the
  `MAX_RECENT_EPISODES = 12` newest. **Older episodes are never discarded** — they remain
  in the history, in the profile counts and in Insights; they simply stop influencing
  today's decision, and the copy says so.

## 17. Adaptation history (Phase 2)

One meaningful event per day, stored in the client's own state (`adaptation_log`, capped
at 90 and upserted per date so recomputing the same day never duplicates an entry):

`date`, `base_demand` / `base_band`, `final_demand` / `final_band`, `adjustment`, `result`
(`reduced` / `raised` / `within_tier` / `no_change`), `confidence`, `evidence`,
`relevant_episodes`, `reason`, `recorded_at`.

Internal calculations are not logged — only decisions. Insights shows it newest first.

## 18. Within-tier personalisation (Phase 2)

The honest replacement for the removed upward tier raise. When, and only when:

1. the personal evidence is **Strong**,
2. the user repeatedly tolerates the current prescribed demand well (≤20% poorer),
3. today's readiness is **GREEN**,
4. no safety flag and no local soreness at or above 4/5 exists,
5. the current band has a legitimate in-range option,

the product offers a small **optional** progression *inside* the demand it already
prescribed — taking the main sets toward the harder end of the existing RIR range
(`1–3 RIR` at normal demand). It adds no tier change, no extra sets, no volume jump, no
new precision, and it cannot override exposure, soreness or readiness.

If a condition fails the product says which one failed in plain language (readiness is not
Green; safety or soreness was reported). If no safe in-range option exists at all it uses
the explicit ceiling message:

> Good tolerance observed. No additional increase is recommended because today's base
> recommendation already uses the available demand range.

The product never claims an upward adaptation it cannot perform.

## 19. Phase 2 testing

`test_adaptive.py` (31 tests) and `test_api.py` (39 tests) cover: the three confidence
states, confidence being about evidence rather than readiness, consistency labels, demand
matching, the recency boundary, older episodes remaining visible, evidence coverage,
pending episodes, the profile and its focus gate, within-tier guidance and every condition
that withholds it, the ceiling message, adaptation-history upsert, base-vs-final
separation, RED/AMBER precedence, and the deterministic Coach answers (asserting **zero**
provider calls with a monkeypatched transport). `pnpm check:store` covers the storage
defaults. The Phase 1 test that asserted the unreachable tier raise was rewritten to
assert its absence.

## 20. Coach questions (deterministic, zero provider calls)

* *How do I usually respond to high-demand sessions?*
* *How confident is today's personalized recommendation?*
* *How many response episodes do I have?*
* *How many sessions support this adjustment?*
* *Has Personal Response changed my training before?*
* *Why didn't you increase today's training if I usually recover well?*
* *Why was today's session adjusted?*
* *What happened after my last session?*

All of these are answered from recorded data. DeepSeek may still *explain* Personal
Response reasoning, but only structured verified facts are sent, and the existing AI-01
grounding guard contracts stay in force — no invented confidence state, episode count,
response pattern or training history.

## 12. Science boundaries

These rules are **transparent product heuristics**. No published study validates this
exact algorithm, its thresholds, its three evidence states or its one-step bound. The
existing evidence boundaries on the Science & Logic page continue to apply, and the
following claims remain out of scope: recovery percentage, training-tolerance percentage,
injury or fatigue probability, "your body needs X hours", and anything resembling a
physiological prediction. Response patterns describe how *this user's own sessions were
followed by their own next check-ins*, nothing more.

**Recommendation Confidence (Phase 2)** reflects the quantity and consistency of the
personal observations available to the product. It is explicitly **not** clinical
confidence, statistical certainty, injury probability or recovery probability, and the
product never renders it as a number. The same boundary applies to the within-tier
guidance: it is an optional nudge inside an already-permitted range, not a validated
progression model.

## 13. Known limitations

1. **The adaptive layer covers the strength-style demand ladder only.** The engine's
   aerobic paths prescribe effort as `RPE 3–4 / 10`, which is not one of the three demand
   bands, so those sessions stay outside Personal Response entirely (the payload reports
   it as not applicable rather than as missing evidence). The running demo profile shows
   this.
2. **Raising the demand tier is not a product capability.** It was removed rather than
   advertised (§7, §18). Good tolerance is expressed within tier, or explained as
   unavailable.
3. The 3-day linking window, the 7-check-in context window, the 56-day recency window and
   the 12-episode cap are product choices, not validated monitoring windows.
4. Episodes need feedback plus a following check-in; a user who logs sessions without
   feedback accumulates no evidence, and the UI says so rather than inventing a pattern.
5. Interpretation uses simple signal counting, not a weighted model — deliberately.
6. Sessions logged before Phase 1 stay unclassified and never contribute evidence.
7. Confidence, consistency and coverage are heuristics with published thresholds; no
   study validates them and none of them is a probability.
8. No wearable, no cloud sync, no accounts, no machine learning, no numeric confidence
   score.
