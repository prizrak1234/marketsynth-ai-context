# PRODUCT-01.1 — Offer Builder Acceptance and Production Hardening

**Status:** implemented (owner click-through pending)  
**Migration:** `20260724_0059` (`20260724_0059_offer_builder_product_01.py`)  
**Offer package hash (unchanged):** `b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4`

## Objective

Close PRODUCT-01 for production deployment: mandatory Alembic migration, scoped lint green, bridge semantics, state/concurrency/recovery hardening, tests, and customer UI acceptance.

## Migration (mandatory)

Revision `20260724_0059` creates:

| Table | Purpose |
|-------|---------|
| `offer_artifacts` | One offer per Launch Pack |
| `offer_artifact_versions` | Immutable version history |
| `offer_review_events` | Approve / reject / revision audit |
| `commercial_upstream_snapshots` | Upstream inputs with bridge metadata |

Indexes: `owner_id`, `project_id`, `launch_pack_id`, `status`, `created_at`, `source_mode`.  
Unique: launch pack per offer, owner+idempotency, version number, review decision per version, upstream artifact type per launch pack.

```bash
uv run alembic upgrade head   # PostgreSQL production path
```

SQLite dev DB uses `create_all` in tests; Alembic full chain requires PostgreSQL (legacy migrations use SQLite-incompatible ALTER).

## Bridge semantics

| Field | Values |
|-------|--------|
| `source_mode` | `native_skill_output` \| `bridged_biv_snapshot` |
| BIV bridge | `bridge_version=product-01-biv-bridge-v1`, `replacement_required=true` |

Bridged artifacts are **not** reported as executed Positioning, Claim Substantiation, or CIM Skills. UI shows `offer-upstream-bridge-notice`; API returns `upstream_sources[]` on `OfferArtifactDetail`.

## Workflow transitions

```
requested → building_offer → offer_review_required → offer_approved
offer_review_required → revision_required → building_offer → offer_review_required
offer_review_required → offer_rejected
```

Invalid transitions → HTTP 409 `invalid_workflow_transition`.

## Recovery

`POST /projects/{id}/offers/{offer_id}/recover` reconciles stuck `building_offer` or failed generation without auto-regenerating paid work.

## Verification

```bash
uv run pytest tests/test_product_01_offer_builder_cwf.py -q
uv run pytest tests/test_cwf_1a_launch_pack_decision.py -q
uv run ruff check app/product/offer_builder app/api/routes/offers.py app/db/models/offer_artifact.py app/db/models/commercial_upstream_snapshot.py app/db/repositories/offer_artifacts.py app/services/launch_pack_service.py
cd web && npm run typecheck
cd web && npm run test:e2e -- e2e/product-01-offer-builder.spec.ts
```

## Owner click-through (manual)

1. `/workspace` → BIV → eligible verdict  
2. **Подготовить запуск** → building → Offer review card  
3. Approve → reload → approved state  
4. Revision / rejection paths  
5. Blocked verdict → no Offer  

**Result:** pending owner sign-off in browser.

## Known limitations

- Upstream Positioning / Claims / CIM remain BIV-bridged until dedicated Skill runtimes (PRODUCT-02+).
- Alembic on SQLite fails at legacy migration `20260602_0003` — use PostgreSQL for migration verification.
- E2E requires live stack + `CPH3_E2E_EMAIL` / `CPH3_E2E_PASSWORD`.

## Out of scope (confirmed)

No Content Strategy, Copywriting, Launch Strategy, publication, Higgsfield, Connector/MCP, new Skills, or frozen package changes.
