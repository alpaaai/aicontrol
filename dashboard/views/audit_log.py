"""Audit event log view."""
import pandas as pd
import streamlit as st

from dashboard.queries import get_audit_events

DECISION_COLORS = {
    "allow": "🟢",
    "deny": "🔴",
    "review": "🟡",
}


def render() -> None:
    st.header("Audit Event Log")

    col1, col2 = st.columns([3, 1])
    with col1:
        limit = st.slider("Max events", 10, 500, 100, step=10)
    with col2:
        if st.button("Refresh"):
            st.rerun()

    events = get_audit_events(limit=limit)

    if not events:
        st.info("No audit events yet. Run the seed script and call /intercept.")
        return

    df = pd.DataFrame(events)
    df["decision"] = df["decision"].map(
        lambda d: f"{DECISION_COLORS.get(d.lower(), '')} {d}"
    )
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    st.dataframe(
        df[[
            "created_at", "agent_name", "tool_name",
            "decision", "decision_reason", "duration_ms", "risk_delta"
        ]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Showing {len(events)} events")
