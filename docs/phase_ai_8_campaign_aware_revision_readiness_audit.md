## Phase AI.8.1 — Campaign-aware revision readiness audit (freeze)

This audit freezes **prompt/context quality** for agent chat revisions (Phase AI.8). AI.8 does **not** expand agent write permissions — it injects a compact campaign revision context before the LLM may call `content_asset.create_revision`.

Human approve, schedule, and publish remain **UI-only**.

**Superseded for orchestrator behavior by:** AI.9 / AI.9.1 (`docs/phase_ai_9_marketing_orchestrator_readiness_audit.md`).

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.7** | Chat `content_asset.create_revision`; copywriter / content_planner / orchestrator |
| **AI.7.1** | Revision write-boundary freeze (`docs/phase_ai_7_revision_readiness_audit.md`) |
| **AI.8** | `app/agents/revision_context.py` — campaign-aware context in chat prompt |
| **AI.8.1** | This document — context size, leak boundaries, no new writes |

---

## Revision context builder

**Module:** `app/agents/revision_context.py`  
**Entry:** `build_campaign_revision_context(session, owner_id, project_id, campaign_id, current_asset_id=...)`  
**Injection:** `AgentChatService.send_message` when `agent_chat_revision_tools_enabled()` and `campaign_id` is set → `agent_chat.revision_context` in run `input_payload`.

**Size limit:** `REVISION_CONTEXT_MAX_BYTES = 8192` (8 KB UTF-8 JSON).  
**Trim:** `trim_revision_context()` may set `context_truncated: true` and shrink examples, previews, and optional blocks.

**Missing campaign:** `missing_campaign_revision_context()` when campaign row not found — empty messaging fields, `campaign_missing: true`, still ≤ 8 KB.

---

## Allowed context fields

| Field | Source | Notes |
|-------|--------|-------|
| `campaign_title` | `MarketingCampaignTable.title` | Truncated |
| `campaign_description` | Campaign description | Truncated (max 600 chars before trim) |
| `workflow_state` | `CampaignWorkflowService.get_workflow` | Enum string |
| `target_audience` | Latest plan draft `plan_payload` | Extracted via `CampaignPlanPayloadShape` — **not** full payload |
| `key_message` | Plan draft | Same |
| `channel` | First `content_items[].channel` or asset metadata / type | String |
| `approved_assets_examples` | Approved campaign assets | Max **3**; `title`, `body_preview`, `channel`, `asset_id` only |
| `current_asset` | Target asset or sole draft | Snapshot: `body_preview`, not full `body` |
| `campaign_history` | `CampaignOverviewService` counts | **Counts only** — no job rows, no delivery logs |
| `campaign_missing` | Fallback only | Boolean when campaign absent |
| `context_truncated` | Trim path only | Boolean when size limit applied |

Plan messaging uses `extract_plan_messaging()` — never embeds `plan_payload` or `content_items` arrays in revision context.

---

## Read tools (unchanged write boundary)

AI.8 adds **one read tool** to the revision chat profile only:

| Tool | Mode |
|------|------|
| `marketing_campaign.overview` | read_only |

Existing revision profile (AI.7 + AI.8):

| Tool | Mode |
|------|------|
| `marketing_campaign.get` | read_only |
| `marketing_campaign.workflow` | read_only |
| `marketing_campaign.overview` | read_only |
| `campaign_asset.list` | read_only |
| `content_asset.get` | read_only |
| `content_asset.create_revision` | write (**only** chat write for revision profile) |

Set: `AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES` in `app/tools/agent_chat_tool_settings.py`.

---

## Copywriter prompt rules (AI.8)

When `revision_tools` and `AgentType.COPYWRITER`, system content includes `_AGENT_CHAT_CAMPAIGN_AWARE_COPYWRITER_RULES`:

- Consistent campaign tone and style
- Align with `workflow_state` and **Campaign revision context** block
- Use campaign `key_message`; do not contradict it
- Do not change the offer unless the user explicitly asks
- Do not invent facts, discounts, dates, or guarantees
- Prefer `approved_assets_examples` as style references

Built by `build_agent_chat_workflow_system_content()` in `app/prompts/agent_chat_workflow.py` (via `message_builder.py`).

---

## Explicit no-goals (AI.8.1 freeze)

| Action | Status |
|--------|--------|
| Approve assets | **Forbidden** — no `content_asset.approve` in chat |
| Schedule publication | **Forbidden** — no schedule tools in chat |
| Publish / dispatch | **Forbidden** — no publish tools in chat |
| New write tools | **Forbidden** — AI.8 added **zero** write tools |
| Full `plan_payload` in prompt context | **Forbidden** — only extracted fields |
| `content_items` array in context | **Forbidden** |
| Channel config / credentials | **Forbidden** |
| Delivery logs / `recent_jobs` detail | **Forbidden** in revision context |
| Campaign status changes via agent | **Forbidden** — no campaign write tools in chat |

`marketing_campaign.overview` tool output strips `campaign_metadata` at executor level (unchanged); revision context builder never copies overview `recent_jobs` into prompt context.

---

## What AI.8 did **not** change

- Feature flags (same as AI.7 revision)
- Agent allowlist (copywriter / content_planner / orchestrator)
- `AgentChatSendResponse.revised_assets` shape (`asset_id`, `version` only)
- Approve / schedule / publish paths

---

## Related freezes

| Doc | Boundary |
|-----|----------|
| `docs/phase_ai_7_revision_readiness_audit.md` | Semantic revision write freeze |
| `docs/phase_12_asset_revision_tools_readiness_audit.md` | Non-chat revision tool |
| `docs/phase_ai_6_agent_chat_generate_assets_readiness_audit.md` | Bulk generate |

---

## Future work (not AI.8.1)

- **AI.9** — marketing orchestrator scenarios (prompt-only; shipped separately)
- Chat approve / schedule / publish — **out of scope**

---

## Freeze checklist

```bash
uv run pytest tests/test_campaign_aware_revision_context.py
uv run pytest tests/test_agent_chat_revision_tool.py
uv run pytest tests/test_phase_ai_7_revision_invariants.py
uv run pytest tests/test_phase_ai_8_campaign_aware_revision_invariants.py
```
