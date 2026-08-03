## Phase 14.3 — Review Queue readiness audit (freeze)

Phase 14 introduces a **human review queue** read model: what content awaits an owner decision before approve/publish. Workflow (Phase 13 + **14.2**) now uses the same pending predicate so `ready_for_review` reflects the real queue, not version heuristics alone.

This audit freezes review-queue diagnostics **before** any agent approve/publish/schedule tools or human-approval automation via agents.

### Scope

- Phase **14.0** — `GET /projects/{project_id}/review-queue`, `ReviewQueueService`, `review_queue.pending_assets` in operational metrics
- Phase **14.1** — `review_queue.list` read tool (strategist, orchestrator, content_planner, analyst)
- Phase **14.2** — `CampaignWorkflowService` ↔ `ReviewQueueService`; `counts.pending_review_assets`; `human_review_required`

---

## Pending review criterion

Implemented in `app/domain/review_queue.py` → `asset_requires_human_review()` and mirrored in `ContentAssetRepository._pending_human_review_filter()`.

An asset is **in the queue** when:

| Condition |
|-----------|
| `status = draft` **and** `approved_version_number is null` |
| **or** `status = draft` **and** `current_version_number > approved_version_number` |

**Not included** (Phase 14.0 scope): publication jobs, campaigns, plan drafts, webhook deliveries, archived assets.

**Excluded after human approve:** `status = approved` (no longer draft).

---

## HTTP API

| Method | Path | Auth | Service |
|--------|------|------|---------|
| `GET` | `/projects/{project_id}/review-queue` | Owner | `ReviewQueueService.get_queue` |

Response: `items[]` with `type`, `id`, `campaign_id`, `campaign_title`, `title`, `status`, `current_version_number`, `created_at`, `updated_at`.

**Read-only** — no `POST`/`PATCH`/`DELETE` on `/review-queue`.

---

## Agent tool: `review_queue.list`

| Property | Value |
|----------|--------|
| Mode | `read_only` |
| Service | `ReviewQueueService.list_for_tool` |
| Arguments | `limit` only (default **50**, max **200**); `project_id` forbidden — scope from run context |
| Output | `{ items: [...], count: N }` — `count` = total pending in project; items sorted `updated_at desc`, capped by `limit` |
| Item fields (tool) | No `created_at`; no bodies |

### Allowlist / denylist

| Agent type | `review_queue.list` |
|------------|---------------------|
| strategist | yes |
| orchestrator | yes |
| content_planner | yes |
| analyst | yes |
| copywriter | **no** |
| researcher | **no** |
| critic | **no** |

---

## Workflow integration (Phase 14.2)

`GET /projects/{project_id}/campaigns/{campaign_id}/workflow` and `marketing_campaign.workflow` include:

```json
"counts": {
  "pending_review_assets": 3,
  ...
}
```

**State priority** (`compute_campaign_workflow`):

1. `completed` — highest
2. **`pending_review_assets > 0`** → `ready_for_review`, `next_recommended_action = human_review_required`
3. `approved_for_publication` — all active assets approved, queue empty for campaign
4. `content_in_revision` / `assets_generated` / `plan_ready` / `planning`

`pending_review_assets` is counted per **campaign** via `ReviewQueueService.count_pending_assets(..., campaign_id=...)`.

---

## Operational metrics

`GET /projects/{project_id}/operational-metrics` includes:

```json
"review_queue": {
  "pending_assets": 12
}
```

Project-scoped total (all campaigns). Owner-wide `/me/operational-metrics` uses `pending_assets: 0` when no `project_id` in build path.

---

## Explicit no-goals (freeze)

| Capability | Status |
|------------|--------|
| `review_queue.approve` | **Not registered** |
| Agent `content_asset.approve` | **Not registered** |
| Agent publish / schedule tools | **Not registered** |
| `publication_job.create` / `schedule` via agent | **Not registered** |
| Review queue mutations (approve via queue API) | **Not implemented** |
| Persist queue rows in DB | **Not implemented** (computed from assets) |

Product boundary: **Agent → Draft** · **Human → Approve (HTTP/UI)** · **System → Publish**. Agents may **list** what awaits review; they cannot clear the queue.

---

## No leaks (API + tools)

Must **not** appear in review-queue HTTP responses, `review_queue.list`, or workflow outputs:

| Forbidden content |
|-------------------|
| Asset `body` |
| Version bodies / `versions[]` |
| `plan_payload` |
| Channel `config` (tokens) |
| Publication delivery logs |
| `campaign_metadata` secrets |

---

## Audit logging

`review_queue.list` executions are recorded via `ToolExecutionLogService` when the executor uses `audit_service` (same as other real read-only tools).

---

## Related tests

| Suite | Focus |
|-------|--------|
| `tests/test_review_queue.py` | HTTP queue, metrics, scope, leaks |
| `tests/test_review_queue_tool.py` | Tool list, limit, allowlist, audit |
| `tests/test_campaign_workflow.py` | Workflow + `pending_review_assets` |
| `tests/test_campaign_workflow_tool.py` | Workflow tool compact output |
| `tests/test_phase_14_review_queue_invariants.py` | Freeze invariants |

---

## Freeze checklist

```bash
uv run pytest tests/test_review_queue.py
uv run pytest tests/test_review_queue_tool.py
uv run pytest tests/test_campaign_workflow.py
uv run pytest tests/test_campaign_workflow_tool.py
uv run pytest tests/test_phase_14_review_queue_invariants.py
```

**Not in this freeze:** `review_queue.approve`, agent approve/publish/schedule, review-queue write APIs, agent-driven approval automation.
