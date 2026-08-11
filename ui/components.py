from __future__ import annotations

import html

import altair as alt
import pandas as pd
import streamlit as st


def metric_card_markup(label: str, value: str, note: str, *, good: bool = True) -> str:
    tone = "metric-good" if good else "metric-warn"
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-note {tone}">{html.escape(note)}</div>'
        "</div>"
    )


def metric_card(label: str, value: str, note: str, *, good: bool = True) -> None:
    st.markdown(metric_card_markup(label, value, note, good=good), unsafe_allow_html=True)


def metric_grid(items: list[tuple[str, str, str, bool]]) -> None:
    cards = "".join(metric_card_markup(label, value, note, good=good) for label, value, note, good in items)
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def panel_intro(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="panel-kicker">{html.escape(kicker)}</div>'
        f'<div class="panel-title">{html.escape(title)}</div>'
        f'<div class="panel-copy">{html.escape(copy)}</div>',
        unsafe_allow_html=True,
    )


def base_chart(data: pd.DataFrame) -> alt.Chart:
    return alt.Chart(data).encode(
        x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M", labelColor="#aeb4be")),
        tooltip=[alt.Tooltip("minute:T", title="Time")],
    )


def line_chart(
    data: pd.DataFrame,
    fields: list[str],
    labels: list[str],
    colors: list[str],
    *,
    unit_title: str,
    threshold: float | None = None,
    threshold_color: str = "#ff9188",
) -> alt.LayerChart | alt.Chart:
    melted = data[["minute", *fields]].melt("minute", var_name="series", value_name="value")
    melted["series"] = melted["series"].map(dict(zip(fields, labels)))
    line = (
        alt.Chart(melted)
        .mark_line(point=alt.OverlayMarkDef(size=45), strokeWidth=2.5)
        .encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M", labelColor="#aeb4be")),
            y=alt.Y("value:Q", title=unit_title, axis=alt.Axis(labelColor="#aeb4be", gridColor="#292e38")),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(domain=labels, range=colors),
                legend=alt.Legend(title=None, orient="top", labelColor="#aeb4be"),
            ),
            tooltip=["minute:T", "series:N", alt.Tooltip("value:Q", format=".3f")],
        )
    )
    if threshold is None:
        return line.properties(height=250)
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(
        color=threshold_color, strokeDash=[6, 5], strokeWidth=1.5
    ).encode(y="threshold:Q")
    return (line + rule).properties(height=250)


def bar_chart(data: pd.DataFrame, field: str, color: str, *, unit_title: str) -> alt.Chart:
    return (
        base_chart(data)
        .mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            y=alt.Y(f"{field}:Q", title=unit_title, axis=alt.Axis(labelColor="#aeb4be", gridColor="#292e38")),
            tooltip=[alt.Tooltip(f"{field}:Q", format=".4f")],
        )
        .properties(height=250)
    )
