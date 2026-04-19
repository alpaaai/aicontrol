# AIControl Docs — Navigation Structure

Sidebar navigation for aictl.io/docs. Each entry maps to one markdown file.

---

## Sidebar

```
AIControl Docs
│
├── Overview                     /docs                       01-overview.md
├── Getting Started              /docs/getting-started       02-getting-started.md
├── Integration
│   ├── How It Works             /docs/integration           03-integration.md
│   └── Framework Wrappers       /docs/integrations          04-integrations.md
│       ├── LangChain
│       ├── CrewAI
│       ├── AutoGen
│       ├── OpenAI Agents SDK
│       ├── LangGraph
│       ├── Vercel AI SDK
│       ├── MCP (Python)
│       └── TypeScript / Node.js
├── Policies                     /docs/policies              05-policies.md
├── Audit Log                    /docs/audit-log             06-audit-log.md
├── API Reference                /docs/api-reference         07-api-reference.md
└── Operations                   /docs/operations            08-operations.md
```

---

## Page summaries (for meta descriptions)

| Slug | Title | One-line |
|------|-------|----------|
| /docs | Overview | What AIControl does, where it sits, and how long integration takes |
| /docs/getting-started | Getting Started | Install, verify, and make your first governed tool call |
| /docs/integration | Integration | The intercept contract — request, response, and decision handling |
| /docs/integrations | Framework Wrappers | Copy-paste integration code for LangChain, CrewAI, AutoGen, and more |
| /docs/policies | Policies | Policy model, rule types, examples, and the policy CRUD API |
| /docs/audit-log | Audit Log | Schema, what's logged, retention, backup, and compliance queries |
| /docs/api-reference | API Reference | Full endpoint reference for all public APIs |
| /docs/operations | Operations | Token lifecycle, HITL workflow, monitoring, updates, troubleshooting |

---

## Page file map

| File | Route |
|------|-------|
| `01-overview.md` | `/docs` |
| `02-getting-started.md` | `/docs/getting-started` |
| `03-integration.md` | `/docs/integration` |
| `04-integrations.md` | `/docs/integrations` |
| `05-policies.md` | `/docs/policies` |
| `06-audit-log.md` | `/docs/audit-log` |
| `07-api-reference.md` | `/docs/api-reference` |
| `08-operations.md` | `/docs/operations` |
