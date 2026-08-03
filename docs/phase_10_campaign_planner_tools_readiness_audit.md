## Phase 10.3 — Campaign planner tools readiness audit (freeze)

Phase 10 gives marketing agents **read-only campaign context** and a **gated write path** to persist a **plan draft** artifact only.
This audit freezes boundaries **before** Phase 11 (`asset.create_from_plan` or any auto-generation from plans).

### Scope

- Read-only campaign agent tools (Phase 10.0)
- Campaign plan draft HTTP API (Phase 10.1)
- Gated write tool `campaign_plan_draft.create` (Phase 10.2)
- Agent allowlists, feature flags, audit, and leak boundaries

---

## Read-only campaign tools (Phase 10.0)

Registered and executable (owner/project scoped, standard tool envelope):

| Tool | Purpose |
|------|---------|
| `marketing_campaign.get` | Single campaign summary |
| `marketing_campaign.list` | List campaigns (compact, no `campaign_metadata`) |
| `marketing_campaign.overview` | Aggregated counts / recent jobs for one campaign |
| `publication_calendar.list` | Scheduled/queued/running jobs (optional `campaign_id` filter) |

Execution mode: **read_only** (`metadata.access_mode` / `REAL_READ_ONLY_EXECUTABLE_TOOLS`).

### Read visibility by agent type

| Agent type | Campaign tools |
|------------|----------------|
| strategist | get, list, overview, calendar |
| orchestrator | get, list, overview, calendar |
| content_planner | get, list, overview, calendar |
| analyst | get, list, overview, calendar |
| copywriter | get, list, calendar (**no** `marketing_campaign.overview`) |
| critic | none |
| researcher | none |

Context comes from run scope (`owner_id`, `project_id`); tools do not accept `owner_id` / `project_id` in arguments (except where explicitly required for write — see below).

---

## Gated write tool: `campaign_plan_draft.create` (Phase 10.2)

- **Mode**: `write` (real executor, not a no-op stub).
- **Service**: `CampaignPlanDraftService` (same rules as HTTP API).
- **Input**: `project_id`, `campaign_id`, `title`, `plan_payload` (`goal`, `target_audience`, `key_message`, `content_items[]`).
- **`source_agent_run_id`**: taken **only** from `ToolExecutionContext.agent_run_id` — **not** accepted in tool arguments.
- **Success envelope** (compact): `draft_id`, `campaign_id`, `status`, `created_at` — **no** full `plan_payload` in tool result.
- **Audit**: tool execution log required (`execution_mode=write`).

### Write feature flags (both required)

| Env variable | Config field |
|--------------|--------------|
| `AGENT_WRITE_TOOLS_ENABLED=true` | `agent_write_tools_enabled` |
| `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED=true` | `agent_write_tool_campaign_plan_draft_create_enabled` |

If global write is off → tool hidden and calls denied (`write_tool_disabled` audit reason).
If specific flag is off → same.

### Allowlist (write tool visibility + execution)

**Allowed** (when flags on):

- `strategist`
- `orchestrator`
- `content_planner`

**Denied** (never see `campaign_plan_draft.create`):

- `copywriter`
- `analyst`
- `researcher`
- `critic`

Note: `content_asset.create_draft` remains a **separate** write gate (Phase 4.2) with its own allowlist; campaign planner freeze does not expand copywriter write beyond existing rules.

---

## Plan draft HTTP API (Phase 10.1)

Under `POST/GET .../campaigns/{campaign_id}/plan-drafts` (owner/project/campaign scoped):

- Create/list/get/archive plan drafts
- Archived campaign → **409** on create
- Secret-like keys in `plan_payload` → **409**
- `plan_payload` JSON size limit **32 KB**
- `source_agent_run_id` validated on HTTP (must belong to owner/project)

Agents use the **tool** path above; HTTP remains for operators/tests.

---

## Explicit no-goals (Phase 10 planner freeze)

Agents with campaign planner tools must **not**:

| Action | Status |
|--------|--------|
| Create content assets (from plan or otherwise via new tools) | **Not implemented** — no `asset.create_from_plan` |
| Create publication jobs | **Not via tools** |
| Approve assets | **Forbidden** (`content_asset.approve` not registered) |
| Publish / dispatch | **Forbidden** |
| Schedule jobs | **Not via tools** (HTTP scheduling unchanged) |
| Update/archive assets via agent tools | **Forbidden** |

`campaign_plan_draft.create` persists a **planning artifact** only — no assets, no jobs, no outbox side effects.

---

## No leaks (tool outputs and audit previews)

Must not expose in campaign read tools or compact create result:

- asset **body**
- asset **version body**
- channel **config** (tokens, webhook secrets)
- delivery **logs** content
- `campaign_metadata` (tools use `format_marketing_campaign_safe`)
- full `plan_payload` in success tool envelope (draft row may store payload server-side; tool returns compact fields only)

`plan_payload` validation rejects secret-like keys at create time (HTTP and tool).

---

## Phase 11 boundary

HTTP `generate-assets` (Phase 11.0–11.2) is frozen in `docs/phase_11_plan_draft_assets_readiness_audit.md`.
No agent tool for bulk generation in that freeze. Future agent access must not bypass idempotency, partial-state rules, or human approval before publish.

---

## Freeze checklist

```bash
uv run pytest tests/test_campaign_readonly_tools.py
uv run pytest tests/test_campaign_plan_drafts.py
uv run pytest tests/test_campaign_plan_draft_create_tool.py
uv run pytest tests/test_phase_10_campaign_planner_invariants.py
```
