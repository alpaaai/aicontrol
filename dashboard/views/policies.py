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

CONDITION_EXAMPLES = {
    "tool_denylist — parameter match": '''{
  "blocked_tools": ["http_post", "http_request"],
  "tool_aliases": ["webhook", "http_get"],
  "parameter_match": {"url": "https://untrusted-*"}
}''',
    "tool_denylist — numeric": '''{
  "blocked_tools": ["approve_loan"],
  "numeric_conditions": [
    {"parameter": "loan_amount", "operator": "gt", "value": 500000}
  ]
}''',
    "tool_denylist — compound AND": '''{
  "blocked_tools": ["query_all_accounts"],
  "all_of": [
    {"parameter_match": {"filter": "null"}},
    {"numeric_conditions": [{"parameter": "limit", "operator": "gte", "value": 1000}]}
  ]
}''',
    "tool_denylist — compound OR": '''{
  "blocked_tools": ["read_customer_account"],
  "any_of": [
    {"parameter_match": {"account_id": "*"}},
    {"parameter_match": {"account_id": "null"}}
  ]
}''',
    "tool_denylist — temporal": '''{
  "blocked_tools": ["deploy_to_production"],
  "time_conditions": {
    "deny_days": [5, 6],
    "deny_hours": {"from": 9, "to": 17}
  }
}''',
    "tool_pattern": '''{
  "tool_name_contains": ["http_", "webhook", "external_"]
}''',
}

# All tool_denylist variants submit as "tool_denylist" to the API
RULE_TYPE_API_VALUE = {k: "tool_denylist" if "tool_denylist" in k else k
                       for k in CONDITION_EXAMPLES}
RULE_TYPE_API_VALUE["tool_pattern"] = "tool_pattern"


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
                try:
                    cond = json.loads(json.dumps(cond, default=str))
                except Exception:
                    pass
                st.json(cond)

    st.divider()

    # Persist expander open state across reruns so rule_type selectbox changes don't collapse it
    if "create_policy_expander_open" not in st.session_state:
        st.session_state["create_policy_expander_open"] = False

    # Display deferred feedback from the previous render cycle before the expander
    if "create_policy_feedback" in st.session_state:
        feedback = st.session_state.pop("create_policy_feedback")
        if feedback["type"] == "success":
            st.success(feedback["message"])
        else:
            st.error(feedback["message"])

    # Create new policy form — rule_type is OUTSIDE the form so placeholder updates on change
    with st.expander("Create Policy", expanded=st.session_state["create_policy_expander_open"]):
        st.session_state["create_policy_expander_open"] = True

        rule_type = st.selectbox(
            "Rule type",
            list(CONDITION_EXAMPLES.keys()),
            key="create_policy_rule_type",
        )
        placeholder = CONDITION_EXAMPLES.get(rule_type, "{}")

        with st.form("create_policy_form"):
            name = st.text_input("Name", placeholder="e.g. block_pii_export")
            description = st.text_input("Description", placeholder="Short description")
            st.markdown(f"**Rule type:** `{rule_type}`")
            action = st.selectbox("Action", ["deny", "review", "allow"])
            severity = st.selectbox("Severity", ["critical", "high", "medium", "low"])
            condition_raw = st.text_area(
                "Condition (JSON)",
                placeholder=placeholder,
                height=120,
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
                        "rule_type": RULE_TYPE_API_VALUE.get(rule_type, rule_type),
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
                            st.session_state["create_policy_feedback"] = {
                                "type": "success",
                                "message": f"Policy '{name}' created.",
                            }
                            st.session_state["create_policy_expander_open"] = False
                            st.rerun()
                        else:
                            st.error(f"API returned {resp.status_code}: {resp.text}")
                    except requests.RequestException as exc:
                        st.error(f"Request failed: {exc}")
