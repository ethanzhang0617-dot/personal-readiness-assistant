"""Small, reusable presentation components. They never calculate readiness."""

from __future__ import annotations

from html import escape
from typing import Any, Callable, Sequence

import streamlit as st

from readiness_engine import AMBER, GREEN, INSUFFICIENT, RED, STOP
from styles import NAV_ELEMENT_KEY, UTILITY_NAV_ELEMENT_KEY


STATUS_META = {GREEN: ("#18864b", "Ready to train", "Your signals are broadly in line with your usual range."), AMBER: ("#b96d00", "Ready, with caution", "Your recovery is slightly below your usual baseline today."), RED: ("#c53f32", "Recovery recommended", "Your current signals suggest a lower-demand day."), STOP: ("#a32626", "Pause training & review symptoms", "A safety check overrides normal training guidance."), INSUFFICIENT: ("#68717a", "Keep collecting data", "There is not enough personal history for a complete readiness decision.")}

#: Primary mobile destinations. The component owns labels, icons and active
#: state; ``styles.SHELL_CSS`` owns placement, height and safe-area spacing.
PRIMARY_NAV_ITEMS: tuple[tuple[str, str], ...] = (("Today", "⌂"), ("Check-in", "✓"), ("Train", "↑"), ("Trends", "⌁"), ("Coach", "◌"))
SECONDARY_NAV_ITEMS: tuple[tuple[str, str], ...] = (("More", "⋯"), ("Profile", "◎"), ("Science & Logic", "⌘"), ("About", "i"))


def status_meta(status: str) -> tuple[str, str, str]:
    return STATUS_META.get(status, STATUS_META[INSUFFICIENT])


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
    colour, label, explanation = status_meta(assessment["overall_readiness"])
    index = assessment["readiness_index"]
    index_text = "—" if index is None else f"{index} / 100"
    st.markdown(
        f"<section class='ara-hero' style='--status:{colour}'>"
        f"<div class='ara-kicker'>TODAY'S READINESS</div><div class='ara-status'><i class='ara-dot'></i>{escape(assessment['overall_readiness'])}</div>"
        f"<h2>{escape(label)}</h2><p>{escape(explanation)}</p>"
        f"<div class='ara-meta'>Readiness index: <b>{index_text}</b> · Assessment confidence: <b>{escape(assessment['assessment_confidence'])}</b></div>"
        "</section>", unsafe_allow_html=True,
    )


def mobile_readiness_hero(profile: dict[str, Any], assessment: dict[str, Any]) -> None:
    """A presentation-only readiness summary; all values come from the engine."""
    colour, label, explanation = status_meta(assessment["overall_readiness"])
    index = assessment["readiness_index"]
    index_text = "—" if index is None else str(index)
    confidence = escape(str(assessment.get("assessment_confidence", "INSUFFICIENT")))
    st.markdown(
        f"<section class='ara-mobile-hero' style='--status:{colour}'>"
        f"<div><div class='ara-kicker'>TODAY'S READINESS</div>"
        f"<div class='ara-status'><i class='ara-dot'></i>{escape(assessment['overall_readiness'])}</div>"
        f"<h2>{escape(label)}</h2><p>{escape(explanation)}</p>"
        f"<div class='ara-meta'>Baseline confidence: <b>{confidence}</b></div></div>"
        f"<div class='ara-readiness-number'>{index_text}<span>INDEX</span></div>"
        "</section>", unsafe_allow_html=True,
    )


def training_summary(name: str, intensity: str, duration: str, training_type: str) -> None:
    st.markdown(
        f"<section class='ara-training-summary'><div class='ara-kicker'>TODAY'S TRAINING</div>"
        f"<h2>{escape(name)}</h2><div class='ara-training-meta'>"
        f"<span>{escape(intensity)}</span><span>{escape(duration)}</span><span>{escape(training_type)}</span>"
        "</div></section>", unsafe_allow_html=True,
    )


def domain_card(title: str, status: str, detail: str) -> None:
    colour, label, _ = status_meta(status)
    st.markdown(
        f"<section class='ara-card' style='--status:{colour}'>"
        f"<div class='ara-status'><i class='ara-dot'></i>{escape(label)}</div>"
        f"<h3>{escape(title)}</h3><p>{detail}</p></section>", unsafe_allow_html=True,
    )


def callout(title: str, body: str, status: str = GREEN) -> None:
    colour, _, _ = status_meta(status)
    st.markdown(f"<section class='ara-callout' style='--status:{colour}'><strong>{escape(title)}</strong><p>{body}</p></section>", unsafe_allow_html=True)


def flow_card(number: str, title: str, body: str) -> None:
    st.markdown(f"<section class='ara-flow'><div class='ara-kicker'>{escape(number)}</div><strong>{escape(title)}</strong><span>{body}</span></section>", unsafe_allow_html=True)


def detail_row(label: str, value: str, description: str) -> None:
    st.markdown(f"<div class='ara-detail'><strong>{escape(label)} · {escape(value)}</strong><br><span>{escape(description)}</span></div>", unsafe_allow_html=True)
