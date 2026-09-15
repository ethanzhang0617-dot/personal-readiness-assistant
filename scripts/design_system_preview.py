"""Developer preview for the V1.1 design system.

Run with::

    python -m streamlit run scripts/design_system_preview.py

This is engineering tooling, **not** a product page: it is intentionally absent
from the application navigation. It exists so the token layer and the reusable
primitives can be inspected on a real viewport without touching a product page.
"""

from __future__ import annotations

import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from readiness_engine import AMBER, GREEN, INSUFFICIENT, RED, STOP  # noqa: E402
from styles import COLOR_TOKENS, DESIGN_TOKENS, RADIUS_TOKENS, SPACE_TOKENS, STATUS_TONE_TOKENS, TYPE_TOKENS, inject_styles  # noqa: E402
from ui_components import (confidence_label, context_chip, decision_trace_row, identity_badge, insight_card,  # noqa: E402
                           metric_tile, primary_cta, recommendation_card, secondary_cta, status_badge)

st.set_page_config(page_title="Design system preview", layout="wide")
inject_styles()

st.markdown("<div class='ara-kicker'>DEVELOPER PREVIEW</div><h1>V1.1 design system</h1>", unsafe_allow_html=True)
st.caption("Not part of the product navigation. Tokens come from styles.DESIGN_TOKENS.")

st.subheader("Typography")
st.markdown(
    "<div class='ara-kicker'>KICKER / CAPTION</div>"
    "<h1>Page title</h1>"
    "<h2>Section title</h2>"
    "<p class='ara-subtitle'>Body large — supporting line under a page title.</p>"
    "<p style='font-size:var(--ara-font-body)'>Body — standard paragraph copy.</p>"
    "<div class='ara-meta'>Secondary — metadata line.</div>"
    "<div class='ara-readiness-number' style='text-align:left'>90<span>INDEX</span></div>",
    unsafe_allow_html=True,
)

st.subheader("Colour tokens")
swatches = "".join(
    f"<div style='display:inline-block;margin:0 var(--ara-space-sm) var(--ara-space-sm) 0'>"
    f"<div style='width:76px;height:44px;border-radius:var(--ara-radius-sm);border:1px solid var(--ara-border);background:{value}'></div>"
    f"<div style='font-size:var(--ara-font-micro);color:var(--ara-text-2)'>{name.replace('--ara-', '')}</div></div>"
    for name, value in COLOR_TOKENS.items()
    if not name.endswith("-bg") or name == "--ara-nav-bg"
)
st.markdown(swatches, unsafe_allow_html=True)

st.subheader("Status semantics")
st.markdown(
    "".join(f"<div style='margin-bottom:var(--ara-space-xs)'>{status_badge(status)} <span class='ara-meta'>{status}</span></div>" for status in (GREEN, AMBER, RED, STOP, INSUFFICIENT)),
    unsafe_allow_html=True,
)
st.caption("Every status pairs colour with a text label; the tone resolves through styles.STATUS_TONE_TOKENS.")

st.subheader("Badges and chips")
st.markdown(
    identity_badge(True) + " " + identity_badge(False, "MY LOCAL PROFILE") + " " + context_chip("Normal")
    + context_chip("50–65 min") + context_chip("Strength", emphasis=True) + "<br><br>" + confidence_label("NORMAL"),
    unsafe_allow_html=True,
)

st.subheader("Metric tiles")
columns = st.columns(4)
for column, (label, value, unit, context, status) in zip(columns, (
    ("HRV", "-0.6", "SD", "vs 28-day baseline", AMBER),
    ("Resting HR", "57", "bpm", "within usual range", GREEN),
    ("Sleep", "7.6", "h", "of 8.0 h need", GREEN),
    ("Training load", "310", "AU", "7d vs 21d", GREEN),
)):
    with column:
        st.markdown(metric_tile(label, value, unit, context, status), unsafe_allow_html=True)

st.subheader("Cards")
left, right = st.columns(2)
with left:
    st.markdown(insight_card("Autonomic", "HRV -0.6 SD", status=AMBER), unsafe_allow_html=True)
with right:
    st.markdown(insight_card("Sleep & Recovery", "7.6h / 8.0h usual need", status=GREEN), unsafe_allow_html=True)

st.subheader("Recommendations")
st.markdown(recommendation_card("Back + Biceps", ("Normal", "50–65 min", "Strength"), "Readiness is GREEN; today's session demand is normal.", eyebrow="PRIMARY RECOMMENDATION"), unsafe_allow_html=True)
st.markdown(recommendation_card("Shoulders + Arms", ("Reduced", "40–50 min"), variant="alternative", eyebrow="ALTERNATIVE"), unsafe_allow_html=True)
st.markdown(recommendation_card("Heavy Legs", ("Avoid today",), variant="avoid", eyebrow="AVOID TODAY"), unsafe_allow_html=True)

st.subheader("Decision trace row")
st.markdown(
    "".join(decision_trace_row(label, value, note) for label, value, note in (
        ("Goal", "Muscle Gain", "Drives volume and split weighting."),
        ("Weekly exposure", "Back 9 / 12 sets", "Completed sessions in the last 7 days."),
        ("Readiness", "GREEN", "Session demand stays normal."),
    )),
    unsafe_allow_html=True,
)

st.subheader("Button hierarchy")
st.markdown("<div class='ara-kicker'>PRIMARY</div>", unsafe_allow_html=True)
primary_cta("View workout", key="preview_primary")
st.markdown("<div class='ara-kicker'>SECONDARY</div>", unsafe_allow_html=True)
secondary_cta("View details", key="preview_secondary")

st.divider()
with st.expander("Token reference"):
    st.json({"design": DESIGN_TOKENS, "spacing": SPACE_TOKENS, "radius": RADIUS_TOKENS, "type": TYPE_TOKENS, "status_map": STATUS_TONE_TOKENS})
