"""Visual system for the Personal Readiness Assistant product shell.

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
    "--ara-bg": "#f7f7f4",
    "--ara-surface": "#ffffff",
    "--ara-surface-2": "#fbfbf8",
    "--ara-surface-3": "#f0f0ec",
    "--ara-text": "#171717",
    "--ara-text-2": "#686868",
    "--ara-text-muted": "#777777",
    "--ara-text-inverse": "#ffffff",
    "--ara-border": "#e8e8e3",
    "--ara-border-strong": "#deded8",
    "--ara-ink": "#1d1d1b",
    "--ara-ink-hover": "#383835",
    "--ara-nav-text": "#5a5a56",
    "--ara-utility-text": "#4c4c48",
    "--ara-header-bg": "rgba(247,247,244,.92)",
    "--ara-nav-bg": "rgba(255,255,253,.98)",
    "--ara-status-green": "#18864b",
    "--ara-status-amber": "#b96d00",
    "--ara-status-red": "#c53f32",
    "--ara-status-stop": "#a32626",
    "--ara-status-neutral": "#68717a",
}

#: Small spacing scale. Component padding uses the nearest step rather than a
#: bespoke value, so pages share one rhythm.
SPACE_TOKENS = {
    "--ara-space-2xs": ".25rem",
    "--ara-space-xs": ".5rem",
    "--ara-space-sm": ".75rem",
    "--ara-space-md": "1rem",
    "--ara-space-lg": "1.25rem",
    "--ara-space-xl": "1.5rem",
    "--ara-space-2xl": "2.25rem",
}

#: Radius family: small (controls inside surfaces), medium (controls and
#: compact cards), large (surfaces), pill (chips and badges).
RADIUS_TOKENS = {
    "--ara-radius-sm": "10px",
    "--ara-radius-md": "12px",
    "--ara-radius-lg": "18px",
    "--ara-radius-pill": "999px",
}

#: Shadows are deliberately minimal: hierarchy comes from surface, border and
#: spacing. ``card`` is reserved for future emphasis surfaces.
SHADOW_TOKENS = {
    "--ara-shadow-subtle": "0 -8px 24px rgba(18,18,18,.06)",
    "--ara-shadow-card": "0 1px 2px rgba(18,18,18,.04)",
}

TYPE_TOKENS = {
    "--ara-font-hero-metric": "3.7rem",
    "--ara-font-hero-metric-mobile": "3.15rem",
    "--ara-font-page-title": "clamp(1.85rem, 5vw, 2.8rem)",
    "--ara-font-page-title-mobile": "1.7rem",
    "--ara-font-hero-title": "clamp(1.55rem, 4vw, 2.25rem)",
    "--ara-font-hero-title-mobile": "1.3rem",
    "--ara-font-title-xl": "1.65rem",
    "--ara-font-title-lg": "1.45rem",
    "--ara-font-title": "1.35rem",
    "--ara-font-title-sm": "1.02rem",
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
  [data-testid="stAppViewContainer"] { background: var(--ara-bg); }
  [data-testid="stHeader"] { background: var(--ara-header-bg); }
  .block-container { max-width: 1120px; padding-top: var(--ara-space-lg); padding-bottom: var(--ara-space-2xl); }
  [data-testid="stSidebar"] { background: var(--ara-surface-2); border-right: 1px solid var(--ara-border); }
  [data-testid="stSidebar"] .block-container { padding-top: var(--ara-space-lg); }
  [data-testid="stSidebar"] div.stButton > button { justify-content: flex-start; text-align: left; border-radius: var(--ara-radius-md); min-height: 2.75rem; border: 1px solid var(--ara-border); background: var(--ara-surface); color: var(--ara-text); }
  [data-testid="stSidebar"] div.stButton > button[kind="primary"] { background: var(--ara-ink); border-color: var(--ara-ink); color: var(--ara-text-inverse); }
  [data-testid="stSidebar"] div.stButton > button:hover { background: var(--ara-surface-3); border-color: var(--ara-border-strong); }
  [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover { background: var(--ara-ink-hover); }
  h1, h2, h3 { color: var(--ara-text); letter-spacing: -.025em; }
  h1 { font-size: var(--ara-font-page-title); margin-bottom: var(--ara-space-2xs); }
  h2 { font-size: var(--ara-font-title); margin-top: var(--ara-space-xl); }
  .ara-kicker { color: var(--ara-text-muted); font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .12em; margin-bottom: var(--ara-space-2xs); }
  .ara-subtitle { color: var(--ara-text-2); max-width: 720px; font-size: var(--ara-font-body-lg); margin: 0 0 var(--ara-space-lg); }
  .ara-card, .ara-hero, .ara-flow, .ara-callout { background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-lg); }
  .ara-card { padding: var(--ara-space-md); min-height: 142px; }
  .ara-card h3 { margin: var(--ara-space-xs) 0 var(--ara-space-2xs); font-size: var(--ara-font-title-sm); }
  .ara-card p { color: var(--ara-text-2); font-size: var(--ara-font-body); line-height: 1.45; margin: 0; }
  .ara-hero { padding: var(--ara-space-lg) var(--ara-space-xl); border-left: 7px solid var(--status); margin: var(--ara-space-xs) 0 var(--ara-space-lg); }
  .ara-hero h2 { margin: var(--ara-space-2xs) 0; font-size: var(--ara-font-hero-title); }
  .ara-hero p { color: var(--ara-text-2); margin: var(--ara-space-2xs) 0 0; }
  .ara-status { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); font-size: var(--ara-font-status); font-weight: 800; letter-spacing: .08em; color: var(--status); }
  .ara-dot { width: .58rem; height: .58rem; border-radius: 50%; background: var(--status); display: inline-block; }
  .ara-meta { color: var(--ara-text-2); font-size: var(--ara-font-secondary); margin-top: var(--ara-space-sm); }
  .ara-mobile-hero { display: flex; justify-content: space-between; gap: var(--ara-space-md); align-items: center; padding: var(--ara-space-lg) var(--ara-space-xl); background: var(--ara-surface); border: 1px solid var(--ara-border); border-left: 6px solid var(--status); border-radius: var(--ara-radius-lg); margin: var(--ara-space-xs) 0 var(--ara-space-md); }
  .ara-mobile-hero h2 { margin: var(--ara-space-2xs) 0; font-size: var(--ara-font-title-xl); }
  .ara-mobile-hero p { color: var(--ara-text-2); margin: 0; max-width: 34rem; }
  .ara-readiness-number { color: var(--ara-text); font-size: var(--ara-font-hero-metric); font-weight: 780; letter-spacing: -.08em; line-height: .85; text-align: right; }
  .ara-readiness-number span { display: block; color: var(--status); font-size: var(--ara-font-micro); letter-spacing: .1em; margin-top: var(--ara-space-xs); }
  .ara-training-summary { background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-lg); padding: var(--ara-space-md) var(--ara-space-lg); margin: var(--ara-space-sm) 0 var(--ara-space-sm); }
  .ara-training-summary h2 { margin: var(--ara-space-2xs) 0 var(--ara-space-sm); font-size: var(--ara-font-title-lg); }
  .ara-training-meta { display: flex; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-training-meta span { display: inline-flex; padding: var(--ara-space-2xs) var(--ara-space-xs); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); font-size: var(--ara-font-chip); color: var(--ara-text-2); background: var(--ara-surface-2); }
  .ara-today-greeting { margin: var(--ara-space-2xs) 0 var(--ara-space-sm); }
  .ara-today-greeting span { color: var(--ara-text-muted); font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .12em; }
  .ara-today-meta { display: flex; align-items: center; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-today-meta .ara-badge { letter-spacing: .08em; }
  .ara-today-greeting h1 { margin: var(--ara-space-2xs) 0; }
  .ara-today-greeting p { color: var(--ara-text-2); margin: 0; }
  .ara-exercise-card { background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); padding: var(--ara-space-md); margin: var(--ara-space-xs) 0; font-weight: 600; line-height: 1.5; }
  .ara-flow { padding: var(--ara-space-md); min-height: 110px; }
  .ara-flow strong { display: block; font-size: var(--ara-font-body); margin: var(--ara-space-2xs) 0; color: var(--ara-text); }
  .ara-flow span { font-size: .83rem; line-height: 1.35; color: var(--ara-text-2); }
  .ara-callout { padding: var(--ara-space-md); border-left: 4px solid var(--status); }
  .ara-callout p { margin: var(--ara-space-2xs) 0 0; color: var(--ara-text-2); }
  .ara-detail { padding: var(--ara-space-sm) 0; border-bottom: 1px solid var(--ara-border); }
  .ara-detail:last-child { border-bottom: 0; }
  .ara-detail strong { font-size: var(--ara-font-body); color: var(--ara-text); }
  .ara-detail span { color: var(--ara-text-2); font-size: var(--ara-font-body-sm); }
  [data-testid="stMetric"] { background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); padding: var(--ara-space-sm); }
  div.stButton > button, div[data-testid="stDownloadButton"] > button { border-radius: var(--ara-radius-md); min-height: 2.7rem; font-weight: 650; }
  [data-testid="stRadio"] [role="radiogroup"] { gap: var(--ara-space-2xs); flex-wrap: wrap; }
  [data-testid="stRadio"] label { border-radius: var(--ara-radius-pill); }
  [data-testid="stExpander"] { border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); background: var(--ara-surface); }

  /* ---------------------------------------------------------- primitives */
  .ara-badge { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); padding: var(--ara-space-2xs) var(--ara-space-xs); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); font-size: var(--ara-font-status); font-weight: 800; letter-spacing: .06em; background: var(--ara-surface-2); color: var(--ara-text-2); text-transform: uppercase; }
  .ara-badge--status { color: var(--status); border-color: var(--status); background: var(--ara-surface); }
  .ara-badge--demo { color: var(--ara-text-2); border-color: var(--ara-border-strong); background: var(--ara-surface-2); }
  .ara-badge--local { color: var(--ara-status-green); border-color: var(--ara-status-green); background: var(--ara-surface); }
  .ara-badge--identity { color: var(--ara-text-2); border-color: var(--ara-border); background: var(--ara-surface-2); }
  .ara-confidence { display: inline-flex; align-items: center; gap: var(--ara-space-2xs); font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-confidence b { color: var(--ara-text); letter-spacing: .04em; }
  .ara-chip { display: inline-flex; align-items: center; padding: var(--ara-space-2xs) var(--ara-space-xs); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-pill); font-size: var(--ara-font-chip); color: var(--ara-text-2); background: var(--ara-surface-2); }
  .ara-chip--emphasis { color: var(--status); border-color: var(--status); background: var(--ara-surface); font-weight: 700; }
  .ara-section { margin: var(--ara-space-xl) 0 0; }
  .ara-section__title { font-size: var(--ara-font-title); color: var(--ara-text); letter-spacing: -.025em; margin: 0; }
  .ara-section__subtitle { color: var(--ara-text-2); font-size: var(--ara-font-body); margin: var(--ara-space-2xs) 0 0; }
  .ara-metric { display: flex; flex-direction: column; gap: var(--ara-space-2xs); padding: var(--ara-space-md); background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-md); }
  .ara-metric__label { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .1em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-metric__value { font-size: var(--ara-font-title); color: var(--ara-text); line-height: 1.15; }
  .ara-metric__value small { font-size: var(--ara-font-secondary); font-weight: 600; color: var(--ara-text-2); margin-left: var(--ara-space-2xs); }
  .ara-metric__context { font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-recommendation { padding: var(--ara-space-md) var(--ara-space-lg); background: var(--ara-surface); border: 1px solid var(--ara-border); border-left: 6px solid var(--ara-border); border-radius: var(--ara-radius-lg); }
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
  .ara-fact-row { display: flex; flex-direction: column; gap: var(--ara-space-2xs); padding-top: var(--ara-space-sm); margin-top: var(--ara-space-sm); border-top: 1px solid var(--ara-border); min-width: 0; }
  .ara-fact-grid .ara-fact-row { padding-top: var(--ara-space-xs); margin-top: var(--ara-space-2xs); }
  .ara-fact-label { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .1em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-fact-value { font-size: var(--ara-font-title-lg); color: var(--ara-text); line-height: 1.2; }
  .ara-fact-value--primary { font-size: var(--ara-font-title-xl); }
  .ara-fact-meta { display: flex; gap: var(--ara-space-xs); flex-wrap: wrap; }
  .ara-metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ara-space-sm); }
  .ara-why { display: flex; flex-direction: column; gap: var(--ara-space-md); }
  .ara-why-group { display: flex; flex-direction: column; gap: var(--ara-space-2xs); }
  .ara-why-list { margin: 0; padding-left: var(--ara-space-md); color: var(--ara-text-2); font-size: var(--ara-font-body); line-height: 1.45; }
  .ara-why-list li { margin-bottom: var(--ara-space-2xs); }
  .ara-training-summary--primary { border-left: 6px solid var(--status); }
  .ara-trace { display: flex; flex-direction: column; }
  .ara-coach-context { display: flex; align-items: center; gap: var(--ara-space-xs); flex-wrap: wrap; margin-bottom: var(--ara-space-xs); }
  .ara-history { display: flex; flex-direction: column; }
  .ara-history-row { display: flex; flex-direction: column; gap: 2px; padding: var(--ara-space-sm) 0; border-bottom: 1px solid var(--ara-border); }
  .ara-history-row:last-child { border-bottom: 0; }
  .ara-history-date { font-size: var(--ara-font-caption); font-weight: 700; letter-spacing: .08em; color: var(--ara-text-muted); text-transform: uppercase; }
  .ara-history-main { font-size: var(--ara-font-body); color: var(--ara-text); }
  .ara-history-meta { font-size: var(--ara-font-secondary); color: var(--ara-text-2); }
  .ara-profile-card { display: flex; flex-direction: column; gap: var(--ara-space-2xs); padding: var(--ara-space-md); background: var(--ara-surface); border: 1px solid var(--ara-border); border-radius: var(--ara-radius-lg); margin-bottom: var(--ara-space-xs); }
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
    .st-key-mobile_bottom_nav button { height: 100%; min-height: 2.75rem !important; border: 0 !important; border-radius: var(--ara-radius-sm) !important; white-space: pre-line !important; font-size: var(--ara-font-caption-sm) !important; line-height: 1.1 !important; padding: .25rem .1rem !important; background: transparent !important; color: var(--ara-nav-text) !important; }
    .st-key-mobile_bottom_nav button[kind="primary"] { background: var(--ara-ink) !important; color: var(--ara-text-inverse) !important; }
    .st-key-mobile_bottom_nav button p { font-size: var(--ara-font-caption-sm) !important; line-height: 1.05 !important; }

    /* Secondary destinations: one lightweight row above the content. */
    .st-key-mobile_utility_nav { display: flex; margin: 0 0 .1rem; }
    .st-key-mobile_utility_nav button { min-height: 2.75rem !important; border: 0 !important; background: transparent !important; color: var(--ara-utility-text) !important; padding: .1rem .35rem !important; }

    /* The chat composer lives inside the shortened scrolling viewport, above
       the navigation band, so its own bottom padding only has to clear the
       navigation border - not the browser chrome it used to avoid. */
    [data-testid="stBottomBlockContainer"] { padding-bottom: .85rem !important; }

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
