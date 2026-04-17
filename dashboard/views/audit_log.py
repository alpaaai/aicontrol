"""Audit event log view."""
import json
import pandas as pd
import streamlit as st

from dashboard.queries import get_audit_events

DECISION_ICON = {
    "allow": "✓",
    "deny": "✗",
    "review": "⚑",
}


def render() -> None:
    st.header("Audit Event Log")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        limit = st.slider("Max events", 10, 500, 200, step=10)
    with col2:
        agent_filter = st.text_input("Filter by agent", placeholder="e.g. crm-automation-agent")
    with col3:
        st.write("")
        if st.button("Refresh"):
            st.rerun()

    events = get_audit_events(limit=limit)

    if not events:
        st.info("No audit events yet. Run a demo script to generate events.")
        return

    df = pd.DataFrame(events)
    df["id"] = df["id"].astype(str)
    df["session_id"] = df["session_id"].astype(str)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    if agent_filter:
        df = df[df["agent_name"].str.contains(agent_filter, case=False, na=False)]

    if df.empty:
        st.info("No events match the filter.")
        return

    # Build display-friendly parameters summary
    def _params_summary(params) -> str:
        if not params:
            return "—"
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                return params
        full = ", ".join(f"{k}={v}" for k, v in params.items())
        return full[:120] + "…" if len(full) > 120 else full

    df["parameters"] = df["tool_parameters"].apply(_params_summary)
    df["decision_icon"] = df["decision"].map(
        lambda d: f"{DECISION_ICON.get(str(d).lower(), '?')} {d}"
    )

    display_cols = [
        "created_at", "agent_name", "tool_name", "parameters",
        "decision_icon", "decision_reason", "duration_ms",
    ]

    # Row selection for detail panel (Tasks 3+4)
    event_selection = st.dataframe(
        df[display_cols].rename(columns={"decision_icon": "decision"}),
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
    )

    st.caption(f"Showing {len(df)} of {len(events)} events")

    # Detail panel for selected row
    selected_rows = event_selection.selection.get("rows", [])
    if selected_rows:
        row = df.iloc[selected_rows[0]]
        st.divider()
        st.subheader("Event Detail")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**ID:** `{row['id']}`")
            st.markdown(f"**Session:** `{row['session_id']}`")
            st.markdown(f"**Agent:** {row['agent_name']}")
            st.markdown(f"**Tool:** `{row['tool_name']}`")
        with c2:
            st.markdown(f"**Decision:** {row['decision_icon']}")
            st.markdown(f"**Reason:** {row['decision_reason'] or '—'}")
            st.markdown(f"**Policy:** {row.get('policy_name') or '—'}")
            st.markdown(f"**Duration:** {row['duration_ms']} ms")

        params = row["tool_parameters"] or {}
        normalized = json.loads(json.dumps(params, default=str))
        st.markdown("**Parameters:**")
        st.json(normalized)
