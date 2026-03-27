"""Decision breakdown view — donut chart of allow/deny/review."""
import plotly.graph_objects as go
import streamlit as st

from dashboard.queries import get_decision_counts, get_audit_events


def render() -> None:
    st.header("Decision Breakdown")

    counts = get_decision_counts()
    total = sum(counts.values())

    if total == 0:
        st.info("No decisions recorded yet.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Allow", counts["allow"],
                delta=None, delta_color="normal")
    col2.metric("Deny", counts["deny"])
    col3.metric("Review", counts["review"])

    fig = go.Figure(data=[go.Pie(
        labels=["Allow", "Deny", "Review"],
        values=[counts["allow"], counts["deny"], counts["review"]],
        hole=0.5,
        marker_colors=["#22c55e", "#ef4444", "#f59e0b"],
    )])
    fig.update_layout(
        title="Decision Distribution",
        showlegend=True,
        height=400,
        margin=dict(t=40, b=0, l=0, r=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Recent decision trend table
    st.subheader("Recent Decisions")
    events = get_audit_events(limit=20)
    if events:
        for e in events[:10]:
            icon = {"allow": "🟢", "deny": "🔴", "review": "🟡"}.get(
                e["decision"].lower(), ""
            )
            st.write(
                f"{icon} **{e['tool_name']}** — {e['decision_reason']} "
                f"({e['agent_name']})"
            )
