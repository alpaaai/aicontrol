"""Agent registry view."""
import pandas as pd
import streamlit as st

from dashboard.queries import get_agents

STATUS_ICONS = {
    "approved": "✅",
    "unregistered": "⚪",
    "suspended": "🔴",
}


def render() -> None:
    st.header("Registered Agents")

    agents = get_agents()

    if not agents:
        st.info("No agents registered yet. Run the seed script.")
        return

    df = pd.DataFrame(agents)
    df["status"] = df["status"].map(
        lambda s: f"{STATUS_ICONS.get(s, '')} {s}"
    )
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    st.dataframe(
        df[["name", "owner", "status", "framework", "model_version", "created_at"]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"{len(agents)} agents registered")
