"""
AIControl — Agent Onboarding
Registers a new agent AND issues a scoped token in one step.

Usage:
    python scripts/onboard_agent.py \
        --name "loan-underwriting-agent" \
        --owner "lending-team" \
        --tools "query_credit_bureau,run_risk_model"

Output:
    Prints ready-to-paste env block with AICONTROL_TOKEN and AGENT_ID.
    Saves to .aicontrol/<agent-name>.env for reference.
"""
import argparse
import os
import sys
from pathlib import Path

import httpx

API_BASE = os.getenv("AICONTROL_URL", "http://localhost:8001")
ADMIN_TOKEN = os.getenv("AICONTROL_ADMIN_TOKEN")


def main() -> None:
    parser = argparse.ArgumentParser(description="Onboard a new AIControl agent")
    parser.add_argument("--name", required=True, help="Agent name (e.g. loan-underwriting-agent)")
    parser.add_argument("--owner", required=True, help="Owning team or person (e.g. lending-team)")
    parser.add_argument("--tools", required=True, help="Comma-separated list of approved tools")
    args = parser.parse_args()

    if not ADMIN_TOKEN:
        print("Error: AICONTROL_ADMIN_TOKEN environment variable not set.")
        print("Issue an admin token first:")
        print("  PYTHONPATH=. python scripts/issue_token.py --role admin --desc 'admin'")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    approved_tools = [t.strip() for t in args.tools.split(",")]

    # Step 1: Register agent
    print(f"Registering agent '{args.name}'...")
    resp = httpx.post(
        f"{API_BASE}/agents",
        headers=headers,
        json={
            "name": args.name,
            "owner": args.owner,
            "approved_tools": approved_tools,
        },
        timeout=10.0,
    )
    if resp.status_code != 201:
        print(f"Error registering agent: {resp.status_code} {resp.text}")
        sys.exit(1)

    agent = resp.json()
    agent_id = agent["id"]
    print(f"  Agent registered. ID: {agent_id}")

    # Step 2: Issue scoped token
    print(f"Issuing scoped token for '{args.name}'...")
    resp = httpx.post(
        f"{API_BASE}/tokens",
        headers=headers,
        json={
            "role": "agent",
            "description": args.name,
            "agent_id": agent_id,
        },
        timeout=10.0,
    )
    if resp.status_code != 200:
        print(f"Error issuing token: {resp.status_code} {resp.text}")
        sys.exit(1)

    token_data = resp.json()
    raw_token = token_data["token"]

    # Step 3: Print env block
    env_block = (
        f"# AIControl — {args.name}\n"
        f"AICONTROL_URL={API_BASE}\n"
        f"AICONTROL_TOKEN={raw_token}\n"
        f"AGENT_ID={agent_id}\n"
        f"AGENT_NAME={args.name}\n"
    )

    print("\n" + "=" * 60)
    print("Agent onboarded successfully. Add these to your .env:")
    print("=" * 60)
    print(env_block)

    # Step 4: Save to .aicontrol/<agent-name>.env
    env_dir = Path(".aicontrol")
    env_dir.mkdir(exist_ok=True)
    env_file = env_dir / f"{args.name}.env"
    env_file.write_text(env_block.strip())
    print(f"Also saved to: {env_file}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
