from __future__ import annotations

import html
import json
import os
import re
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

import altair as alt
import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
_repo_root = str(REPO_ROOT)
# ``streamlit run ui/app.py`` puts ``ui/`` before the repository root. Since
# this entrypoint is also named app.py, importing ``app.pii`` would find this
# file again and recurse. Always move the repository root to index 0 so the
# real backend package at ``<repo>/app/`` wins module resolution.
while _repo_root in sys.path:
    sys.path.remove(_repo_root)
sys.path.insert(0, _repo_root)

# Streamlit executes this file with the module name ``app`` in some launch
# contexts.  That shadows the repository's actual ``app/`` package, so imports
# such as ``from app.pii import scrub_text`` would otherwise resolve back to
# this UI file.  Remove only that accidental alias before importing backend
# helpers.
_streamlit_app_alias = sys.modules.get("app")
if _streamlit_app_alias is not None:
    _alias_path = getattr(_streamlit_app_alias, "__file__", None)
    if _alias_path and Path(_alias_path).resolve() == Path(__file__).resolve():
        del sys.modules["app"]

from ui.data import (  # noqa: E402
    dashboard_snapshot,
    filter_recent,
    latest_event_time,
    load_yaml,
    minute_series,
    read_jsonl,
    records_frame,
)
from app.pii import scrub_text  # noqa: E402
from scripts.manage_prompts import prompt_status  # noqa: E402
from scripts.validate_dashboard import DashboardConfigError, load_dashboard_config  # noqa: E402
from scripts.validate_logs import ENRICHMENT_FIELDS, PII_DETECTORS  # noqa: E402


load_dotenv(REPO_ROOT / ".env")

API_BASE_URL = os.getenv("UI_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
LOG_PATH = REPO_ROOT / os.getenv("LOG_PATH", "data/logs.jsonl")
AUDIT_PATH = REPO_ROOT / os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl")
DASHBOARD_CONFIG = load_yaml(REPO_ROOT / "config" / "dashboard.yaml")
SLO_CONFIG = load_yaml(REPO_ROOT / "config" / "slo.yaml")
ALERT_CONFIG = load_yaml(REPO_ROOT / "config" / "alert_rules.yaml")


st.set_page_config(
    page_title="SignalOps · AI Reliability Studio",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --bg: #090b10;
          --surface: #11141c;
          --surface-2: #171b25;
          --border: rgba(255,255,255,.08);
          --muted: #969cab;
          --text: #f5f7fb;
          --violet: #8b5cf6;
          --cyan: #22d3ee;
          --green: #34d399;
          --amber: #fbbf24;
          --red: #fb7185;
        }
        .stApp { background:
          radial-gradient(circle at 78% -10%, rgba(139,92,246,.16), transparent 32rem),
          radial-gradient(circle at 5% 20%, rgba(34,211,238,.08), transparent 28rem),
          var(--bg); }
        [data-testid="stSidebar"] {
          background: rgba(12,14,20,.96);
          border-right: 1px solid var(--border);
        }
        [data-testid="stHeader"] { background: transparent; }
        .block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3 { letter-spacing: -.03em; }
        .eyebrow { color: var(--cyan); font-size: .72rem; font-weight: 750; letter-spacing: .16em;
          text-transform: uppercase; margin-bottom: .55rem; }
        .hero-title { font-size: clamp(2.15rem, 5vw, 4.2rem); line-height: .96; font-weight: 780;
          letter-spacing: -.065em; margin: 0 0 1rem; max-width: 900px; }
        .hero-title span { background: linear-gradient(110deg, #fff 25%, #a78bfa 62%, #22d3ee);
          -webkit-background-clip: text; color: transparent; }
        .hero-copy { color: var(--muted); max-width: 760px; font-size: 1.05rem; line-height: 1.7; }
        .status-row { display: flex; flex-wrap: wrap; gap: .55rem; margin: 1.25rem 0 1.8rem; }
        .pill { display: inline-flex; align-items: center; gap: .45rem; padding: .42rem .68rem;
          border: 1px solid var(--border); border-radius: 999px; background: rgba(255,255,255,.035);
          color: #d9dce5; font-size: .78rem; }
        .dot { width: .45rem; height: .45rem; border-radius: 50%; background: var(--green);
          box-shadow: 0 0 12px rgba(52,211,153,.7); }
        .dot.off { background: var(--red); box-shadow: 0 0 12px rgba(251,113,133,.6); }
        .metric-card { min-height: 142px; border: 1px solid var(--border); border-radius: 18px;
          padding: 1.05rem 1.1rem; background: linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.018));
          box-shadow: 0 16px 42px rgba(0,0,0,.18); }
        .metric-label { color: var(--muted); font-size: .74rem; text-transform: uppercase;
          letter-spacing: .1em; font-weight: 700; }
        .metric-value { color: var(--text); font-size: 2rem; letter-spacing: -.055em;
          font-weight: 760; margin: .45rem 0 .25rem; }
        .metric-note { color: var(--muted); font-size: .78rem; }
        .metric-good { color: var(--green); } .metric-warn { color: var(--amber); }
        .panel-kicker { color: var(--muted); font-size: .73rem; letter-spacing: .08em;
          text-transform: uppercase; margin-bottom: .1rem; }
        .panel-title { color: var(--text); font-size: 1.15rem; font-weight: 720; margin-bottom: .2rem; }
        .panel-copy { color: var(--muted); font-size: .82rem; margin-bottom: .8rem; }
        .journey { display: grid; grid-template-columns: repeat(3,1fr); gap: .8rem; margin: 1rem 0; }
        .journey-step { border: 1px solid var(--border); border-radius: 16px; padding: 1rem;
          background: rgba(255,255,255,.025); }
        .journey-index { color: var(--violet); font-weight: 800; font-size: .72rem; }
        .journey-name { font-weight: 720; margin: .25rem 0; }
        .journey-copy { color: var(--muted); font-size: .8rem; line-height: 1.5; }
        .trace-chip { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem;
          color: #c4b5fd; background: rgba(139,92,246,.12); border: 1px solid rgba(139,92,246,.25);
          border-radius: 8px; padding: .3rem .5rem; word-break: break-all; }
        .flow-grid { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: .55rem; }
        .flow-node { min-height: 112px; border: 1px solid var(--border); border-radius: 14px;
          background: rgba(255,255,255,.028); padding: .8rem; }
        .flow-node b { display: block; color: #c4b5fd; font-size: .68rem; letter-spacing: .08em;
          text-transform: uppercase; margin-bottom: .45rem; }
        .flow-node span { color: #d9dce5; font-size: .78rem; line-height: 1.45; }
        .delta { color: var(--cyan); font-weight: 720; }
        .stButton > button, .stLinkButton > a { border-radius: 11px; font-weight: 650; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--border) !important;
          background: rgba(17,20,28,.62); border-radius: 18px; }
        [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
        @media (max-width: 900px) { .journey, .flow-grid { grid-template-columns: 1fr; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_health() -> tuple[bool, dict[str, Any]]:
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=2.0)
        response.raise_for_status()
        return True, response.json()
    except Exception:
        return False, {}


def analyze_log_quality(records: list[dict[str, Any]]) -> dict[str, Any]:
    missing_required = 0
    missing_enrichment = 0
    correlation_ids: set[str] = set()
    pii_hits: list[dict[str, Any]] = []
    for record in records:
        if not {"ts", "level", "event"}.issubset(record):
            missing_required += 1
        if record.get("service") == "api":
            correlation_id = record.get("correlation_id")
            if not correlation_id or correlation_id == "MISSING":
                missing_required += 1
            if not ENRICHMENT_FIELDS.issubset(record):
                missing_enrichment += 1
        raw = json.dumps(record, ensure_ascii=False)
        detected = [name for name, detector in PII_DETECTORS.items() if detector.search(raw)]
        if detected:
            pii_hits.append({"event": record.get("event", "unknown"), "types": detected})
        correlation_id = record.get("correlation_id")
        if correlation_id and correlation_id not in {"MISSING", "system"}:
            correlation_ids.add(str(correlation_id))

    score = 100
    if missing_required:
        score -= 30
    if len(correlation_ids) < 2:
        score -= 20
    if missing_enrichment:
        score -= 20
    if pii_hits:
        score -= 30
    return {
        "score": max(0, score),
        "missing_required": missing_required,
        "missing_enrichment": missing_enrichment,
        "correlation_ids": len(correlation_ids),
        "pii_hits": pii_hits,
    }


def fetch_langfuse_snapshot() -> dict[str, Any]:
    from app.tracing import get_langfuse_client

    client = get_langfuse_client()
    if not client.auth_check():
        raise RuntimeError("Langfuse authentication failed")
    labels = prompt_status(client)
    response = client.api.trace.list(limit=20, order_by="timestamp.desc")
    traces: list[dict[str, Any]] = []
    for trace in response.data:
        metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
        traces.append(
            {
                "timestamp": trace.timestamp,
                "trace_id": trace.id,
                "name": trace.name,
                "session_id": trace.session_id,
                "prompt_label": metadata.get("prompt_label"),
                "prompt_version": metadata.get("prompt_version"),
                "correlation_id": metadata.get("correlation_id"),
            }
        )
    return {"labels": labels, "traces": traces, "count": len(traces)}


INCIDENT_PLAYBOOKS = {
    "rag_slow": {
        "metric": "P95 latency rises above the 3,000 ms SLO line.",
        "trace": "Open a slow trace; rag.retrieve dominates the waterfall.",
        "log": "retrieval_completed has the same correlation ID and elevated latency_ms.",
        "root": "Injected retrieval delay in the mock vector-store path.",
        "fix": "Disable the scenario; apply cache, timeout or a retrieval fallback.",
        "prevent": "Alert on tail latency and add timeout/circuit-breaker coverage.",
    },
    "tool_fail": {
        "metric": "Error rate and request_failed count increase.",
        "trace": "rag.retrieve is the first span with ERROR level.",
        "log": "retrieval_failed and request_failed share one correlation ID.",
        "root": "The vector-store call raises a timeout exception.",
        "fix": "Disable the failing tool and serve a safe fallback response.",
        "prevent": "Add retries with budget, circuit breaker and downstream health checks.",
    },
    "cost_spike": {
        "metric": "Output tokens and cost rise while traffic stays flat.",
        "trace": "llm.generate has abnormal usage and total cost.",
        "log": "response_sent shows elevated tokens_out and cost_usd.",
        "root": "The incident multiplies generated output tokens.",
        "fix": "Disable the scenario and cap output tokens.",
        "prevent": "Alert on cost/request and version token limits with prompts.",
    },
}


def run_demo_burst(count: int, scenario: str) -> list[dict[str, Any]]:
    prompts = [
        "Explain how metrics traces and logs work together",
        "How should an engineer investigate tail latency",
        "Summarize the observability workflow for an AI API",
        "Which signal should be checked after latency increases",
        "Describe how to prove a slow span is the root cause",
        "How can an AI team control token cost",
        "Why is correlation ID useful during incidents",
        "What makes an alert actionable",
    ]
    results: list[dict[str, Any]] = []
    session_id = f"ui-{scenario}-{uuid.uuid4().hex[:6]}"
    for index in range(count):
        started = pd.Timestamp.now(tz="UTC")
        try:
            response = httpx.post(
                f"{API_BASE_URL}/chat",
                json={
                    "user_id": "ui-incident-demo",
                    "session_id": session_id,
                    "feature": "monitoring",
                    "message": prompts[index % len(prompts)],
                },
                timeout=30.0,
            )
            elapsed_ms = int((pd.Timestamp.now(tz="UTC") - started).total_seconds() * 1000)
            payload = response.json()
            results.append(
                {
                    "request": index + 1,
                    "status": response.status_code,
                    "latency_ms": elapsed_ms,
                    "correlation_id": payload.get("correlation_id") or response.headers.get("x-request-id"),
                    "trace_id": payload.get("trace_id"),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "request": index + 1,
                    "status": "client_error",
                    "latency_ms": None,
                    "correlation_id": None,
                    "trace_id": None,
                    "detail": type(exc).__name__,
                }
            )
    return results


def metric_card(label: str, value: str, note: str, *, good: bool = True) -> None:
    tone = "metric-good" if good else "metric-warn"
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{html.escape(value)}</div>
          <div class="metric-note {tone}">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_intro(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="panel-kicker">{html.escape(kicker)}</div>
        <div class="panel-title">{html.escape(title)}</div>
        <div class="panel-copy">{html.escape(copy)}</div>
        """,
        unsafe_allow_html=True,
    )


def base_chart(data: pd.DataFrame) -> alt.Chart:
    return alt.Chart(data).encode(
        x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M", labelColor="#969cab")),
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
) -> alt.LayerChart | alt.Chart:
    melted = data[["minute", *fields]].melt("minute", var_name="series", value_name="value")
    label_map = dict(zip(fields, labels))
    melted["series"] = melted["series"].map(label_map)
    line = (
        alt.Chart(melted)
        .mark_line(point=alt.OverlayMarkDef(size=45), strokeWidth=2.5)
        .encode(
            x=alt.X("minute:T", title=None, axis=alt.Axis(format="%H:%M", labelColor="#969cab")),
            y=alt.Y("value:Q", title=unit_title, axis=alt.Axis(labelColor="#969cab", gridColor="#262a35")),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(domain=labels, range=colors),
                legend=alt.Legend(title=None, orient="top", labelColor="#c8cbd4"),
            ),
            tooltip=["minute:T", "series:N", alt.Tooltip("value:Q", format=".3f")],
        )
    )
    if threshold is None:
        return line.properties(height=250)
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(
        color="#fb7185", strokeDash=[6, 5], strokeWidth=1.5
    ).encode(y="threshold:Q")
    return (line + rule).properties(height=250)


def bar_chart(data: pd.DataFrame, field: str, color: str, *, unit_title: str) -> alt.Chart:
    return (
        base_chart(data)
        .mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            y=alt.Y(f"{field}:Q", title=unit_title, axis=alt.Axis(labelColor="#969cab", gridColor="#262a35")),
            tooltip=[alt.Tooltip(f"{field}:Q", format=".4f")],
        )
        .properties(height=250)
    )


def load_dashboard_data(minutes: int) -> tuple[pd.DataFrame, pd.DataFrame, Any]:
    frame = records_frame(read_jsonl(LOG_PATH))
    recent = filter_recent(frame, minutes)
    return recent, minute_series(recent), dashboard_snapshot(recent)


def render_header(api_ok: bool, health: dict[str, Any]) -> None:
    tracing = bool(health.get("tracing_enabled")) if api_ok else False
    st.markdown('<div class="eyebrow">Day 13 · AI Observability</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-title"><span>SignalOps</span> reliability studio</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-copy">Một control room trực quan cho AI API: quan sát tín hiệu, '
        'đi sâu vào trace, xác minh bằng log và thao tác incident ngay trong một luồng demo.</div>',
        unsafe_allow_html=True,
    )
    api_dot = "" if api_ok else " off"
    trace_dot = "" if tracing else " off"
    st.markdown(
        f"""
        <div class="status-row">
          <span class="pill"><span class="dot{api_dot}"></span>API {'online' if api_ok else 'offline'}</span>
          <span class="pill"><span class="dot{trace_dot}"></span>Langfuse {'enabled' if tracing else 'not detected'}</span>
          <span class="pill">60m default window</span>
          <span class="pill">30s live refresh</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview(api_ok: bool, health: dict[str, Any]) -> None:
    render_header(api_ok, health)
    frame, _, snap = load_dashboard_data(60)
    panels = DASHBOARD_CONFIG.get("dashboard", {}).get("panels", [])
    cols = st.columns(4)
    with cols[0]:
        metric_card("Service", "Healthy" if api_ok else "Offline", f"{API_BASE_URL}/health", good=api_ok)
    with cols[1]:
        metric_card("Observed requests", str(snap.request_count), "Structured request events")
    with cols[2]:
        metric_card("Dashboard contract", f"{len(panels)}/6", "All required signal groups", good=len(panels) == 6)
    with cols[3]:
        metric_card("Error rate", f"{snap.error_rate_pct:.2f}%", "SLO ≤ 2%", good=snap.error_rate_pct <= 2)

    st.write("")
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        with st.container(border=True):
            panel_intro("Investigation path", "Metrics → Traces → Logs", "Ba lớp bằng chứng, một correlation path xuyên suốt.")
            st.markdown(
                """
                <div class="journey">
                  <div class="journey-step"><div class="journey-index">01 · DETECT</div>
                    <div class="journey-name">Metrics</div><div class="journey-copy">Nhận diện cửa sổ, tail latency, error và cost bất thường.</div></div>
                  <div class="journey-step"><div class="journey-index">02 · LOCALIZE</div>
                    <div class="journey-name">Traces</div><div class="journey-copy">So sánh agent.run, rag.retrieve và llm.generate để khoanh vùng.</div></div>
                  <div class="journey-step"><div class="journey-index">03 · PROVE</div>
                    <div class="journey-name">Logs</div><div class="journey-copy">Dùng correlation ID và structured fields để chốt root cause.</div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with right:
        with st.container(border=True):
            panel_intro("Live context", "Current run", "Dữ liệu lấy trực tiếp từ workspace.")
            st.write(f"**Latest event**  \\n+{latest_event_time(frame)}")
            st.write(f"**Prompt route**  \\n+`{os.getenv('LANGFUSE_PROMPT_NAME', 'day13-chat')}:{os.getenv('LANGFUSE_PROMPT_LABEL', 'production')}`")
            active = [name for name, enabled in health.get("incidents", {}).items() if enabled] if api_ok else []
            st.write(f"**Active incidents**  \\n+{', '.join(active) if active else 'None'}")
            st.link_button("Open FastAPI docs ↗", f"{API_BASE_URL}/docs", width="stretch")

    st.write("")
    st.subheader("What this demo proves")
    cards = st.columns(3)
    items = [
        ("Structured telemetry", "Correlation IDs, enriched JSON logs và recursive PII scrubbing."),
        ("Managed AI lifecycle", "Langfuse prompt versions, labels, nested traces, token và cost metadata."),
        ("Operational readiness", "SLO thresholds, symptom-based alerts, runbooks và incident injection."),
    ]
    for column, (title, copy) in zip(cards, items):
        with column:
            with st.container(border=True):
                st.markdown(f"#### {title}")
                st.caption(copy)


def render_chat(api_ok: bool) -> None:
    st.markdown('<div class="eyebrow">Live experience</div>', unsafe_allow_html=True)
    st.title("Chat with the observable agent")
    st.caption("Mỗi câu hỏi tạo một correlation ID, trace ID, token/cost record và quality proxy.")

    config_col, chat_col, inspect_col = st.columns([0.85, 1.8, 1], gap="large")
    with config_col:
        with st.container(border=True):
            panel_intro("Request context", "Runtime controls", "Context này được bind vào log và trace.")
            user_id = st.text_input("Demo user", value="ui-demo-user")
            session_id = st.text_input(
                "Session ID",
                value=st.session_state.setdefault("demo_session", f"ui-{uuid.uuid4().hex[:8]}"),
            )
            feature = st.selectbox("Feature", ["monitoring", "qa", "summary", "refund"])
            st.markdown(
                f'<span class="pill"><span class="dot{"" if api_ok else " off"}"></span>'
                f'{"Ready to send" if api_ok else "Start FastAPI first"}</span>',
                unsafe_allow_html=True,
            )
            if st.button("Clear conversation", width="stretch"):
                st.session_state.messages = []
                st.session_state.last_response = None
                st.rerun()

    with chat_col:
        with st.container(border=True):
            messages = st.session_state.setdefault("messages", [])
            if not messages:
                st.info("Try: “Explain how metrics, traces and logs work together.”")
            for message in messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            prompt = st.chat_input("Ask the observable agent…", disabled=not api_ok)
            if prompt:
                messages.append({"role": "user", "content": prompt})
                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/chat",
                        json={
                            "user_id": user_id,
                            "session_id": session_id,
                            "feature": feature,
                            "message": prompt,
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    messages.append({"role": "assistant", "content": payload["answer"]})
                    st.session_state.last_response = payload
                    st.rerun()
                except Exception as exc:
                    st.error(f"Request failed: {type(exc).__name__}")

    with inspect_col:
        with st.container(border=True):
            panel_intro("Request inspector", "Latest response", "Operational metadata returned by the API.")
            response = st.session_state.get("last_response")
            if not response:
                st.caption("Send a message to populate live telemetry.")
            else:
                st.metric("Latency", f"{response['latency_ms']} ms")
                c1, c2 = st.columns(2)
                c1.metric("Tokens in", response["tokens_in"])
                c2.metric("Tokens out", response["tokens_out"])
                st.metric("Cost", f"${response['cost_usd']:.6f}")
                st.metric("Quality", f"{response['quality_score']:.2f}")
                st.caption("Correlation ID")
                st.markdown(f'<div class="trace-chip">{html.escape(response["correlation_id"])}</div>', unsafe_allow_html=True)
                st.caption("Trace ID")
                st.markdown(
                    f'<div class="trace-chip">{html.escape(response.get("trace_id") or "pending")}</div>',
                    unsafe_allow_html=True,
                )


def render_metrics(minutes: int) -> None:
    st.markdown('<div class="eyebrow">Signal explorer</div>', unsafe_allow_html=True)
    st.title("AI observability dashboard")
    st.caption("Nguồn chuẩn: `data/logs.jsonl` · Threshold lấy từ `config/dashboard.yaml`.")
    frame, series, snap = load_dashboard_data(minutes)
    if frame.empty:
        st.warning("No log events in this window. Start the API and send a few chat requests.")
        return

    panels = {panel["id"]: panel for panel in DASHBOARD_CONFIG["dashboard"]["panels"]}
    control_left, control_right, control_note = st.columns([1, 1, 3])
    with control_left:
        if st.button("Capture baseline", width="stretch", type="primary"):
            st.session_state.metric_baseline = asdict(snap)
            st.session_state.metric_baseline_time = latest_event_time(frame)
            st.rerun()
    with control_right:
        if st.button("Clear baseline", width="stretch", disabled="metric_baseline" not in st.session_state):
            st.session_state.pop("metric_baseline", None)
            st.session_state.pop("metric_baseline_time", None)
            st.rerun()
    baseline = st.session_state.get("metric_baseline")
    with control_note:
        if baseline:
            st.info(f"Baseline captured at {st.session_state.get('metric_baseline_time')} · deltas below compare against it.")
        else:
            st.caption("Capture a clean baseline before enabling an incident; then return here to show before/after deltas.")

    def note_with_delta(note: str, field: str, current: float, *, decimals: int = 1) -> str:
        if not baseline:
            return note
        delta = current - float(baseline.get(field, 0))
        return f"{note} · Δ {delta:+.{decimals}f}"

    top = st.columns(6)
    values = [
        ("P95 latency", f"{snap.latency_p95:.0f} ms", note_with_delta(f"≤ {panels['latency']['threshold']['value']} ms", "latency_p95", snap.latency_p95, decimals=0), snap.latency_p95 <= 3000),
        ("Traffic", f"{snap.request_count}", note_with_delta(f"{snap.request_rate_per_minute:.1f} req/min", "request_count", snap.request_count, decimals=0), True),
        ("Error rate", f"{snap.error_rate_pct:.2f}%", note_with_delta("SLO ≤ 2%", "error_rate_pct", snap.error_rate_pct, decimals=2), snap.error_rate_pct <= 2),
        ("Cost", f"${snap.total_cost_usd:.4f}", note_with_delta("Window total", "total_cost_usd", snap.total_cost_usd, decimals=4), snap.total_cost_usd <= 2.5),
        ("Tokens", f"{snap.tokens_in_total + snap.tokens_out_total:,}", note_with_delta(f"{snap.tokens_in_total:,} in · {snap.tokens_out_total:,} out", "tokens_out_total", snap.tokens_out_total, decimals=0), True),
        ("Quality", f"{snap.quality_avg:.2f}", note_with_delta("Target ≥ 0.75", "quality_avg", snap.quality_avg, decimals=2), snap.quality_avg >= 0.75),
    ]
    for column, (label, value, note, good) in zip(top, values):
        with column:
            metric_card(label, value, note, good=good)

    st.caption(f"Last event: {latest_event_time(frame)} · Window: {minutes} minutes · Auto-refresh: 30 seconds")
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            panel_intro("01 · Latency", "Tail latency", "P50 / P95 / P99 in milliseconds · red line = P95 SLO")
            st.altair_chart(
                line_chart(series, ["latency_p50", "latency_p95", "latency_p99"], ["P50", "P95", "P99"],
                           ["#22d3ee", "#8b5cf6", "#fbbf24"], unit_title="ms", threshold=3000),
                width="stretch",
            )
        with st.container(border=True):
            panel_intro("03 · Errors", "Error pressure", "Error rate by minute · SLO ≤ 2%")
            st.altair_chart(
                line_chart(series, ["error_rate_pct"], ["Error rate"], ["#fb7185"], unit_title="percent", threshold=2),
                width="stretch",
            )
        with st.container(border=True):
            panel_intro("05 · Tokens", "Token volume", "Input and output token totals by minute")
            st.altair_chart(
                line_chart(series, ["tokens_in", "tokens_out"], ["Input", "Output"], ["#22d3ee", "#a78bfa"], unit_title="tokens"),
                width="stretch",
            )
    with right:
        with st.container(border=True):
            panel_intro("02 · Traffic", "Request traffic", "Count of request_received events per minute")
            st.altair_chart(bar_chart(series, "requests", "#22d3ee", unit_title="requests/min"), width="stretch")
        with st.container(border=True):
            panel_intro("04 · Cost", "Cost over time", "Generation cost summed by minute in USD")
            st.altair_chart(bar_chart(series, "cost_usd", "#8b5cf6", unit_title="USD"), width="stretch")
        with st.container(border=True):
            panel_intro("06 · Quality", "Quality proxy", "Heuristic score · green target line = 0.75")
            st.altair_chart(
                line_chart(series, ["quality"], ["Quality"], ["#34d399"], unit_title="score", threshold=0.75),
                width="stretch",
            )


def render_operations(api_ok: bool, health: dict[str, Any]) -> None:
    st.markdown('<div class="eyebrow">Operations</div>', unsafe_allow_html=True)
    st.title("Incident control room")
    st.caption("Bật scenario, quan sát tín hiệu thay đổi, sau đó điều tra Metrics → Traces → Logs.")

    incidents = health.get("incidents", {}) if api_ok else {}
    cols = st.columns(3)
    descriptions = {
        "rag_slow": "Inject 2.5s retrieval delay; P95 and rag.retrieve duration should spike.",
        "tool_fail": "Raise vector-store timeout; error rate and request_failed should increase.",
        "cost_spike": "Multiply output tokens; token and cost panels should rise.",
    }
    for column, name in zip(cols, ["rag_slow", "tool_fail", "cost_spike"]):
        with column:
            with st.container(border=True):
                enabled = bool(incidents.get(name))
                st.markdown(f"### {name.replace('_', ' ').title()}")
                st.caption(descriptions[name])
                st.markdown(
                    f'<span class="pill"><span class="dot{" off" if not enabled else ""}"></span>'
                    f'{"Enabled" if enabled else "Disabled"}</span>',
                    unsafe_allow_html=True,
                )
                action = "disable" if enabled else "enable"
                if st.button(f"{action.title()} scenario", key=f"incident-{name}", disabled=not api_ok, width="stretch"):
                    try:
                        result = httpx.post(f"{API_BASE_URL}/incidents/{name}/{action}", timeout=5.0)
                        result.raise_for_status()
                        st.success(f"{name} {action}d")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Control failed: {type(exc).__name__}")

    st.write("")
    active_incidents = [name for name, enabled in incidents.items() if enabled]
    selected_index = ["rag_slow", "tool_fail", "cost_spike"].index(active_incidents[0]) if active_incidents else 0
    load_col, flow_col = st.columns([0.75, 2], gap="large")
    with load_col:
        with st.container(border=True):
            panel_intro("Demo accelerator", "Generate observed traffic", "Run safe requests after enabling a scenario.")
            scenario = st.selectbox("Investigation scenario", ["rag_slow", "tool_fail", "cost_spike"], index=selected_index)
            burst_count = st.slider("Requests", 3, 8, 5)
            if st.button("Run demo burst", type="primary", disabled=not api_ok, width="stretch"):
                with st.spinner(f"Sending {burst_count} observable requests…"):
                    st.session_state.demo_burst = run_demo_burst(burst_count, scenario)
                    st.session_state.demo_scenario = scenario
                st.success("Traffic generated. Open Metrics to compare against the captured baseline.")
            if st.session_state.get("demo_burst"):
                st.dataframe(pd.DataFrame(st.session_state.demo_burst), width="stretch", hide_index=True)
    with flow_col:
        with st.container(border=True):
            playbook = INCIDENT_PLAYBOOKS[scenario]
            panel_intro("Required narrative", "Metric → Trace → Log → Root cause → Fix → Prevention", f"Live playbook for {scenario}.")
            st.markdown(
                f"""
                <div class="flow-grid">
                  <div class="flow-node"><b>01 · Metric</b><span>{html.escape(playbook['metric'])}</span></div>
                  <div class="flow-node"><b>02 · Trace</b><span>{html.escape(playbook['trace'])}</span></div>
                  <div class="flow-node"><b>03 · Log</b><span>{html.escape(playbook['log'])}</span></div>
                  <div class="flow-node"><b>04 · Root cause</b><span>{html.escape(playbook['root'])}</span></div>
                  <div class="flow-node"><b>05 · Fix</b><span>{html.escape(playbook['fix'])}</span></div>
                  <div class="flow-node"><b>06 · Prevention</b><span>{html.escape(playbook['prevent'])}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    alert_col, log_col = st.columns([1, 1.7], gap="large")
    with alert_col:
        st.subheader("SLO-backed alerts")
        for alert in ALERT_CONFIG.get("alerts", []):
            with st.container(border=True):
                severity = str(alert.get("severity", "unknown")).upper()
                st.markdown(f"**{alert.get('name')}** · `{severity}`")
                st.caption(alert.get("condition", ""))
                st.write(alert.get("user_impact", ""))
                st.caption(f"Owner: {alert.get('owner')} · Runbook: {alert.get('runbook')}")
    with log_col:
        st.subheader("Recent structured events")
        records = read_jsonl(LOG_PATH)
        frame = records_frame(records)
        correlation_filter = st.text_input("Filter by correlation ID", placeholder="req-1234abcd")
        if correlation_filter and "correlation_id" in frame:
            frame = frame[frame["correlation_id"].astype(str) == correlation_filter.strip()]
        fields = [
            field for field in [
                "ts", "level", "event", "correlation_id", "feature", "latency_ms", "error_type", "trace_id",
                "payload.message_preview", "payload.query_preview", "payload.answer_preview",
            ]
            if field in frame
        ]
        if frame.empty:
            st.info("No logs yet.")
        else:
            st.dataframe(frame[fields].tail(30).sort_values("ts", ascending=False), width="stretch", hide_index=True)

        quality = analyze_log_quality(records)
        with st.container(border=True):
            panel_intro("Security proof", "PII redaction", "Independent regex scan over rendered JSON logs.")
            p1, p2, p3 = st.columns(3)
            p1.metric("Raw PII hits", len(quality["pii_hits"]))
            p2.metric("Log score", f"{quality['score']}/100")
            p3.metric("Correlation IDs", quality["correlation_ids"])
            samples = pd.DataFrame(
                [
                    {"PII type": "Email", "Stored preview": scrub_text("Contact student@vinuni.edu.vn")},
                    {"PII type": "Phone", "Stored preview": scrub_text("Contact 090 123 4567")},
                    {"PII type": "Credit card", "Stored preview": scrub_text("Card 4111 1111 1111 1111")},
                ]
            )
            st.dataframe(samples, width="stretch", hide_index=True)

    with st.expander("Audit trail"):
        audit = records_frame(read_jsonl(AUDIT_PATH))
        if audit.empty:
            st.caption("No audit events yet.")
        else:
            columns = [field for field in ["ts", "action", "actor", "correlation_id", "details.name"] if field in audit]
            st.dataframe(audit[columns].sort_values("ts", ascending=False), width="stretch", hide_index=True)


def render_evidence() -> None:
    st.markdown('<div class="eyebrow">Delivery map</div>', unsafe_allow_html=True)
    st.title("What has been completed")
    st.caption("Một view dành cho demo: contract, implementation và runtime proof đặt cạnh nhau.")

    records = read_jsonl(LOG_PATH)
    frame = records_frame(records)
    snap = dashboard_snapshot(frame)
    log_quality = analyze_log_quality(records)
    try:
        load_dashboard_config(REPO_ROOT / "config" / "dashboard.yaml")
        dashboard_status = "6 / 6"
    except DashboardConfigError:
        dashboard_status = "Invalid"
    test_summary = os.getenv("UI_TEST_SUMMARY", "Run via scripts/run_demo.py")
    checks = [
        ("JSON logging", f"{log_quality['score']} / 100", "Required fields, enrichment and correlation IDs"),
        ("PII protection", f"{len(log_quality['pii_hits'])} leaks", "Independent scan of rendered JSON logs"),
        ("Nested tracing", f"{int(frame.get('trace_id', pd.Series(dtype=object)).dropna().nunique())} linked", "agent.run → rag.retrieve + llm.generate"),
        ("Test suite", test_summary, "Current preflight result from the demo launcher"),
        ("Dashboard contract", dashboard_status, "Latency, traffic, errors, cost, tokens and quality"),
        ("Alert readiness", f"{len(ALERT_CONFIG.get('alerts', []))} rules", "Latency, error and cost symptoms with runbooks"),
    ]
    rows = st.columns(3)
    for index, (name, value, detail) in enumerate(checks):
        with rows[index % 3]:
            metric_card(name, value, detail)
        if index == 2:
            rows = st.columns(3)

    st.write("")
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        with st.container(border=True):
            panel_intro("Runtime proof", "Observed in local logs", "Live values, not presentation-only placeholders.")
            proof = pd.DataFrame(
                [
                    {"Signal": "Requests", "Value": str(snap.request_count), "Source": "request_received"},
                    {"Signal": "Responses", "Value": str(snap.response_count), "Source": "response_sent"},
                    {"Signal": "Unique trace links", "Value": str(int(frame.get("trace_id", pd.Series(dtype=object)).dropna().nunique())), "Source": "trace_id"},
                    {"Signal": "Error events", "Value": str(snap.error_count), "Source": "request_failed"},
                    {"Signal": "Total tokens", "Value": str(snap.tokens_in_total + snap.tokens_out_total), "Source": "tokens_in/out"},
                    {"Signal": "Total cost", "Value": f"${snap.total_cost_usd:.6f}", "Source": "cost_usd"},
                ]
            )
            st.dataframe(proof, width="stretch", hide_index=True)
    with right:
        with st.container(border=True):
            panel_intro("Repository contract", "Submission readiness", "Machine-checkable artifacts already present.")
            artifacts = [
                ("Log schema", REPO_ROOT / "config" / "logging_schema.json"),
                ("Dashboard config", REPO_ROOT / "config" / "dashboard.yaml"),
                ("SLOs", REPO_ROOT / "config" / "slo.yaml"),
                ("Alert rules", REPO_ROOT / "config" / "alert_rules.yaml"),
                ("Report", REPO_ROOT / "submission" / "REPORT.md"),
            ]
            for label, path in artifacts:
                st.write(f"{'✓' if path.exists() else '○'} **{label}** · `{path.relative_to(REPO_ROOT)}`")
            st.link_button("Open Langfuse ↗", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"), width="stretch")

    st.write("")
    with st.container(border=True):
        refresh_col, copy_col = st.columns([1, 3])
        with refresh_col:
            if st.button("Refresh Langfuse snapshot", width="stretch"):
                with st.spinner("Reading prompt labels and latest traces…"):
                    try:
                        st.session_state.langfuse_snapshot = fetch_langfuse_snapshot()
                        st.session_state.langfuse_error = None
                    except Exception as exc:
                        st.session_state.langfuse_error = f"{type(exc).__name__}: {exc}"
        with copy_col:
            panel_intro("External runtime", "Langfuse snapshot", "Secrets stay server-side; only safe trace metadata is rendered.")
        if st.session_state.get("langfuse_error"):
            st.error(st.session_state.langfuse_error)
        snapshot = st.session_state.get("langfuse_snapshot")
        if snapshot:
            labels = snapshot["labels"]
            label_cols = st.columns(4)
            label_cols[0].metric("Latest traces", snapshot["count"])
            label_cols[1].metric("Baseline", f"v{labels.get('baseline')}")
            label_cols[2].metric("Candidate", f"v{labels.get('candidate')}")
            label_cols[3].metric("Production", f"v{labels.get('production')}")
            traces = pd.DataFrame(snapshot["traces"])
            if not traces.empty:
                st.dataframe(traces, width="stretch", hide_index=True)
        else:
            st.caption("Click refresh during the demo to show prompt labels and the latest 20 trace IDs.")

    with st.expander("SLO contract"):
        slis = SLO_CONFIG.get("slis", {})
        table = [
            {"SLI": name, "Objective": values.get("objective"), "Target %": values.get("target")}
            for name, values in slis.items()
        ]
        st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)


inject_styles()
api_ok, health = get_health()

with st.sidebar:
    st.markdown("## ◈ SignalOps")
    st.caption("AI Reliability Studio")
    st.write("")
    page = st.radio(
        "Workspace",
        ["Overview", "Live Chat", "Metrics", "Operations", "Evidence"],
        label_visibility="collapsed",
    )
    st.divider()
    time_range = st.selectbox("Dashboard window", [15, 60, 360, 1440], index=1, format_func=lambda x: f"Last {x} min")
    st.caption(f"API · {API_BASE_URL}")
    st.caption(f"Data · {LOG_PATH.relative_to(REPO_ROOT)}")

if page == "Overview":
    render_overview(api_ok, health)
elif page == "Live Chat":
    render_chat(api_ok)
elif page == "Metrics":
    @st.fragment(run_every="30s")
    def live_metrics() -> None:
        render_metrics(time_range)

    live_metrics()
elif page == "Operations":
    render_operations(api_ok, health)
else:
    render_evidence()
