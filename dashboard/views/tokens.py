"""Token management view — issue and revoke API tokens."""
import os
import subprocess
import sys
import pandas as pd
import streamlit as st

from dashboard.queries import get_tokens


def _run_script(script: str, args: list[str]) -> tuple[bool, str]:
    """Run a management script via subprocess. Returns (success, output)."""
    env = {**os.environ, "APP_ENV": "production"}
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"] + args,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode == 0, result.stdout + result.stderr


def render() -> None:
    st.header("API Token Management")
    st.caption(
        "Tokens grant access to the AIControl API. "
        "Store them securely — shown once only."
    )

    # Issue new token
    with st.expander("Issue New Token", expanded=False):
        with st.form("issue_token_form"):
            role = st.selectbox("Role", ["agent", "admin"])
            desc = st.text_input(
                "Description", placeholder="e.g. Claims processing agent"
            )
            submitted = st.form_submit_button("Issue Token")

        if submitted:
            if not desc.strip():
                st.error("Description is required.")
            else:
                success, output = _run_script(
                    "issue_token.py", ["--role", role, "--desc", desc]
                )
                if success:
                    st.success("Token issued successfully.")
                    st.code(output, language=None)
                    st.warning("Copy this token now — it will not be shown again.")
                else:
                    st.error(f"Failed to issue token:\n{output}")

    st.divider()

    # Token table
    st.subheader("Active Tokens")
    if st.button("Refresh"):
        st.rerun()

    tokens = get_tokens()
    if not tokens:
        st.info("No tokens issued yet.")
        return

    df = pd.DataFrame(tokens)
    df["id"] = df["id"].astype(str)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    active = df[df["revoked"] == False]
    revoked_df = df[df["revoked"] == True]

    st.dataframe(
        active[["id", "role", "description", "created_at"]],
        use_container_width=True,
        hide_index=True,
    )

    # Revoke form
    if not active.empty:
        st.divider()
        st.subheader("Revoke Token")
        with st.form("revoke_form"):
            options = {
                f"{r['description']} ({r['role']})": r["id"]
                for _, r in active.iterrows()
            }
            selected = st.selectbox("Select token to revoke", list(options.keys()))
            confirmed = st.checkbox("I confirm I want to revoke this token")
            revoke_submitted = st.form_submit_button("Revoke", type="primary")

        if revoke_submitted:
            if not confirmed:
                st.warning("Check the confirmation box to proceed.")
            else:
                success, output = _run_script(
                    "revoke_token.py", ["--id", options[selected]]
                )
                if success:
                    st.success(f"Revoked: {selected}")
                    st.rerun()
                else:
                    st.error(f"Failed:\n{output}")

    if not revoked_df.empty:
        with st.expander(f"Revoked tokens ({len(revoked_df)})"):
            st.dataframe(
                revoked_df[["id", "role", "description", "created_at"]],
                use_container_width=True,
                hide_index=True,
            )
