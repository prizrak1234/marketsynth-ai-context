## Phase AI.7.1 — Agent chat content revision readiness audit (freeze)

This audit freezes the **first semantic content-write boundary** in agent chat: agents may rewrite asset body text via `content_asset.create_revision`. This is higher risk than plan drafts (AI.3) or bulk generate (AI.5) because it changes **meaning**, not only structure.

Human approve, schedule, and publish remain **UI-only** (`/review`, campaign assets, publication calendar).

**Superseded for context quality by:** AI.8 / AI.8.1 (`docs/phase_ai_8_campaign_aware_revision_readiness_audit.md`).

---

## What changed after AI.7

| Before AI.7 | After AI.7 |
|-------------|------------|
| Campaign → Plan → Draft assets | Campaign → Draft assets → **Rewrite content** |
| Agent creates structures | Agent edits **semantic** copy |

This is the first **content agent** in chat — infrastructure must be frozen before quality work (AI.8).

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.1** | Chat pipe, sessions, `AgentRun`, sanitize, no tools by default |
| **AI.2** | Optional `campaign_id` → workflow context |
| **AI.3** | `campaign_plan_draft.create` + campaign read tools |
| **AI.5** | `campaign_plan_draft.generate_assets` (orchestrator / content_planner) |
| **AI.6** | Generate-assets freeze (`docs/phase_ai_6_agent_chat_generate_assets_readiness_audit.md`) |
| **AI.7** | `content_asset.create_revision` in chat (copywriter / content_planner / orchestrator) |

---

## AI.7 scope (allowed)

### Write tool (chat only)

| Tool | Mode | Purpose |
|------|------|---------|
| `content_asset.create_revision` | write | Apply new `body` (optional `title`, `metadata_patch`); uses `ContentAssetService.apply_agent_content_revision` |

### Read tools (revision profile)

| Tool | Mode |
|------|------|
| `marketing_campaign.get` | read_only |
| `marketing_campaign.workflow` | read_only |
| `content_asset.get` | read_only |
| `campaign_asset.list` | read_only |

Source: `AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES` in `app/tools/agent_chat_tool_settings.py`.  
Executor: `AgentRunExecutor` → `list_tools_for_agent_chat()` when `run_metadata.agent_chat` is true.

### Agent types

**Allowed** (when all revision flags on):

- `copywriter`
- `content_planner`
- `orchestrator`

**Denied** (empty chat tool list for revision profile):

- `strategist`
- `researcher`
- `critic`
- `analyst`

Chat allowlist is **narrower** than Phase 12 non-chat revision (`CREATE_REVISION_ALLOWED_AGENT_TYPES` may still include strategist/critic outside chat).

### User instruction

Revision intent is conveyed in **chat message** text. The tool still requires explicit `body` (and `asset_id`); the LLM must read the asset (`content_asset.get` / `campaign_asset.list`) then call `create_revision` with the full revised body.

### Campaign cap

Prompt guidance: max **20** draft assets revised per run (`AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS` in `app/services/agent_chat_revision.py`). Default `MAX_TOOL_CALLS_PER_ROUND` may be lower — operational limit is the stricter of the two.

---

## Feature flags

### Base (chat tool rounds)

| Env variable | Config field | Role |
|--------------|--------------|------|
| `AGENT_WRITE_TOOLS_ENABLED=true` | `agent_write_tools_enabled` | Global agent write gate |
| `AGENT_CHAT_TOOLS_ENABLED=true` | `agent_chat_tools_enabled` | Chat-only tool profiles |
| `TOOLS_PROVIDER_ENABLED=true` | `tools_provider_enabled` | LLM tool rounds |

Implementation: `_agent_chat_base_enabled()` in `app/tools/agent_chat_tool_settings.py`.

### Content revision (AI.7)

| Env variable | Config field |
|--------------|--------------|
| `CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED=true` | `agent_write_tool_content_asset_revision_enabled` |

`agent_chat_revision_tools_enabled()` = base + revision write flag.

**Independent:** revision does **not** require plan-draft create or generate-assets flags. Profiles compose per agent type when multiple flags are on.

All relevant flags default to **`false`**.

---

## Explicit no-goals (AI.7.1 chat freeze)

Agent chat must **not**:

| Action | Status |
|--------|--------|
| Approve assets | **Forbidden** — no `content_asset.approve` in chat profile |
| Schedule publication | **Forbidden** — no `content_asset.schedule` / `publication_job.schedule` in chat profile |
| Publish / dispatch | **Forbidden** — no `content_asset.publish` |
| Create publication jobs | **Forbidden** — no `publication_job.create` |
| Archive / delete assets | **Forbidden** — no archive/delete agent tools in chat profile |
| Auto-approve revised content | **Forbidden** — revisions stay `draft` until human approve |
| `campaign_plan_draft.create` / `generate_assets` | **Separate flags** — not implied by revision flag |

---

## Revision behavior (domain)

`apply_agent_content_revision` (`app/services/content_asset_service.py`):

| Source status | Effect |
|---------------|--------|
| **draft** | Update **same** asset id; new version row; status stays `draft` |
| **approved** | New **draft** revision asset (`create_revision_from_approved`); source approved asset unchanged |
| **archived** | Rejected (`InvalidStateError`) |

No publication jobs, approval, schedule, publish, or archive on the revision path.

---

## Response and leak boundaries

### Tool result (compact)

`format_content_asset_create_revision_result`:

- `asset_id`, `status`, `current_version_number`, `approved_version_number`
- **No** full `body`, `versions`, or plan JSON in tool envelope

### Audit preview

`app/tools/audit_preview.py` → `_build_create_revision_result_preview`:

- `asset_id`, `current_version_number`, `ok` / `error_code`
- **No** body text in `result_preview`

### API `AgentChatSendResponse.revised_assets`

Per item (`AgentChatRevisedAsset`):

```json
{ "asset_id": "...", "version": 4 }
```

`version` maps to `current_version_number` from tool log preview. **No** full body in structured chat response — UI uses asset id + version for CTAs (`/assets/{id}`, Review Queue).

### Assistant messages (AI.7)

- Success: RU copy — draft updated + Review Queue guidance (`format_revision_chat_assistant_message`)
- Structured `revised_assets` only — UI must not parse assistant prose for asset ids

---

## MVP agent loop (frozen context, not new code)

```
Chat → Plan → Generate → Revise → Review Queue → Human Approve → Schedule
```

AI.7.1 documents the **Revise** step boundary only. Steps after Review Queue stay human/UI.

---

## UI boundary

`/agents/chat`:

- `revised_assets` → **Open Asset** + **Open Review Queue**
- No approve / schedule / publish / archive in chat

---

## Observability

Every successful or failed tool round writes **`ToolExecutionLog`** (`ToolExecutionLogService`). Chat revision tests assert logs for `content_asset.create_revision` with compact preview.

---

## Related freezes

| Doc | Boundary |
|-----|----------|
| `docs/phase_ai_6_agent_chat_generate_assets_readiness_audit.md` | Bulk generate; no revision |
| `docs/phase_12_asset_revision_tools_readiness_audit.md` | Non-chat revision tool + read matrix |
| `docs/phase_14_review_queue_readiness_audit.md` | Human review; no agent approve |

---

## Future work (not AI.7.1)

- **AI.8 / AI.8.1** — campaign-aware revision context freeze: `docs/phase_ai_8_campaign_aware_revision_readiness_audit.md`
- Chat approve / schedule / publish — **out of scope**

---

## Freeze checklist

```bash
uv run pytest tests/test_agent_chat_revision_tool.py
uv run pytest tests/test_phase_ai_7_revision_invariants.py
uv run pytest tests/test_agent_chat.py
uv run pytest tests/test_agent_chat_generate_assets_tool.py
uv run pytest tests/test_phase_ai_6_agent_chat_generate_assets_invariants.py
```
