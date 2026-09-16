# V1.2 — Phase 3 Product UI Polish

**Branch:** `v1.2-nextjs-migration`
**Scope:** presentation only. No new product features, no engine change, no AI change.

## 1. Visual direction

Graphite and off-white neutrals, one elevated surface where it carries meaning, and status colour
reserved for readiness meaning. The product should read as a calm performance tool rather than a
dashboard: strong type, hairline dividers, generous rhythm, no decorative colour.

| Token | Value | Note |
|---|---|---|
| Background | `#f6f6f3` | warm off-white |
| Surface | `#ffffff` / `#fafaf7` | cards and quiet rows |
| Ink | `#14161a` | primary text |
| Muted | `#62666f` | supporting text |
| Line | `#e9e9e4` | hairline dividers |
| Primary action | `#17191c` | charcoal, never a status colour |
| Status | green `#1c7a4d`, amber `#9c5c00`, red `#ad241c` | readiness meaning only |

Typography scale: one hero number (`clamp(3.4rem, 13vw, 4.5rem)`, tabular), one page title
(1.6rem), one section title (1.06rem), body 0.86–0.95rem, meta 0.68–0.75rem. Labels are used
sparingly; the previous all-caps-everywhere treatment was removed.

Spacing rhythm: page gap 20–24px, section gap 24px, card padding 16–20px, control height 44–48px
(`min-h-11` / `min-h-12`), hairline dividers between list rows instead of nested cards.

Icon system: Lucide only, 14–16px, meaningful actions only — no decorative icons and no emoji.

Accessibility: one consistent `:focus-visible` outline, 44px minimum targets, `prefers-reduced-motion`
respected, status colour always paired with a written label.

## 2. The card wall was the main problem

Phase 2 answered every information block with a bordered rectangle. Phase 3 introduces a
`Section` primitive (eyebrow + title + description + divider) and reserves `Card` for content that
genuinely needs a surface:

| Screen | Before | After |
|---|---|---|
| Today | 4 stacked cards + 2 extra blocks | 1 elevated readiness hero + typographic decision block + inline check-in row + expandable chain |
| Train | 4 cards | page header + segmented switcher + hairline lists + one card for the log form |
| Insights | 5 cards | one prominent load card + sections with a 2-column chart grid on desktop |
| Profile | one long settings wall | four labelled groups (Training, Readiness, Planning, Demo) + information links |
| Check-in | 5 cards | four sections with a full-width action bar |
| Science | 8 cards | anchored sections with an in-page nav and reference list items |

## 3. Screen-by-screen changes

**Today (flagship).** Readiness hero: large tabular index, status badge, a clamped interpretation,
a quiet four-domain strip and a baseline line. The decision block carries the session name at
1.75rem with a three-column stat row (How hard / Duration / Effort) so the answer reads as a
decision rather than a metric. The primary CTA sits directly under it. The check-in state is a
single inline row, and the Decision Trace is a collapsible causal chain with a connector line.
Desktop uses two columns and fits the whole screen in 900px with no scrolling.

**Train.** Session switcher is a segmented control; the prescription is a hairline list; weekly
exposure is a progress list that shows recorded sets, the target, and how far below target a
muscle group is; recent sessions are compact rows; the log form is grouped with units, a segmented
completion control and per-exercise actual sets.

**Coach.** Assistant answers use a small avatar, a quiet provenance line ("From your recorded
data", "AI explanation", "Rule-based answer", "Safety guidance") and full-width text; user messages
are right-aligned charcoal bubbles. The composer is a single raised surface with a charcoal send
button, and the empty state explains what the Coach will and will not do.

**Insights.** A segmented window control, then a prominent training-load card (7-day AU, 21-day
reference, calendar coverage, sessions in the last 14 days, data sufficiency), then a Signals
section with four charts in a responsive grid, weekly exposure, and readiness history.

**Charts.** Still dependency-free SVG, now with y-axis ticks, a current-value readout, a hover/tap
guide with an accessible `aria-live` value, gaps for missing days, and a legend explaining the
solid value line, the dashed 7-check-in mean and the dotted personal baseline.

**Check-in.** Compact numeric inputs with units, one-tap 1–5 segmented scales with the direction of
each scale written out, per-muscle soreness selects and the safety screen, with a full-width sticky
action bar instead of a floating card.

**Profile / About / Data.** Profile is grouped and scannable; About is now its own route; the Data
page keeps the honest storage and AI disclosure and replaces immediate import with
select → validate → summary → explicit confirmation.

## 4. Approved cleanups in this phase

* **Import safety:** choosing a file no longer overwrites local data. The file is parsed and shown
  as a summary (profiles, check-ins, sessions, messages) with a warning, and only the explicit
  "Replace local data" action imports it.
* **Insights parity gap:** "Sessions, last 14 days" is now shown, computed server-side with the same
  date rule as the reference implementation. No new analytics logic.
* **About route:** `/profile/about`.
* **Coach provenance wording:** the uppercase `VERIFIED DATA` badge became "From your recorded data"
  (Phase 3 asks for a subtle, non-developer distinction). The behaviour is unchanged: personal
  factual and correction turns still make **zero** provider calls.

## 5. Verification

* Responsive QA: **45 / 45 route × viewport combinations pass** — 375×812, 390×844, 430×932,
  768×1024, 1440×900 across `/`, `/check-in`, `/train`, `/coach`, `/insights`, `/profile`,
  `/profile/data`, `/profile/about`, `/profile/science`. Zero horizontal overflow, zero controls
  resting under the bottom navigation, desktop sidebar present at ≥1024px.
* Screenshot QA: Today (mobile + desktop), Train, Coach, Insights, Profile, Check-in, About — all
  reviewed at 390×844, plus Today at 1440×900 (single screen, two columns, no scrolling).
* Functional regression: the full Phase 2 journey still passes **20 / 20** (check-in → Today update
  → session log → history/exposure update → Insights charts → Coach factual + explanation →
  profile edit → reload persistence). Profile switching: 6 / 6.
* Python: `compileall` PASS, `pytest` **161 / 161 PASS**. Frontend: `typecheck`, `lint`, `build` PASS.
  No React warnings or blocking console errors in the dev-server log.

## 6. Remaining visual limitations

1. Charts are still hand-rolled SVG: no zoom or pan, and tooltips are single-value rather than a
   full crosshair readout.
2. The Coach conversation area intentionally reserves space for the composer; with an empty
   conversation this leaves a visible gap on tall phones.
3. Native controls (select, number input, checkbox) keep the platform look; they are styled,
   not replaced.
4. No dark mode in this phase.
5. Science & Logic is a long page; the in-page anchors help, but sub-routes were deliberately not
   created.
6. The desktop layout is a comfortable reading column plus a two-column Today; it is not a
   wide-screen dashboard by design.
