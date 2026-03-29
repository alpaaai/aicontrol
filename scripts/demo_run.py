"""AIControl End-to-End Demo Script.

Simulates an insurance claims processing agent making 5 tool calls,
demonstrating allow, deny, and review (HITL) decisions in real time.

Usage:
    python scripts/demo_run.py --token <agent-token> [--mode fast|walkthrough]
"""
import argparse
import time
import uuid

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

console = Console()

API_BASE = "http://localhost:8000"
AGENT_ID = "00000000-0000-0000-0000-000000000001"
SESSION_ID = "00000000-0000-0000-0000-000000000002"

TOOL_CALLS = [
    {
        "tool_name": "lookup_policy",
        "tool_parameters": {
            "policy_id": "POL-2024-00892",
            "customer_id": "CUST-44821",
        },
        "label": "Look up customer policy",
        "expected": "allow",
    },
    {
        "tool_name": "calculate_payout",
        "tool_parameters": {
            "claim_amount": 12500.00,
            "policy_type": "comprehensive",
            "deductible": 1000.00,
        },
        "label": "Calculate claim payout",
        "expected": "allow",
    },
    {
        "tool_name": "http_request",
        "tool_parameters": {
            "method": "POST",
            "url": "https://api.acme-partners.com/claims/notify",
            "body": {"claim_id": "CLM-2024-7732", "status": "approved"},
        },
        "label": "Notify external partner API",
        "expected": "review",
    },
    {
        "tool_name": "execute_code",
        "tool_parameters": {
            "language": "python",
            "code": "import subprocess; subprocess.run(['rm', '-rf', '/'])",
        },
        "label": "Execute arbitrary code",
        "expected": "deny",
    },
    {
        "tool_name": "send_notification",
        "tool_parameters": {
            "channel": "email",
            "recipient": "customer@example.com",
            "template": "claim_approved",
        },
        "label": "Send approval notification to customer",
        "expected": "allow",
    },
]

DECISION_STYLE = {
    "allow":  ("[bold green]ALLOW[/bold green]",  "green"),
    "deny":   ("[bold red]DENY[/bold red]",       "red"),
    "review": ("[bold yellow]REVIEW[/bold yellow]", "yellow"),
}


def _pause(seconds: int, message: str, walkthrough: bool) -> None:
    if walkthrough:
        console.print(f"\n[dim]{message}[/dim]")
        time.sleep(seconds)


def _intercept(token: str, session_id: str, tool: dict, sequence: int) -> dict:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{API_BASE}/intercept",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": session_id,
                "agent_id": AGENT_ID,
                "agent_name": "claims-processing-agent",
                "tool_name": tool["tool_name"],
                "tool_parameters": tool["tool_parameters"],
                "sequence_number": sequence,
            },
        )
        response.raise_for_status()
        return response.json()


def run_demo(token: str, walkthrough: bool) -> None:
    console.print()
    console.print(Panel.fit(
        "[bold white]AIControl[/bold white]  —  AI Agent Governance Platform\n"
        "[dim]Enterprise governance for every agent tool call[/dim]",
        border_style="blue",
    ))

    _pause(2, "Setting the scene...", walkthrough)

    if walkthrough:
        console.print(Panel(
            "[bold]Scenario:[/bold] Acme Insurance has deployed an AI claims "
            "processing agent. AIControl sits in the execution loop — every "
            "tool call the agent makes is intercepted, evaluated against "
            "governance policies, and logged to an immutable audit trail.\n\n"
            "Watch what happens when the agent tries 5 different actions.",
            title="Demo Scenario",
            border_style="dim",
        ))
        time.sleep(3)

    session_id = SESSION_ID
    console.print(
        f"\n[dim]Session:[/dim] [cyan]{session_id[:8]}...[/cyan]  "
        f"[dim]Agent:[/dim] [cyan]claims-processing-agent[/cyan]\n"
    )

    results = []

    for i, tool in enumerate(TOOL_CALLS, 1):
        _pause(1, f"Agent is about to call: {tool['tool_name']}", walkthrough)

        console.print(
            f"[dim]{i}/5[/dim]  [bold]{tool['label']}[/bold]  "
            f"[dim]→ {tool['tool_name']}()[/dim]"
        )

        try:
            result = _intercept(token, session_id, tool, i)
        except httpx.HTTPError as e:
            console.print(f"     [red]ERROR: {e}[/red]")
            results.append({**tool, "decision": "error", "reason": str(e)})
            continue

        decision = result["decision"]
        label, color = DECISION_STYLE.get(
            decision, (decision.upper(), "white")
        )[:2]

        console.print(
            f"     {label}  [dim]{result.get('reason', '')}[/dim]  "
            f"[dim]{result.get('audit_event_id', '')[:8]}...[/dim]"
        )

        if decision == "review":
            console.print(
                f"\n     [yellow]Slack notification sent to "
                f"#aicontrol-reviews[/yellow]"
            )
            if walkthrough:
                console.print(
                    "     [dim]A compliance officer will approve or deny "
                    "this action in Slack.[/dim]"
                )
                console.print(
                    "\n     [bold yellow]>>> Check your Slack channel "
                    "and click Approve or Deny <<<[/bold yellow]"
                )
                input("\n     Press Enter once you've responded in Slack...")

        elif decision == "deny" and walkthrough:
            console.print(
                "     [dim]Policy: block_dangerous_tools — "
                "this tool is blacklisted for all agents.[/dim]"
            )

        results.append({**tool, "decision": decision,
                        "reason": result.get("reason", "")})
        console.print()
        _pause(1, "", walkthrough)

    # Summary table
    console.print()
    console.rule("[bold]Demo Summary[/bold]")
    console.print()

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Tool Call", min_width=25)
    table.add_column("Decision", min_width=10)
    table.add_column("Reason", min_width=25)

    counts: dict[str, int] = {"allow": 0, "deny": 0, "review": 0, "error": 0}
    for i, r in enumerate(results, 1):
        d = r["decision"]
        counts[d] = counts.get(d, 0) + 1
        style_map = {
            "allow": "green", "deny": "red",
            "review": "yellow", "error": "red"
        }
        table.add_row(
            str(i),
            r["label"],
            Text(d.upper(), style=f"bold {style_map.get(d, 'white')}"),
            r.get("reason", ""),
        )

    console.print(table)
    console.print()
    console.print(
        f"  [green]Allow[/green]: {counts['allow']}   "
        f"[yellow]Review[/yellow]: {counts['review']}   "
        f"[red]Deny[/red]: {counts['deny']}   "
        f"Total: {sum(counts.values())}"
    )
    console.print()

    if walkthrough:
        console.print(Panel(
            "[bold]What you just saw:[/bold]\n\n"
            "1. Every agent tool call was intercepted before execution\n"
            "2. Policies evaluated in real time by OPA — sub-10ms latency\n"
            "3. External API call flagged for human review via Slack\n"
            "4. Dangerous tool blocked automatically\n"
            "5. Complete immutable audit trail written to Postgres\n\n"
            "[dim]All of this works across any AI framework — LangChain, "
            "CrewAI, AutoGen, custom agents.[/dim]",
            title="AIControl in Action",
            border_style="green",
        ))

    console.print(
        f"[dim]View full audit trail at:[/dim] "
        f"[cyan]http://localhost:8501[/cyan]\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIControl Demo")
    parser.add_argument(
        "--token", required=True,
        help="Agent API token (from scripts/issue_token.py --role agent)"
    )
    parser.add_argument(
        "--mode", choices=["fast", "walkthrough"], default="fast",
        help="fast = 3 min, walkthrough = 10 min with narrative pauses"
    )
    args = parser.parse_args()
    run_demo(token=args.token, walkthrough=(args.mode == "walkthrough"))
