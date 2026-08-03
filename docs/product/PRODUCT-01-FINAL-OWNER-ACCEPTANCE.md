# PRODUCT-01 — Final Owner Acceptance (Index)

**Work package:** PRODUCT-01.2  
**Status:** `pending_owner_acceptance`

This document indexes the owner acceptance gate. Detailed steps live in:

- [PRODUCT-01-OWNER-ACCEPTANCE-RUNBOOK.md](./PRODUCT-01-OWNER-ACCEPTANCE-RUNBOOK.md) — commands and stack
- [PRODUCT-01-OWNER-ACCEPTANCE.md](./PRODUCT-01-OWNER-ACCEPTANCE.md) — decision template

---

## What must pass before freeze

1. PostgreSQL Alembic `20260724_0059` verified (not SQLite `create_all`)
2. Live stack E2E: `web/e2e/product-01-offer-builder.spec.ts`
3. Owner browser click-through recorded as **`accepted`**
4. Scoped backend tests + ruff + typecheck green

---

## What Cursor must not do

- Set `owner_acceptance=accepted` without owner confirmation
- Mark E2E passed without credentials and live stack
- Change frozen Offer Skill bytes (`b637c392…`)

---

## After owner accepts

Update:

- `packages/product/product_01_offer_builder/0.1.0/acceptance_manifest.json`
- [PRODUCT-01-FREEZE-AUDIT.md](./PRODUCT-01-FREEZE-AUDIT.md) → `frozen_commercial_slice`
- `AGENTS.md` active track (Offer Builder closed)

Next product phase (both gates): **PRODUCT-MEDIA-01** — not Content Strategy / Copywriting.
