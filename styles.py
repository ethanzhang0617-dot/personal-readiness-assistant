"""Visual system for the Personal Readiness Assistant product shell."""

from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
  :root { --ink:#171717; --muted:#686868; --line:#e8e8e3; --paper:#ffffff; --wash:#f7f7f4; }
  [data-testid="stAppViewContainer"] { background: var(--wash); }
  [data-testid="stHeader"] { background: rgba(247,247,244,.92); }
  .block-container { max-width: 1120px; padding-top: 1.3rem; padding-bottom: 5.2rem; }
  [data-testid="stSidebar"] { background:#fbfbf8; border-right:1px solid var(--line); }
  [data-testid="stSidebar"] .block-container { padding-top:1.2rem; }
  [data-testid="stSidebar"] div.stButton > button { justify-content:flex-start; text-align:left; border-radius:12px; min-height:2.75rem; border:1px solid #e8e8e3; background:#fff; color:#292929; }
  [data-testid="stSidebar"] div.stButton > button[kind="primary"] { background:#1d1d1b; border-color:#1d1d1b; color:#fff; }
  [data-testid="stSidebar"] div.stButton > button:hover { background:#f0f0ec; border-color:#deded8; }
  [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover { background:#383835; }
  h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
  h1 { font-size:clamp(1.85rem, 5vw, 2.8rem); margin-bottom:.25rem; }
  h2 { font-size:1.35rem; margin-top:1.5rem; }
  .ara-kicker { color:#777; font-size:.72rem; font-weight:700; letter-spacing:.12em; margin-bottom:.35rem; }
  .ara-subtitle { color:var(--muted); max-width:720px; font-size:1rem; margin:0 0 1.35rem; }
  .ara-card, .ara-hero, .ara-flow, .ara-callout { background:var(--paper); border:1px solid var(--line); border-radius:18px; }
  .ara-card { padding:1rem 1.05rem; min-height:142px; }
  .ara-card h3 { margin:.55rem 0 .35rem; font-size:1.02rem; }
  .ara-card p { color:var(--muted); font-size:.9rem; line-height:1.45; margin:0; }
  .ara-hero { padding:1.35rem 1.45rem; border-left:7px solid var(--status); margin:.65rem 0 1.25rem; }
  .ara-hero h2 { margin:.25rem 0 .25rem; font-size:clamp(1.55rem, 4vw, 2.25rem); }
  .ara-hero p { color:var(--muted); margin:.15rem 0 0; }
  .ara-status { display:inline-flex; align-items:center; gap:.42rem; font-size:.76rem; font-weight:800; letter-spacing:.08em; color:var(--status); }
  .ara-dot { width:.58rem; height:.58rem; border-radius:50%; background:var(--status); display:inline-block; }
  .ara-meta { color:var(--muted); font-size:.84rem; margin-top:.65rem; }
  .ara-mobile-hero { display:flex; justify-content:space-between; gap:1rem; align-items:center; padding:1.3rem 1.4rem; background:var(--paper); border:1px solid var(--line); border-left:6px solid var(--status); border-radius:18px; margin:.65rem 0 1rem; }
  .ara-mobile-hero h2 { margin:.25rem 0; font-size:1.65rem; }
  .ara-mobile-hero p { color:var(--muted); margin:0; max-width:34rem; }
  .ara-readiness-number { color:var(--ink); font-size:3.7rem; font-weight:780; letter-spacing:-.08em; line-height:.85; text-align:right; }
  .ara-readiness-number span { display:block; color:var(--status); font-size:.62rem; letter-spacing:.1em; margin-top:.55rem; }
  .ara-training-summary { background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:1.15rem 1.25rem; margin:.85rem 0 .65rem; }
  .ara-training-summary h2 { margin:.22rem 0 .7rem; font-size:1.45rem; }
  .ara-training-meta { display:flex; gap:.45rem; flex-wrap:wrap; }
  .ara-training-meta span { display:inline-flex; padding:.3rem .55rem; border:1px solid var(--line); border-radius:999px; font-size:.8rem; color:var(--muted); background:#fbfbf8; }
  .ara-today-greeting { margin:.35rem 0 .7rem; }
  .ara-today-greeting span { color:#777; font-size:.72rem; font-weight:700; letter-spacing:.12em; }
  .ara-today-greeting h1 { margin:.18rem 0 .25rem; }
  .ara-today-greeting p { color:var(--muted); margin:0; }
  .ara-exercise-card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:.9rem 1rem; margin:.5rem 0; font-weight:600; line-height:1.5; }
  .ara-flow { padding:.9rem; min-height:110px; }
  .ara-flow strong { display:block; font-size:.9rem; margin:.35rem 0; color:var(--ink); }
  .ara-flow span { font-size:.83rem; line-height:1.35; color:var(--muted); }
  .ara-callout { padding:1rem 1.05rem; border-left:4px solid var(--status); }
  .ara-callout p { margin:.3rem 0 0; color:var(--muted); }
  .ara-detail { padding:.75rem 0; border-bottom:1px solid var(--line); }
  .ara-detail:last-child { border-bottom:0; }
  .ara-detail strong { font-size:.9rem; color:var(--ink); }
  .ara-detail span { color:var(--muted); font-size:.88rem; }
  [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding:.7rem; }
  div.stButton > button, div[data-testid="stDownloadButton"] > button { border-radius:12px; min-height:2.7rem; font-weight:650; }
  [data-testid="stRadio"] [role="radiogroup"] { gap:.35rem; flex-wrap:wrap; }
  [data-testid="stRadio"] label { border-radius:999px; }
  [data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; background:#fff; }
  .st-key-mobile_bottom_nav, .st-key-mobile_utility_nav { display:none; }
  @media (max-width: 768px) {
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display:none !important; }
    .block-container { padding: .7rem 1rem calc(6.6rem + env(safe-area-inset-bottom)) !important; max-width:100%; }
    [data-testid="stHeader"] { background:rgba(247,247,244,.96); }
    .ara-hero { padding:1.05rem; }
    .ara-card { min-height:auto; margin-bottom:.45rem; }
    .ara-mobile-hero { padding:1.05rem; gap:.65rem; align-items:flex-start; }
    .ara-mobile-hero h2 { font-size:1.3rem; }
    .ara-readiness-number { font-size:3.15rem; }
    .ara-training-summary { padding:1rem; }
    .ara-training-summary h2 { font-size:1.3rem; }
    .ara-today-greeting h1 { font-size:1.7rem; }
    .st-key-mobile_utility_nav { display:flex; margin:0 0 .1rem; }
    .st-key-mobile_utility_nav button { min-height:2.35rem !important; border:0 !important; background:transparent !important; color:#4c4c48 !important; padding:.35rem .1rem !important; }
    .st-key-mobile_bottom_nav { display:block; position:fixed; left:0; right:0; bottom:0; z-index:1000; padding:.45rem .55rem calc(.45rem + env(safe-area-inset-bottom)); background:rgba(255,255,253,.98); border-top:1px solid var(--line); box-shadow:0 -8px 24px rgba(18,18,18,.06); }
    .st-key-mobile_bottom_nav [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:.18rem !important; }
    .st-key-mobile_bottom_nav [data-testid="stColumn"] { min-width:0 !important; width:20% !important; flex:1 1 20% !important; }
    .st-key-mobile_bottom_nav button { min-height:2.8rem !important; border:0 !important; border-radius:10px !important; white-space:pre-line !important; font-size:.67rem !important; line-height:1.1 !important; padding:.25rem .1rem !important; background:transparent !important; color:#5a5a56 !important; }
    .st-key-mobile_bottom_nav button[kind="primary"] { background:#1d1d1b !important; color:#fff !important; }
    .st-key-mobile_bottom_nav button p { font-size:.67rem !important; line-height:1.05 !important; }
    /* Streamlit columns become intentional single-column content on phone; the fixed nav is exempt above. */
    [data-testid="stHorizontalBlock"] { flex-wrap:wrap; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex:1 1 100%; min-width:100%; }
    [data-testid="stMetric"] { padding:.75rem .85rem; }
    div.stButton > button, div[data-testid="stDownloadButton"] > button { min-height:3rem; font-size:.95rem; }
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input { min-height:2.9rem; font-size:1rem; }
    [data-testid="stDataFrame"] { overflow-x:auto; }
  }
</style>
"""


def inject_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
