"""Policy list view."""
import json
import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from dashboard.queries import get_policies

load_dotenv()

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_API_BASE = os.environ.get("AICONTROL_API_URL", "http://localhost:8001")
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


def render() -> None:
    st.header("Active Policies")

    policies = get_policies()

    if not policies:
        st.info("No policies loaded. Check that the app started correctly.")
    else:
        df = pd.DataFrame(policies)
        df["active"] = df["active"].map(lambda x: "Active" if x else "Inactive")

        # Row selection for condition detail
        selection = st.dataframe(
            df[["name", "rule_type", "condition", "action", "severity", "active", "description"]],
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )
        st.caption(f"{len(policies)} policies loaded")

        selected_rows = selection.selection.get("rows", [])
        if selected_rows:
            row = df.iloc[selected_rows[0]]
            st.divider()
            st.subheader(f"Policy: {row['name']}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Rule type:** {row['rule_type']}")
                st.markdown(f"**Action:** {row['action']}")
                st.markdown(f"**Severity:** {row['severity']}")
            with c2:
                st.markdown(f"**Status:** {row['active']}")
                st.markdown(f"**Description:** {row.get('description') or '—'}")
            cond = row.get("condition")
            if cond:
                st.markdown("**Condition:**")
                if isinstance(cond, str):
                    try:
                        cond = json.loads(cond)
                    except Exception:
                        pass
                st.json(cond)

    st.divider()

    # Create new policy form
    with st.expander("Create Policy", expanded=False):
        with st.form("create_policy_form"):
            name = st.text_input("Name", placeholder="e.g. block_pii_export")
            description = st.text_input("Description", placeholder="Short description")
            rule_type = st.selectbox("Rule type", ["tool_blacklist", "parameter_match", "rate_limit"])
            action = st.selectbox("Action", ["deny", "review", "allow"])
            severity = st.selectbox("Severity", ["critical", "high", "medium", "low"])
            condition_raw = st.text_area(
                "Condition (JSON)",
                placeholder='{"tool_name": "export_records"}',
                height=100,
            )
            compliance_raw = st.text_input(
                "Compliance frameworks (comma-separated)",
                placeholder="e.g. HIPAA, SOC2",
            )
            submitted = st.form_submit_button("Create Policy")

        if submitted:
            if not name.strip():
                st.error("Name is required.")
            elif not _ADMIN_TOKEN:
                st.error("ADMIN_TOKEN environment variable not set.")
            else:
                try:
                    condition = json.loads(condition_raw) if condition_raw.strip() else {}
                except json.JSONDecodeError as exc:
                    st.error(f"Condition is not valid JSON: {exc}")
                    condition = None

                if condition is not None:
                    frameworks = [f.strip() for f in compliance_raw.split(",") if f.strip()]
                    payload = {
                        "name": name.strip(),
                        "description": description.strip(),
                        "rule_type": rule_type,
                        "action": action,
                        "severity": severity,
                        "condition": condition,
                        "compliance_frameworks": frameworks,
                    }
                    try:
                        resp = requests.post(
                            f"{_API_BASE}/policies",
                            json=payload,
                            headers={"Authorization": f"Bearer {_ADMIN_TOKEN}"},
                            timeout=10,
                        )
                        if resp.status_code == 201:
                            st.success(f"Policy '{name}' created.")
                            st.rerun()
                        else:
                            st.error(f"API returned {resp.status_code}: {resp.text}")
                    except requests.RequestException as exc:
                        st.error(f"Request failed: {exc}")
