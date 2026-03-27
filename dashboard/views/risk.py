"""Risk score over time view — line chart per session."""
import plotly.express as px
import pandas as pd
import streamlit as st

from dashboard.queries import get_risk_scores


def render() -> None:
    st.header("Risk Score Over Time")

    rows = get_risk_scores()

    if not rows:
        st.info("No session data yet. Run the demo script to generate events.")
        return

    df = pd.DataFrame(rows)
    df["session_id"] = df["session_id"].astype(str).str[:8]  # truncate UUID
    df["created_at"] = pd.to_datetime(df["created_at"])

    fig = px.line(
        df,
        x="sequence_number",
        y="cumulative_risk",
        color="session_id",
        title="Cumulative Risk Score per Session",
        labels={
            "sequence_number": "Tool Call #",
            "cumulative_risk": "Cumulative Risk",
            "session_id": "Session",
        },
        markers=True,
    )
    fig.update_layout(height=450, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Showing {df['session_id'].nunique()} session(s), "
        f"{len(df)} data points"
    )
