from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
repo_root = str(REPO_ROOT)
while repo_root in sys.path:
    sys.path.remove(repo_root)
sys.path.insert(0, repo_root)

# Streamlit may run this entrypoint under the name ``app``. Remove that alias
# so imports resolve to the backend package at <repo>/app/.
streamlit_app_alias = sys.modules.get("app")
if streamlit_app_alias is not None:
    alias_path = getattr(streamlit_app_alias, "__file__", None)
    if alias_path and Path(alias_path).resolve() == Path(__file__).resolve():
        del sys.modules["app"]

import streamlit as st  # noqa: E402

from ui.pages.chat import render_chat  # noqa: E402
from ui.pages.evidence import render_evidence  # noqa: E402
from ui.pages.metrics import render_metrics  # noqa: E402
from ui.pages.operations import render_operations  # noqa: E402
from ui.pages.overview import render_overview  # noqa: E402
from ui.services import get_health  # noqa: E402
from ui.settings import API_BASE_URL, LOG_PATH  # noqa: E402
from ui.theme import inject_styles  # noqa: E402


st.set_page_config(
    page_title="SignalOps · AI Reliability Studio",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
api_ok, health = get_health()

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
          <div class="brand-mark">SO</div>
          <div><div class="brand-name">SignalOps</div><div class="brand-plan">AI Reliability Studio</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Workspace",
        ["Overview", "Live Chat", "Metrics", "Operations", "Evidence"],
        label_visibility="collapsed",
    )
    st.divider()
    time_range = st.selectbox("Dashboard window", [15, 60, 360, 1440], index=1, format_func=lambda value: f"Last {value} min")
    st.caption(f"API · {API_BASE_URL}")
    st.caption(f"Data · {LOG_PATH.relative_to(REPO_ROOT)}")

if page == "Overview":
    render_overview(api_ok, health)
elif page == "Live Chat":
    render_chat(api_ok)
elif page == "Metrics":
    render_metrics(time_range)
elif page == "Operations":
    render_operations(api_ok, health)
else:
    render_evidence()
