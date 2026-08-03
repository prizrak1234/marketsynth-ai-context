## Phase 9.4 — Campaigns readiness audit (freeze)

Phase 9 turns campaigns into a **real container** above briefs, assets, and publication jobs.
This audit freezes the expected behavior **before** any AI planning is introduced.

### Scope

- Campaign domain model and lifecycle
- Brief binding (optional)
- Asset/job binding (Phase 9.1)
- Campaign overview read model (Phase 9.2)
- Campaign operational metrics (Phase 9.3)
- Calendar campaign filter (Phase 9.1)
- Archived rules
- No AI generation/planning in Phase 9
- No leaks of asset body/version body/channel config/delivery logs

---

## Domain model

Entity: `MarketingCampaign`

Key fields:

- `id`, `owner_id`, `project_id`
- `brief_id | null` (if set, must belong to same project)
- `title`, `description | null`
- `status`: `draft | active | paused | completed | archived`
- `start_at | null`, `end_at | null` (timezone-aware, normalized to UTC)
- `campaign_metadata: dict`
- `created_at`, `updated_at`

### Status lifecycle rules (Phase 9)

- Campaigns are editable while not archived.
- `archived` is terminal for writes: archived campaigns are read-only.
- Archiving uses a dedicated endpoint: `POST /.../campaigns/{id}/archive`

---

## Brief binding

- `brief_id` is optional.
- If provided, brief must belong to the same `owner_id + project_id`.

---

## Asset/job binding (Phase 9.1)

### Assets

- `content_assets.campaign_id` is nullable.
- If provided at create/update, it must belong to the same project.
- Archived campaigns cannot be used for new/updated assets.

### Publication jobs

- `publication_jobs.campaign_id` is nullable.
- On job creation:
  - if asset has `campaign_id` → job inherits it automatically
  - if request provides `campaign_id` → it must match `asset.campaign_id` (otherwise 409)
  - if asset has no campaign → request must not set `campaign_id` (409)

---

## Campaign overview (Phase 9.2)

Endpoint:

- `GET /projects/{project_id}/campaigns/{campaign_id}/overview`

Behavior:

- read-only, owner/project/campaign scoped
- archived campaign is readable
- counts and schedule are computed using only assets/jobs bound to this `campaign_id`
- `recent_jobs` is limited to 10, sorted by `created_at desc`

No leaks:

- no asset body
- no asset version body
- no channel config
- no delivery logs content in response

---

## Campaign operational metrics (Phase 9.3)

Included in:

- `GET /projects/{project_id}/operational-metrics`
- `GET /me/operational-metrics`

Block:

```json
{
  "campaigns": {
    "total": 0,
    "draft": 0,
    "active": 0,
    "paused": 0,
    "completed": 0,
    "archived": 0,
    "active_with_scheduled_jobs": 0,
    "active_without_approved_assets": 0
  }
}
```

Rules:

- owner-scoped only
- `active_with_scheduled_jobs`: active campaign with at least one job `status=scheduled`
- `active_without_approved_assets`: active campaign with no approved assets
- counts only (no `campaign_metadata` output)

---

## Calendar campaign filter (Phase 9.1)

Endpoint:

- `GET /projects/{project_id}/publication-calendar?campaign_id=...`

Behavior:

- filter is optional
- response items include `campaign_id` and `campaign_title`
- must not expose asset body or channel config

---

## Archived campaign rules

- Archived campaigns can be read (GET/list/overview/metrics).
- Archived campaigns cannot be updated.
- Archived campaigns cannot be used when creating/updating assets via `campaign_id`.

---

## Explicit non-goals (Phase 9)

- No AI campaign planning agent.
- No AI content generation.
- No performance analytics (CTR/views/conversions).
- No auto-publishing changes beyond existing publishing layer rules.

---

## Freeze checklist

```bash
uv run pytest tests/test_marketing_campaigns.py
uv run pytest tests/test_campaign_binding.py
uv run pytest tests/test_campaign_overview.py
uv run pytest tests/test_campaign_metrics.py
uv run pytest tests/test_phase_9_campaigns_invariants.py
```

