# Policies

Policies are the rules AIControl evaluates against every tool call. A policy specifies what to watch for, what decision to make, and optionally which compliance frameworks it satisfies.

Policy changes take effect immediately — pushed to the policy evaluation engine without a restart or redeployment.

---

## Policy model

Each policy has the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier — used in audit records |
| `description` | string | Human-readable explanation |
| `rule_type` | string | `tool_denylist` or `tool_pattern` |
| `condition` | object | Rule-specific match criteria (see below) |
| `action` | string | `deny` or `review` |
| `severity` | string | `critical`, `high`, `medium`, or `low` |
| `active` | boolean | Whether the policy is enforced |
| `compliance_frameworks` | array | e.g. `["SOC2", "GDPR", "HIPAA"]` — for audit export |

---

## Rule types

### `tool_denylist`

Matches on tool name, with optional parameter-level conditions. Action is always `deny`.

**Global ban — block a tool entirely:**

```json
{
  "rule_type": "tool_denylist",
  "action": "deny",
  "condition": {
    "blocked_tools": ["export_all_records", "delete_database", "shell_exec"]
  }
}
```

**Parameter-level ban — block a tool only when a specific parameter is missing or null:**

```json
{
  "rule_type": "tool_denylist",
  "action": "deny",
  "condition": {
    "blocked_tools": ["query_accounts"],
    "parameter_match": { "filter": null }
  }
}
```

This denies calls to `query_accounts` when the `filter` parameter is absent or null — allowing scoped queries while blocking unfiltered ones.

---

### `tool_pattern`

Matches on tool name substrings. Action is always `review` — a Slack notification is sent and a review record is created.

```json
{
  "rule_type": "tool_pattern",
  "action": "review",
  "condition": {
    "tool_name_contains": ["export", "delete", "bulk"]
  }
}
```

Any tool whose name contains one of the listed strings will trigger a review decision.

---

## Default policies

Three policies are pre-installed and active on a fresh deployment:

**`block_dangerous_tools`** — `tool_denylist`, `deny`, `critical`
```json
{
  "blocked_tools": ["execute_code", "delete_database", "drop_table", "shell_exec", "rm_rf"]
}
```

**`require_review_for_external_calls`** — `tool_pattern`, `review`, `high`
```json
{
  "tool_name_contains": ["http_request", "webhook", "external_api"]
}
```

**`allow_standard_tools`** — default allow; no condition; all unmatched tool calls pass through.

---

## Creating a policy

### Via the dashboard

Open the **Policy Manager** tab at `http://localhost:8501`. Fill in the form — the condition field updates with an example when you select a rule type. Click **Create Policy**. It takes effect immediately.

### Via the API

```
POST /policies
Authorization: Bearer <admin-token>
Content-Type: application/json
```

```json
{
  "name": "block_unscoped_crm_query",
  "description": "Prevent CRM queries without a filter — blocks bulk data exposure",
  "rule_type": "tool_denylist",
  "condition": {
    "blocked_tools": ["query_accounts"],
    "parameter_match": { "filter": null }
  },
  "action": "deny",
  "severity": "critical",
  "compliance_frameworks": ["SOC2", "GDPR"]
}
```

Response `201`:

```json
{
  "id": "9a3b1c2d-...",
  "name": "block_unscoped_crm_query",
  "rule_type": "tool_denylist",
  "condition": { "blocked_tools": ["query_accounts"], "parameter_match": { "filter": null } },
  "action": "deny",
  "severity": "critical",
  "active": true,
  "compliance_frameworks": ["SOC2", "GDPR"]
}
```

---

## Updating a policy

All fields are optional. Changes take effect in OPA immediately.

```
PUT /policies/{policy_id}
Authorization: Bearer <admin-token>
```

```json
{
  "active": false
}
```

To add a tool to an existing blacklist, update the full `condition` object:

```json
{
  "condition": {
    "blocked_tools": ["query_accounts", "query_all_leads"]
  }
}
```

---

## Disabling and deleting

To temporarily suspend a policy without deleting it, set `active: false`:

```
PUT /policies/{policy_id}
{ "active": false }
```

To permanently delete:

```
DELETE /policies/{policy_id}
```

Response `204`. Takes effect in OPA immediately.

---

## How evaluation works

When an agent calls `/intercept`, AIControl loads all active policies and evaluates them in order against the tool name and parameters. The first matching policy wins.

Evaluation order:
1. `tool_denylist` policies — checked first; produce `deny`
2. `tool_pattern` policies — checked second; produce `review`
3. Default allow — if nothing matches, decision is `allow`

The policy that fires is recorded in the audit event as `policy_name` and `policy_id`. If no policy matches, both are null.

---

## Policy and compliance frameworks

The `compliance_frameworks` field is metadata — it does not affect evaluation, but it is recorded in every audit event where that policy fires. This enables compliance exports filtered by framework (e.g. "show me all SOC2-relevant deny events from the last 30 days").

Supported values are free-form strings. Common values used by existing customers: `SOC2`, `GDPR`, `HIPAA`, `ISO27001`, `CCPA`, `EU_AI_Act`.

---

## Full policy examples by use case

**Block all bulk data operations:**
```json
{
  "name": "block_bulk_operations",
  "rule_type": "tool_denylist",
  "condition": { "blocked_tools": ["bulk_export", "export_all_records", "mass_delete"] },
  "action": "deny",
  "severity": "critical",
  "compliance_frameworks": ["SOC2", "GDPR"]
}
```

**Flag any outbound HTTP call for review:**
```json
{
  "name": "review_outbound_http",
  "rule_type": "tool_pattern",
  "condition": { "tool_name_contains": ["http", "webhook", "fetch", "request"] },
  "action": "review",
  "severity": "high",
  "compliance_frameworks": ["SOC2"]
}
```

**Block unfiltered database queries (parameter-level):**
```json
{
  "name": "require_query_filter",
  "rule_type": "tool_denylist",
  "condition": {
    "blocked_tools": ["query_database", "search_records"],
    "parameter_match": { "filter": null }
  },
  "action": "deny",
  "severity": "high",
  "compliance_frameworks": ["GDPR"]
}
```
