## Phase 12.2 — Asset revision tools readiness audit (freeze)

Phase 12 gives agents **read-only** access to campaign content assets and a **gated write** path for draft revisions only.
This audit freezes agent tool behavior **before** any approve, publish, schedule, or publication-job tools.

### Scope

- Phase **12.0** — `content_asset.get`, `content_asset.list`, `campaign_asset.list`
- Phase **12.1** — `content_asset.create_revision` (gated write)
- HTTP approve / publish / schedule unchanged (human-only product boundary)

---

## Read-only asset tools (Phase 12.0)

| Tool | Mode | Purpose |
|------|------|---------|
| `content_asset.get` | `read_only` | Single asset; optional `include_body` |
| `content_asset.list` | `read_only` | Project list; filters `brief_id`, `campaign_id`, `status`, `type` |
| `campaign_asset.list` | `read_only` | Assets for one `campaign_id` (required) |

### Read rules

- Owner / project scope from run context (not tool arguments).
- **List** — `body_preview` + safe `metadata` preview only; **no** full `body`.
- **Get** — full `body` only when `include_body=true` **and** agent type is in body allowlist.
- **No** version history array or historical version bodies in tool output.
- **No** secrets in metadata preview (`_redacted` when sensitive keys detected).

### Read allowlist

| Agent type | `get` | `list` / `campaign_asset.list` | `get` + `include_body` |
|------------|-------|--------------------------------|-------------------------|
| copywriter | yes | yes | yes |
| content_planner | yes | yes | yes |
| strategist | yes | yes | yes |
| orchestrator | yes | yes | yes |
| critic | yes | yes | yes |
| analyst | no | yes | no |
| researcher | no | no | no |

---

## Gated write: `content_asset.create_revision` (Phase 12.1)

| Flag | Required value |
|------|----------------|
| `AGENT_WRITE_TOOLS_ENABLED` | `true` |
| `CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED` | `true` |

Both must be set; otherwise the tool is **hidden** from agent allowlists and **rejected** at execution.

### Write allowlist / denylist

**Allowed:** copywriter, content_planner, strategist, orchestrator, critic  

**Denied:** analyst, researcher (and any type not in `CREATE_REVISION_ALLOWED_AGENT_TYPES`)

### Input schema

```json
{
  "project_id": "<uuid>",
  "asset_id": "<uuid>",
  "body": "<required>",
  "title": "<optional>",
  "metadata_patch": {}
}
```

**Forbidden in arguments** (rejected at parse): `owner_id`, `agent_id`, `agent_run_id`, `run_id`, `task_id`, `source_agent_run_id`, `brief_id`, `campaign_id`, `status`, revision lineage fields.

`project_id` must match run context `project_id`.

### Revision behavior

| Source asset status | Action | `approved_version_number` on source |
|---------------------|--------|-----------------------------------|
| **draft** | New draft **version** on same asset (`current_version_number` += 1) | unchanged (`null`) |
| **approved** | New **draft revision** asset linked to source | **unchanged** (pinning preserved) |
| **archived** | **Rejected** (`invalid_asset_state`) | — |

- `body` required; max length `AGENT_WRITE_TOOL_BODY_MAX_CHARS`.
- Secret-like content in `body` or sensitive keys in `metadata_patch` → reject.
- `source_agent_run_id` written to **version metadata** from run context only (never from tool input).
- **Does not** change `campaign_id` or `brief_id` on draft in-place updates.
- **Does not** create publication jobs, approve, publish, or schedule.

### Compact success response

```json
{
  "asset_id": "...",
  "status": "draft",
  "current_version_number": 4,
  "approved_version_number": null
}
```

No full `body`, no `versions[]`, no version bodies in tool output.

---

## Explicit no-goals (freeze)

| Action | Agent tool status |
|--------|-------------------|
| `content_asset.approve` | **Not registered** — human API only |
| `content_asset.publish` | **Not registered** |
| Schedule / create publication jobs | **Not registered** |
| `publication_job.create` / `schedule` | **Not registered** |
| Reassign `campaign_id` / `brief_id` via revision tool | **Blocked** (forbidden args + service does not relink) |
| Change asset `status` via revision tool | **Blocked** |
| Bulk `campaign_plan_draft.generate_assets` agent tool | **Not registered** (Phase 11 freeze) |

Product boundary: agents may **read** and **propose edits** (draft revisions); humans **approve** before publish.

---

## Audit logging

All real read-only asset tool executions and `content_asset.create_revision` writes are recorded via `ToolExecutionLogService` when the executor is constructed with `audit_service`.

Argument/result previews must not leak full bodies or secrets (see `app/tools/audit_preview.py` patterns).

---

## Related tests

| Suite | Focus |
|-------|--------|
| `tests/test_campaign_asset_read_tools.py` | Phase 12.0 read tools |
| `tests/test_content_asset_create_revision_tool.py` | Phase 12.1 write tool |
| `tests/test_phase_12_asset_revision_invariants.py` | Freeze invariants |

---

## Freeze checklist

```bash
uv run pytest tests/test_campaign_asset_read_tools.py
uv run pytest tests/test_content_asset_create_revision_tool.py
uv run pytest tests/test_phase_12_asset_revision_invariants.py
```

Not in this freeze: agent approve/publish/schedule tools, publication automation from revisions, `campaign_plan_draft.generate_assets` tool.
