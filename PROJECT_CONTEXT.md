# AIControl — Project Context

## What We Are Building
Enterprise AI agent governance middleware. Sits in agent execution loops.
Intercepts tool calls before they execute. Enforces policy. Logs everything.
Tagline: "The Control Plane for AI Agents."

## Product Positioning
- Framework-agnostic HTTP intercept (POST /intercept) — works with any agent on any framework
- OPA-powered policy engine — policy-as-code, runtime updates, no deployment required
- Immutable audit trail — append-only PostgreSQL, compliance evidence on demand
- Human-in-the-loop — Slack HITL with approve/deny, reviewer identity logged
- Self-hosted Docker Compose — customer data never leaves their environment

## Stack
- Python 3.14, FastAPI, SQLAlchemy async (asyncpg), PostgreSQL 15
- OPA (Open Policy Agent) sidecar — latest-debug image, port 8181
- Streamlit dashboard — sync SQLAlchemy (psycopg2), port 8501
- Slack Bolt — HITL notifications with approve/deny buttons
- Docker Compose — two-file pattern (infra + app)
- Alembic — database migrations
- structlog — structured JSON logging
- rich — terminal output for demo scripts
- GitHub Actions CI/CD — builds to ghcr.io, linux/amd64 + linux/arm64

## OS
Ubuntu WSL2 on Windows, username: deven, project at ~/aicontrol

## Project Structure
```
~/aicontrol/
  app/
    main.py              — FastAPI app, lifespan hook loads policies to OPA
    routers/
      intercept.py       — POST /intercept (core governance loop)
      policies.py        — CRUD /policies (admin only)
      agents.py          — CRUD /agents (admin only)
      slack.py           — POST /slack/actions (HITL callbacks)
    models/              — SQLAlchemy async models
    services/
      opa_client.py      — OPA evaluation
      hitl_service.py    — Slack notifications
    core/
      auth.py            — JWT auth, SHA-256 token hashing
      logging.py         — structlog config
  dashboard/             — Streamlit dashboard (6 views)
  policies/
    base.rego            — OPA policy rules
    policies.yaml        — seed policies (loaded at startup)
  scripts/
    demo_run.py          — generic demo script
    demos/               — six industry-specific demo scripts (TO BUILD)
      demo_lending.py
      demo_manufacturing.py
      demo_healthcare.py
      demo_support.py
      demo_itsm.py
      demo_revops.py
      run_demo.py        — scenario selector
    issue_token.py
    revoke_token.py
    seed.py
    demo_reset.py
  tests/
  docker-compose.yml     — infra: postgres + opa
  docker-compose.app.yml — app: api + dashboard
  install.sh
  verify.sh
  diagnose.sh
```

## Database Schema (6 tables)
- agents — registry, approved_tools JSONB, status, tenant_id
- sessions — groups tool calls, risk_score accumulation
- policies — governance rules, condition JSONB, OPA-compiled at startup
- audit_events — append-only, every intercept regardless of decision
- hitl_reviews — human review queue, status: pending/approved/denied
- api_tokens — SHA-256 hashed JWTs, revoked flag, role (agent/admin)
All tables have tenant_id UUID nullable column (multi-tenancy ready, not yet enforced)

## Key Commands
```bash
# Start infra (postgres + opa)
docker compose up -d

# Run API (dev)
uvicorn app.main:app --reload --port 8000

# Run dashboard
streamlit run dashboard/app.py

# Run tests
pytest tests/

# Reset demo data
python scripts/demo_reset.py

# Run generic demo
python scripts/demo_run.py --token $TOKEN --mode walkthrough

# Run industry demo (once scripts/demos/ is built)
python scripts/demos/run_demo.py --scenario lending --token $TOKEN --mode walkthrough

# Issue token
python scripts/issue_token.py --role agent --desc "description"

# Revoke token
python scripts/revoke_token.py --id TOKEN_UUID

# Database migration
alembic revision --autogenerate -m "description"
alembic upgrade head

# Full deployment (infra + app)
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d

# Update deployment
docker compose -f docker-compose.yml -f docker-compose.app.yml pull
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d
docker compose exec api alembic upgrade head
```

## Architecture Decisions
- OPA evaluates all policies — no custom policy logic in Python
- Every intercept writes audit_event regardless of decision
- Policies: YAML is seed source, Postgres is source of truth, OPA is execution engine
- Policy changes via API immediately push updated Rego bundle to OPA (no restart)
- JWT: non-expiring tokens, SHA-256 hash stored (never raw token), revoked flag
- Streamlit uses sync SQLAlchemy (psycopg2); FastAPI uses async (asyncpg)
- OPA image: latest-debug (includes wget for healthcheck)
- Slack HITL is fire-and-forget (asyncio.create_task) — intercept response never waits
- Two compose files: docker-compose.yml (stable infra), docker-compose.app.yml (versioned app)

## Default Policies (policies/policies.yaml)
1. block_dangerous_tools — deny: execute_code, delete_database, drop_table, shell_exec, rm_rf
2. require_review_for_external_calls — review: http_request, webhook, external_api
3. allow_standard_tools — default allow

## Integration Pattern (how agents call AIControl)
```python
# Agent adds one call before executing any tool:
response = httpx.post(
    "http://aicontrol:8000/intercept",
    headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
    json={
        "session_id": session_id,
        "agent_id": agent_id,
        "agent_name": "my-agent",
        "tool_name": tool_name,
        "tool_parameters": tool_parameters,
        "sequence_number": seq,
    }
)
decision = response.json()["decision"]  # allow | deny | review
```
Wrappers/decorators available for: LangChain, CrewAI, AutoGen, OpenAI Agents SDK,
LangGraph, Vercel AI SDK, MCP Python server, TypeScript/Node.js universal.
See: outputs/integration-guide.md

## Current Phase
V1 complete — pre-revenue, pre-outreach

## What's Built (Days 1-10 complete)
- Day 1-2: Docker stack, DB models, FastAPI, Alembic, MCP proxy intercept loop, OPA
- Day 3: Streamlit dashboard (6 views: audit log, decision breakdown, risk score, policies, agents, tokens)
- Day 4: JWT auth, token issuance/revocation, policy CRUD API
- Day 5: HITL Slack notifications, structlog, /debug endpoint
- Day 6: Multi-tenancy columns, agent CRUD API, demo script (rich, fast/walkthrough modes)
- Day 7: Docker containerization, two-file compose, GitHub Actions CI/CD, onboarding scripts
- Day 8: Six industry demo scripts (scripts/demos/) — lending, manufacturing, healthcare,
  support, itsm, revops. Each produces allow → allow → deny sequence with realistic
  parameters. Selector script run_demo.py. Parameter-based deny policies added to
  policies.yaml. base.rego split into two deny paths: is_blacklisted (global tool ban,
  reason: tool_blacklisted) and is_parameter_violation (parameter-level, reason:
  parameter_policy_violation: key=value). All six scenarios verified end to end.
  Dashboard populates correctly. Step 3 mechanics check complete for all six scenarios.
- Day 9: Three workstreams completed:
  (a) Parameter-based deny policies — base.rego split into is_blacklisted (global tool
      ban, reason: tool_blacklisted) and is_parameter_violation (parameter-level, reason:
      parameter_policy_violation: key=value). All six demo scenarios updated. Manufacturing
      and ITSM remain tool blacklists. Lending/support/healthcare/revops now fire precise
      parameter reason codes. Verified end to end across all six scenarios.
  (b) Reviews endpoints — GET /reviews/{review_id} (agent scoped to own sessions + admin)
      and GET /reviews (admin only, filterable by status). Fields: id, status, reviewer,
      review_note, reviewed_at, audit_event_id, session_id, created_at.
  (c) Agent-scoped tokens — api_tokens.agent_id FK column (Alembic migration
      93b453657c1a). POST /tokens accepts agent_id, auto-revokes prior active token for
      same agent. /intercept enforces 403 if agent token's agent_id != request body
      agent_id. Admin tokens remain unscoped. Three new scripts: onboard_agent.py
      (register + issue in one command, saves to .aicontrol/<name>.env),
      list_agents.py (tabular listing), revoke_agent.py (deactivate + revoke in one
      step). DELETE /agents/{id}/token endpoint added.
- Day 10: Dashboard & demo fixes — two-batch sprint (April 12, 2026)
    Data layer (app/routers/intercept.py):
      enrich_parameters: extracts domain from URL on HTTP tool calls (http_post, http_get, etc.) before persisting to audit_events
      RISK_SCORE_DELTA: allow=1, review=10, deny=25 — passed to write_event on every intercept, risk score chart no longer flat
      find_fired_policy: mirrors Rego logic in Python to match fired policy from active policies list by reason string (tool_blacklisted, parameter_policy_violation:*, requires_human_review) — writes policy_name and policy_id to audit_events on deny/review
      get_active_policies: updated to include id in returned dicts

    Dashboard layer (refactored into dashboard/queries.py + dashboard/views/):
      queries.py: audit events query now includes tool_parameters, session_id, policy_name; policies query includes condition
      views/audit_log.py: full rewrite — parameters column (all params, truncated 120 chars), agent text filter, row selection with full detail panel (parameters JSON, session ID, policy name, duration, reason)
      views/policies.py: condition column with row detail; Create Policy form with rule_type selector outside form for live placeholder updates; four condition examples (tool_blacklist, tool_pattern, parameter_match, rate_limit); reads AICONTROL_API_URL and ADMIN_TOKEN from env

    Demo scripts (scripts/demos/ — all six):
      session_id generated fresh with uuid4() per run — each execution is a distinct session on risk score chart
      audit_event_id removed from terminal output
      Policy name shown on deny decisions
      Default API port 8000 → 8001
      demo_revops.py: deal_id removed entirely; opportunity_name: "Acme Corp — Enterprise Q2" added to update_deal_stage and log_sales_activity; labels updated to reference opportunity name

    Environment:
      .env now includes AICONTROL_API_URL=http://localhost:8001 and ADMIN_TOKEN for dashboard policy create form
    Day 11: Agent registry fix — per-scenario agent IDs (April 2026)
      Problem: all six demo scripts were using the same hardcoded agent_id (00000000-0000-0000-0000-000000000001), so the Agents dashboard showed one agent and audit events didn't link to the correct agent row.
    Changes:
      Each demo script now has its own agent_id defined in SCENARIO — agent_name and agent_id travel together on every intercept call
      scripts/seed.py updated to register all 6 scenario agents with fixed memorable UUIDs — idempotent, safe to re-run anytime (ON CONFLICT DO NOTHING)
      Audit events now correctly FK to the right agent row in the database
      Agents dashboard view now shows all 6 scenario agents with their approved tool lists
    Agent UUIDs (fixed, memorable):
      loan-underwriting-agent — registered in seed
      clinical-documentation-agent — registered in seed
      incident-response-agent — registered in seed
      supplier-sourcing-agent — registered in seed
      support-resolution-agent — registered in seed
      crm-automation-agent — registered in seed
    Note: Audit events from runs prior to this fix have agent_id = 00000000-0000-0000-0000-000000000001 (old hardcoded value). Historical only — all new runs link correctly.
    Operational note: Run python scripts/seed.py after any fresh database reset to ensure all agents are registered before running demo scenarios.
    37 test policies deleted. 9 demo scenario policies remain:
      allow_standard_tools
      block_dangerous_tools
      block_http_post_in_itsm
      block_unapproved_outbound_http
      deny_bulk_account_lookup
      deny_bulk_credit_query
      deny_cross_encounter_phi_access
      deny_unscoped_crm_query
      require_review_for_external_calls

    Day 12: Auto-session creation on intercept (April 17, 2026)
      ensure_session helper added to app/routers/intercept.py — called before
      write_event on every intercept request. If session_id is not found in the
      sessions table, creates Session(id=session_id, agent_id=agent_id, status="active")
      automatically. Demo scripts and production agents no longer need to pre-register
      sessions before calling /intercept.

## What's NOT Built Yet
- Agent status defaults to 'unregistered' on POST /agents — should be 'active'
  (minor fix needed before customer installs)
- Per-agent tool enforcement at intercept time (approved_tools exists in DB, not yet enforced)
- Behavioral drift detection (V2)
- Compliance report export PDF (V2)
- React frontend (V2 — Streamlit is V1 dashboard)
- Multi-tenancy enforcement (tenant_id columns exist, queries not yet scoped)

## Go-To-Market Status
- Domain: aictl.io (purchased, 1 year)
- Email: hello@aictl.io (Zoho Mail, DNS configured)
- Website: live at aictl.io (Next.js + Vercel, one-page + /docs unlinked)
- Calendly: 30-min "AIControl Demo" configured
- GitHub: github.com/alpaaai/aicontrol (public)
- Website repo: github.com/alpaaai/aicontrol-site
- GitHub history cleaned: PROJECT_CONTEXT.md, CLAUDE.md, .claude/ purged from all commits via git-filter-repo (April 2026)
- .gitignore blocks: PROJECT_CONTEXT.md, CLAUDE.md, .claude/, docs/01-aicontrol-overview.md, docs/03-aicontrol-vision.md, docs/04-aicontrol-battle-card.md, docs/demo-scenarios-v2.md
- Public docs only: docs/02-aicontrol-technical-design.md, docs/GETTING_STARTED.md, docs/integration-guide.md

## Pricing (finalized)
| Tier       | Agents | Monthly | Annual      | Per agent/mo |
|------------|--------|---------|-------------|--------------|
| Starter    | 10     | $2,000  | $24,000/yr  | $200         |
| Business   | 50     | $5,000  | $60,000/yr  | $100         |
| Enterprise | ∞      | Custom  | Custom      | —            |
Annual default, 20% premium for monthly.

## Key Output Files (in outputs/)
- 01-aicontrol-overview.md — market context, product thesis, hard questions
- 02-aicontrol-technical-design.md — full technical reference
- 03-aicontrol-vision.md — roadmap, acquisition thesis, conviction document
- 04-aicontrol-battle-card.md — competitive positioning, objection handling
- aicontrol-website-copy.md — all website copy
- website-claude-code-brief-v2.md — Claude Code brief for website build
- demo-scenarios-v2.md — six industry demo scenarios with real incident refs
- demo-scripts-claude-code-brief.md — Claude Code brief for demo scripts build
- integration-guide.md — copy-paste integration for all major frameworks

## Next Actions (in priority order)
1. Full six-scenario walkthrough verification after batch 2 fixes (new chat, read PROJECT_CONTEXT.md first). 
2. Adversarial objection practice runs (Step 5)
3. Start outreach: 30 direct emails to CISOs/Chief AI Officers
4. Parallel: TOS + Privacy Policy, Stripe setup
5. Parallel: 2 blog posts for aictl.io/blog
6. Minor fix: agent status should default to 'active' on registration

## Docs Site
April 15, 2026
- Built and deployed the public-facing documentation site at aictl.io/docs.

### What was produced
- Eight new doc pages written from scratch — replacing the previous GETTING_STARTED.md / integration-guide.md / 02-aicontrol-technical-design.md trio which were README-style and missing critical sections an evaluating engineer would need.

  Source files stored at ~/aicontrol/docs/public/:
- 00-navigation.md — sidebar structure and slug map
- 01-overview.md → /docs
- 02-getting-started.md → /docs/getting-started
- 03-integration.md → /docs/integration
- 04-integrations.md → /docs/integrations (all 8 framework wrappers)
- 05-policies.md → /docs/policies
- 06-audit-log.md → /docs/audit-log
- 07-api-reference.md → /docs/api-reference
- 08-operations.md → /docs/operations

April 16, 2026
- All 6 changes shipped. Here's the before/after summary:
  Change 1 — Hero subheadline:
  ▎ Before: "AIControl intercepts every agent tool call, enforces your policies, and writes an immutable audit trail — before
  anything executes. Works with any framework. No re-platforming required."
  ▎ After: "Ship agents to production knowing every tool call is allowed, denied, or escalated to a human reviewer before it
  executes — and every decision is on record."

  Change 2 — IncidentCards section:
  New section inserted between Hero and WhatItIs with Meta/Replit/AWS incident cards, headline "This is what ungoverned
  production agents do.", closing bold line.

  Change 3 — WhatItIs headline:
  ▎ Before: "Your agents are taking actions. Can you prove they were authorized?"
  ▎ After: "Your agents are already in production. Every tool call they make is either authorized — or it isn't."

  Change 4 — WhatItIs card 3 body:
  ▎ Before: "When an agent tries something ambiguous, there's no mechanism to pause, escalate to a human, and resume only
  after approval."
  ▎ After: "When an agent tool call falls outside clear policy — ambiguous parameters, unexpected context, high-stakes action
  — there is no mechanism to pause, route to a human reviewer, and resume with a decision on record. Exceptions disappear into
   logs nobody reads."

  Change 5 — Features "Universal Intercept" body:
  ▎ Before: "Framework-agnostic MCP proxy. LangChain, CrewAI, AutoGen, custom agents — all governed by the same policy
  engine."
  ▎ After: "Framework-agnostic. Works with any agent on any framework — LangChain, CrewAI, AutoGen, MCP-based agents, or
  custom code. One integration point. No re-platforming."

  Change 6 — Pricing Business tier:
  ▎ Before: "Compliance report export"
  ▎ After: "Compliance report export (coming soon)"


### What was added that didn't exist before
- Policy model documented: both working rule types (tool_blacklist, tool_pattern)
  with full condition schemas and examples. rate_limit and agent_name_pattern
  intentionally omitted — not enforced in Rego.
- Full audit_events schema with accurate column names (decision_reason, policy_name,
  policy_id) and example compliance SQL queries.
- Full API reference for all public endpoints: /intercept, /agents, /tokens,
  /policies, /reviews.
- HITL workflow documented accurately: /intercept returns immediately, review does
  not block the agent, polling pattern provided for teams that need blocking behavior.
- Operations page: token lifecycle, rotation, backup, single-node topology, update
  steps, troubleshooting.

### Site build
Claude Code built the /docs section into aictl.io (Next.js + Vercel,
github.com/alpaaai/aicontrol-site). Two-column layout with fixed sidebar,
active link highlighting, nested Integration group, dark code blocks
(github-dark shiki, #0F172A background) on light page background, copy button
on hover, language label on each block, mobile hamburger drawer. Deployed to
Vercel via git push to main.

### Key editorial decisions
- Only tool_blacklist and tool_pattern documented — rate_limit / agent_name_pattern
  held back until enforced in Rego
- risk_delta and tool_response excluded from audit schema docs
- HITL documented as fire-and-forget (accurate) not blocking (inaccurate)
- Dark code blocks on light page — deliberate product decision, not an error

### Next Actions (updated)
1. Link /docs from homepage nav on aictl.io
2. Full six-scenario walkthrough verification (new chat, read PROJECT_CONTEXT.md first)
3. Adversarial objection practice runs
4. Start outreach: 30 direct emails to CISOs/Chief AI Officers
5. Parallel: TOS + Privacy Policy, Stripe setup
6. Parallel: 2 blog posts for aictl.io/blog
7. Minor fix: agent status should default to 'active' on registration

## Superpowers Skills Active
- writing-plans
- executing-plans
- test-driven-development
- systematic-debugging
- verification-before-completion
- finishing-a-development-branch
