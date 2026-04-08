#!/usr/bin/env python3
"""
AIControl Demo — Banking / Lending
Agent: loan-underwriting-agent
Scenario: Reads loan applications, queries credit bureau, runs risk model. Wildcard bulk access attempt is blocked.
"""

import asyncio
import httpx
import json
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

API_BASE = os.getenv("AICONTROL_API_URL", "http://localhost:8000")

SCENARIO = {
    "name": "Banking / Lending — Loan Underwriting Agent",
    "agent_name": "loan-underwriting-agent",
    "description": "Reads loan applications, queries credit bureau, runs risk model. Processes 400 files/day autonomously.",
    "incident_ref": "2024 financial services reconciliation agent exfiltration via wildcard query parameter",
}

TOOL_CALLS = [
    {
        "tool_name": "query_credit_bureau",
        "tool_parameters": {
            "applicant_id": "APP-2024-00847",
            "bureau": "equifax",
            "report_type": "full",
        },
        "label": "Pull credit report for loan applicant APP-2024-00847",
        "expected": "allow",
    },
    {
        "tool_name": "run_risk_model",
        "tool_parameters": {
            "applicant_id": "APP-2024-00847",
            "model": "lending_risk_v3",
            "loan_amount": 125000,
            "loan_type": "mortgage",
        },
        "label": "Run internal risk scoring model for applicant",
        "expected": "allow",
    },
    {
        "tool_name": "query_credit_bureau",
        "tool_parameters": {
            "applicant_id": "*",
            "bureau": "equifax",
            "report_type": "full",
        },
        "label": "Query credit bureau — wildcard applicant_id (bulk access attempt)",
        "expected": "deny",
    },
]


async def run_demo(token: str, mode: str = "walkthrough") -> None:
    session_id = "00000000-0000-0000-0000-000000000002"
    agent_id   = "00000000-0000-0000-0000-000000000001"

    console.print()
    console.print(Panel(
        f"[bold white]{SCENARIO['name']}[/bold white]\n"
        f"[dim]{SCENARIO['description']}[/dim]",
        style="blue", box=box.ROUNDED
    ))
    console.print()

    results = []

    for i, call in enumerate(TOOL_CALLS, 1):
        console.print(f"[dim]Step {i} of {len(TOOL_CALLS)}[/dim]")
        console.print(f"[bold]→ {call['label']}[/bold]")
        console.print(f"  Tool: [cyan]{call['tool_name']}[/cyan]")
        console.print(f"  Params: [dim]{json.dumps(call['tool_parameters'])}[/dim]")

        if mode == "walkthrough":
            console.print("\n  [dim]Press ENTER to send...[/dim]", end="")
            input()

        start = time.time()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/intercept",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "agent_name": SCENARIO["agent_name"],
                    "tool_name": call["tool_name"],
                    "tool_parameters": call["tool_parameters"],
                    "sequence_number": i,
                },
                timeout=10.0,
            )
        elapsed = (time.time() - start) * 1000

        data = resp.json()
        decision = data.get("decision", "error")

        color = {"allow": "green", "deny": "red", "review": "yellow"}.get(decision, "white")
        icon  = {"allow": "✓", "deny": "✗", "review": "⚑"}.get(decision, "?")

        console.print(
            f"\n  [{color}]{icon} DECISION: {decision.upper()}[/{color}]"
            f"  [dim]reason: {data.get('reason', '—')}  |  {elapsed:.0f}ms[/dim]"
        )
        console.print(f"  [dim]audit_event_id: {data.get('audit_event_id', '—')}[/dim]")

        results.append({
            "step": i,
            "tool": call["tool_name"],
            "decision": decision,
            "reason": data.get("reason"),
            "ms": f"{elapsed:.0f}",
            "expected": call["expected"],
        })

        if mode == "walkthrough":
            console.print()
            time.sleep(0.5)
        else:
            time.sleep(0.3)

    console.print()
    table = Table(title="Session Summary", box=box.SIMPLE_HEAVY)
    table.add_column("Step", style="dim", width=6)
    table.add_column("Tool", style="cyan")
    table.add_column("Decision", width=10)
    table.add_column("Reason", style="dim")
    table.add_column("ms", style="dim", width=6)

    for r in results:
        color = {"allow": "green", "deny": "red", "review": "yellow"}.get(r["decision"], "white")
        table.add_row(
            str(r["step"]),
            r["tool"],
            f"[{color}]{r['decision'].upper()}[/{color}]",
            r["reason"] or "—",
            r["ms"],
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Dashboard: http://localhost:8501[/dim]")
    console.print()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=f"AIControl Demo — {SCENARIO['name']}")
    parser.add_argument("--token", required=True, help="Agent JWT token")
    parser.add_argument("--mode", choices=["fast", "walkthrough"], default="walkthrough")
    args = parser.parse_args()
    asyncio.run(run_demo(args.token, args.mode))


if __name__ == "__main__":
    main()
