## Phase 11.2 — Plan draft asset generation readiness audit (freeze)

Phase 11 turns an approved **campaign plan draft** into **draft content assets** mechanically (no LLM).
This audit freezes HTTP behavior **before** any agent tool (`campaign_plan_draft.generate_assets`) or bulk automation.

### Scope

- `POST .../plan-drafts/{draft_id}/generate-assets` (Phase 11.0)
- Idempotency and partial-state protection (Phase 11.1)
- No agent tools for generation in this freeze

---

## Endpoint

`POST /projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets`

- Owner / project / campaign scoped; wrong scope → **404**
- Success body (compact — **no** `plan_payload`):

```json
{
  "created_count": 3,
  "asset_ids": ["..."],
  "already_generated": false
}
```

- First creation → **201 Created**
- Idempotent replay (full set already exists) → **200 OK**, `created_count: 0`, `already_generated: true`

---

## Generation rules (Phase 11.0)

| Rule | Behavior |
|------|----------|
| Source | Only `plan_payload.content_items[]` on the plan draft |
| Asset status | Always `ContentAssetStatus.DRAFT` |
| `campaign_id` | Set to the campaign on the plan draft |
| `brief_id` | Inherited from `campaign.brief_id` when present |
| `scheduled_at` | Stored only as `metadata.planned_scheduled_at` — **no** publication job |
| Mapping | One `content_item` → one asset; `body` = item `notes` or `""` |
| Channel/format | Stored in asset `metadata`; asset `type` resolved mechanically by channel |
| Max items | **50** per call (`PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS`) |
| Empty items | **409** |
| LLM | **None** — mechanical mapping only |

Metadata written per asset:

- `source_plan_draft_id`
- `plan_item_index`
- `channel`, `format`
- `planned_scheduled_at` (when present on the item)

---

## Idempotency (Phase 11.1)

Within a **single DB transaction**:

1. Load existing draft assets for this campaign where `metadata.source_plan_draft_id == draft_id`.
2. **None** → create all items.
3. **Full set** (count matches `content_items`, indices `0..N-1`) → return existing `asset_ids`, `created_count: 0`, `already_generated: true`.
4. **Partial set** (some but not all) → **409** `plan_draft_generation_partial_state` — do **not** create the remainder.

No `regenerate` / `force` in this freeze.

---

## Conflict rules (409)

| Condition | Detail |
|-----------|--------|
| Campaign archived | Cannot generate |
| Plan draft archived | Cannot generate |
| Empty `content_items` | Cannot generate |
| More than 50 items | Cannot generate |
| Partial prior generation | `plan_draft_generation_partial_state` |

---

## Explicit no-goals (freeze)

| Action | Status |
|--------|--------|
| Approve assets | **Not** called by generate |
| Publish / dispatch | **Not** called |
| Schedule publication jobs | **Not** called (`planned_scheduled_at` is metadata only) |
| LLM text generation | **Not** implemented |
| Agent tool `campaign_plan_draft.generate_assets` | **Not registered** (future gated tool only after review) |
| `asset.create_from_plan` | **Not implemented** |
| `regenerate` / `force` replay | **Not implemented** |

`content_asset.create_draft` (Phase 4.2) remains a separate write gate for single manual/agent drafts.

---

## Version / approval invariants

- Generate creates assets with `approved_version_number = null`, `current_version_number = 1`.
- Generate does **not** approve, archive, or revise existing assets.
- Human `POST .../content-assets/{id}/approve` after generate follows the normal approval path unchanged.

---

## No leaks

Generate-assets response must **not** include:

- Full `plan_payload`
- `content_items` bodies from the plan
- Asset full bodies (only `asset_ids` returned)

---

## Agent tool boundary (post-freeze consideration)

`campaign_plan_draft.generate_assets` is **intentionally omitted** from the tool registry.
Bulk asset creation is higher risk than `campaign_plan_draft.create` (plan artifact only).
Any future tool needs:

- Separate feature flag
- Tight allowlist
- Same idempotency / partial-state rules as HTTP
- No bypass of human approval before publish

---

## Freeze checklist

```bash
uv run pytest tests/test_plan_draft_generate_assets.py
uv run pytest tests/test_plan_draft_generate_assets_idempotency.py
uv run pytest tests/test_phase_11_plan_draft_assets_invariants.py
```
