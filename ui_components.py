"""Reusable presentation components. They never calculate readiness.

Two groups:

*Primitives* (design-system foundation, safe to reuse on any page)
    ``status_badge``, ``context_chip``, ``identity_badge``, ``confidence_label``,
    ``metric_tile``, ``insight_card``, ``recommendation_card``,
    ``decision_trace_row``, ``section_header``, ``primary_cta``, ``secondary_cta``.

*Page components* (already used by the V1.0/V1.1 pages)
    ``page_intro``, ``readiness_hero``, ``mobile_readiness_hero``,
    ``training_summary``, ``domain_card``, ``callout``, ``flow_card``,
    ``detail_row``, and the mobile navigation components.

Colour never comes from a literal here: status tones resolve through
``styles.STATUS_TONE_TOKENS`` so one status has exactly one colour everywhere.
"""

from __future__ import annotations

from html import escape
from typing import Any, Callable, Iterable, Sequence

import streamlit as st

from readiness_engine import AMBER, GREEN, INSUFFICIENT, RED, STOP
from styles import NAV_ELEMENT_KEY, STATUS_TONE_TOKENS, UTILITY_NAV_ELEMENT_KEY


#: status -> (tone, short label, one-line explanation). ``tone`` is a CSS custom
#: property reference, so the hex value lives once in ``styles.COLOR_TOKENS``.
STATUS_META = {
    GREEN: ("var(--ara-status-green)", "Ready to train", "Your signals are broadly in line with your usual range."),
    AMBER: ("var(--ara-status-amber)", "Ready, with caution", "Your recovery is slightly below your usual baseline today."),
    RED: ("var(--ara-status-red)", "Recovery recommended", "Your current signals suggest a lower-demand day."),
    STOP: ("var(--ara-status-stop)", "Pause training & review symptoms", "A safety check overrides normal training guidance."),
    INSUFFICIENT: ("var(--ara-status-neutral)", "Keep collecting data", "There is not enough personal history for a complete readiness decision."),
}

#: Baseline confidence wording. The calculation is untouched; this only keeps the
#: label identical wherever it is shown.
CONFIDENCE_LABELS = {"NORMAL": "Normal", "LIMITED": "Limited", "INSUFFICIENT": "Insufficient"}

#: Primary mobile destinations. The component owns labels, icons and active
#: state; ``styles.SHELL_CSS`` owns placement, height and safe-area spacing.
PRIMARY_NAV_ITEMS: tuple[tuple[str, str], ...] = (("Today", "⌂"), ("Check-in", "✓"), ("Train", "↑"), ("Trends", "⌁"), ("Coach", "◌"))
SECONDARY_NAV_ITEMS: tuple[tuple[str, str], ...] = (("More", "⋯"), ("Profile", "◎"), ("Science & Logic", "⌘"), ("About", "i"))


# --------------------------------------------------------------------------- #
# Tone helpers
# --------------------------------------------------------------------------- #


def status_tone(status: str) -> str:
    """CSS custom-property reference for a readiness status."""
    return STATUS_META.get(status, STATUS_META[INSUFFICIENT])[0]


def status_meta(status: str) -> tuple[str, str, str]:
    return STATUS_META.get(status, STATUS_META[INSUFFICIENT])


def confidence_label(value: Any) -> str:
    """Consistent 'Baseline confidence: NORMAL' markup."""
    text = CONFIDENCE_LABELS.get(str(value).upper(), str(value))
    return f"<span class='ara-confidence'>Baseline confidence: <b>{escape(text.upper())}</b></span>"


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


def status_badge(status: str, label: str | None = None) -> str:
    """Status pill. Always pairs the colour with a text label."""
    tone, default_label, _ = status_meta(status)
    text = escape(label if label is not None else str(status))
    title = escape(default_label)
    return f"<span class='ara-badge ara-badge--status' style='--status:{tone}' title='{title}'>{text}</span>"


def identity_badge(is_demo: bool, name: str | None = None) -> str:
    """DEMO PROFILE / LOCAL PROFILE badge (profile switching lands in Phase 9)."""
    if is_demo:
        return "<span class='ara-badge ara-badge--demo'>DEMO PROFILE</span>"
    label = escape(name) if name else "LOCAL PROFILE"
    return f"<span class='ara-badge ara-badge--local'>{label}</span>"


def context_chip(text: str, emphasis: bool = False) -> str:
    """Compact metadata chip (session demand, duration, training type, …)."""
    cls = "ara-chip ara-chip--emphasis" if emphasis else "ara-chip"
    return f"<span class='{cls}'>{escape(str(text))}</span>"


def metric_tile(label: str, value: Any, unit: str | None = None, context: str | None = None, status: str | None = None) -> str:
    """Label / value / unit / optional context and status."""
    unit_html = f"<small>{escape(str(unit))}</small>" if unit else ""
    context_html = f"<div class='ara-metric__context'>{escape(str(context))}</div>" if context else ""
    status_html = f"<div>{status_badge(status)}</div>" if status else ""
    return (
        f"<section class='ara-metric' style='--status:{status_tone(status) if status else 'var(--ara-border)'}'>"
        f"<div class='ara-metric__label'>{escape(str(label))}</div>"
        f"<div class='ara-metric__value'>{escape(str(value))}{unit_html}</div>"
        f"{context_html}{status_html}</section>"
    )


def insight_card(title: str, body: str, status: str | None = None) -> str:
    """Standard information card; ``status`` adds a labelled status pill."""
    badge = status_badge(status) if status else ""
    return (
        f"<section class='ara-card' style='--status:{status_tone(status) if status else 'var(--ara-border)'}'>"
        f"{badge}<h3>{escape(title)}</h3><p>{escape(body)}</p></section>"
    )


def recommendation_card(title: str, chips: Iterable[str] = (), body: str | None = None, variant: str = "primary", eyebrow: str | None = None) -> str:
    """Recommendation pattern: primary / alternative / avoid.

    Foundation for PHASE 6; the Train page still renders its V1.0 markup.
    """
    variant_class = {"primary": "ara-recommendation--primary", "alternative": "ara-recommendation--alternative", "avoid": "ara-recommendation--avoid"}.get(variant, "ara-recommendation--primary")
    chips_html = "".join(context_chip(chip) for chip in chips)
    eyebrow_html = f"<div class='ara-kicker'>{escape(eyebrow)}</div>" if eyebrow else ""
    body_html = f"<p class='ara-recommendation__body'>{escape(body)}</p>" if body else ""
    chips_block = f"<div class='ara-recommendation__chips'>{chips_html}</div>" if chips_html else ""
    return (
        f"<section class='ara-recommendation {variant_class}' style='--status:{status_tone(GREEN)}'>"
        f"{eyebrow_html}<h3 class='ara-recommendation__title'>{escape(title)}</h3>"
        f"{body_html}{chips_block}</section>"
    )


def decision_trace_row(label: str, value: str, note: str | None = None, status: str | None = None) -> str:
    """Decision Trace row: label / value / optional note and status."""
    tone = status_tone(status) if status else "var(--ara-border)"
    note_html = f"<div class='ara-trace-row__note'>{escape(note)}</div>" if note else ""
    status_html = f"<div>{status_badge(status)}</div>" if status else ""
    return (
        f"<div class='ara-trace-row' style='--status:{tone}'>"
        f"<div class='ara-trace-row__label'>{escape(label)}</div>"
        f"<div class='ara-trace-row__value'>{escape(value)}</div>{note_html}{status_html}</div>"
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    """Section title + optional supporting line."""
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def primary_cta(label: str, key: str, disabled: bool = False, on_click: Callable[[], None] | None = None) -> bool:
    """Primary call to action (one per view)."""
    return st.button(label, key=key, type="primary", width="stretch", disabled=disabled, on_click=on_click)


def secondary_cta(label: str, key: str, disabled: bool = False, on_click: Callable[[], None] | None = None) -> bool:
    """Secondary action: same geometry, lower visual weight."""
    return st.button(label, key=key, type="secondary", width="stretch", disabled=disabled, on_click=on_click)


# --------------------------------------------------------------------------- #
# Page components
# --------------------------------------------------------------------------- #


def nav_label(page: str, icon: str) -> str:
    """Two-line label used by the compact mobile navigation."""
    return f"{icon}\n{page}"


def mobile_bottom_nav_component(
    current_page: str,
    on_select: Callable[[str], None],
    items: Sequence[tuple[str, str]] = PRIMARY_NAV_ITEMS,
) -> None:
    """Mobile-only bottom navigation.

    The component owns the active state and the destination list; the shell CSS
    owns height, placement, safe-area spacing, z-index and the desktop hiding
    rule. Nothing here positions the bar.
    """
    with st.container(key=NAV_ELEMENT_KEY):
        columns = st.columns(len(items), gap="small")
        for column, (page, icon) in zip(columns, items):
            with column:
                if st.button(nav_label(page, icon), key=f"mobile_nav_{page}", type="primary" if page == current_page else "secondary", width="stretch"):
                    on_select(page)


def mobile_utility_nav_component(on_select: Callable[[str], None], page: str = "More") -> None:
    """Secondary destinations that do not fit the five primary tabs."""
    with st.container(key=UTILITY_NAV_ELEMENT_KEY, horizontal=True, horizontal_alignment="right"):
        if st.button(page, key=f"mobile_{page.casefold()}", width="content"):
            on_select(page)


def page_intro(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='ara-kicker'>{escape(kicker)}</div><h1>{escape(title)}</h1><p class='ara-subtitle'>{escape(subtitle)}</p>", unsafe_allow_html=True)


def readiness_hero(profile: dict[str, Any], assessment: dict[str, Any], greeting: str) -> None:
    tone, label, explanation = status_meta(assessment["overall_readiness"])
    index = assessment["readiness_index"]
    index_text = "—" if index is None else f"{index} / 100"
    st.markdown(
        f"<section class='ara-hero' style='--status:{tone}'>"
        f"<div class='ara-kicker'>TODAY'S READINESS</div><div class='ara-status'><i class='ara-dot'></i>{escape(assessment['overall_readiness'])}</div>"
        f"<h2>{escape(label)}</h2><p>{escape(explanation)}</p>"
        f"<div class='ara-meta'>Readiness index: <b>{index_text}</b> · Assessment confidence: <b>{escape(assessment['assessment_confidence'])}</b></div>"
        "</section>", unsafe_allow_html=True,
    )


def mobile_readiness_hero(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    """A presentation-only readiness summary; all values come from the engine."""
    tone, label, explanation = status_meta(assessment["overall_readiness"])
    index = assessment["readiness_index"]
    index_text = "—" if index is None else str(index)
    confidence = escape(str(assessment.get("assessment_confidence", "INSUFFICIENT")))
    st.markdown(
        f"<section class='ara-mobile-hero' style='--status:{tone}'>"
        f"<div><div class='ara-kicker'>TODAY'S READINESS</div>"
        f"<div class='ara-status'><i class='ara-dot'></i>{escape(assessment['overall_readiness'])}</div>"
        f"<h2>{escape(label)}</h2><p>{escape(explanation)}</p>"
        f"<div class='ara-meta'>Baseline confidence: <b>{confidence}</b></div></div>"
        f"<div class='ara-readiness-number'>{index_text}<span>INDEX</span></div>"
        "</section>", unsafe_allow_html=True,
    )


def training_summary(name: str, intensity: str, duration: str, training_type: str) -> None:
    chips = "".join(context_chip(value) for value in (intensity, duration, training_type))
    st.markdown(
        f"<section class='ara-training-summary'><div class='ara-kicker'>TODAY'S TRAINING</div>"
        f"<h2>{escape(name)}</h2><div class='ara-training-meta'>{chips}</div></section>", unsafe_allow_html=True,
    )


def domain_card(title: str, status: str, detail: str) -> None:
    """Domain card used by Today's Key Signals (insight card + status line)."""
    tone, label, _ = status_meta(status)
    st.markdown(
        f"<section class='ara-card' style='--status:{tone}'>"
        f"<div class='ara-status'><i class='ara-dot'></i>{escape(label)}</div>"
        f"<h3>{escape(title)}</h3><p>{escape(detail)}</p></section>", unsafe_allow_html=True,
    )


def callout(title: str, body: str, status: str = GREEN) -> None:
    tone, _, _ = status_meta(status)
    st.markdown(f"<section class='ara-callout' style='--status:{tone}'><strong>{escape(title)}</strong><p>{body}</p></section>", unsafe_allow_html=True)


def flow_card(number: str, title: str, body: str) -> None:
    st.markdown(f"<section class='ara-flow'><div class='ara-kicker'>{escape(number)}</div><strong>{escape(title)}</strong><span>{body}</span></section>", unsafe_allow_html=True)


def detail_row(label: str, value: str, description: str) -> None:
    st.markdown(f"<div class='ara-detail'><strong>{escape(label)} · {escape(value)}</strong><br><span>{escape(description)}</span></div>", unsafe_allow_html=True)
