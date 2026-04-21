"""
AIControl — Revoke Agent
Deactivates the agent AND revokes its scoped token in one step.

Usage:
    python scripts/revoke_agent.py --name "loan-underwriting-agent"
    python scripts/revoke_agent.py --id <agent-uuid>
"""
import argparse
import os
import sys

import httpx

API_BASE = os.getenv("AICONTROL_URL", "http://localhost:8001")
ADMIN_TOKEN = os.getenv("AICONTROL_ADMIN_TOKEN")


def main() -> None:
    parser = argparse.ArgumentParser(description="Revoke an AIControl agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="Agent name")
    group.add_argument("--id", dest="agent_id", help="Agent UUID")
    args = parser.parse_args()

    if not ADMIN_TOKEN:
        print("Error: AICONTROL_ADMIN_TOKEN not set.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

    # Resolve agent_id from name if needed
    agent_id = args.agent_id
    agent_name = agent_id
    if args.name:
        resp = httpx.get(f"{API_BASE}/agents", headers=headers, timeout=10.0)
        if resp.status_code != 200:
            print(f"Error fetching agents: {resp.status_code} {resp.text}")
            sys.exit(1)
        agents = resp.json()
        match = next((a for a in agents if a["name"] == args.name), None)
        if not match:
            print(f"Agent '{args.name}' not found.")
            sys.exit(1)
        agent_id = match["id"]
        agent_name = args.name

    print(f"\nThis will deactivate agent '{agent_name}' and revoke its token.")
    confirm = input("Type 'revoke' to confirm: ").strip()
    if confirm != "revoke":
        print("Cancelled.")
        sys.exit(0)

    # Suspend agent via PUT
    resp = httpx.put(
        f"{API_BASE}/agents/{agent_id}",
        headers=headers,
        json={"status": "suspended"},
        timeout=10.0,
    )
    if resp.status_code != 200:
        print(f"Error deactivating agent: {resp.status_code} {resp.text}")
        sys.exit(1)
    print("Agent suspended.")

    # Revoke agent's scoped token
    resp = httpx.delete(
        f"{API_BASE}/agents/{agent_id}/token",
        headers=headers,
        timeout=10.0,
    )
    if resp.status_code == 200:
        count = resp.json().get("revoked", 0)
        print(f"Token revoked ({count} token(s)).")
    elif resp.status_code == 404:
        print("No active token found for this agent.")
    else:
        print(f"Warning: could not revoke token: {resp.status_code} {resp.text}")

    print(f"\nAgent '{agent_name}' fully offboarded.\n")


if __name__ == "__main__":
    main()
