# AIControl Day 3 — Streamlit Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working Streamlit dashboard with 5 views — audit log, policy list, agent list, decision breakdown, and risk score chart — all reading live from Postgres. Read-only now, architected for interactive HITL reviews later.

**Architecture:** Dashboard runs as a separate process (`streamlit run dashboard/app.py`). It connects to Postgres directly via SQLAlchemy sync (Streamlit doesn't support async). Shared DB models are imported from `app/models/`. Each view is a separate module in `dashboard/views/`. A `dashboard/db.py` provides a sync session factory separate from the async one used by FastAPI.

**Tech Stack:** Streamlit, SQLAlchemy sync, psycopg2, Plotly (charts), pandas (data frames)

---

## File Map

| File | Purpose |
|---|---|
| `dashboard/__init__.py` | Package marker |
| `dashboard/db.py` | Sync SQLAlchemy engine + session factory for Streamlit |
| `dashboard/queries.py` | All DB query functions — one per view |
| `dashboard/views/__init__.py` | Package marker |
| `dashboard/views/audit_log.py` | Audit event log view |
| `dashboard/views/policies.py` | Policy list view |
| `dashboard/views/agents.py` | Agent list view |
| `dashboard/views/decisions.py` | Decision breakdown (allow/deny/review counts + chart) |
| `dashboard/views/risk.py` | Risk score over time per session (Plotly line chart) |
| `dashboard/app.py` | Main Streamlit entry point — sidebar nav, mounts all views |
| `tests/test_dashboard_queries.py` | Tests for query functions (sync, uses real DB) |

---

## Task 1: Sync DB Connection for Streamlit

`dashboard/db.py` — Streamlit is synchronous, so we need a separate sync SQLAlchemy engine. It reads from the same `.env` / `DATABASE_URL` but uses `psycopg2` instead of `asyncpg`.

**Files:**
- Create: `dashboard/__init__.py`
- Create: `dashboard/db.py`
- Create: `tests/test_dashboard_db.py`

- [x] **Step 1: Install psycopg2 if not already installed**

```bash
pip install psycopg2-binary --break-system-packages
```

- [x] **Step 2: Write the failing test**

```bash
cat > ~/aicontrol/tests/test_dashboard_db.py << 'EOF'
"""Tests for sync dashboard DB connection."""
from sqlalchemy.orm import Session
from sqlalchemy import text


def test_sync_engine_connects():
    """Sync engine must connect to Postgres and return a result."""
    from dashboard.db import sync_engine
    with sync_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_get_sync_session_returns_session():
    """get_sync_session must return a usable SQLAlchemy Session."""
    from dashboard.db import get_sync_session
    with get_sync_session() as session:
        assert isinstance(session, Session)
EOF
```

- [x] **Step 3: Run test — verify it FAILS**

```bash
cd ~/aicontrol && pytest tests/test_dashboard_db.py -v
```
Expected: `ImportError` for `dashboard.db`.

- [x] **Step 4: Create package marker and write `dashboard/db.py`**

```bash
mkdir -p ~/aicontrol/dashboard/views
touch ~/aicontrol/dashboard/__init__.py ~/aicontrol/dashboard/views/__init__.py
```

```bash
cat > ~/aicontrol/dashboard/db.py << 'EOF'
"""Sync SQLAlchemy engine for Streamlit dashboard."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Convert asyncpg URL to psycopg2 URL
_sync_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)

sync_engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
    pool_size=5,
)

_SyncSession = sessionmaker(bind=sync_engine, expire_on_commit=False)


@contextmanager
def get_sync_session() -> Session:
    """Context manager yielding a sync DB session."""
    session = _SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
EOF
```

- [x] **Step 5: Run test — verify it PASSES**

```bash
cd ~/aicontrol && pytest tests/test_dashboard_db.py -v
```
Expected: `2 passed`.

- [x] **Step 6: Commit**

```bash
cd ~/aicontrol
git add dashboard/ tests/test_dashboard_db.py
git commit -m "feat: add sync db connection for streamlit dashboard"
```

---

## Task 2: Dashboard Query Functions

`dashboard/queries.py` — all DB queries in one place. Each function returns plain Python dicts or lists that views can pass directly to Streamlit/Plotly. No ORM objects leak into views.

**Files:**
- Create: `dashboard/queries.py`
- Create: `tests/test_dashboard_queries.py`

- [x] **Step 1: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_dashboard_queries.py << 'EOF'
"""Tests for dashboard query functions against live DB."""
import pytest


def test_get_audit_events_returns_list():
    """get_audit_events must return a list."""
    from dashboard.queries import get_audit_events
    result = get_audit_events(limit=10)
    assert isinstance(result, list)


def test_get_audit_events_fields():
    """Each audit event must have required display fields."""
    from dashboard.queries import get_audit_events
    results = get_audit_events(limit=10)
    if results:
        row = results[0]
        for field in ["tool_name", "decision", "created_at"]:
            assert field in row, f"Missing field: {field}"


def test_get_policies_returns_list():
    """get_policies must return a list."""
    from dashboard.queries import get_policies
    result = get_policies()
    assert isinstance(result, list)


def test_get_agents_returns_list():
    """get_agents must return a list."""
    from dashboard.queries import get_agents
    result = get_agents()
    assert isinstance(result, list)


def test_get_decision_counts_returns_dict():
    """get_decision_counts must return dict with allow/deny/review keys."""
    from dashboard.queries import get_decision_counts
    result = get_decision_counts()
    assert isinstance(result, dict)
    for key in ["allow", "deny", "review"]:
        assert key in result


def test_get_risk_scores_returns_list():
    """get_risk_scores must return a list of session risk data."""
    from dashboard.queries import get_risk_scores
    result = get_risk_scores()
    assert isinstance(result, list)
EOF
```

- [x] **Step 2: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_dashboard_queries.py -v
```
Expected: `ImportError` for `dashboard.queries`.

- [x] **Step 3: Write `dashboard/queries.py`**

```bash
cat > ~/aicontrol/dashboard/queries.py << 'EOF'
"""All dashboard DB query functions. Return plain dicts, never ORM objects."""
from datetime import datetime
from typing import Any

from sqlalchemy import text

from dashboard.db import get_sync_session


def get_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent audit events for the log view."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT
                ae.id,
                ae.tool_name,
                ae.decision,
                ae.decision_reason,
                ae.agent_name,
                ae.sequence_number,
                ae.duration_ms,
                ae.risk_delta,
                ae.created_at,
                p.name AS policy_name
            FROM audit_events ae
            LEFT JOIN policies p ON ae.policy_id = p.id
            ORDER BY ae.created_at DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def get_policies() -> list[dict[str, Any]]:
    """Return all active policies."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT id, name, description, rule_type, action,
                   severity, active, created_at
            FROM policies
            ORDER BY severity DESC, name
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_agents() -> list[dict[str, Any]]:
    """Return all registered agents."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT id, name, owner, status, framework,
                   model_version, created_at
            FROM agents
            ORDER BY created_at DESC
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_decision_counts() -> dict[str, int]:
    """Return count of allow/deny/review decisions across all events."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT decision, COUNT(*) as count
            FROM audit_events
            GROUP BY decision
        """)).mappings().all()
    counts = {"allow": 0, "deny": 0, "review": 0}
    for row in rows:
        decision = row["decision"].lower()
        if decision in counts:
            counts[decision] = int(row["count"])
    return counts


def get_risk_scores() -> list[dict[str, Any]]:
    """Return risk score progression per session for chart."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT
                s.id AS session_id,
                ae.sequence_number,
                SUM(ae.risk_delta) OVER (
                    PARTITION BY ae.session_id
                    ORDER BY ae.sequence_number
                ) AS cumulative_risk,
                ae.created_at
            FROM audit_events ae
            JOIN sessions s ON ae.session_id = s.id
            ORDER BY ae.session_id, ae.sequence_number
        """)).mappings().all()
    return [dict(r) for r in rows]
EOF
```

- [x] **Step 4: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_dashboard_queries.py -v
```
Expected: `6 passed`.

- [x] **Step 5: Commit**

```bash
cd ~/aicontrol
git add dashboard/queries.py tests/test_dashboard_queries.py
git commit -m "feat: add dashboard query functions"
```

---

## Task 3: Audit Log + Policy + Agent Views

Three simple table views. Each is a standalone function that Streamlit calls. TDD is relaxed here — these are pure UI rendering functions, tested visually.

**Files:**
- Create: `dashboard/views/audit_log.py`
- Create: `dashboard/views/policies.py`
- Create: `dashboard/views/agents.py`

- [x] **Step 1: Write `dashboard/views/audit_log.py`**

```bash
cat > ~/aicontrol/dashboard/views/audit_log.py << 'EOF'
"""Audit event log view."""
import pandas as pd
import streamlit as st

from dashboard.queries import get_audit_events

DECISION_COLORS = {
    "allow": "🟢",
    "deny": "🔴",
    "review": "🟡",
}


def render() -> None:
    st.header("Audit Event Log")

    col1, col2 = st.columns([3, 1])
    with col1:
        limit = st.slider("Max events", 10, 500, 100, step=10)
    with col2:
        if st.button("Refresh"):
            st.rerun()

    events = get_audit_events(limit=limit)

    if not events:
        st.info("No audit events yet. Run the seed script and call /intercept.")
        return

    df = pd.DataFrame(events)
    df["decision"] = df["decision"].map(
        lambda d: f"{DECISION_COLORS.get(d.lower(), '')} {d}"
    )
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    st.dataframe(
        df[[
            "created_at", "agent_name", "tool_name",
            "decision", "decision_reason", "duration_ms", "risk_delta"
        ]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Showing {len(events)} events")
EOF
```

- [x] **Step 2: Write `dashboard/views/policies.py`**

```bash
cat > ~/aicontrol/dashboard/views/policies.py << 'EOF'
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
EOF
```

- [x] **Step 3: Write `dashboard/views/agents.py`**

```bash
cat > ~/aicontrol/dashboard/views/agents.py << 'EOF'
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
EOF
```

- [x] **Step 4: Commit**

```bash
cd ~/aicontrol
git add dashboard/views/
git commit -m "feat: add audit log, policy, and agent dashboard views"
```

---

## Task 4: Decision Breakdown + Risk Score Views

Two chart views using Plotly. Decision breakdown is a donut chart. Risk score is a line chart showing cumulative risk per session over time.

**Files:**
- Create: `dashboard/views/decisions.py`
- Create: `dashboard/views/risk.py`

- [x] **Step 1: Install plotly and pandas if not already installed**

```bash
pip install plotly pandas --break-system-packages
```

- [x] **Step 2: Write `dashboard/views/decisions.py`**

```bash
cat > ~/aicontrol/dashboard/views/decisions.py << 'EOF'
"""Decision breakdown view — donut chart of allow/deny/review."""
import plotly.graph_objects as go
import streamlit as st

from dashboard.queries import get_decision_counts, get_audit_events


def render() -> None:
    st.header("Decision Breakdown")

    counts = get_decision_counts()
    total = sum(counts.values())

    if total == 0:
        st.info("No decisions recorded yet.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Allow", counts["allow"],
                delta=None, delta_color="normal")
    col2.metric("Deny", counts["deny"])
    col3.metric("Review", counts["review"])

    fig = go.Figure(data=[go.Pie(
        labels=["Allow", "Deny", "Review"],
        values=[counts["allow"], counts["deny"], counts["review"]],
        hole=0.5,
        marker_colors=["#22c55e", "#ef4444", "#f59e0b"],
    )])
    fig.update_layout(
        title="Decision Distribution",
        showlegend=True,
        height=400,
        margin=dict(t=40, b=0, l=0, r=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Recent decision trend table
    st.subheader("Recent Decisions")
    events = get_audit_events(limit=20)
    if events:
        for e in events[:10]:
            icon = {"allow": "🟢", "deny": "🔴", "review": "🟡"}.get(
                e["decision"].lower(), ""
            )
            st.write(
                f"{icon} **{e['tool_name']}** — {e['decision_reason']} "
                f"({e['agent_name']})"
            )
EOF
```

- [x] **Step 3: Write `dashboard/views/risk.py`**

```bash
cat > ~/aicontrol/dashboard/views/risk.py << 'EOF'
"""Risk score over time view — line chart per session."""
import plotly.express as px
import pandas as pd
import streamlit as st

from dashboard.queries import get_risk_scores


def render() -> None:
    st.header("Risk Score Over Time")

    rows = get_risk_scores()

    if not rows:
        st.info("No session data yet. Run the demo script to generate events.")
        return

    df = pd.DataFrame(rows)
    df["session_id"] = df["session_id"].astype(str).str[:8]  # truncate UUID
    df["created_at"] = pd.to_datetime(df["created_at"])

    fig = px.line(
        df,
        x="sequence_number",
        y="cumulative_risk",
        color="session_id",
        title="Cumulative Risk Score per Session",
        labels={
            "sequence_number": "Tool Call #",
            "cumulative_risk": "Cumulative Risk",
            "session_id": "Session",
        },
        markers=True,
    )
    fig.update_layout(height=450, margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Showing {df['session_id'].nunique()} session(s), "
        f"{len(df)} data points"
    )
EOF
```

- [x] **Step 4: Commit**

```bash
cd ~/aicontrol
git add dashboard/views/decisions.py dashboard/views/risk.py
git commit -m "feat: add decision breakdown and risk score chart views"
```

---

## Task 5: Main App Entry Point

`dashboard/app.py` — the Streamlit entry point. Sidebar navigation routes between all 5 views. Sets page config, auto-refreshes every 30 seconds.

**Files:**
- Create: `dashboard/app.py`

- [x] **Step 1: Write `dashboard/app.py`**

```bash
cat > ~/aicontrol/dashboard/app.py << 'EOF'
"""AIControl Dashboard — main Streamlit entry point."""
import streamlit as st

st.set_page_config(
    page_title="AIControl",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.views import audit_log, policies, agents, decisions, risk

VIEWS = {
    "Audit Log": audit_log,
    "Decision Breakdown": decisions,
    "Risk Score": risk,
    "Policies": policies,
    "Agents": agents,
}

with st.sidebar:
    st.title("🛡️ AIControl")
    st.caption("AI Agent Governance")
    st.divider()
    selected = st.radio("View", list(VIEWS.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("Auto-refresh every 30s")

# Auto-refresh
import time
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

VIEWS[selected].render()
EOF
```

- [x] **Step 2: Verify dashboard starts**

```bash
cd ~/aicontrol
streamlit run dashboard/app.py --server.port 8501
```

Expected: Browser opens at `http://localhost:8501`. All 5 views accessible from sidebar. No errors in terminal.

- [x] **Step 3: Smoke test each view**

Navigate to each view in the sidebar and confirm:
- Audit Log — shows table (empty or seeded data)
- Decision Breakdown — shows donut chart
- Risk Score — shows line chart or info message
- Policies — shows 3 policies from seed
- Agents — shows demo agent from seed

- [x] **Step 4: Commit**

```bash
cd ~/aicontrol
git add dashboard/app.py
git commit -m "feat: add streamlit dashboard entry point with sidebar nav"
```

---

## Task 6: Full Verification

- [ ] **Step 1: Run full test suite**

```bash
cd ~/aicontrol && pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 2: Run seed script to populate data**

```bash
cd ~/aicontrol && python scripts/seed.py
```

- [ ] **Step 3: Fire 3 test intercepts**

```bash
# Allow
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{"session_id":"00000000-0000-0000-0000-000000000002","agent_id":"00000000-0000-0000-0000-000000000001","agent_name":"demo-agent","tool_name":"safe_tool","tool_parameters":{},"sequence_number":1}'

# Deny
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{"session_id":"00000000-0000-0000-0000-000000000002","agent_id":"00000000-0000-0000-0000-000000000001","agent_name":"demo-agent","tool_name":"execute_code","tool_parameters":{},"sequence_number":2}'

# Review
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{"session_id":"00000000-0000-0000-0000-000000000002","agent_id":"00000000-0000-0000-0000-000000000001","agent_name":"demo-agent","tool_name":"http_request","tool_parameters":{},"sequence_number":3}'
```

- [ ] **Step 4: Verify dashboard shows live data**

Open `http://localhost:8501` and confirm:
- Audit Log shows 3 events with correct allow/deny/review decisions
- Decision Breakdown donut shows 1 of each
- Risk Score chart shows progression for the session
- Policies shows 3 policies
- Agents shows demo-agent

- [ ] **Step 5: Final commit**

```bash
cd ~/aicontrol
git add -A
git commit -m "chore: day 3 complete — streamlit dashboard verified"
```

---

## Troubleshooting Quick Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: psycopg2` | Not installed | `pip install psycopg2-binary --break-system-packages` |
| `ModuleNotFoundError: plotly` | Not installed | `pip install plotly --break-system-packages` |
| Dashboard shows no data | Seed not run | `python scripts/seed.py` |
| Sync engine connection refused | Postgres not running | `docker compose up -d` |
| `DATABASE_URL` asyncpg error | URL not converted | Check `db.py` replace logic |
| Streamlit port in use | Another instance running | `pkill -f streamlit` |
