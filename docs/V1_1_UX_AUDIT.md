# V1.1 UX Audit (V1.0 baseline, real-browser)

**Audited build:** V1.0.0 `fe09ab6` (branch `v1.1-productization`, no product code modified)
**Audit date:** 2026-09-16
**Method:** the real Streamlit app served locally (`python -m streamlit run app.py`), driven by
headless Chromium (Playwright 1.62) with device emulation; every number below is a measured DOM
geometry value or a screenshot observation, not a generic UI opinion.
**Language of the product UI:** English-only (V1.0) — this audit does not propose bilingual UI.

Everything in this document is read-only analysis. No app file was edited to produce it.

---

## 0. Evidence and reproduction

| Item | Path |
|---|---|
| Measurement driver | `/Users/eeeethanz/Documents/Codex/2026-09-16/hi/work/v11_audit/audit_ui.py` |
| Targeted probes | `.../v11_audit/audit_probe.py`, `probe2.py` … `probe6.py` |
| Raw measurements | `.../v11_audit/ui_audit.json`, `.../v11_audit/probe.json` |
| Screenshots (top / bottom / full page per viewport) | `.../v11_audit/shots/` |

Viewports audited, at the plan's exact sizes: **375×812, 390×844, 393×852, 430×932, 768×1024,
1440×900** (mobile contexts use `is_mobile`, touch, DPR 3 and a real mobile UA string).
Pages audited at every viewport: Today, Check-in, Train, Trends, Coach, More — plus Science &
Logic / About / Profile by code and route inspection.

The audit scripts are intentionally kept **outside** the repository until PHASE 10 defines the
official `scripts/` + `artifacts/ui_screenshots/` layout.

---

## 1. P0 — Mobile shell findings (must be fixed first)

### 1.1 The fixed bottom navigation covers real content, and the Today primary CTA is its first victim

Actual geometry at the top of the Today page (scroll position 0), mobile shell active:

| Viewport | Bottom-nav top edge | Primary CTA `View workout` | CTA visible above nav | Centre tap hit-test |
|---|---|---|---|---|
| 375×812 | 751.8 | y 776.1 → 824.1 | **0 %** | hits the nav, not the button |
| 390×844 | 783.8 | y 776.1 → 824.1 | **16 %** | hits the nav, not the button |
| 393×852 | 791.8 | y 776.1 → 824.1 | **33 %** | hits the nav, not the button |
| 430×932 | 871.8 | y 753.7 → 801.7 | 100 % | button |
| 768×1024 | 963.8 | y 728.1 → 776.1 | 100 % | button |

Screenshots `shots/today_375x812_top.png` and `shots/today_390x844_top.png` show the consequence
directly: only a thin red sliver of the primary button is visible above the nav bar.

Interpretation: the app reserves bottom padding for the nav **at the end of the document**
(`.block-container { padding-bottom: calc(6.6rem + env(safe-area-inset-bottom)) }` → measured
105.6 px), which is why the *last* content is safe. But the nav is painted *over* the live viewport
at every scroll position, so any content that happens to sit in the last ~60 px of the viewport
while you are reading is covered — including the single most important call to action on the
product's most important page. On the plan's own acceptance wording this is
**"Content hidden behind nav: FOUND"**.

### 1.2 The safe-area mechanism cannot fire on a real iPhone as shipped

| Measurement | Value |
|---|---|
| Streamlit viewport meta tag | `width=device-width, initial-scale=1, shrink-to-fit=no` |
| `env(safe-area-inset-bottom)` on this page | **0 px** (measured with a fixed probe element) |
| Nav box with no inset | y 783.8, height **60.2**, `padding-bottom: 7.2px` |
| Nav box with an emulated 34 px home-indicator inset (CDP `Emulation.setSafeAreaInsetsOverride`) | height **94.2**, `padding-bottom: **41.2px**` |
| Content padding with the same inset | 105.6 → **139.6 px** |

This is the root cause of the reported "bottom navigation is partially covered on a real phone"
symptom, and it is precise:

* the CSS itself is correct — it uses `env(safe-area-inset-bottom)` and it demonstrably reacts
  to insets (60.2 → 94.2 px) when the browser reports them;
* but `env(safe-area-inset-bottom)` returns 0 unless the document declares
  **`viewport-fit=cover`**, and Streamlit's default viewport meta tag does not;
* so on iOS the nav keeps only 7.2 px of breathing room at the bottom, sits inside the
  home-indicator strip, and — because iOS Safari's collapsible bottom toolbar floats *over* the
  layout viewport — is overlapped by browser chrome while scrolling.

No `dvh`/`visualViewport` handling exists either, so the nav does not react to the collapsing
URL bar or the on-screen keyboard.

Fixing this in V1.1 means (a) declaring `viewport-fit=cover` (Viewport meta must be injected /
overridden, since Streamlit does not expose it), and (b) making the nav + content padding
safe-area-aware with a non-zero floor (e.g. `max(env(safe-area-inset-bottom), 8px)`), then verifying
on a physical iOS device — Chromium cannot prove Safari's floating-toolbar behaviour.

### 1.3 `st.chat_input` and the custom bottom nav collide (Coach page)

| Element | Measured at 390×844 |
|---|---|
| `[data-testid="stBottom"]` chat dock | y 651.7 → **843.7**, height 192, `position: sticky`, `z-index: 99` |
| `[data-testid="stChatInput"]` | y 667.7 → 787.7, height 120 |
| Chat textarea | 324 × 54 px |
| Send button | **32 × 32 px** (below the 44 px touch-target guideline) |
| Fixed bottom nav | y 783.8 → 844, `z-index: 1000` |
| **Dock area covered by the nav** | **59.9 px** |

The Streamlit chat composer is a bottom-docked sticky bar; the app adds a second, higher-z-index bar
on top of it. The result (see `shots/probe_coach_390x844.png`) is that the lower part of the
composer, its rounded container and its safe padding sit underneath the nav. It is still *usable*
by a ~9 px margin on 390×844, but it is fragile by construction: any shorter viewport, any
safe-area inset (which pushes the nav up to 94.2 px tall), or an open on-screen keyboard will
cover the send control. Two competing "bottom bars" is structurally wrong, not cosmetically wrong.

### 1.4 P0 acceptance matrix (measured, V1.0 baseline)

| Check | 375×812 | 390×844 | 393×852 | 430×932 | 768×1024 | 1440×900 |
|---|---|---|---|---|---|---|
| Bottom navigation visible | PASS | PASS | PASS | PASS | PASS | n/a (hidden by design) |
| Bottom navigation tappable (all 5 items clicked) | PASS | PASS | PASS | PASS | PASS | n/a |
| Safe area | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | n/a |
| Content hidden behind nav | **FOUND** | **FOUND** | **FOUND** | none | none | none |
| Horizontal overflow (document) | NONE | NONE | NONE | NONE | NONE | NONE |
| Desktop regression | — | — | — | — | — | **NONE** |

Nav height measured 60.2 px at every viewport with a 0 px inset, `z-index: 1000`, nav label font
size 0.67 rem (≈10.7 px) with 2-line labels.

---

## 2. Cross-cutting shell findings

### 2.1 Streamlit chrome is fully visible inside a consumer-style mobile shell

The `stHeader` is 60 px tall on a phone and contains, measured at 390×844:
`Deploy` button (57 × 28 px) and the ⋮ main menu (28 × 28 px). The main menu is Streamlit's
developer menu (Rerun / Settings / Print / Record a screencast) — it directly undercuts the
"early sports-tech product" impression the release is aiming for, and the Deploy button is a
publishing artifact, not a user feature. The header is also semi-transparent
(`rgba(247,247,244,.96)`), so page text scrolling underneath it is faintly legible, which reads as
a rendering glitch rather than as a design decision.

### 2.2 The browser-storage component leaks its status line into the page

Measured: the custom component iframe `browser_storage.personal_readiness_indexeddb` renders at
**358 × 24 px at y = 11.2** on a 390 px phone and **960 × 24 px at y = 20.8** on desktop — i.e. it
is visible, sitting in the header band. Its inner text ("Preparing local browser storage…",
"No local browser history yet.", "Local browser storage is ready.") bleeds through the translucent
header as ghost text in every screenshot, desktop included.

Internal plumbing must be invisible. This is a small change with a large perceived-quality payoff.

### 2.3 A dead sidebar-expand chevron is visible on phones

After any interaction that triggers a rerun, Streamlit 1.56 renders
`[data-testid="stExpandSidebarButton"]` (28 × 28 px at x 18, y 16) in the mobile header.
`styles.py` hides the **legacy** testid `stSidebarCollapsedControl`, so this newer control is not
hidden. Verified behaviour: tapping it does nothing visible — the sidebar remains
`display: none`, width 0 — so the user gets a control that looks tappable and is inert.

### 2.4 Vertical rhythm wastes first-screen space

On every mobile page there is a ~100–130 px empty band between the `More` utility row and the page
kicker (visible in all six top screenshots). Combined with Streamlit's default block gaps, the
Today page reaches 2046 px of content at 390×844 (2.4 screens) and Check-in reaches 2483 px, largely
because horizontal columns collapse to full-width stacked blocks without any compensating gap
tightening.

### 2.5 Status colour usage

Positive: status is never communicated by colour alone — `GREEN` / `AMBER` / `RED` text labels
accompany every dot (see `ui_components.STATUS_META`), and the hero repeats the state as a word.
This satisfies the accessibility requirement in the plan and should be preserved.

---

## 3. Today

**Current strengths.** The page tells the right story in the right order: date → greeting →
readiness hero (state, label, one-line explanation, index, baseline confidence) → today's training
(name, session demand, duration, type as chips) → CTA → "WHY TODAY?" bullets → "KEY SIGNALS" domain
cards → collapsed Decision Trace + readiness details + JSON download. The hero is genuinely
legible and the mobile variant (`.ara-mobile-hero`) reads well.

**Current problems.**

| # | Problem | Evidence |
|---|---|---|
| 1 | Primary CTA hidden behind the bottom nav on 375 / 390 / 393 | 0 % / 16 % / 33 % visible, centre tap hits the nav |
| 2 | First screen cannot answer "what do I train today?" | at 390×844: greeting 135.6–262.3, hero 344.6–577.9, training card 607.5–765.7, CTA 776.1–824.1, nav 783.8–844 |
| 3 | ~100 px dead band above the date, ~80 px between greeting and hero | screenshots `today_*_top.png` |
| 4 | Ghost storage-status text behind the header | section 2.2 |
| 5 | The four readiness domains are rendered twice (4 stacked domain cards, then the same four rows inside "Readiness details") | `render_today` |
| 6 | "KEY SIGNALS" cards each take a full screen-width on mobile and contain a single short line | `shots/today_390x844_full.png` |

**Mobile problems.** The 4-column "KEY SIGNALS" row becomes 4 very tall stacked cards; the hero's
right-hand index block competes with the status text for width at 375 px; the CTA is the only
primary action and it is the element that gets covered.

**Information hierarchy problems.** The page answers "how am I?" before "what do I do?" only in
theory: on a phone the actionable part (training + CTA) lands at the fold boundary. Redundant
domain blocks push the page to 2.4 screens.

**Visual problems.** Excessive top whitespace; four near-identical white cards in a row; the demo
caption is a full-width two-line sentence competing with the greeting; the ghost status text.

**Interaction problems.** The Decision Trace (the product's explainability asset) is collapsed by
default; the only above-the-fold action is partially untappable without scrolling.

**V1.1 proposed change.** Reorder to Greeting → Readiness Hero → Today's Training + primary CTA →
Why Today → compact Key Signals; make the CTA reachable without scrolling at 390×844 (tighten top
spacing, merge the demo badge into the header row, and/or make the CTA row sticky above the nav);
de-duplicate the domain presentation so signals are shown once; hide the storage status line.

**Core Logic Impact: NO.**

---

## 4. Check-in

**Current strengths.** Clear sectioning — `Recovery`, `How do you feel?`, `Local soreness
(optional)`, `Safety check` — inside one `st.form` with a single submit. Demo profiles offer three
scenario shortcuts. Safety flags are intact and unchanged.

**Current problems.**

| # | Problem | Evidence |
|---|---|---|
| 1 | Submit CTA is ~2.7 screens below the fold on every phone size | `Calculate readiness` at y 2305.9 (390×844); page 2483 px tall |
| 2 | Scale direction is ambiguous for Motivation | all four sliders share the caption `1 = low · 5 = high`; for Fatigue/Stress/Soreness high is worse, for Motivation high is better — exactly the confusion PHASE 5 calls out |
| 3 | The three demo scenario buttons stack full-width on mobile | adds ~250 px before the form |
| 4 | Local soreness = 7 selectboxes stacked full-width | long, repetitive, hard to scan |
| 5 | Number-input steppers are small (− / + inside a 48 px row) | screenshot `checkin_390x844_top.png` |

**Mobile problems.** The stacked scenario buttons and the 7 soreness selects dominate the scroll
distance; there is no sticky or per-section save affordance; the form ends with the safety check,
so the visual order of "past the end" is long.

**Information hierarchy problems.** "How do you feel?" mixes four different psychological constructs
under one identical caption; Local soreness (optional) is visually as heavy as the required
recovery inputs.

**Visual problems.** ~130 px dead band at the top; the `Recovery` form panel begins after three
large buttons, so the first field starts below 1400 px.

**Interaction problems.** Nothing indicates which values changed from the previous check-in; no
progress indicator; the only submit is at the very bottom.

**V1.1 proposed change.** Explicit direction labels (`Low → High`, plus per-scale
"higher = better/worse" wording — Motivation must state that higher is better); compact the demo
scenario shortcuts into a chip row; convert local soreness to a compact grid; consider a sticky
"Calculate readiness" affordance so the action is always reachable; tighten spacing.

**Core Logic Impact: NO** (labels/presentation only — the underlying scales and their direction in
the engine must not change).

---

## 5. Train

**Current strengths.** Alternatives are selectable without overwriting the primary (explicit
caption: "Selecting an alternative does not overwrite the primary recommendation."), the summary
card carries demand/duration/type, workout template and logging are behind expanders so the page
opens compact, and the log form is a real form with prescribed-vs-actual sets.

**Current problems.**

| # | Problem | Evidence |
|---|---|---|
| 1 | The alternatives radio group appears **above** the primary training card | `render_train` order; screenshot `train_390x844_top.png` — the first interactive element is the alternative selector |
| 2 | `TODAY'S TRAINING` is duplicated as the page kicker and as the card kicker | screenshot |
| 3 | "WHAT to train" vs "HOW HARD to train" is not visually separated | rationale bullets carry "Readiness is GREEN; today's session demand is…" mixed with selection logic |
| 4 | The exercise prescription requires a tap ("View workout" opens the template expander) | interaction cost on mobile |

**Mobile problems.** The page is 2657 px at 390×844; the primary card starts at y 455, and the
Decision-Trace material sits inside a text-only "WHY THIS WORKOUT?" bullet list whose content is
clipped at the fold by the nav.

**Information hierarchy problems.** Intended hierarchy is Primary > Alternatives > Avoid. On mobile
the render order is Alternatives (radio) > Primary (card) > rationale > template > Avoid, so the
hierarchy is inverted exactly where it matters most.

**Visual problems.** The `PRIMARY RECOMMENDATION · Selecting an alternative never overwrites…`
caption is a long two-line grey paragraph placed where a label would normally go.

**Interaction problems.** Selecting an alternative that is not the primary triggers a selectbox
workflow; there is no visible indication of which workout is currently "the plan" once a radio
selection is made.

**V1.1 proposed change.** Lead with the primary card and its CTA, then Alternatives, then a
structured Decision Trace component (GOAL → PROGRAMME/SPLIT → WEEKLY EXPOSURE → RECENT TRAINING →
LOCAL SORENESS → READINESS → SESSION DEMAND → RECOMMENDATION), then Avoid Today, with the log flow
last. Keep the deterministic content untouched; present it as a component rather than bullets.

**Core Logic Impact: NO.**

---

## 6. Trends

**Current strengths.** Calendar-based semantics are already correct in the engine (verified by
`test_training_load_uses_calendar_days_not_sessions` and the rest-day/sparse-history tests).
Time-window control (7 / 28 / all) exists; charts are native Streamlit/Altair so they resize with no
extra JS.

**Current problems.**

| # | Problem | Evidence |
|---|---|---|
| 1 | `st.dataframe` tables are wider than a phone and clip columns mid-word | `Shoulders + Arm…`, `overal…`, `GREE…` in `shots/trends_390x844_bottom.png` |
| 2 | Raw timestamps `2026-09-12 00:00:00` are shown to users | same screenshot |
| 3 | Internal identifiers are shown (`id` = `assessment-profile-2026-09-15`) | same screenshot |
| 4 | HRV chart is flattened because the y-axis starts at 0 while the data sits at ~3.5–4.1 | `shots/trends_390x844_top.png` |
| 5 | X-axis ticks mix formats (`Wed 09`, `Fri 11`, `Sep 13`, `Tue 15`) | same screenshot |
| 6 | Legend order is inverted relative to the data (7-day average listed before daily value) | same screenshot |
| 7 | No personal-baseline band, no green/amber/red readiness-over-time view | page structure |
| 8 | Readiness History is a raw table instead of a status trend | `render_trends` |

**Mobile problems.** Every data table needs horizontal scrolling inside a phone viewport; there is
no mobile-friendly column reduction; the "Sleep" section is cut by the nav at the fold.

**Information hierarchy problems.** Four signals are presented as four charts, then two raw tables;
the user cannot answer "is my trend normal for me?" without reading numbers.

**Visual problems.** Chart legend/axis styling is Streamlit-default and inconsistent with the
designed cards elsewhere; table typography is dense.

**Interaction problems.** No way to inspect a single day's value; tables are the only "history"
surface for training and readiness.

**V1.1 proposed change.** Rebuild the presentation layer: personal-baseline bands, status-coloured
readiness-over-time, one consistent chart style and axis behaviour (do not force a zero baseline on
log-scaled HRV), formatted dates, and mobile-friendly history cards or slim tables instead of raw
dumps. Evaluate `streamlit-echarts` for this phase only after a compatibility spike.

**Core Logic Impact: NO** for presentation (any change to the 7-day / 21-day calendar window
semantics would be a regression and is explicitly forbidden).

---

## 7. Coach

**Current strengths.** The architecture is right and worth protecting: deterministic engine →
structured context → optional Qwen wording, with a visible rule-based fallback and a
"How the Coach works" explainer. Engine status is surfaced honestly.

**Current problems.**

| # | Problem | Evidence |
|---|---|---|
| 1 | 8 full-width question buttons occupy the entire page before any conversation | 8 matched buttons counted on the Coach page; `shots/probe_coach_390x844.png` |
| 2 | The page opens **auto-scrolled to the bottom** — the context header and intro are off-screen | measured `scrollTop 607 / max 607`, h1 at y −453 after entering the page |
| 3 | The chat composer dock is overlapped by the bottom nav | 59.9 px of the dock is covered (section 1.3) |
| 4 | Send button 32 × 32 px; textarea 324 × 54 px | measured |
| 5 | The only "context header" is two grey caption lines | `render_coach` |

**Mobile problems.** The first screen is a wall of buttons, not a conversation; the composer — the
primary interaction — is the element that is partially covered.

**Information hierarchy problems.** Quick questions are visually dominant; the conversation history
(empty on first visit) sits below them; today's readiness context is a caption.

**Visual problems.** Eight identical full-width outlined buttons is the single heaviest visual block
in the whole product.

**Interaction problems.** Streamlit's chat auto-scroll means the user must scroll *up* immediately
after arriving to see what the Coach is; there is no compact context strip to anchor the page.

**V1.1 proposed change.** Reduce to 3–4 compact question chips (wrap or horizontal scroll), add a
lightweight context header (readiness state, today's training, session demand), make conversation
the visual centre, and resolve the composer/nav collision (e.g. nav hidden while the composer is
focused, or the composer raised above the nav). Keep the deterministic-first, Qwen-second
architecture and the fallback exactly as they are.

**Core Logic Impact: NO.**

---

## 8. More / Profile (mobile profile switching)

**Current strengths.** `More` is a sensible hub (Profile / Data / Learn / Info), with demo-vs-local
disclosure copy and clear routing buttons. Desktop keeps a proper active-profile selector in the
sidebar with `DEMO ·` / `MY LOCAL DATA ·` prefixes.

**Current problems.**

| # | Problem | Evidence |
|---|---|---|
| 1 | **The active-profile selector does not exist anywhere on a phone.** The only switcher is `st.selectbox("Active profile", …)` in `render_sidebar`, and the sidebar is `display: none` below 768 px | measured `[data-testid="stSidebar"]` display `none`, width 0 |
| 2 | Even the stray expand chevron cannot reveal it | tapping `stExpandSidebarButton` leaves the sidebar at `display: none`, width 0 |
| 3 | No active-profile indicator in the mobile shell | no visible "Active profile" label on any mobile page (`activeProfileLabelVisible: false`) |
| 4 | Demo/local identity is only a caption on Today and an info box on More | `render_today`, `render_more` |
| 5 | `Profile` is reachable only via `More → Profile` (not in the bottom nav) | `MORE_NAV_ITEMS` |

**Mobile problems.** Profile switching is functionally absent, which the plan lists as an explicit
V1.1 requirement (#70–#72). A demo user cannot switch between Ethan / Alex / Jessica on a phone, and
a local user cannot switch back to a demo profile.

**Information hierarchy problems.** Profile identity (who am I, demo or local) is buried below
navigation buttons on More.

**Visual problems.** More is a plain list of full-width buttons with `PROFILE / DATA / LEARN / INFO`
caps headers — functional, but visually unfinished compared with Today.

**Interaction problems.** No `Change Profile` affordance; deleting/creating profiles lives inside
expanders on the Profile page.

**V1.1 proposed change.** Add a mobile profile header at the top of `More` (Active profile name,
`DEMO PROFILE` / `LOCAL PROFILE` badge, `Change Profile` action) and a real mobile switcher covering
Ethan / Alex / Jessica / My Local Profile, with the demo/local isolation guarantees preserved.

**Core Logic Impact: NO** (routing/presentation; `profile_store` semantics must stay as they are —
demo and local data isolation is already enforced and tested).

---

## 9. Science & Logic / About

Not re-screenshotted in this pass beyond route verification: the page renders long-form evidence
content (`EVIDENCE_MAP`, `LIMITATIONS`, `REFERENCES`) and is structurally sound at desktop widths.
**Current problems (by inspection):** it inherits the same mobile shell issues (dead top band, nav
overlay, ghost status text) and its dense paragraph/bullet blocks have no mobile-specific
typography. **V1.1 proposed change:** apply the design system only — no content rewrite without
explicit request. **Core Logic Impact: NO.**

---

## 10. Honest verification boundary

| Claim | Status |
|---|---|
| Occlusion, nav geometry, safe-area behaviour, chat-dock collision, chrome visibility, overflow | **VERIFIED** by measurement in emulated Chromium |
| iOS Safari bottom-toolbar overlap and `env()` behaviour on a physical iPhone | **NOT VERIFIED** — structurally argued from the missing `viewport-fit=cover` and the CDP inset experiment; needs a real device before Phase 2 is declared done |
| Android Chrome dynamic URL bar behaviour | **NOT VERIFIED** |
| On-screen keyboard interaction with the nav and the Coach composer | **NOT VERIFIED** |
| IndexedDB save → reload → reopen | **NOT VERIFIED** (also unverified in V1.0's own QA report) |
| Desktop 1440×900 regression | **VERIFIED — none found** (nav `display: none`, sidebar intact, CTA visible) |

No screenshot in this audit was hand-edited, and no demo value was fabricated; all screenshots show
the real running app with real demo-profile data.

---

## 11. Prioritised V1.1 backlog derived from this audit

| Priority | Item | Phase | Core logic risk |
|---|---|---|---|
| P0 | Safe-area-correct bottom nav (`viewport-fit=cover`, inset floor, dynamic-viewport handling) | PHASE 2 | none |
| P0 | Stop the nav covering live content — guarantee the primary CTA is tappable at 375/390/393 | PHASE 2 + PHASE 4 | none |
| P0 | Resolve chat-composer vs bottom-nav collision | PHASE 2 + PHASE 8 | none |
| P1 | Remove Streamlit chrome (Deploy, main menu, stray expand chevron); hide the storage-status iframe | PHASE 2 | none |
| P1 | Mobile profile switching + active-profile badge | PHASE 9 | none (store untouched) |
| P1 | Today: first-screen reordering and spacing so "what to train / how hard" is above the fold | PHASE 4 | none |
| P1 | Check-in: explicit scale direction (esp. Motivation) and shorter scroll distance | PHASE 5 | none (labels only) |
| P1 | Trends: chart axis/baseline/labels + mobile-friendly history surfaces | PHASE 7 | none (calendar semantics frozen) |
| P2 | Design tokens + reusable components to replace per-page HTML/CSS | PHASE 3 | none |
| P2 | Coach: 3–4 question chips, context header, conversation-first | PHASE 8 | none |
| P2 | Train: Primary > Alternatives > Avoid hierarchy and a real Decision Trace component | PHASE 6 | none |
| P2 | Pin the Streamlit version and re-verify shell selectors against it | PHASE 3 / PHASE 12 | none |

---

## 12. Phase 1 conclusion

V1.0's engines, tests and data model are in good shape. Its mobile shell is not: the plan's known
"bottom navigation gets covered" problem is **confirmed**, and it is now explained by three
independent, measurable causes — a viewport meta tag that disables safe-area insets, an overlay
model that covers live viewport content (hitting the Today CTA hardest), and a second bottom bar
(`st.chat_input`) that the nav is drawn over on Coach — plus leaking Streamlit chrome.

No product code has been changed. Ready to start **PHASE 2 — P0 Mobile Shell** on your approval.

---

# PHASE 2 IMPLEMENTATION OUTCOME

**Commit:** `fix(mobile): make app shell safe-area aware` (see the Phase 2 report for the hash)
**Files:** `styles.py`, `ui_components.py`, `app.py`, `mobile_shell/` (new), `browser_storage/frontend/*`, `test_app.py`
**Architecture and rationale:** `docs/V1_1_MOBILE_SHELL.md`

## 13. What changed

1. The scrolling viewport (`stMain` / `stAppScrollToBottomContainer`) is shortened by the
   navigation band, so the fixed navigation can no longer cover live content.
2. Safe area is now effective: `mobile_shell/frontend/shell.js` adds `viewport-fit=cover` to the
   viewport meta (re-applied through a `MutationObserver`), and the CSS uses
   `max(env(safe-area-inset-bottom), 8px)`.
3. The navigation is a reusable component (`ui_components.mobile_bottom_nav_component`) that owns
   destinations, icons and active state; placement, height, z-index and safe-area spacing are owned
   by one shell rule set in `styles.py`.
4. Coach: the composer dock is `sticky` inside the shortened viewport, so it sits above the
   navigation band instead of under it.
5. Streamlit chrome is hidden on mobile (header, toolbar, Deploy, ⋮ menu, sidebar, legacy *and*
   current expand-sidebar testids).
6. The browser-storage bridge keeps identical IndexedDB behaviour but has no visible surface
   (0 px frame, screen-reader-only status, hidden wrapper).
7. One central mobile rhythm rule (`--ara-block-gap`, shell-owned) replaces the zero-height
   stylesheet block's default gap; it is what lets the Today CTA clear the navigation at 375 px.

## 14. Before / after measurements (same tooling, same viewports)

### 14.1 Today primary CTA (`View workout`) at first paint

| Viewport | Before: CTA box | Before: nav top | Before: visible | Before: centre hit | After: CTA box | After: nav top | After: visible | After: centre hit |
|---|---|---|---|---|---|---|---|---|
| 375×812 | 776.1 → 824.1 | 751.8 | **0 %** | nav button | 687.6 → 735.6 | 748 | **100 %** | CTA |
| 390×844 | 776.1 → 824.1 | 783.8 | **16 %** | nav button | 687.6 → 735.6 | 780 | **100 %** | CTA |
| 393×852 | 776.1 → 824.1 | 791.8 | **33 %** | nav button | 687.6 → 735.6 | 788 | **100 %** | CTA |
| 430×932 | 753.7 → 801.7 | 871.8 | 100 % | CTA | 665.2 → 713.2 | 868 | 100 % | CTA |
| 768×1024 | 728.1 → 776.1 | 963.8 | 100 % | CTA | 639.6 → 687.6 | 960 | 100 % | CTA |
| 1440×900 | 741.1 → 784.3 | n/a | 100 % | CTA | 693.5 → 736.7 | n/a (hidden) | 100 % | CTA |

### 14.2 Shell geometry

| Item | Before (V1.0) | After (V1.1 Phase 2) |
|---|---|---|
| Navigation height (no inset) | 60.2 px (`7.2 px` bottom padding) | **64 px** = 56 content + 8 floor |
| Navigation with a 34 px emulated inset | 94.2 px (mechanism correct but inert: meta had no `viewport-fit=cover`) | **90 px** = 56 + 34, viewport `754 px` |
| `env(safe-area-inset-bottom)` read by the page | 0 px | 0 px in Chromium (no device inset to report) — **active** when the browser reports one |
| Viewport meta | `…shrink-to-fit=no` | `…shrink-to-fit=no, viewport-fit=cover` |
| Content hidden behind nav (bottom of page) | 733.8 px on Today; −45 px on other pages (document-end padding only) | **0 px at every mobile viewport** |
| Horizontal overflow | none | none |
| Navigation fully visible / fully tappable | visible; covered the CTA | visible; all five tabs clicked through with the correct active state at every mobile viewport |

### 14.3 Coach composer

| Metric | Before | After |
|---|---|---|
| Composer dock box (390×844) | 651.7 → 843.7 (`sticky`, z-index 99) | 630.4 → 780.0 |
| Navigation box | 783.8 → 844 (z-index 1000) | 780 → 844 |
| **Overlap** | **59.9 px** | **0 px** (gap 0.0 px) |
| Send control | 32 × 32, partially covered | 32 × 32, hit-tests to itself (not 44 px — a Phase 8 sizing item, not a shell blocker) |
| Textarea | 324 × 54, lower edge under the nav | 324 × 54, fully above the nav, focusable |

### 14.4 Chrome and plumbing

| Item | Before | After |
|---|---|---|
| `Deploy` button | visible on mobile | hidden (`display: none`) |
| ⋮ developer menu | visible on mobile | hidden |
| Sidebar expand chevron | appears after each rerun (V1.0 hid only the legacy testid) | present in the DOM after a rerun but `display: none` |
| Storage bridge iframe | 358 × 24 at y = 11.2 (mobile) / 960 × 24 at y = 20.8 (desktop), status text legible through the header | 0 × 0, hidden wrapper, status text screen-reader-only |
| Shell bridge iframe | n/a (did not exist) | 0 × 0, hidden wrapper |
| Ghost "No local browser history yet." through the header | visible on every page | gone |

### 14.5 Desktop 1440×900 regression

| Check | Result |
|---|---|
| Mobile navigation hidden | PASS (`display: none`, 0 × 0) |
| Utility (`More`) row hidden | PASS |
| Sidebar present and usable | PASS (300 × 900; sidebar navigation switches pages, `Train` verified) |
| Profile selector | PASS (`Active profile` label + selectbox present at y 125.6) |
| Scrolling viewport height | PASS (900 px, unchanged) |
| Container padding | PASS (`20.8px 80px 83.2px`, unchanged) |
| Block gap | PASS (16 px, unchanged — the mobile rhythm rule is media-scoped) |
| Horizontal overflow | NONE |
| Chat composer | PASS (dock 770 → 900, textarea and send inside the viewport) |
| Unexpected bottom spacing | NONE |
| Content shift | Content sits ~48 px higher because the 24 px storage iframe and its block gap are gone. Intended, not a broken layout. |

## 15. Persistence after the storage-surface change

Chromium emulation, 390×844:

| Step | Result |
|---|---|
| Fresh context | no IndexedDB record |
| Create `My Local Profile` | record written; 1 non-demo profile; active profile = that profile |
| Reload | record still present; hydrated into the runtime (Today shows the local profile's empty state) |
| Bridge iframe height | 0 px |

This closes the "IndexedDB E2E — NOT VERIFIED" gap for Chromium. IndexedDB on a real iOS/Android
browser remains **NOT VERIFIED**.

## 16. Tests

| Command | Result |
|---|---|
| `python -m compileall .` | PASS |
| `python -m pytest -v` | **77 / 77 passed** = 72 existing (unchanged, none skipped or weakened) + 5 new shell tests |

New tests: shell spacing contract (tokens → viewport reservation → navigation, no legacy hard-coded
offset), chrome-hiding selector list incl. the current Streamlit testid, mobile navigation rendering
+ active state + navigation behaviour, viewport-bridge contract (and that it cannot trigger a
rerun), browser-storage invisibility.

## 17. Remaining verification boundaries (unchanged by Phase 2)

| Item | Status |
|---|---|
| Mobile shell geometry, occlusion, composer relationship, chrome, overflow | **EMULATION PASS** (Chromium, 6 viewports) |
| Real iOS Safari bottom-toolbar behaviour and real `env()` values | **REAL DEVICE NOT VERIFIED** |
| On-screen keyboard interaction with the composer and navigation | **REAL DEVICE NOT VERIFIED** (the CSS contract is measured by toggling `ara-keyboard-open`) |
| Android Chrome dynamic URL-bar behaviour | **NOT VERIFIED** |
| IndexedDB save/load + reload hydration | **EMULATION PASS**; real mobile browser **NOT VERIFIED** |
| PWA / standalone display-mode behaviour | **NOT VERIFIED** |

Items deliberately **not** touched in Phase 2 (later phases): mobile profile switching, Check-in
scale wording and length, Trends table clipping and timestamp formatting, HRV chart axis, Today /
Train / Coach / More redesigns, design-system migration, `streamlit-shadcn-ui`, `streamlit-echarts`.

---

# PHASE 4 IMPLEMENTATION OUTCOME — Today

**Commit:** `feat(today): improve daily decision dashboard`
**Files:** `app.py` (Today renderer), `ui_components.py` (Today components + primitives),
`styles.py` (Today blocks, tokens only), `test_app.py` (6 Today tests)

## 18. Information architecture

Today is organised as a **daily decision dashboard**, not a metrics dashboard:

```
Greeting (date · profile badge · name)
  ↓
Readiness hero        status badge · status label · one-line explanation · index · baseline confidence
  ↓
Today's Training      WHAT TO TRAIN | HOW HARD  +  primary CTA (View workout)
  ↓
WHY TODAY?            TRAINING DIRECTION (weekly exposure · recent training · programme)
                      SESSION DEMAND (readiness · session demand)
  ↓
KEY SIGNALS           2×2 metric grid: HRV · Resting HR · Sleep · Training load
  ↓
Readiness details / full Decision Trace (collapsed) · assessment JSON download
```

Design-system adoption in this phase: `status_badge` (readiness + every metric tile),
`confidence_label`, `context_chip`, `metric_tile` (4 signals in a real grid, not four stacked cards),
`primary_cta`, `identity_badge`. New page components: `today_training_card`, `metric_grid`,
`why_today`. `domain_card` is no longer used on Today (its four stacked cards duplicated the hero's
status four times); it remains part of the design-system API.

## 19. Before / after

| Measurement | Before | After |
|---|---|---|
| 390×844 — Readiness hero visible | 100 % | 100 % |
| 390×844 — Today's Training visible | 100 % | 100 % |
| 390×844 — Primary CTA visible / hit test | 100 % / CTA | 100 % / CTA (CTA at y 632.7–680.7, navigation starts at 780 → 99 px clearance) |
| 390×844 — "Why today" heading | 64 % | 100 % |
| 390×844 — page scroll height | 1814 px | **1438 px** (−21 %) |
| 375×812 — CTA visible / hit test | 100 % / CTA | 100 % / CTA |
| Stacked domain cards on the main screen | 4 | 0 |
| "Ready to train" repetitions in page text | 4 | **1** |
| `metric_tile` count | 0 | 4 |
| Status badges | 0 | 6 |
| Horizontal overflow (all six viewports) | none | none |

The first attempt at the new WHAT/HOW-HARD layout pushed the CTA below the fold at 375/390/393
(CTA visible 0 %, centre hit test returned the navigation). The layout was corrected in the same
phase — two-column fact grid plus an inline identity badge — and re-measured; the previous V1.0
numbers above are the pre-Phase-4 baseline, the corrected result is what shipped.

## 20. Wording / terminology decision (weekly exposure)

The engine's exposure window is `weekly_training_exposure()`: completed sessions with
`0 <= age < 7` days — **the last seven days including today**, not a calendar week. Today therefore
labels it exactly as the engine does:

> `Weekly exposure: Back 9.5/12 · below target`

and never calls it a "calendar week". The window itself was not modified. The same wording is used
by the Coach facts layer (`ai_facts.EXPOSURE_PERIOD`), so the product has one definition.

## 21. Factual integrity and duplication

* Every number on Today comes from `readiness_engine` / `training_recommendation_engine` output
  (verified by a test that renders Today in the same session and compares the rendered values with
  `ai_facts.build_personal_facts`).
* The main screen no longer shows z-scores, LnRMSSD, rolling SD or "21-day" reference wording; the
  technical rationale stays in Science & Logic and in the downloaded assessment JSON.
* Duplicate status text was removed (hero badge/label once; metric tiles carry their own status).
* No Qwen involvement on Today: opening the page does not load the embedded model (asserted in tests).

## 22. Phase 4 verification boundaries

| Item | Status |
|---|---|
| First-screen geometry, CTA hit test, overflow, shell contract at 6 viewports | **EMULATION PASS** (Chromium) |
| Phase 2 mobile shell contract after the redesign | **PASS** (nav band 64 px, CTA overlap 0 px, no content behind nav, Coach composer gap 0.1 px, safe-area inset still live) |
| Phase 3.5 coach grounding after the redesign | **PASS** (unchanged; re-verified end to end) |
| Real iOS Safari / Android rendering | **REAL DEVICE NOT VERIFIED** |
| 768×1024 Key Signals first-screen visibility | Still below the fold on that viewport (tablet is treated as the mobile shell); acceptable, Key Signals is a second-screen section |
