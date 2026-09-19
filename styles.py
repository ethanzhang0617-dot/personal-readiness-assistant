"""Visual system for the historical V1.1 Streamlit prototype
(formerly Personal Readiness Assistant).

Three layers live here and nowhere else:

``DESIGN_TOKENS``
    Colour, spacing, radius, shadow and typography tokens. Python is the single
    source of truth: the dictionary is emitted into the document as CSS custom
    properties, so a value cannot drift between Python and CSS.

``APP_CSS``
    Page and component presentation, written against the tokens only.

``SHELL_CSS``
    The mobile *shell* contract: bottom navigation placement, safe-area
    spacing, content clearance and the Streamlit chrome that must not appear in
    the end-user interface.

Shell spacing contract:

    --ara-nav-content-h   height of the navigation row itself
    --ara-safe-bottom     env() safe-area inset, with a non-zero floor
    --ara-nav-h           navigation band = content height + safe inset
    --ara-shell-bottom    space the scrolling viewport must leave free

The scrolling viewport is shortened by ``--ara-shell-bottom`` instead of relying
on document-end padding, so fixed navigation cannot cover live content.
"""

from __future__ import annotations

import streamlit as st

from readiness_engine import AMBER, GREEN, INSUFFICIENT, RED, STOP


MOBILE_SHELL_BREAKPOINT_PX = 768
STYLESHEET_ELEMENT_KEY = "ara_stylesheet"
NAV_ELEMENT_KEY = "mobile_bottom_nav"
UTILITY_NAV_ELEMENT_KEY = "mobile_utility_nav"
SHELL_BRIDGE_ELEMENT_KEY = "mobile_shell_viewport"

# --------------------------------------------------------------------------- #
# Design tokens
# --------------------------------------------------------------------------- #

#: Surfaces, text, borders and status semantics. Status colours are the only
#: saturated colours in the product and are always paired with a text label.
COLOR_TOKENS = {
    "--ara-bg": "#f8f7f4",
    "--ara-surface": "#ffffff",
    "--ara-surface-2": "#fbfaf7",
    "--ara-surface-3": "#f1f0eb",
    "--ara-text": "#16181a",
    "--ara-text-2": "#6b6f73",
    "--ara-text-muted": "#8a8d90",
    "--ara-text-inverse": "#ffffff",
    "--ara-border": "#eeeeea",
    "--ara-border-strong": "#e2e2dc",
    "--ara-ink": "#1a1c1e",
    "--ara-ink-hover": "#33363a",
    "--ara-action": "#1a1c1e",
    "--ara-action-hover": "#33363a",
    "--ara-nav-text": "#6b6f73",
    "--ara-utility-text": "#6b6f73",
    "--ara-header-bg": "rgba(248,247,244,.92)",
    "--ara-nav-bg": "rgba(255,255,254,.96)",
    "--ara-status-green": "#18864b",
    "--ara-status-amber": "#b96d00",
    "--ara-status-red": "#c53f32",
    "--ara-status-stop": "#a32626",
    "--ara-status-neutral": "#68717a",
    "--ara-font-sans": "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
}

#: Small spacing scale. Component padding uses the nearest step rather than a
#: bespoke value, so pages share one rhythm.
SPACE_TOKENS = {
    "--ara-space-2xs": ".25rem",
    "--ara-space-xs": ".5rem",
    "--ara-space-sm": ".7rem",
    "--ara-space-md": "1rem",
    "--ara-space-lg": "1.15rem",
    "--ara-space-xl": "1.4rem",
    "--ara-space-2xl": "1.9rem",
}

#: Radius family: small (controls inside surfaces), medium (controls and
#: compact cards), large (surfaces), pill (chips and badges).
RADIUS_TOKENS = {
    "--ara-radius-sm": "10px",
    "--ara-radius-md": "12px",
    "--ara-radius-lg": "16px",
    "--ara-radius-pill": "999px",
}

#: Shadows are deliberately minimal: hierarchy comes from surface, border and
#: spacing. ``card`` is reserved for future emphasis surfaces.
SHADOW_TOKENS = {
    "--ara-shadow-subtle": "0 -8px 24px rgba(18,18,18,.06)",
    "--ara-shadow-card": "0 1px 2px rgba(18,18,18,.04)",
}

TYPE_TOKENS = {
    "--ara-font-hero-metric": "3.2rem",
    "--ara-font-hero-metric-mobile": "2.9rem",
    "--ara-font-page-title": "clamp(1.55rem, 2.6vw, 2rem)",
    "--ara-font-page-title-mobile": "1.5rem",
    "--ara-font-hero-title": "clamp(1.35rem, 2.6vw, 1.7rem)",
    "--ara-font-hero-title-mobile": "1.2rem",
    "--ara-font-title-xl": "1.35rem",
    "--ara-font-title-lg": "1.2rem",
    "--ara-font-title": "1.1rem",
    "--ara-font-title-sm": "1rem",
    "--ara-font-body-lg": "1rem",
    "--ara-font-body": ".9rem",
    "--ara-font-body-sm": ".88rem",
    "--ara-font-secondary": ".84rem",
    "--ara-font-chip": ".8rem",
    "--ara-font-status": ".76rem",
    "--ara-font-caption": ".72rem",
    "--ara-font-caption-sm": ".67rem",
    "--ara-font-micro": ".62rem",
}

DESIGN_TOKENS: dict[str, str] = {
    **COLOR_TOKENS,
    **SPACE_TOKENS,
    **RADIUS_TOKENS,
    **SHADOW_TOKENS,
    **TYPE_TOKENS,
}

#: Readiness status -> colour token, keyed by the engine's own status constants so
#: a mapping cannot silently miss a status. ``ui_components`` resolves tones here.
STATUS_TONE_TOKENS = {
    GREEN: "--ara-status-green",
    AMBER: "--ara-status-amber",
    RED: "--ara-status-red",
    STOP: "--ara-status-stop",
    INSUFFICIENT: "--ara-status-neutral",
}

#: CSS-only fallback for the shell band, used when the browser bridge cannot
#: run. The navigation row height stays CSS-owned and deterministic.
SHELL_TOKENS = {
    "--ara-nav-content-h": "56px",                                   # navigation row height
    "--ara-shell-floor": "8px",                                      # minimum bottom breathing room
    "--ara-block-gap": ".7rem",                                      # mobile vertical rhythm
    "--ara-safe-top": "env(safe-area-inset-top, 0px)",
    "--ara-safe-bottom": "env(safe-area-inset-bottom, 0px)",
    "--ara-shell-inset": "max(var(--ara-safe-bottom), var(--ara-shell-floor))",
    "--ara-nav-h": "calc(var(--ara-nav-content-h) + var(--ara-shell-inset))",
    "--ara-shell-bottom": "var(--ara-nav-h)",
}

#: Streamlit chrome that must not appear in the end-user mobile shell. Each
#: selector was verified against the installed Streamlit DOM; the expand control
#: was renamed from ``stSidebarCollapsedControl`` in older releases.
MOBILE_HIDDEN_CHROME_SELECTORS = (
    '[data-testid="stHeader"]',
    '[data-testid="stAppDeployButton"]',
    '[data-testid="stMainMenu"]',
    '[data-testid="stToolbar"]',
    '[data-testid="stSidebar"]',
    '[data-testid="stSidebarCollapsedControl"]',
    '[data-testid="stExpandSidebarButton"]',
)


def _root_block(tokens: dict[str, str]) -> str:
    return ":root {\n" + "\n".join(f"    {name}: {value};" for name, value in tokens.items()) + "\n  }"


DESIGN_TOKEN_CSS = "<style>\n  /* design tokens (generated from styles.DESIGN_TOKENS) */\n  " + _root_block(DESIGN_TOKENS) + "\n</style>"

_SHELL_ROOT_CSS = _root_block(SHELL_TOKENS)


APP_CSS = """
<style>
  html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] { font-family: var(--ara-font-sans); }
  [data-testid="stAppViewContainer"] { background: var(--ara-bg); }
  [data-testid="stHeader"] { background: var(--ara-header-bg); }
  .block-container { max-width: 1240px; padding-top: var(--ara-space-lg); padding-bottom: var(--ara-space-2xl); }
  [data-testid="stSidebar"] { background: var(--ara-surface-2); border-right: 1px solid var(--ara-border); }
  [data-testid="stSidebar"] .block-container { padding-top: var(--ara-space-lg); }
  [data-testid="stSidebar"] div.stButton > button { justify-content: flex-start; text-align: left; border-radius: var(--ara-radius-md); min-height: 2.5rem; border: 1px solid transparent; background: transparent; color: var(--ara-text); font-weight: 550; }
  [data-testid="stSidebar"] div.stButton > button[kind="primary"] { background: var(--ara-surface); border-color: var(--ara-border); color: var(--ara-text); font-weight: 700; }
  [data-testid="stSidebar"] div.stButton > button:hover { background: var(--ara-surface-3); border-color: transparent; }
  [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover { background: var(--ara-surface); }
  h1, h2, h3 { color: var(--ara-text); letter-spacing: -.012em; font-weight: 700; }
  h1 { font-size: var(--ara-font-page-title); margin-bottom: var(--ara-space-2xs); }
  h2 { font-size: var(--ara-font-title); margin-top: var(--ara-space-xl); }
  .ara-kicker { color: var(--ara-text-muted); font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .1em; margin-bottom: var(--ara-space-2xs); text-transform: uppercase; }
  .ara-subtitle { color: var(--ara-text-2); max-width: 720px; font-size: var(--ara-font-body-lg); margin: 0 0 var(--ara-space-lg); }
  .ara-card, .ara-hero, .ara-flow, .ara-callout { background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-lg); }
  .ara-card { padding: var(--ara-space-md); min-height: 118px; }
  .ara-card h3 { margin: var(--ara-space-xs) 0 var(--ara-space-2xs); font-size: var(--ara-font-title-sm); }
  .ara-card p { color: var(--ara-text-2); font-size: var(--ara-font-body); line-height: 1.45; margin: 0; }
  .ara-hero { padding: var(--ara-space-lg) var(--ara-space-xl); border: 0; border-left: 4px solid var(--status); border-radius: var(--ara-radius-lg); box-shadow: 0 1px 0 rgba(22,24,26,.03); margin: var(--ara-space-xs) 0 var(--ara-space-lg); }
  .ara-hero h2 { margin: var(--ara-space-2xs) 0; font-size: var(--ara-font-hero-title); }
  .ara-hero p { color: var(--ara-text-2); margin: var(--ara-space-2xs) 0 0; }
  .ara-status { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); font-size: var(--ara-font-status); font-weight: 750; letter-spacing: .06em; color: var(--status); }
  .ara-dot { width: .58rem; height: .58rem; border-radius: 50%; background: var(--status); display: inline-block; }
  .ara-meta { color: var(--ara-text-2); font-size: var(--ara-font-secondary); margin-top: var(--ara-space-sm); }
  .ara-mobile-hero { display: flex; justify-content: space-between; gap: var(--ara-space-md); align-items: center; padding: var(--ara-space-lg) var(--ara-space-xl); background: var(--ara-surface); border: 0; border-left: 4px solid var(--status); border-radius: var(--ara-radius-lg); box-shadow: 0 1px 0 rgba(22,24,26,.03); margin: var(--ara-space-xs) 0 var(--ara-space-md); }
  .ara-mobile-hero h2 { margin: var(--ara-space-2xs) 0; font-size: var(--ara-font-title-xl); }
  .ara-mobile-hero p { color: var(--ara-text-2); margin: 0; max-width: 34rem; }
  .ara-readiness-number { color: var(--ara-text); font-size: var(--ara-font-hero-metric); font-weight: 750; letter-spacing: -.05em; line-height: .85; text-align: right; }
  .ara-readiness-number span { display: block; color: var(--status); font-size: var(--ara-font-micro); letter-spacing: .1em; margin-top: var(--ara-space-xs); }
  .ara-training-summary { background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-lg); padding: var(--ara-space-md) var(--ara-space-lg); margin: var(--ara-space-sm) 0 var(--ara-space-sm); }
  .ara-training-summary--plain { background: transparent; border: 0; border-radius: 0; padding: var(--ara-space-xs) 0 0; }
  .ara-training-summary h2 { margin: var(--ara-space-2xs) 0 var(--ara-space-sm); font-size: var(--ara-font-title-lg); }
  .ara-training-meta { display: flex; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-training-meta span { display: inline-flex; padding: var(--ara-space-2xs) var(--ara-space-xs); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); font-size: var(--ara-font-chip); color: var(--ara-text-2); background: var(--ara-surface-2); }
  .ara-today-greeting { margin: var(--ara-space-2xs) 0 var(--ara-space-sm); }
  .ara-today-greeting span { color: var(--ara-text-muted); font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .12em; }
  .ara-today-meta { display: flex; align-items: center; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-today-meta .ara-badge { letter-spacing: .08em; }
  .ara-today-greeting h1 { margin: var(--ara-space-2xs) 0; }
  .ara-today-greeting p { color: var(--ara-text-2); margin: 0; }
  .ara-exercise-row { display: flex; flex-direction: column; gap: 2px; padding: var(--ara-space-sm) 0; border-bottom: 1px solid var(--ara-border); }
  .ara-exercise-row:last-child { border-bottom: 0; }
  .ara-exercise-row__name { font-size: var(--ara-font-body); font-weight: 650; color: var(--ara-text); }
  .ara-exercise-row__meta { font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-flow { padding: var(--ara-space-md); min-height: 96px; }
  .ara-flow strong { display: block; font-size: var(--ara-font-body); margin: var(--ara-space-2xs) 0; color: var(--ara-text); }
  .ara-flow span { font-size: .83rem; line-height: 1.35; color: var(--ara-text-2); }
  .ara-callout { padding: var(--ara-space-md); border: 0; border-left: 3px solid var(--status); background: var(--ara-surface-2); }
  .ara-callout p { margin: var(--ara-space-2xs) 0 0; color: var(--ara-text-2); }
  .ara-detail { padding: var(--ara-space-xs) 0; border-bottom: 1px solid var(--ara-border); }
  .ara-detail:last-child { border-bottom: 0; }
  .ara-detail strong { font-size: var(--ara-font-body); color: var(--ara-text); }
  .ara-detail span { color: var(--ara-text-2); font-size: var(--ara-font-body-sm); }
  [data-testid="stMetric"] { background: transparent; border: 0; border-left: 3px solid var(--ara-border-strong); border-radius: 0; padding: var(--ara-space-2xs) 0 var(--ara-space-2xs) var(--ara-space-sm); }
  div.stButton > button, div[data-testid="stDownloadButton"] > button { border-radius: var(--ara-radius-md); min-height: 2.6rem; font-weight: 600; border-color: var(--ara-border); }
  div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"], div[data-testid="stBaseButton-primary"] { background: var(--ara-action); border-color: var(--ara-action); color: var(--ara-text-inverse); font-weight: 650; }
  div.stButton > button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover { background: var(--ara-action-hover); border-color: var(--ara-action-hover); }
  [data-testid="stRadio"] [role="radiogroup"] { gap: var(--ara-space-2xs); flex-wrap: wrap; }
  [data-testid="stRadio"] label { border-radius: var(--ara-radius-pill); }
  [data-testid="stExpander"] { border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); background: var(--ara-surface); }

  /* ---------------------------------------------------------- primitives */
  .ara-badge { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); padding: 2px var(--ara-space-xs); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); font-size: var(--ara-font-status); font-weight: 750; letter-spacing: .05em; background: var(--ara-surface-2); color: var(--ara-text-2); text-transform: uppercase; }
  .ara-badge--status { color: var(--status); border-color: var(--status); background: var(--ara-surface); }
  .ara-badge--demo { color: var(--ara-text-2); border-color: var(--ara-border-strong); background: var(--ara-surface-2); }
  .ara-badge--local { color: var(--ara-status-green); border-color: var(--ara-status-green); background: var(--ara-surface); }
  .ara-badge--identity { color: var(--ara-text-2); border-color: var(--ara-border); background: var(--ara-surface-2); }
  .ara-confidence { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-confidence b { color: var(--ara-text); letter-spacing: .04em; }
  .ara-chip { display: inline-flex; align-items: center; padding: 2px var(--ara-space-xs); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); font-size: var(--ara-font-chip); color: var(--ara-text-2); background: var(--ara-surface-2); }
  .ara-chip--emphasis { color: var(--status); border-color: var(--status); background: var(--ara-surface); font-weight: 700; }
  .ara-section { margin: var(--ara-space-xl) 0 0; }
  .ara-section__title { font-size: var(--ara-font-title); color: var(--ara-text); letter-spacing: -.025em; margin: 0; }
  .ara-section__subtitle { color: var(--ara-text-2); font-size: var(--ara-font-body); margin: var(--ara-space-2xs) 0 0; }
  .ara-metric { display: flex; flex-direction: column; gap: 2px; padding: var(--ara-space-sm); background: var(--ara-surface-2); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); }
  .ara-metric__label { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .08em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-metric__value { font-size: var(--ara-font-title); color: var(--ara-text); line-height: 1.15; font-weight: 650; }
  .ara-metric__value small { font-size: var(--ara-font-secondary); font-weight: 600; color: var(--ara-text-2); margin-left: var(--ara-space-2xs); }
  .ara-metric__context { font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-recommendation { padding: var(--ara-space-md) var(--ara-space-lg); background: var(--ara-surface); border: 0; border-left: 4px solid var(--ara-border); border-radius: var(--ara-radius-lg); }
  .ara-recommendation--primary { border-left-color: var(--status); }
  .ara-recommendation--alternative { border-left-color: var(--ara-border-strong); background: var(--ara-surface-2); }
  .ara-recommendation--avoid { border-left-color: var(--ara-status-red); background: var(--ara-surface-2); }
  .ara-recommendation__title { font-size: var(--ara-font-title-lg); color: var(--ara-text); margin: var(--ara-space-2xs) 0; }
  .ara-recommendation__body { color: var(--ara-text-2); font-size: var(--ara-font-body); margin: 0; }
  .ara-recommendation__chips { display: flex; gap: var(--ara-space-xs); flex-wrap: wrap; margin-top: var(--ara-space-sm); }
  .ara-trace-row { display: flex; flex-direction: column; gap: 2px; padding: var(--ara-space-sm) 0; border-bottom: 1px solid var(--ara-border); }
  .ara-trace-row:last-child { border-bottom: 0; }
  .ara-trace-row__label { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .08em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-trace-row__value { font-size: var(--ara-font-body); color: var(--ara-text); }
  .ara-trace-row__note { font-size: var(--ara-font-body-sm); color: var(--ara-text-2); }

  /* --------------------------------------------------- Today (PHASE 4) */
  .ara-hero-badge { margin-top: var(--ara-space-2xs); }
  .ara-fact-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); gap: var(--ara-space-md); }
  .ara-fact-row { display: flex; flex-direction: column; gap: 2px; padding-top: var(--ara-space-xs); margin-top: var(--ara-space-2xs); border-top: 1px solid var(--ara-border); min-width: 0; }
  .ara-fact-grid .ara-fact-row { padding-top: var(--ara-space-xs); margin-top: var(--ara-space-2xs); }
  .ara-fact-label { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .1em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-fact-value { font-size: var(--ara-font-title); color: var(--ara-text); line-height: 1.2; font-weight: 650; }
  .ara-fact-value--primary { font-size: var(--ara-font-title-xl); font-weight: 700; }
  .ara-fact-meta { display: flex; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ara-space-sm); }
  .ara-why { display: flex; flex-direction: column; gap: var(--ara-space-md); }
  .ara-why-group { display: flex; flex-direction: column; gap: var(--ara-space-2xs); }
  .ara-why-list { margin: 0; padding-left: var(--ara-space-md); color: var(--ara-text-2); font-size: var(--ara-font-body); line-height: 1.45; }
  .ara-why-list li { margin-bottom: var(--ara-space-2xs); }
  .ara-training-summary--primary { border-left: 6px solid var(--status); }
  .ara-trace { display: flex; flex-direction: column; }
  .ara-coach-context { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); flex-wrap: wrap; padding: 3px var(--ara-space-xs); background: var(--ara-surface-2); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); }
  /* Settings-style rows (More page): light dividers instead of big cards. */
  .st-key-settings_rows [data-testid="stVerticalBlock"] { gap: 0 !important; }
  .st-key-settings_rows [data-testid="stButton"] button { justify-content: space-between; text-align: left; background: transparent !important; border: 0 !important; border-bottom: 1px solid var(--ara-border) !important; border-radius: 0 !important; min-height: 3rem; font-weight: 550; padding-left: 0 !important; padding-right: 0 !important; }
  .st-key-settings_rows button > div, .st-key-settings_rows button [data-testid="stMarkdownContainer"] { width: 100%; justify-content: flex-start !important; text-align: left !important; }
  .st-key-settings_rows button p { text-align: left !important; font-size: var(--ara-font-body) !important; }
  .st-key-settings_rows button:hover { background: var(--ara-surface-2) !important; }
  /* Coach: lighter action chips and a single integrated composer. */
  .st-key-coach_quick_questions button { border-radius: var(--ara-radius-md) !important; border: 1px solid var(--ara-border) !important; background: var(--ara-surface) !important; color: var(--ara-text) !important; font-size: var(--ara-font-body-sm) !important; font-weight: 550 !important; text-align: left !important; padding: var(--ara-space-xs) var(--ara-space-sm) !important; }
  .st-key-coach_quick_questions button:hover { background: var(--ara-surface-2) !important; }
  /* Today's context: one light surface, not a row of pills. */
  .ara-context-surface { display: flex; flex-direction: column; gap: 2px; padding: var(--ara-space-xs) var(--ara-space-md); background: var(--ara-surface-2); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); }
  .ara-context-surface__row { display: flex; align-items: center; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-context-surface__title { font-size: var(--ara-font-title-sm); font-weight: 700; color: var(--ara-text); }
  .ara-context-surface__meta { font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  /* Suggested prompts read as conversation starters: quiet rows with dividers. */
  .st-key-coach_suggested [data-testid="stVerticalBlock"] { gap: 0 !important; }
  /* Coach rhythm: keep the whole page inside the reserved composer area. */
  .st-key-coach_page > [data-testid="stVerticalBlock"] { gap: var(--ara-space-sm) !important; }
  .st-key-coach_page .ara-subtitle { margin-bottom: var(--ara-space-xs); }
  .st-key-coach_suggested button { padding-top: 0 !important; padding-bottom: 0 !important; }

  .st-key-coach_suggested [data-testid="stButton"] button { justify-content: flex-start; text-align: left; background: transparent !important; border: 0 !important; border-bottom: 1px solid var(--ara-border) !important; border-radius: 0 !important; min-height: 2.75rem; font-size: var(--ara-font-body) !important; font-weight: 550 !important; color: var(--ara-text) !important; padding-left: 0 !important; padding-right: 0 !important; }
  .st-key-coach_suggested button { justify-content: flex-start !important; text-align: left !important; }
  .st-key-coach_suggested button > div, .st-key-coach_suggested button [data-testid="stMarkdownContainer"] { width: 100%; justify-content: flex-start !important; text-align: left !important; }
  .st-key-coach_suggested button p { text-align: left !important; width: 100%; font-size: var(--ara-font-body) !important; }
  .st-key-coach_suggested button:hover { background: var(--ara-surface-2) !important; }
  /* "How the Coach works" behaves as a disclosure row, not a fifth CTA. */
  .st-key-coach_how [data-testid="stExpander"], .st-key-coach_how [data-testid="stExpander"] details, .st-key-coach_how details { border: 0 !important; background: transparent !important; box-shadow: none !important; }
  .st-key-coach_how [data-testid="stExpander"] summary { font-size: var(--ara-font-secondary) !important; color: var(--ara-text-2) !important; padding: var(--ara-space-xs) 0 !important; }
  .st-key-coach_how [data-testid="stExpander"] summary p { font-size: var(--ara-font-secondary) !important; }
  /* Reserved conversation area: readable as an empty state, not dead space. */
  .ara-chat-empty { display: flex; align-items: center; justify-content: center; min-height: 24px; color: var(--ara-text-muted); font-size: var(--ara-font-secondary); text-align: center; }
  .ara-msg-meta { display: flex; align-items: center; gap: var(--ara-space-xs); flex-wrap: wrap; margin-bottom: 2px; }
  .ara-msg-meta__text { font-size: var(--ara-font-caption); color: var(--ara-text-muted); }
  /* Coach stays a comfortable reading column on wide screens: the content and
     the pinned composer share one centred width instead of spanning 1240px. */
  @media (min-width: 769px) {
    .st-key-coach_page { max-width: 780px; margin: 0 auto; }
    [data-testid="stChatInput"] { max-width: 780px; margin-left: auto; margin-right: auto; }
  }
  /* Message styling: user gets a quiet neutral bubble, assistant stays open. */
  [data-testid="stChatMessage"] { background: transparent !important; border: 0 !important; padding: var(--ara-space-xs) 0 !important; }
  [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"] ~ div [data-testid="stMarkdownContainer"] { background: var(--ara-surface-3); border-radius: var(--ara-radius-md); padding: var(--ara-space-sm); }
  [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { font-size: var(--ara-font-body); }
  [data-testid="stChatInput"] { border-radius: var(--ara-radius-lg); border: 1px solid var(--ara-border); background: var(--ara-surface); }
  [data-testid="stChatInput"] textarea { background: transparent !important; font-size: var(--ara-font-body) !important; min-height: 2.4rem !important; }
  [data-testid="stChatInput"] > div { border: 0 !important; box-shadow: none !important; background: transparent !important; }
  [data-testid="stChatInput"] textarea::placeholder { color: var(--ara-text-muted) !important; }
  [data-testid="stChatInput"] button { background: var(--ara-action) !important; color: var(--ara-text-inverse) !important; border-radius: var(--ara-radius-md) !important; }
  .ara-history { display: flex; flex-direction: column; }
  .ara-history-row { display: flex; flex-direction: column; gap: 2px; padding: var(--ara-space-sm) 0; border-bottom: 1px solid var(--ara-border); }
  .ara-history-row:last-child { border-bottom: 0; }
  .ara-history-date { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .08em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-history-main { font-size: var(--ara-font-body); color: var(--ara-text); }
  .ara-history-meta { font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-profile-card { display: flex; flex-direction: column; gap: var(--ara-space-2xs); padding: var(--ara-space-md); background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-lg); margin-bottom: var(--ara-space-xs); }
  .ara-trend-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--ara-space-sm); flex-wrap: wrap; margin: var(--ara-space-sm) 0 0; }
  .ara-trend-head__title { font-size: var(--ara-font-title-sm); font-weight: 700; color: var(--ara-text); }
  .ara-trend-head__unit { margin-left: var(--ara-space-xs); font-size: var(--ara-font-caption); font-weight: 600; color: var(--ara-text-muted); letter-spacing: .04em; }
  .ara-trend-head__values { display: flex; gap: var(--ara-space-sm); font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-trend-head__values b { color: var(--ara-text); }
  .ara-exercise-list { display: flex; flex-direction: column; }
  /* Charts sit on the page background: no white box inside a white card. */
  [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"], .stElementContainer:has([data-testid="stVegaLiteChart"]) { background: transparent !important; border: 0 !important; }
  @media (min-width: 769px) {
    .ara-metric-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  }
</style>
"""


SHELL_CSS = """
<style>
  /* ------------------------------------------------------------------ tokens */
  """ + _SHELL_ROOT_CSS + """
  html.ara-keyboard-open { --ara-shell-bottom: 0px; }    /* the composer needs the room */

  /* The mobile shell exists only below the breakpoint; desktop keeps the
     sidebar shell and must not render the compact navigation at all. */
  .st-key-mobile_bottom_nav, .st-key-mobile_utility_nav { display: none; }

  /* Internal plumbing is never visible product chrome. */
  .st-key-mobile_shell_viewport, .st-key-browser_storage_bridge { display: none !important; }

  /* Mobile shell only: desktop keeps the sidebar shell untouched. */
  @media (max-width: 768px) {
    /* Reserve the navigation band out of the scrolling viewport, so fixed
       navigation cannot cover live content at any scroll position. */
    [data-testid="stMain"], [data-testid="stAppScrollToBottomContainer"] {
      height: calc(100vh - var(--ara-shell-bottom)) !important;
      max-height: calc(100vh - var(--ara-shell-bottom)) !important;
      bottom: auto !important;
    }
    [data-testid="stMain"], [data-testid="stAppScrollToBottomContainer"] {
      height: calc(100dvh - var(--ara-shell-bottom)) !important;
      max-height: calc(100dvh - var(--ara-shell-bottom)) !important;
    }
    /* One central mobile rhythm rule for the shell. The injected stylesheet is
       itself a zero-height block whose default 1rem block gap used to sit above
       every page's first element. */
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: var(--ara-block-gap) !important; }
    .st-key-ara_stylesheet { display: none !important; }
    .block-container {
      padding: calc(.5rem + var(--ara-safe-top)) 1rem 1.15rem !important;
      max-width: 100%;
    }

    /* Streamlit chrome that does not belong in the end-user mobile shell.
       Exact testids, verified against the installed Streamlit version. */
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stExpandSidebarButton"] { display: none !important; }

    /* Bottom navigation: fixed inside its own reserved band. */
    .st-key-mobile_bottom_nav {
      display: block;
      position: fixed;
      left: 0; right: 0; bottom: 0;
      z-index: 1000;
      height: var(--ara-nav-h);
      box-sizing: border-box;
      padding: .25rem .55rem var(--ara-shell-inset);
      background: var(--ara-nav-bg);
      border-top: 1px solid var(--ara-border);
      box-shadow: var(--ara-shadow-subtle);
      transition: transform .18s ease, opacity .18s ease;
    }
    html.ara-keyboard-open .st-key-mobile_bottom_nav { transform: translateY(105%); opacity: 0; pointer-events: none; }
    .st-key-mobile_bottom_nav > [data-testid="stVerticalBlock"] { height: 100%; }
    .st-key-mobile_bottom_nav [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .18rem !important; height: 100%; align-items: stretch; }
    .st-key-mobile_bottom_nav [data-testid="stColumn"] { min-width: 0 !important; width: 20% !important; flex: 1 1 20% !important; }
    .st-key-mobile_bottom_nav button { height: 100%; min-height: 2.75rem !important; border: 0 !important; border-radius: var(--ara-radius-sm) !important; white-space: pre-line !important; font-size: var(--ara-font-caption-sm) !important; line-height: 1.1 !important; padding: .25rem .1rem !important; background: transparent !important; color: var(--ara-nav-text) !important; font-weight: 550 !important; }
    .st-key-mobile_bottom_nav button[kind="primary"] { background: var(--ara-surface-3) !important; color: var(--ara-text) !important; font-weight: 750 !important; }
    .st-key-mobile_bottom_nav button p { font-size: var(--ara-font-caption-sm) !important; line-height: 1.05 !important; }

    /* Secondary destinations: one lightweight row above the content. */
    .st-key-mobile_utility_nav { display: flex; margin: 0 0 .1rem; }
    .st-key-mobile_utility_nav button { min-height: 2.75rem !important; border: 0 !important; background: transparent !important; color: var(--ara-utility-text) !important; padding: .1rem .35rem !important; }

    /* The chat composer lives inside the shortened scrolling viewport, above
       the navigation band, so its own bottom padding only has to clear the
       navigation border - not the browser chrome it used to avoid. */
    [data-testid="stBottomBlockContainer"] { padding-bottom: .85rem !important; }
    /* Coach: keep the reserved composer area tight so the page does not end in
       a large empty band on short screens. */
    [data-testid="stBottomBlockContainer"] { padding-top: .5rem !important; padding-bottom: .5rem !important; }
    [data-testid="stChatInput"] textarea { min-height: 2.4rem !important; }

    /* Coach send control: a real touch target. */
    [data-testid="stChatInput"] button { min-width: 44px !important; min-height: 44px !important; }
    /* Form submit CTAs and the number steppers need real touch targets too. */
    [data-testid="stFormSubmitButton"] button, [data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stBaseButton-primaryFormSubmit"] { min-height: 2.75rem !important; }
    [data-testid="stNumberInput"] button { min-width: 2.75rem !important; min-height: 2.75rem !important; }

    /* Single-column content on phones; the navigation row is exempt above. */
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex: 1 1 100%; min-width: 100%; }
    /* Scoped exemptions from the single-column rule: these rows stay multi-column
       because they are compact grouped controls, not page content. */
    .st-key-coach_quick_questions [data-testid="stHorizontalBlock"],
    .st-key-checkin_soreness [data-testid="stHorizontalBlock"],
    .st-key-checkin_scenarios [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
    .st-key-coach_quick_questions [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
    .st-key-checkin_soreness [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
    .st-key-checkin_scenarios [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex: 1 1 0 !important; min-width: 0 !important; }
    .st-key-coach_quick_questions button, .st-key-checkin_scenarios button { min-height: 2.75rem !important; }
    .st-key-checkin_scenarios button { font-size: var(--ara-font-body-sm) !important; }
    h1 { font-size: var(--ara-font-page-title-mobile); }
    .ara-hero { padding: var(--ara-space-md); }
    .ara-card { min-height: auto; margin-bottom: var(--ara-space-xs); }
    .ara-mobile-hero { padding: var(--ara-space-md); gap: var(--ara-space-sm); align-items: flex-start; }
    .ara-mobile-hero h2 { font-size: var(--ara-font-hero-title-mobile); }
    .ara-readiness-number { font-size: var(--ara-font-hero-metric-mobile); }
    .ara-fact-value { font-size: var(--ara-font-title); }
    .ara-fact-value--primary { font-size: var(--ara-font-hero-title-mobile); }
    .ara-fact-grid { gap: var(--ara-space-sm); }
    .ara-fact-value--primary { overflow-wrap: anywhere; }
    .ara-training-summary { padding: var(--ara-space-md); }
    .ara-training-summary h2 { font-size: var(--ara-font-hero-title-mobile); }
    .ara-today-greeting h1 { font-size: var(--ara-font-page-title-mobile); }
    [data-testid="stMetric"] { padding: var(--ara-space-sm) var(--ara-space-sm); }
    div.stButton > button, div[data-testid="stDownloadButton"] > button { min-height: 3rem; font-size: var(--ara-font-body-lg); }
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input { min-height: 2.9rem; font-size: var(--ara-font-body-lg); }
    [data-testid="stDataFrame"] { overflow-x: auto; }
  }
</style>
"""


def inject_styles() -> None:
    """Inject the token, page and shell layers from one keyed block.

    The block is hidden on mobile because it is plumbing, not page content; the
    ``<style>`` elements keep applying regardless of the wrapper's display.
    """
    with st.container(key=STYLESHEET_ELEMENT_KEY):
        st.markdown(DESIGN_TOKEN_CSS + APP_CSS + SHELL_CSS, unsafe_allow_html=True)
