# V1.1 Design System

**Phase:** PHASE 3 — Design System
**Scope:** design tokens, reusable primitives, status semantics, and the
`streamlit-shadcn-ui` evaluation. Page-level redesigns belong to later phases.

## 1. Principles

1. **One source of truth.** Tokens live in `styles.DESIGN_TOKENS` and are emitted into the document as
   CSS custom properties, so a value cannot exist twice.
2. **Token-first CSS.** `APP_CSS` references `var(--ara-*)` only, and `ui_components.py` contains no
   colour literal at all.
3. **Status = colour + words.** Green / amber / red are the only saturated colours and always carry a
   text label.
4. **Hierarchy without decoration.** Surface, border and spacing carry hierarchy; shadow is limited to
   the mobile navigation bar.
5. **Mobile first.** A primitive is not "done" until it is verified at 375 / 390 / 430 px.

## 2. Tokens

All tokens are generated from `styles.DESIGN_TOKENS` (`COLOR_TOKENS`, `SPACE_TOKENS`,
`RADIUS_TOKENS`, `SHADOW_TOKENS`, `TYPE_TOKENS`). 53 tokens in total.

### 2.1 Colour

| Purpose | Token | Value |
|---|---|---|
| App background | `--ara-bg` | `#f7f7f4` |
| Surface | `--ara-surface` | `#ffffff` |
| Surface secondary | `--ara-surface-2` | `#fbfbf8` |
| Surface hover / tertiary | `--ara-surface-3` | `#f0f0ec` |
| Text primary | `--ara-text` | `#171717` |
| Text secondary | `--ara-text-2` | `#686868` |
| Text muted (labels) | `--ara-text-muted` | `#777777` |
| Border / border strong | `--ara-border`, `--ara-border-strong` | `#e8e8e3`, `#deded8` |
| Ink (primary button) | `--ara-ink`, `--ara-ink-hover` | `#1d1d1b`, `#383835` |
| Status: green / amber / red | `--ara-status-green` … | `#18864b`, `#b96d00`, `#c53f32` |
| Status: stop / insufficient | `--ara-status-stop`, `--ara-status-neutral` | `#a32626`, `#68717a` |
| Shell surfaces | `--ara-header-bg`, `--ara-nav-bg` | translucent tints |

### 2.2 Spacing

`--ara-space-2xs .25rem · xs .5rem · sm .75rem · md 1rem · lg 1.25rem · xl 1.5rem · 2xl 2.25rem`

Component padding uses the nearest step. The mobile block rhythm is the shell token
`--ara-block-gap` (`.7rem`, PHASE 2) so page spacing and shell spacing stay in one system.

### 2.3 Radius

`--ara-radius-sm 10px` (compact controls) · `--ara-radius-md 12px` (buttons, inputs, metric tiles,
inline cards) · `--ara-radius-lg 18px` (hero, cards, recommendation surfaces) ·
`--ara-radius-pill 999px` (badges, chips, radio pills).

### 2.4 Shadow

`--ara-shadow-subtle` (mobile navigation only) and `--ara-shadow-card` (reserved; unused by default,
because hierarchy comes from surfaces and borders).

### 2.5 Typography

| Role | Token |
|---|---|
| Hero metric / label | `--ara-font-hero-metric` (`3.7rem`), `--ara-font-hero-metric-mobile` (`3.15rem`) |
| Page title | `--ara-font-page-title`, `--ara-font-page-title-mobile` (`1.7rem`) |
| Hero title | `--ara-font-hero-title`, `--ara-font-hero-title-mobile` (`1.3rem`) |
| Titles | `--ara-font-title-xl` `1.65rem`, `--ara-font-title-lg` `1.45rem`, `--ara-font-title` `1.35rem`, `--ara-font-title-sm` `1.02rem` |
| Body | `--ara-font-body-lg` `1rem`, `--ara-font-body` `.9rem`, `--ara-font-body-sm` `.88rem` |
| Supporting | `--ara-font-secondary` `.84rem`, `--ara-font-chip` `.8rem` |
| Labels | `--ara-font-status` `.76rem`, `--ara-font-caption` `.72rem`, `--ara-font-caption-sm` `.67rem`, `--ara-font-micro` `.62rem` |

Mobile overrides stay inside the shell media query: page title `1.7rem`, hero title `1.3rem`,
hero metric `3.15rem`, inputs and buttons `1rem`.

### 2.6 Normalisation applied in this phase

V1.0 carried bespoke values (18 distinct font sizes, six radii, 15 colour literals, padding such as
`1.35rem 1.45rem`). Mapping them onto the scale produced deliberately tiny changes, verified by a
before/after computed-style fingerprint of 18 selectors × 6 pages × 2 viewports:

| Property | Before | After | Reason |
|---|---|---|---|
| Card / hero / summary padding | `1.35rem 1.45rem`, `1rem 1.05rem`, `1.15rem 1.25rem` … | nearest scale step (≤ 0.15rem change) | one spacing ramp |
| `border-radius` on `.ara-exercise-card`, metrics, expander | `14px` | `12px` | one radius family |
| `.block-container` bottom padding | `83.2px` | `36px` | it existed to clear a navigation bar desktop never had |

No colour, font-size, border-colour or structural change was introduced. The full diff is
`work/v11_audit/fingerprint_before.json` vs `fingerprint_after.json`.

## 3. Status semantics

`styles.STATUS_TONE_TOKENS` maps the **engine's own status constants** to colour tokens, and
`ui_components.status_meta()` resolves label plus explanation. One status therefore has exactly one
colour and one wording everywhere.

| Status | Tone token | Badge label |
|---|---|---|
| `GREEN` | `--ara-status-green` | Ready to train |
| `AMBER` | `--ara-status-amber` | Ready, with caution |
| `RED` | `--ara-status-red` | Recovery recommended |
| `STOP / PROFESSIONAL REVIEW` | `--ara-status-stop` | Pause training & review symptoms |
| `INSUFFICIENT DATA` | `--ara-status-neutral` | Keep collecting data |

Baseline confidence wording is fixed by `ui_components.CONFIDENCE_LABELS`
(`NORMAL` / `LIMITED` / `INSUFFICIENT`); the calculation is untouched.

## 4. Reusable components

Primitives live in `ui_components.py` (one module; it is still small enough to stay maintainable).

| Primitive | Adopted in the product now? |
|---|---|
| `status_badge(status, label=None)` | Foundation (new component API) |
| `context_chip(text, emphasis=False)` | **Used** by `training_summary` (Today, Train) |
| `identity_badge(is_demo, name=None)` | Foundation (Phase 9 profile work) |
| `confidence_label(value)` | Foundation |
| `metric_tile(label, value, unit, context, status)` | Foundation (Phase 4/7 adoption) |
| `insight_card(title, body, status)` | Foundation (Phase 4/6 adoption) |
| `recommendation_card(title, chips, body, variant)` | Foundation (Phase 6 adoption) |
| `decision_trace_row(label, value, note, status)` | Foundation (Phase 6 adoption) |
| `section_header(title, subtitle)` | Foundation |
| `primary_cta` / `secondary_cta` | **Used** by Today (`View workout`) and More (four routes) |

Existing page components (`page_intro`, `readiness_hero`, `mobile_readiness_hero`, `training_summary`,
`domain_card`, `callout`, `flow_card`, `detail_row`, mobile navigation) keep their V1.0/V1.1 markup and
now consume tokens; no page was redesigned.

Inspect everything at a real viewport:

```bash
python -m streamlit run scripts/design_system_preview.py
```

The preview is developer tooling and is deliberately absent from the product navigation.

## 5. streamlit-shadcn-ui decision

**Decision: NOT USED.**

Measured in an isolated virtual environment (no project dependency added):

| Item | Result |
|---|---|
| Package | `streamlit-shadcn-ui 1.4.0` (MIT, single maintainer) |
| Runtime requirement | **Streamlit >= 1.60** — enforced by `RuntimeError` in `require_v2_runtime()` |
| Project version | Streamlit **1.56.0** (verified baseline; this phase must not upgrade it) |
| Python | 3.14.6 (satisfies `>=3.10`) |
| On 1.56 | every component raises `RuntimeError: streamlit-shadcn-ui requires Streamlit >= 1.60` |
| On 1.64 (spike venv) | all five components render; button/select values return to Python and reruns behave correctly |
| Rendering model | each component mounts a **Shadow DOM** host with bundled Tailwind v4 CSS |
| Colours | computed in `oklch()` — e.g. primary button `oklch(0.205 0 0)`, secondary `oklch(0.97 0 0)` |
| Geometry at 390×844 | button `111 × 32`, tabs `53.6 × 25`, select trigger `358 × 32`, badge `60 × 22` |
| Native equivalent | Streamlit primary button `358 × 48` |
| Overflow / errors | none; no horizontal overflow at 390 or 1440 |

Reasons for rejection (in priority order):

1. **Version conflict.** It cannot run on the Streamlit version this project is verified against, and
   PHASE 3 explicitly forbids upgrading Streamlit. On Streamlit Cloud the resolved version would drift
   into 1.6x domain without any of the mobile-shell work being re-verified there.
2. **Second visual language.** Shadow DOM + bundled Tailwind means the components cannot consume
   `--ara-*` tokens. The app would ship two palettes (warm white / green-black vs zinc/oklch) and two
   radius families, which is the opposite of this phase's goal.
3. **Touch targets.** 32 px buttons and 25 px tabs are below the 44 px baseline the mobile shell just
   established.
4. **Dependency and deployment risk.** A third-party component tied to Streamlit's Components V2 API,
   with no pinning strategy for Community Cloud, for a visual result no better than token-driven
   CSS.

Reconsider only if: Streamlit is upgraded to >= 1.60 for other reasons **and** the product accepts a
Tailwind-themed component island (or the package exposes token overrides).

## 6. Usage guidance

* New page or section: start from tokens, not literals. If a value is missing, add it to
  `styles.DESIGN_TOKENS` — do not inline a hex, radius or font size.
* Status display: use `status_badge` / `status_meta`; never print a bare colour dot.
* Primary action: exactly one `primary_cta` per view; everything else is `secondary_cta`.
* Card hierarchy: not every block is a card. Prefer plain content, then `context_chip`, then
  `insight_card`, and reserve `recommendation_card` for actual recommendations.
* Mobile: verify 375 px before merging anything new; reuse the shell clearance contract instead of
  adding page padding.

## 7. Tests that guard this layer

`test_app.py` now includes: token emission and token-only component CSS, single-source status colour
mapping (this test caught a real mismatch between `styles.STATUS_TONE_TOKENS` and the engine's status
strings), badge colour+label pairing, metric/recommendation/trace-row content and escaping, CTA
hierarchy (`primary` vs `secondary`), and a guard that no `streamlit-shadcn-ui` dependency or import
appears in the product modules.
