from __future__ import annotations

import html
import uuid

import httpx
import streamlit as st

from ui.components import panel_intro
from ui.settings import API_BASE_URL


def render_chat(api_ok: bool) -> None:
    st.markdown('<div class="eyebrow">TRẢI NGHIỆM TRỰC TIẾP</div>', unsafe_allow_html=True)
    st.title("Chat với observable agent")
    st.caption("Mỗi câu hỏi tạo một correlation ID, trace ID, token/cost record và quality proxy.")
    config_col, chat_col, inspect_col = st.columns([0.85, 1.8, 1], gap="large")
    with config_col, st.container(border=True):
        panel_intro("REQUEST CONTEXT", "Điều khiển runtime", "Context này được bind vào log và trace.")
        user_id = st.text_input("Người dùng demo", value="ui-demo-user")
        session_id = st.text_input("Session ID", value=st.session_state.setdefault("demo_session", f"ui-{uuid.uuid4().hex[:8]}"))
        feature = st.selectbox("Feature", ["monitoring", "qa", "summary", "refund"])
        st.markdown(
            f'<span class="pill"><span class="dot{"" if api_ok else " off"}"></span>'
            f'{"Sẵn sàng gửi" if api_ok else "Hãy khởi động FastAPI trước"}</span>',
            unsafe_allow_html=True,
        )
        if st.button("Xóa cuộc trò chuyện", width="stretch"):
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()

    with chat_col, st.container(border=True):
        messages = st.session_state.setdefault("messages", [])
        if not messages:
            st.info("Thử hỏi: “Metrics, Traces và Logs phối hợp với nhau như thế nào?”")
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        prompt = st.chat_input("Nhập câu hỏi cho observable agent…", disabled=not api_ok)
        if prompt:
            messages.append({"role": "user", "content": prompt})
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/chat",
                    json={"user_id": user_id, "session_id": session_id, "feature": feature, "message": prompt},
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                messages.append({"role": "assistant", "content": payload["answer"]})
                st.session_state.last_response = payload
                st.rerun()
            except Exception as exc:
                st.error(f"Request thất bại: {type(exc).__name__}")

    with inspect_col, st.container(border=True):
        panel_intro("REQUEST INSPECTOR", "Response gần nhất", "Operational metadata do API trả về.")
        response = st.session_state.get("last_response")
        if not response:
            st.caption("Gửi một tin nhắn để tạo live telemetry.")
            return
        st.metric("Latency", f"{response['latency_ms']} ms")
        c1, c2 = st.columns(2)
        c1.metric("Tokens in", response["tokens_in"])
        c2.metric("Tokens out", response["tokens_out"])
        st.metric("Cost", f"${response['cost_usd']:.6f}")
        st.metric("Quality", f"{response['quality_score']:.2f}")
        st.caption("Correlation ID")
        st.markdown(f'<div class="trace-chip">{html.escape(response["correlation_id"])}</div>', unsafe_allow_html=True)
        st.caption("Trace ID")
        st.markdown(f'<div class="trace-chip">{html.escape(response.get("trace_id") or "pending")}</div>', unsafe_allow_html=True)
