## Phase AI.6 — Agent chat bulk-write readiness audit (freeze)

This audit freezes the **agent chat write boundary** after plan-draft create (AI.3) and bulk **generate assets** (AI.5). Chat may materialize draft content assets from a plan draft; it must **not** approve, schedule, publish, or create publication jobs.

Human review and publication remain **UI-only** (`/review`, campaign assets, publication calendar).

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.1** | Chat pipe: `POST /projects/{id}/agent-chat`, sessions, messages, `AgentRun` on user message, assistant from run output, PII sanitize, no tools by default |
| **AI.2** | Optional `campaign_id` → workflow context in `input_payload.agent_chat`; prompt guidance for strategist / orchestrator / content_planner |
| **AI.3** | Gated chat profile: `campaign_plan_draft.create` + `marketing_campaign.get` + `marketing_campaign.workflow`; structured `plan_draft` in API response; UI CTA to campaign plan drafts |
| **AI.5** | Gated chat bulk-write: `campaign_plan_draft.generate_assets` (orchestrator / content_planner only); structured `generated_assets` in API response; UI CTAs to Review Queue and campaign assets |

---

## Feature flags

### Base (chat tool rounds)

| Env variable | Config field | Role |
|--------------|--------------|------|
| `AGENT_WRITE_TOOLS_ENABLED=true` | `agent_write_tools_enabled` | Global agent write gate |
| `AGENT_CHAT_TOOLS_ENABLED=true` | `agent_chat_tools_enabled` | Chat-only tool profiles |
| `TOOLS_PROVIDER_ENABLED=true` | `tools_provider_enabled` | LLM tool rounds |

Implementation: `_agent_chat_base_enabled()` in `app/tools/agent_chat_tool_settings.py`.

### Plan draft create (AI.3)

| Env variable | Config field |
|--------------|--------------|
| `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED=true` | `agent_write_tool_campaign_plan_draft_create_enabled` |

`agent_chat_tools_enabled()` = base + plan draft write flag.

### Generate assets (AI.5)

| Env variable | Config field |
|--------------|--------------|
| `CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED=true` | `agent_write_tool_campaign_plan_draft_generate_assets_enabled` |

`agent_chat_generate_assets_tools_enabled()` = base + generate flag.

**Independent:** generate assets does **not** require `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED`. Plan create and generate are separate gates.

All relevant flags default to **`false`**.

---

## Chat tool allowlists

Source: `app/tools/agent_chat_tool_settings.py`.  
Executor: `AgentRunExecutor` uses `list_tools_for_agent_chat()` when `run_metadata.agent_chat` is true.

### Plan draft create profile

When plan-create flags + agent type allow:

| Tool | Mode |
|------|------|
| `campaign_plan_draft.create` | write |
| `marketing_campaign.get` | read_only |
| `marketing_campaign.workflow` | read_only |

**Agent types:** `strategist`, `orchestrator`, `content_planner`.

Set: `AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES`.

### Generate assets profile

When generate flags + agent type allow:

| Tool | Mode |
|------|------|
| `campaign_plan_draft.generate_assets` | write |
| `marketing_campaign.get` | read_only |
| `marketing_campaign.workflow` | read_only |

**Agent types:** `orchestrator`, `content_planner` only (**not** strategist).

Set: `AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES`.

### Input contract (generate assets)

- Required: `campaign_id`, `draft_id`
- **Forbidden:** `project_id` (scope from `ToolExecutionContext`)
- Reuses `CampaignPlanDraftService.generate_assets` (same as HTTP `POST .../plan-drafts/{id}/generate-assets`)

### Denied agent types (chat)

`copywriter`, `analyst`, `researcher`, `critic` — empty chat tool list when flags on.

---

## Explicit no-goals (AI.6 chat freeze)

Agent chat must **not**:

| Action | Status |
|--------|--------|
| Approve assets | **Forbidden** — no `content_asset.approve` in chat profile or registry |
| Schedule publication | **Forbidden** — no schedule agent tools in chat profile |
| Publish / dispatch | **Forbidden** — no publish agent tools |
| Create publication jobs | **Forbidden** — generate path does not enqueue jobs |
| Auto-approve generated assets | **Forbidden** — assets stay `draft` status |
| `content_asset.create_draft` / revisions via chat | **Not in chat profile** |
| `memory.write`, `task.create`, legacy writes | **Not in chat profile** |

`campaign_plan_draft.generate_assets` creates **draft** content assets only. Idempotent replay returns existing asset IDs without new jobs.

Human next step after generate: **Review Queue** (`/review`) → approve in UI.

---

## Response and leak boundaries

### Tool result (compact)

`format_campaign_plan_draft_generate_assets_result`:

- `created_count`
- `already_generated`
- `asset_ids` (string UUIDs)

**No** `plan_payload`, `content_items`, `goal`, `target_audience`, or full plan JSON in tool envelope or audit preview.

### API `AgentChatSendResponse.generated_assets`

- `campaign_id`, `draft_id`, `created_count`, `already_generated`, `asset_ids`
- Structured only — UI CTAs must not parse assistant prose

### Assistant messages (AI.5)

- Success: draft count + Review Queue guidance (RU copy in service)
- Idempotent: already generated + Review Queue

### Errors

- Partial existing assets → `plan_draft_generation_partial_state` → error envelope (`invalid_arguments`)
- Archived campaign/draft → error envelope
- Tool execution **audit log** required (`ToolExecutionLogService`)

---

## UI boundary

`/agents/chat`:

- Campaign selector + workflow badge (AI.2)
- `plan_draft` → campaign plan drafts CTA (AI.3)
- `generated_assets` → **Open Review Queue** + **Open Campaign Assets** (AI.5)
- No approve / schedule / publish controls in chat

---

## Related freezes

| Doc | Boundary |
|-----|----------|
| `docs/phase_ai_4_agent_chat_plan_draft_readiness_audit.md` | Plan draft create-only freeze (superseded for generate by AI.6) |
| `docs/phase_11_plan_draft_assets_readiness_audit.md` | HTTP bulk generate-assets |
| `docs/phase_13_campaign_workflow_readiness_audit.md` | Workflow read; gated generate tool |
| `docs/phase_14_review_queue_readiness_audit.md` | Human review; no agent approve |

---

## Future work (not AI.6)

- **AI.7 / AI.7.1** — agent-assisted revision freeze: `docs/phase_ai_7_revision_readiness_audit.md`
- Chat approve / schedule / publish — **out of scope**; human/UI only

---

## Freeze checklist

```bash
uv run pytest tests/test_agent_chat.py
uv run pytest tests/test_agent_chat_workflow_context.py
uv run pytest tests/test_agent_chat_plan_draft_tool.py
uv run pytest tests/test_agent_chat_generate_assets_tool.py
uv run pytest tests/test_phase_ai_6_agent_chat_generate_assets_invariants.py
```
