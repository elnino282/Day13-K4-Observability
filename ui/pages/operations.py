from __future__ import annotations

import html
from typing import Any

import httpx
import pandas as pd
import streamlit as st

from app.pii import scrub_text
from ui.components import panel_intro
from ui.data import read_jsonl, records_frame
from ui.services import INCIDENT_PLAYBOOKS, SCENARIO_LABELS, analyze_log_quality, run_demo_burst
from ui.settings import ALERT_CONFIG, API_BASE_URL, AUDIT_PATH, LOG_PATH


def render_operations(api_ok: bool, health: dict[str, Any]) -> None:
    st.markdown('<div class="eyebrow">VẬN HÀNH</div>', unsafe_allow_html=True)
    st.title("Trung tâm điều khiển incident")
    st.caption("Bật scenario, quan sát tín hiệu thay đổi, sau đó điều tra Metrics → Traces → Logs.")
    incidents = health.get("incidents", {}) if api_ok else {}
    descriptions = {
        "rag_slow": "Chèn retrieval delay 2,5 giây; P95 và thời lượng rag.retrieve sẽ tăng mạnh.",
        "tool_fail": "Tạo vector-store timeout; error rate và request_failed sẽ tăng.",
        "cost_spike": "Nhân output token; các panel token và cost sẽ tăng.",
    }
    for column, name in zip(st.columns(3), ["rag_slow", "tool_fail", "cost_spike"]):
        with column, st.container(border=True):
            enabled = bool(incidents.get(name))
            st.markdown(f"### {SCENARIO_LABELS[name]}")
            st.caption(descriptions[name])
            st.markdown(
                f'<span class="pill"><span class="dot{"" if enabled else " off"}"></span>'
                f'{"Đang bật" if enabled else "Đang tắt"}</span>',
                unsafe_allow_html=True,
            )
            action = "disable" if enabled else "enable"
            if st.button("Tắt scenario" if enabled else "Bật scenario", key=f"incident-{name}", disabled=not api_ok, width="stretch"):
                try:
                    result = httpx.post(f"{API_BASE_URL}/incidents/{name}/{action}", timeout=5.0)
                    result.raise_for_status()
                    st.success(f"Đã {'tắt' if enabled else 'bật'} {SCENARIO_LABELS[name]}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Điều khiển thất bại: {type(exc).__name__}")

    active_incidents = [name for name, enabled in incidents.items() if enabled]
    selected_index = ["rag_slow", "tool_fail", "cost_spike"].index(active_incidents[0]) if active_incidents else 0
    load_col, flow_col = st.columns([0.75, 2], gap="large")
    with load_col, st.container(border=True):
        panel_intro("TĂNG TỐC DEMO", "Tạo observed traffic", "Chạy các request an toàn sau khi bật scenario.")
        scenario = st.selectbox("Scenario điều tra", ["rag_slow", "tool_fail", "cost_spike"], index=selected_index, format_func=lambda value: SCENARIO_LABELS[value])
        burst_count = st.slider("Số request", 3, 8, 5)
        if st.button("Chạy demo burst", type="primary", disabled=not api_ok, width="stretch"):
            with st.spinner(f"Đang gửi {burst_count} observable request…"):
                st.session_state.demo_burst = run_demo_burst(burst_count, scenario)
                st.session_state.demo_scenario = scenario
            st.success("Đã tạo traffic. Mở Metrics để so sánh với baseline đã ghi nhận.")
        if st.session_state.get("demo_burst"):
            st.dataframe(pd.DataFrame(st.session_state.demo_burst), width="stretch", hide_index=True)
    with flow_col, st.container(border=True):
        playbook = INCIDENT_PLAYBOOKS[scenario]
        panel_intro("KỊCH BẢN BẮT BUỘC", "Metric → Trace → Log → Root cause → Fix → Prevention", f"Live playbook cho {SCENARIO_LABELS[scenario]}.")
        nodes = [
            ("01 · Metric", playbook["metric"]), ("02 · Trace", playbook["trace"]),
            ("03 · Log", playbook["log"]), ("04 · Root cause", playbook["root"]),
            ("05 · Khắc phục", playbook["fix"]), ("06 · Phòng ngừa", playbook["prevent"]),
        ]
        rendered = "".join(f'<div class="flow-node"><b>{title}</b><span>{html.escape(copy)}</span></div>' for title, copy in nodes)
        st.markdown(f'<div class="flow-grid">{rendered}</div>', unsafe_allow_html=True)

    alert_col, log_col = st.columns([1, 1.7], gap="large")
    with alert_col:
        st.subheader("Alert dựa trên SLO")
        for alert in ALERT_CONFIG.get("alerts", []):
            with st.container(border=True):
                severity = str(alert.get("severity", "unknown")).upper()
                st.markdown(f"**{alert.get('name')}** · `{severity}`")
                st.caption(alert.get("condition", ""))
                st.write(alert.get("user_impact", ""))
                st.caption(f"Phụ trách: {alert.get('owner')} · Runbook: {alert.get('runbook')}")
    with log_col:
        st.subheader("Structured event gần đây")
        records = read_jsonl(LOG_PATH)
        frame = records_frame(records)
        correlation_filter = st.text_input("Lọc theo correlation ID", placeholder="req-1234abcd")
        if correlation_filter and "correlation_id" in frame:
            frame = frame[frame["correlation_id"].astype(str) == correlation_filter.strip()]
        fields = [field for field in ["ts", "level", "event", "correlation_id", "feature", "latency_ms", "error_type", "trace_id", "payload.message_preview", "payload.query_preview", "payload.answer_preview"] if field in frame]
        if frame.empty:
            st.info("Chưa có log.")
        else:
            st.dataframe(frame[fields].tail(30).sort_values("ts", ascending=False), width="stretch", hide_index=True)

        quality = analyze_log_quality(records)
        with st.container(border=True):
            panel_intro("BẰNG CHỨNG BẢO MẬT", "PII redaction", "Quét regex độc lập trên JSON logs đã render.")
            p1, p2, p3 = st.columns(3)
            p1.metric("PII thô phát hiện", len(quality["pii_hits"]))
            p2.metric("Điểm log", f"{quality['score']}/100")
            p3.metric("Correlation IDs", quality["correlation_ids"])
            samples = pd.DataFrame([
                {"Loại PII": "Email", "Preview đã lưu": scrub_text("Liên hệ student@vinuni.edu.vn")},
                {"Loại PII": "Điện thoại", "Preview đã lưu": scrub_text("Liên hệ 090 123 4567")},
                {"Loại PII": "Thẻ tín dụng", "Preview đã lưu": scrub_text("Thẻ 4111 1111 1111 1111")},
            ])
            st.dataframe(samples, width="stretch", hide_index=True)

    with st.expander("Lịch sử audit"):
        audit = records_frame(read_jsonl(AUDIT_PATH))
        if audit.empty:
            st.caption("Chưa có audit event.")
        else:
            columns = [field for field in ["ts", "action", "actor", "correlation_id", "details.name"] if field in audit]
            st.dataframe(audit[columns].sort_values("ts", ascending=False), width="stretch", hide_index=True)
