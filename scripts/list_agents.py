"""
AIControl — List Agents
Shows all registered agents with their IDs and status.

Usage:
    python scripts/list_agents.py
"""
import os
import sys

import httpx

API_BASE = os.getenv("AICONTROL_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("AICONTROL_ADMIN_TOKEN")


def main() -> None:
    if not ADMIN_TOKEN:
        print("Error: AICONTROL_ADMIN_TOKEN not set.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    resp = httpx.get(f"{API_BASE}/agents", headers=headers, timeout=10.0)
    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}")
        sys.exit(1)

    agents = resp.json()

    if not agents:
        print("No agents registered.")
        return

    col_name = max(len(a["name"]) for a in agents)
    col_id = 36
    col_status = 12
    header = f"{'Name':<{col_name}}  {'ID':<{col_id}}  {'Status':<{col_status}}  Approved Tools"
    print(header)
    print("-" * len(header))

    for agent in agents:
        tools = ", ".join(agent.get("approved_tools", []))
        print(
            f"{agent['name']:<{col_name}}  "
            f"{agent['id']:<{col_id}}  "
            f"{agent.get('status', 'unknown'):<{col_status}}  "
            f"{tools}"
        )

    print(f"\n{len(agents)} agent(s) total.")


if __name__ == "__main__":
    main()
