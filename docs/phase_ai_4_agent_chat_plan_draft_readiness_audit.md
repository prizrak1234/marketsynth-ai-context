## Phase AI.4 — Agent chat plan-draft readiness audit (freeze)

This audit freezes the **agent chat write boundary** before any bulk-write path (e.g. `campaign_plan_draft.generate_assets` as an agent tool or chat-exposed bulk generation).

Chat may create **one** artifact type via tools: **campaign plan draft**. Everything else remains human-initiated in the product UI or non-chat agent runs.

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.1** | Chat pipe: `POST /projects/{id}/agent-chat`, sessions, messages, `AgentRun` on user message, assistant from run output, PII sanitize, no tools by default |
| **AI.2** | Optional `campaign_id` → workflow context in `input_payload.agent_chat`; prompt guidance for strategist / orchestrator / content_planner |
| **AI.3** | Gated chat tool profile: `campaign_plan_draft.create` + `marketing_campaign.get` + `marketing_campaign.workflow`; structured `plan_draft` in API response; UI CTA to campaign plan drafts |

---

## Required feature flags (all four)

Chat write tools are **off by default**. All must be `true`:

| Env variable | Config field | Role |
|--------------|--------------|------|
| `AGENT_WRITE_TOOLS_ENABLED=true` | `agent_write_tools_enabled` | Global agent write gate |
| `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED=true` | `agent_write_tool_campaign_plan_draft_create_enabled` | Plan draft write gate (Phase 10.2) |
| `AGENT_CHAT_TOOLS_ENABLED=true` | `agent_chat_tools_enabled` | Chat-only tool profile (Phase AI.3) |
| `TOOLS_PROVIDER_ENABLED=true` | `tools_provider_enabled` | LLM tool rounds (dry-run / production) |

Implementation: `app/tools/agent_chat_tool_settings.py` → `agent_chat_tools_enabled()`.

Non-chat agent runs are **unchanged**: they use full `get_tool_registry().list_for_agent()` unless `run_metadata.agent_chat` is set (chat runs only).

---

## Chat tool allowlist

Only these tools may be exposed on **`agent_chat`** runs (when flags + agent type allow):

| Tool | Mode | Purpose |
|------|------|---------|
| `campaign_plan_draft.create` | write | Persist plan draft; `source_agent_run_id` from run context only |
| `marketing_campaign.get` | read_only | Campaign summary for selected campaign |
| `marketing_campaign.workflow` | read_only | Workflow state / next action for chat advice |

Source of truth: `AGENT_CHAT_TOOL_NAMES` in `app/tools/agent_chat_tool_settings.py`.  
Executor: `AgentRunExecutor` calls `list_tools_for_agent_chat()` when `run_metadata.agent_chat` is true.

### Agent types

**Allowed** (when all flags on):

- `strategist`
- `orchestrator`
- `content_planner`

**Denied** (empty chat tool list):

- `copywriter`
- `analyst`
- `researcher`
- `critic`

---

## Explicit no-goals (AI.4 chat freeze)

Agent chat must **not**:

| Action | Status |
|--------|--------|
| Bulk **Generate Assets** from plan (`generate-assets` HTTP or agent tool) | **Not in chat** — HTTP `POST .../plan-drafts/{id}/generate-assets` exists (Phase 11) but is **not** registered as an agent tool and **not** in `AGENT_CHAT_TOOL_NAMES` |
| Create content assets via chat | **Forbidden** — `content_asset.create_draft` not in chat profile |
| Approve assets | **Forbidden** — no `content_asset.approve` tool |
| Schedule publication | **Forbidden** — no schedule agent tools |
| Publish / dispatch | **Forbidden** — no publish agent tools |
| Other write tools (`memory.write`, revisions, etc.) | **Not in chat profile** |

`campaign_plan_draft.create` persists a **planning artifact** only. A successful chat run must **not** create content assets or publication jobs as side effects.

Human next step after draft: **Generate Assets** in campaign UI (not via chat).

---

## Response and leak boundaries

- Tool success envelope (compact): `draft_id`, `campaign_id`, `status`, `created_at` — **no** full `plan_payload` (`format_campaign_plan_draft_create_result`).
- API `AgentChatSendResponse.plan_draft`: `draft_id`, `campaign_id`, optional `title` — structured, not parsed from assistant prose.
- Assistant message: confirms creation, `draft_id`, next step Generate Assets; must not embed full plan JSON.
- Tool execution **audit log** required for real tool calls (`ToolExecutionLogService`).

---

## UI boundary

`/agents/chat`:

- Optional campaign selector + workflow badge (AI.2).
- When `plan_draft` present in response → link to `/campaigns/{id}#create-plan-draft` (AI.3).
- No approve / schedule / publish / generate-assets actions in chat UI.

---

## Related freezes (do not bypass)

| Doc | Boundary |
|-----|----------|
| `docs/phase_10_campaign_planner_tools_readiness_audit.md` | Plan draft create tool (non-chat agents) |
| `docs/phase_11_plan_draft_assets_readiness_audit.md` | HTTP bulk generate-assets |
| `docs/phase_13_campaign_workflow_readiness_audit.md` | Workflow read tool; forbidden bulk/approve tools |
| `docs/phase_14_review_queue_readiness_audit.md` | Human review; no agent approve |

---

## Future work (not AI.4)

- Agent or chat exposure of **generate-assets** (bulk write) — separate phase, separate flag, explicit UX consent.
- Chat approve / schedule / publish — out of scope; violates product safety model.

---

## Freeze checklist

```bash
uv run pytest tests/test_agent_chat.py
uv run pytest tests/test_agent_chat_workflow_context.py
uv run pytest tests/test_agent_chat_plan_draft_tool.py
uv run pytest tests/test_phase_ai_4_agent_chat_plan_draft_invariants.py
```
