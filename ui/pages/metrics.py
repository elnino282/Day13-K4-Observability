from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from ui.components import bar_chart, line_chart, metric_grid, panel_intro
from ui.data import latest_event_time
from ui.services import load_dashboard_data
from ui.settings import DASHBOARD_CONFIG


def render_metrics(minutes: int) -> None:
    st.markdown('<div class="eyebrow">KHÁM PHÁ SIGNAL</div>', unsafe_allow_html=True)
    st.title("Dashboard AI observability")
    st.caption("Nguồn chuẩn: `data/logs.jsonl` · Threshold lấy từ `config/dashboard.yaml`.")
    frame, series, snap = load_dashboard_data(minutes)
    if frame.empty:
        st.warning("Không có log event trong cửa sổ này. Hãy khởi động API và gửi một vài chat request.")
        return

    panels = {panel["id"]: panel for panel in DASHBOARD_CONFIG["dashboard"]["panels"]}
    control_left, control_right, control_note = st.columns([1, 1, 3])
    with control_left:
        if st.button("Ghi nhận baseline", width="stretch", type="primary"):
            st.session_state.metric_baseline = asdict(snap)
            st.session_state.metric_baseline_time = latest_event_time(frame)
            st.rerun()
    with control_right:
        if st.button("Xóa baseline", width="stretch", disabled="metric_baseline" not in st.session_state):
            st.session_state.pop("metric_baseline", None)
            st.session_state.pop("metric_baseline_time", None)
            st.rerun()
    baseline = st.session_state.get("metric_baseline")
    with control_note:
        if baseline:
            st.info(f"Đã ghi nhận baseline lúc {st.session_state.get('metric_baseline_time')} · các delta bên dưới được so sánh với mốc này.")
        else:
            st.caption("Ghi nhận baseline sạch trước khi bật incident; sau đó quay lại để xem delta trước và sau.")

    def note_with_delta(note: str, field: str, current: float, *, decimals: int = 1) -> str:
        if not baseline:
            return note
        delta = current - float(baseline.get(field, 0))
        return f"{note} · Δ {delta:+.{decimals}f}"

    metric_grid(
        [
            ("P95 latency", f"{snap.latency_p95:.0f} ms", note_with_delta(f"≤ {panels['latency']['threshold']['value']} ms", "latency_p95", snap.latency_p95, decimals=0), snap.latency_p95 <= 3000),
            ("Traffic", f"{snap.request_count}", note_with_delta(f"{snap.request_rate_per_minute:.1f} req/phút", "request_count", snap.request_count, decimals=0), True),
            ("Error rate", f"{snap.error_rate_pct:.2f}%", note_with_delta("SLO ≤ 2%", "error_rate_pct", snap.error_rate_pct, decimals=2), snap.error_rate_pct <= 2),
            ("Cost", f"${snap.total_cost_usd:.4f}", note_with_delta("Tổng trong cửa sổ", "total_cost_usd", snap.total_cost_usd, decimals=4), snap.total_cost_usd <= 2.5),
            ("Tokens", f"{snap.tokens_in_total + snap.tokens_out_total:,}", note_with_delta(f"{snap.tokens_in_total:,} input · {snap.tokens_out_total:,} output", "tokens_out_total", snap.tokens_out_total, decimals=0), True),
            ("Quality", f"{snap.quality_avg:.2f}", note_with_delta("Mục tiêu ≥ 0.75", "quality_avg", snap.quality_avg, decimals=2), snap.quality_avg >= 0.75),
        ]
    )
    st.caption(f"Event gần nhất: {latest_event_time(frame)} · Cửa sổ: {minutes} phút · Tự làm mới: 30 giây")
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            panel_intro("01 · LATENCY", "Tail latency", "P50 / P95 / P99 theo mili giây · đường đỏ = P95 SLO")
            st.altair_chart(line_chart(series, ["latency_p50", "latency_p95", "latency_p99"], ["P50", "P95", "P99"], ["#858c98", "#f5f7f9", "#f0bd65"], unit_title="ms", threshold=3000), width="stretch")
        with st.container(border=True):
            panel_intro("03 · ERRORS", "Áp lực lỗi", "Error rate theo từng phút · SLO ≤ 2%")
            st.altair_chart(line_chart(series, ["error_rate_pct"], ["Error rate"], ["#ff9188"], unit_title="percent", threshold=2), width="stretch")
        with st.container(border=True):
            panel_intro("05 · TOKENS", "Khối lượng token", "Tổng input và output token theo từng phút")
            st.altair_chart(line_chart(series, ["tokens_in", "tokens_out"], ["Input", "Output"], ["#f5f7f9", "#858c98"], unit_title="tokens"), width="stretch")
    with right:
        with st.container(border=True):
            panel_intro("02 · TRAFFIC", "Request traffic", "Số event request_received theo từng phút")
            st.altair_chart(bar_chart(series, "requests", "#f5f7f9", unit_title="requests/min"), width="stretch")
        with st.container(border=True):
            panel_intro("04 · COST", "Cost theo thời gian", "Generation cost cộng dồn theo từng phút, đơn vị USD")
            st.altair_chart(bar_chart(series, "cost_usd", "#d2d6dc", unit_title="USD"), width="stretch")
        with st.container(border=True):
            panel_intro("06 · QUALITY", "Quality proxy", "Heuristic score · đường mục tiêu màu xanh = 0.75")
            st.altair_chart(line_chart(series, ["quality"], ["Quality"], ["#77d89a"], unit_title="score", threshold=0.75, threshold_color="#77d89a"), width="stretch")
