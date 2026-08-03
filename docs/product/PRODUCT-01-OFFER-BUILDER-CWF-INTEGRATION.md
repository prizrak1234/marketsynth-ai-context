# PRODUCT-01 — Offer Builder Runtime and CWF Integration

**Status:** PRODUCT-01.1 hardening complete — owner acceptance pending  
**Follow-up:** [PRODUCT-01.1-ACCEPTANCE-AND-PRODUCTION-HARDENING.md](./PRODUCT-01.1-ACCEPTANCE-AND-PRODUCTION-HARDENING.md)  
**Skill:** `ms.skill.offer_builder` 0.1.0 (frozen, unchanged)  
**Package hash:** `b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4`  
**Migration:** `20260724_0059` (mandatory for production DB)

## Objective

Wire the frozen Offer Builder contract into CWF Launch Pack so that an eligible BIV verdict produces a persisted Offer artifact, human review, and Launch Pack workflow progression — without Content Strategy, Copywriting, publication, or Connector execution.

## Customer journey

1. BIV returns eligible verdict (`proceed` / `proceed_with_conditions`).
2. User clicks **Подготовить запуск**.
3. Launch Pack request is created; Offer Builder runs automatically.
4. Persisted Offer appears in workspace with review UI.
5. User approves, rejects, or requests revision (hash-safe).
6. Launch Pack advances to `offer_approved` — **not** complete Launch Pack.

## Runtime architecture

```
app/product/offer_builder/
├── eligibility.py      # pure BIV→MV gate
├── input_builder.py    # upstream from BIV bridge (+ future skill artifacts)
├── bridge.py           # bridged_biv_snapshot metadata (PRODUCT-01.1)
├── transitions.py      # workflow guards + 409 transitions
├── adapter.py          # deterministic output from frozen fixture + context
├── output_validation.py
├── service.py          # orchestration + persistence
├── lineage.py
└── contracts.py
```

No generic Skill loader. No package byte changes.

## CWF state progression

`requested → building_offer → offer_review_required → offer_approved → ready_for_next_stage`

Blocked: `blocked_by_verdict`, `blocked_by_missing_positioning`, `blocked_by_claims`, `blocked_by_evidence`, `offer_generation_failed`, `offer_rejected`, `revision_required`.

## API

- `POST /projects/{id}/launch-packs/{lp_id}/offer`
- `GET  /projects/{id}/launch-packs/{lp_id}/offer`
- `GET  /projects/{id}/offers/{offer_id}`
- `GET  /projects/{id}/offers/{offer_id}/versions`
- `POST /projects/{id}/offers/{offer_id}/approve`
- `POST /projects/{id}/offers/{offer_id}/reject`
- `POST /projects/{id}/offers/{offer_id}/request-revision`
- `POST /projects/{id}/offers/{offer_id}/recover`

## Bridge labeling (PRODUCT-01.1)

Upstream snapshots expose `source_mode`: `native_skill_output` or `bridged_biv_snapshot`. BIV-derived Positioning / Claims / CIM are bridged — not native Skill executions. See `upstream_sources` on offer detail.

## UI

- `launch-pack-decision-panel.tsx` — offer build/blocked states
- `offer-review-card.tsx` — preview + approve/reject/revision
- `offer-detail-view.tsx`, `offer-version-history.tsx`

## Out of scope (PRODUCT-01)

Content Strategy, Copywriting, Launch Strategy posts/visuals, Higgsfield, Connector/MCP, publication, Skill marketplace.

## Verification

```bash
uv run pytest tests/test_product_01_offer_builder_cwf.py tests/test_cwf_1a_launch_pack_decision.py tests/test_skill_02_8_offer_builder.py -q
uv run alembic upgrade head   # PostgreSQL
uv run ruff check app/product/offer_builder app/api/routes/offers.py app/services/launch_pack_service.py
cd web && npm run typecheck
cd web && npm run test:e2e -- e2e/product-01-offer-builder.spec.ts
```
