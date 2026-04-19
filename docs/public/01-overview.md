# What is AIControl

AIControl is a governance middleware layer for enterprise AI agents. It sits in the execution path between an agent and its tools — every tool call the agent attempts passes through AIControl before it runs.

AIControl evaluates each call against your policies, returns a decision in under 10ms, and writes an immutable audit record to PostgreSQL. The agent acts on the decision. Nothing else in your stack changes.

---

## The core loop

```
Agent decides to call a tool
        ↓
POST /intercept  →  AIControl evaluates policy  →  returns decision
        ↓
allow   → agent executes the tool normally
deny    → agent aborts, reason is logged
review  → agent receives review ID, human is notified via Slack
```

Every path through this loop produces an audit event. There are no gaps in the trail.

---

## Architecture

AIControl runs as four Docker containers in your environment. Nothing leaves your network.

```
┌─────────────────────────────────────────────────────────┐
│                   Your Environment                      │
│                                                         │
│  LangChain Agent   CrewAI Agent   Custom Agent          │
│        │                │              │                │
│        └────────────────┴──────────────┘                │
│                         │                               │
│                POST /intercept                          │
│                         │                               │
│         ┌───────────────▼──────────────┐                │
│         │   AIControl API  (:8000)     │                │
│         │                             │                │
│         │  JWT auth → policy load     │                │
│         │  → OPA eval → audit write   │                │
│         └──────┬──────────────┬───────┘                │
│                │              │                         │
│         ┌──────▼──┐    ┌──────▼──────┐                 │
│         │   OPA   │    │  PostgreSQL │                  │
│         │ (:8181) │    │   (:5432)   │                  │
│         └─────────┘    └─────────────┘                  │
│                                                         │
│         ┌──────────────────────┐                        │
│         │  Dashboard (:8501)   │                        │
│         └──────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

| Container | Purpose | Port |
|-----------|---------|------|
| `api` | FastAPI governance API | 8000 |
| `opa` | Open Policy Agent — policy evaluation | 8181 |
| `postgres` | Audit store | 5432 |
| `dashboard` | Streamlit governance dashboard | 8501 |

---

## What AIControl does — and what it doesn't

**It does:**
- Intercept agent tool calls before execution
- Evaluate them against policies defined in your environment
- Return allow / deny / review decisions in under 10ms
- Write an immutable audit record for every intercept, regardless of decision
- Notify a Slack channel when a call requires human review
- Provide a dashboard for reviewing the audit trail and managing policies

**It doesn't:**
- Sit in the LLM inference path — it governs tool execution, not prompt/completion
- Require changes to your LLM provider, agent framework, or data infrastructure
- Send audit data to external services — everything stays in your PostgreSQL instance
- Replace your existing access controls — it operates as an additional enforcement layer above them

---

## Framework support

Any agent that can make an HTTP call can integrate with AIControl. Native integration patterns are provided for:

- LangChain
- CrewAI
- AutoGen (Microsoft)
- OpenAI Agents SDK
- LangGraph
- Vercel AI SDK
- MCP (Model Context Protocol) Python servers
- TypeScript / Node.js (universal)

See [Integrations](/docs/integrations) for copy-paste wrappers.

---

## How long does integration take?

For a team with a running agent:

| Step | Time |
|------|------|
| Deploy AIControl (Docker Compose) | ~15 minutes |
| Issue agent token | 2 minutes |
| Copy integration wrapper for your framework | 10 minutes |
| Test end-to-end | 10 minutes |
| **Total** | **~1 hour** |

Most teams complete initial integration in a single afternoon.

---

## Next steps

- [Getting Started](/docs/getting-started) — install, verify, run your first governed call
- [Integration](/docs/integration) — how agents connect to the intercept endpoint
- [Policies](/docs/policies) — define what agents can and cannot do
