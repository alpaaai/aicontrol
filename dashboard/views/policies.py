"""Policy list view."""
import pandas as pd
import streamlit as st

from dashboard.queries import get_policies

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def render() -> None:
    st.header("Active Policies")

    policies = get_policies()

    if not policies:
        st.info("No policies loaded. Check that the app started correctly.")
        return

    df = pd.DataFrame(policies)
    df["active"] = df["active"].map(lambda x: "✅ Active" if x else "❌ Inactive")

    st.dataframe(
        df[["name", "rule_type", "action", "severity", "active", "description"]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"{len(policies)} policies loaded")
