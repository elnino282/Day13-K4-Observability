from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from scripts.validate_dashboard import DashboardConfigError, load_dashboard_config
from ui.components import metric_card, panel_intro
from ui.data import dashboard_snapshot, read_jsonl, records_frame
from ui.services import analyze_log_quality, fetch_langfuse_snapshot
from ui.settings import ALERT_CONFIG, LOG_PATH, REPO_ROOT, SLO_CONFIG


def render_evidence() -> None:
    st.markdown('<div class="eyebrow">BẢN ĐỒ BÀN GIAO</div>', unsafe_allow_html=True)
    st.title("Những hạng mục đã hoàn thành")
    st.caption("Một view dành cho demo: contract, implementation và runtime proof được đặt cạnh nhau.")
    records = read_jsonl(LOG_PATH)
    frame = records_frame(records)
    snap = dashboard_snapshot(frame)
    log_quality = analyze_log_quality(records)
    try:
        load_dashboard_config(REPO_ROOT / "config" / "dashboard.yaml")
        dashboard_status = "6 / 6"
    except DashboardConfigError:
        dashboard_status = "Không hợp lệ"
    checks = [
        ("JSON logging", f"{log_quality['score']} / 100", "Required fields, enrichment và correlation ID"),
        ("Bảo vệ PII", f"{len(log_quality['pii_hits'])} rò rỉ", "Quét độc lập trên JSON logs đã render"),
        ("Nested tracing", f"{int(frame.get('trace_id', pd.Series(dtype=object)).dropna().nunique())} liên kết", "agent.run → rag.retrieve + llm.generate"),
        ("Bộ test", os.getenv("UI_TEST_SUMMARY", "Chạy qua scripts/run_demo.py"), "Kết quả preflight hiện tại từ demo launcher"),
        ("Dashboard contract", dashboard_status, "Latency, traffic, errors, cost, tokens và quality"),
        ("Mức sẵn sàng alert", f"{len(ALERT_CONFIG.get('alerts', []))} rule", "Triệu chứng latency, error và cost kèm runbook"),
    ]
    rows = st.columns(3)
    for index, (name, value, detail) in enumerate(checks):
        with rows[index % 3]:
            metric_card(name, value, detail)
        if index == 2:
            rows = st.columns(3)

    left, right = st.columns([1.2, 1], gap="large")
    with left, st.container(border=True):
        panel_intro("RUNTIME PROOF", "Quan sát trong local logs", "Giá trị trực tiếp, không phải placeholder trình bày.")
        proof = pd.DataFrame([
            {"Signal": "Request", "Giá trị": str(snap.request_count), "Nguồn": "request_received"},
            {"Signal": "Response", "Giá trị": str(snap.response_count), "Nguồn": "response_sent"},
            {"Signal": "Trace link duy nhất", "Giá trị": str(int(frame.get("trace_id", pd.Series(dtype=object)).dropna().nunique())), "Nguồn": "trace_id"},
            {"Signal": "Error event", "Giá trị": str(snap.error_count), "Nguồn": "request_failed"},
            {"Signal": "Tổng token", "Giá trị": str(snap.tokens_in_total + snap.tokens_out_total), "Nguồn": "tokens_in/out"},
            {"Signal": "Tổng cost", "Giá trị": f"${snap.total_cost_usd:.6f}", "Nguồn": "cost_usd"},
        ])
        st.dataframe(proof, width="stretch", hide_index=True)
    with right, st.container(border=True):
        panel_intro("REPOSITORY CONTRACT", "Sẵn sàng nộp bài", "Các artifact có thể kiểm tra bằng máy đã đầy đủ.")
        artifacts = [
            ("Log schema", REPO_ROOT / "config" / "logging_schema.json"),
            ("Cấu hình dashboard", REPO_ROOT / "config" / "dashboard.yaml"),
            ("SLOs", REPO_ROOT / "config" / "slo.yaml"),
            ("Alert rules", REPO_ROOT / "config" / "alert_rules.yaml"),
            ("Báo cáo", REPO_ROOT / "submission" / "REPORT.md"),
        ]
        for label, path in artifacts:
            st.write(f"{'✓' if path.exists() else '○'} **{label}** · `{path.relative_to(REPO_ROOT)}`")
        st.link_button("Mở Langfuse ↗", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"), width="stretch")

    with st.container(border=True):
        refresh_col, copy_col = st.columns([1, 3])
        with refresh_col:
            if st.button("Làm mới Langfuse snapshot", width="stretch"):
                with st.spinner("Đang đọc prompt labels và các trace mới nhất…"):
                    try:
                        st.session_state.langfuse_snapshot = fetch_langfuse_snapshot()
                        st.session_state.langfuse_error = None
                    except Exception as exc:
                        st.session_state.langfuse_error = f"{type(exc).__name__}: {exc}"
        with copy_col:
            panel_intro("EXTERNAL RUNTIME", "Langfuse snapshot", "Secret luôn ở server-side; UI chỉ render trace metadata an toàn.")
        if st.session_state.get("langfuse_error"):
            st.error(st.session_state.langfuse_error)
        snapshot = st.session_state.get("langfuse_snapshot")
        if snapshot:
            labels = snapshot["labels"]
            label_cols = st.columns(4)
            label_cols[0].metric("Trace mới nhất", snapshot["count"])
            label_cols[1].metric("Baseline", f"v{labels.get('baseline')}")
            label_cols[2].metric("Candidate", f"v{labels.get('candidate')}")
            label_cols[3].metric("Production", f"v{labels.get('production')}")
            traces = pd.DataFrame(snapshot["traces"])
            if not traces.empty:
                st.dataframe(traces, width="stretch", hide_index=True)
        else:
            st.caption("Nhấn làm mới khi demo để hiển thị prompt labels và 20 trace ID gần nhất.")

    with st.expander("SLO contract"):
        table = [
            {"SLI": name, "Mục tiêu": values.get("objective"), "Target %": values.get("target")}
            for name, values in SLO_CONFIG.get("slis", {}).items()
        ]
        st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
