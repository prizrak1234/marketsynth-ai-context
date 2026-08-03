## Phase 13.2 — Campaign workflow readiness audit (freeze)

Phase 13 adds a **machine-readable campaign execution workflow** (read model) and an agent **diagnostics tool** so specialists can see lifecycle state and the next recommended step **without** bulk writes, approve, publish, or schedule.

This audit freezes workflow diagnostics **before** any agent `campaign_plan_draft.generate_assets` bulk-write tool.

### Scope

- Phase **13.0** — `CampaignWorkflowState`, pure `compute_campaign_workflow()`, `GET /projects/{project_id}/campaigns/{campaign_id}/workflow` (no DB persistence of state)
- Phase **13.1** — `marketing_campaign.workflow` read tool + prompt guidance (strategist, orchestrator, content_planner)

---

## Workflow state model

Enum `CampaignWorkflowState` (`app/schemas/contracts.py`):

| State | Meaning |
|-------|---------|
| `planning` | No plan drafts |
| `plan_ready` | Plan draft(s) exist; no campaign assets yet |
| `assets_generated` | Assets exist; no revision activity after generation |
| `content_in_revision` | Draft assets + revision activity; not all assets review-ready |
| `ready_for_review` | All active draft assets have revision activity; none approved |
| `approved_for_publication` | All active assets approved |
| `completed` | Every active campaign asset has at least one `SUCCEEDED` publication job |

Recommended next step enum `CampaignWorkflowRecommendedAction`: `create_plan_draft`, `generate_assets`, `review_assets`, `approve_assets`, `schedule_publication`, `monitor_publication`, `none`.

**Revision activity** (per asset): `current_version_number > 1` or `source_asset_id` set.

**Counts** (non-archived assets): `plan_drafts`, `assets_total`, `assets_approved`, `assets_draft`.

---

## Compute priority (highest wins)

Evaluated in `app/domain/campaign_workflow.py` → `compute_campaign_workflow()`:

1. `completed` — all active asset IDs ⊆ assets with `SUCCEEDED` publication jobs
2. `approved_for_publication` — `assets_total > 0` and all counted assets approved
3. `ready_for_review` — drafts only, revision activity, every active draft has revision activity
4. `content_in_revision` — drafts only, revision activity, not all review-ready
5. `assets_generated` — `assets_total > 0`, no revision activity yet
6. `plan_ready` — `plan_drafts > 0`, no assets
7. `planning` — default

Pure function: **no** SQLAlchemy session, **no** writes.

---

## HTTP API (human / product)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `GET` | `/projects/{project_id}/campaigns/{campaign_id}/workflow` | Owner | `CampaignWorkflowService.get_workflow`; 404 if campaign not in scope |

Response: `campaign_id`, `workflow_state`, `counts`, `next_recommended_action`.

**Read-only** — no `POST`/`PATCH`/`DELETE` on this path.

---

## Agent tool: `marketing_campaign.workflow`

| Property | Value |
|----------|--------|
| Mode | `read_only` |
| Service | `CampaignWorkflowService` (same compute as HTTP) |
| Arguments | `campaign_id` only (`project_id` forbidden — scope from run context) |
| Output | Compact: `campaign_id`, `workflow_state`, `next_recommended_action`, `counts` |

### Allowlist / denylist

| Agent type | Tool exposed |
|------------|--------------|
| strategist | yes |
| orchestrator | yes |
| content_planner | yes |
| analyst | yes |
| copywriter | **no** |
| researcher | **no** |
| critic | **no** |

Copywriter retains `marketing_campaign.get` / `list` / calendar (no overview, no workflow) to limit context size.

### Prompt guidance (Phase 13.1)

Included in default system prompts for **strategist**, **orchestrator**, **content_planner** (`app/prompts/templates.py`):

- Before proposing campaign actions, call `marketing_campaign.workflow` when `campaign_id` is available.
- Never approve, publish, schedule, or claim execution unless a tool/API result confirms it.

---

## Explicit no-goals (freeze)

| Capability | Status |
|------------|--------|
| Agent `content_asset.approve` | **Not registered** |
| Agent publish / schedule tools | **Not registered** |
| Agent `publication_job.create` / `schedule` | **Not registered** |
| Agent `campaign_plan_draft.generate_assets` (bulk write) | **Not registered** |
| Persist `CampaignWorkflowState` in DB | **Not implemented** |
| Workflow endpoint mutating campaigns/assets/plans/jobs | **Not implemented** |

Product boundary unchanged: agents **diagnose** lifecycle; humans **approve** and **publish**; bulk asset generation from plan remains HTTP-only until a future gated phase.

---

## No leaks (API + tool)

Must **not** appear in workflow HTTP responses or `marketing_campaign.workflow` tool output:

| Forbidden content |
|-------------------|
| `plan_payload` (goal, audience, items, notes) |
| Asset `body` / version bodies |
| `campaign_metadata` secrets |
| Channel `config` (tokens) |
| Publication delivery logs |

Allowed: state enums, counts, `campaign_id`, recommended action string.

---

## Audit logging

`marketing_campaign.workflow` executions are recorded via `ToolExecutionLogService` when the executor is constructed with `audit_service` (same pattern as other real read-only marketing tools).

---

## Related tests

| Suite | Focus |
|-------|--------|
| `tests/test_campaign_workflow.py` | HTTP workflow states, scope, leaks |
| `tests/test_campaign_workflow_tool.py` | Agent tool behavior, allowlist, audit |
| `tests/test_phase_13_campaign_workflow_invariants.py` | Freeze invariants |

---

## Freeze checklist

```bash
uv run pytest tests/test_campaign_workflow.py
uv run pytest tests/test_campaign_workflow_tool.py
uv run pytest tests/test_phase_13_campaign_workflow_invariants.py
```

**Not in this freeze:** agent bulk-write `campaign_plan_draft.generate_assets`, approve/publish/schedule agent tools, persisting workflow state to DB.
