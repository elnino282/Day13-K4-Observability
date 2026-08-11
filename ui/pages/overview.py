from __future__ import annotations

import os
from typing import Any

import streamlit as st

from ui.components import metric_grid, panel_intro
from ui.data import latest_event_time
from ui.services import load_dashboard_data
from ui.settings import API_BASE_URL, DASHBOARD_CONFIG


def render_header(api_ok: bool, health: dict[str, Any]) -> None:
    tracing = bool(health.get("tracing_enabled")) if api_ok else False
    st.markdown('<div class="eyebrow">Day 13 · AI Observability</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">SignalOps · trung tâm giám sát AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Một control room trực quan cho AI API: quan sát tín hiệu, '
        'đi sâu vào trace, xác minh bằng log và thao tác incident ngay trong một luồng demo.</div>',
        unsafe_allow_html=True,
    )
    api_dot = "" if api_ok else " off"
    trace_dot = "" if tracing else " off"
    st.markdown(
        f'<div class="status-row">'
        f'<span class="pill"><span class="dot{api_dot}"></span>API {"đang hoạt động" if api_ok else "ngoại tuyến"}</span>'
        f'<span class="pill"><span class="dot{trace_dot}"></span>Langfuse {"đã bật" if tracing else "chưa phát hiện"}</span>'
        '<span class="pill">Cửa sổ mặc định 60 phút</span>'
        '<span class="pill">Tự làm mới mỗi 30 giây</span></div>',
        unsafe_allow_html=True,
    )


def render_overview(api_ok: bool, health: dict[str, Any]) -> None:
    render_header(api_ok, health)
    frame, _, snap = load_dashboard_data(60)
    panels = DASHBOARD_CONFIG.get("dashboard", {}).get("panels", [])
    metric_grid(
        [
            ("Dịch vụ", "Ổn định" if api_ok else "Ngoại tuyến", f"{API_BASE_URL}/health", api_ok),
            ("Request đã quan sát", str(snap.request_count), "Structured request events", True),
            ("Dashboard contract", f"{len(panels)}/6", "Đủ các nhóm signal bắt buộc", len(panels) == 6),
            ("Error rate", f"{snap.error_rate_pct:.2f}%", "SLO ≤ 2%", snap.error_rate_pct <= 2),
        ]
    )
    left, right = st.columns([1.6, 1], gap="large")
    with left, st.container(border=True):
        panel_intro("LUỒNG ĐIỀU TRA", "Metrics → Traces → Logs", "Ba lớp bằng chứng, một correlation path xuyên suốt.")
        st.markdown(
            '<div class="journey">'
            '<div class="journey-step"><div class="journey-index">01 · PHÁT HIỆN</div><div class="journey-name">Metrics</div><div class="journey-copy">Nhận diện cửa sổ, tail latency, error và cost bất thường.</div></div>'
            '<div class="journey-step"><div class="journey-index">02 · KHOANH VÙNG</div><div class="journey-name">Traces</div><div class="journey-copy">So sánh agent.run, rag.retrieve và llm.generate để khoanh vùng.</div></div>'
            '<div class="journey-step"><div class="journey-index">03 · XÁC MINH</div><div class="journey-name">Logs</div><div class="journey-copy">Dùng correlation ID và structured fields để chốt root cause.</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
    with right, st.container(border=True):
        panel_intro("NGỮ CẢNH TRỰC TIẾP", "Phiên chạy hiện tại", "Dữ liệu lấy trực tiếp từ workspace.")
        st.write(f"**Event gần nhất**\n\n{latest_event_time(frame)}")
        st.write(f"**Model**\n\n`{health.get('model', 'chưa xác định')}`")
        route = f"{os.getenv('LANGFUSE_PROMPT_NAME', 'day13-chat')}:{os.getenv('LANGFUSE_PROMPT_LABEL', 'production')}"
        st.write(f"**Prompt route**\n\n`{route}`")
        active = [name for name, enabled in health.get("incidents", {}).items() if enabled] if api_ok else []
        st.write(f"**Incident đang bật**\n\n{', '.join(active) if active else 'Không có'}")
        st.link_button("Mở FastAPI docs ↗", f"{API_BASE_URL}/docs", width="stretch")

    st.subheader("Những gì demo này chứng minh")
    items = [
        ("Structured telemetry", "Correlation ID, enriched JSON logs và recursive PII scrubbing."),
        ("Vòng đời AI được quản lý", "Langfuse prompt versions, labels, nested traces, token và cost metadata."),
        ("Sẵn sàng vận hành", "SLO thresholds, symptom-based alerts, runbook và incident injection."),
    ]
    for column, (title, copy) in zip(st.columns(3), items):
        with column, st.container(border=True):
            st.markdown(f"#### {title}")
            st.caption(copy)
