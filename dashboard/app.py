"""AIControl Dashboard — main Streamlit entry point."""
import streamlit as st

st.set_page_config(
    page_title="AIControl",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.views import audit_log, policies, agents, decisions, risk, tokens

VIEWS = {
    "Audit Log": audit_log,
    "Decision Breakdown": decisions,
    "Risk Score": risk,
    "Policies": policies,
    "Agents": agents,
    "Tokens": tokens,
}

with st.sidebar:
    st.title("🛡️ AIControl")
    st.caption("AI Agent Governance")
    st.divider()
    selected = st.radio("View", list(VIEWS.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("Auto-refresh every 30s")

# Auto-refresh
import time
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

VIEWS[selected].render()
