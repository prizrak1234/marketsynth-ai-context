# PRODUCT-01 — Owner Acceptance Runbook

**Work package:** PRODUCT-01.2  
**Status:** `pending_owner_acceptance`  
**Skill (frozen):** `ms.skill.offer_builder` 0.1.0 · hash `b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4`

---

## Prerequisites

| Item | Requirement |
|------|-------------|
| Database | PostgreSQL with migrations at head (`20260724_0059`) |
| Backend | Python 3.12, `uv sync --extra dev` |
| Frontend | Node 20+, `cd web && npm install` |
| Auth | Valid pilot user (not mock integration mode) |
| E2E | `CPH3_E2E_EMAIL` + `CPH3_E2E_PASSWORD` in environment |

---

## A1 — PostgreSQL migration verification

```bash
# Start isolated PostgreSQL (example — adjust credentials)
docker run --rm -d --name marketsynth-pg-migrate-test \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=marketsynth_migrate_test \
  -p 5433:5432 postgres:16

export DATABASE_URL="postgresql+asyncpg://postgres:test@localhost:5433/marketsynth_migrate_test"

uv run python scripts/verify_product_01_postgres_migration.py
# Expect: "status": "passed", "final_revision": "20260724_0059"

# Optional downgrade check
export PRODUCT_01_VERIFY_DOWNGRADE=true
uv run python scripts/verify_product_01_postgres_migration.py
```

**Do not** use `create_all` as migration proof.

---

## A2 — Live stack

### Backend

```bash
cd botfazer   # repo root
cp .env.example .env   # configure DATABASE_URL, secrets
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify: `GET http://127.0.0.1:8000/health` (or project health endpoint).

### Frontend

```bash
cd web
# Ensure API points to backend (not mock)
npm run dev -- --port 3000
```

Verify in browser DevTools:

- `marketsynth.integration.mode.v1` = `backend`
- No `NEXT_PUBLIC_*` secrets in UI copy
- No package hashes or Skill IDs in customer views

---

## A3 — Focused E2E

```bash
cd web
export CPH3_E2E_EMAIL="your-pilot-user@example.com"
export CPH3_E2E_PASSWORD="your-password"
export CPH2_BACKEND_URL="http://127.0.0.1:8000"
export CPH2_FRONTEND_URL="http://127.0.0.1:3000"

npm run test:e2e -- e2e/product-01-offer-builder.spec.ts
```

If credentials missing → status `blocked_by_missing_e2e_credentials` (do not mark passed).

---

## A4 — Owner click-through checklist

### A. Main journey

- [ ] Open `/workspace`
- [ ] Start BIV («Проверить идею»)
- [ ] Receive `proceed` or `proceed_with_conditions`
- [ ] Click «Подготовить запуск» (`data-testid="cwf-cta-prepare_launch"`)
- [ ] Observe building state (`cwf-offer-building`)
- [ ] Offer review card appears (`offer-review-card`)
- [ ] Bridge notice visible (`offer-upstream-bridge-notice`)
- [ ] Approve (`offer-approve-btn`)
- [ ] Reload page — approved badge persists (`offer-approved-badge`)

### B. Revision

- [ ] «Запросить доработку» with comment
- [ ] Version increments; history shows prior version
- [ ] New version unapproved

### C. Rejection

- [ ] Reject current version
- [ ] Correct state and next action

### D. Blocked verdict

- [ ] Non-eligible verdict → blocker, no Offer card

### E. UI hygiene

- [ ] Russian customer labels
- [ ] No Skill IDs, package hashes, env var names, raw JSON, provider traces
- [ ] No redirect to generic assistant from Launch Pack panel

Record outcome in [PRODUCT-01-OWNER-ACCEPTANCE.md](./PRODUCT-01-OWNER-ACCEPTANCE.md).

---

## A5 — Backend regression (before sign-off)

```bash
uv run pytest tests/test_product_01_offer_builder_cwf.py -q
uv run pytest tests/test_cwf_1a_launch_pack_decision.py -q
uv run pytest tests/test_skill_02_8_offer_builder.py -q
uv run ruff check app/product/offer_builder app/api/routes/offers.py app/services/launch_pack_service.py
cd web && npm run typecheck
```

---

## Stop gates

| Gate | Owner action required |
|------|----------------------|
| PostgreSQL migration | Disposable Postgres + run verification script |
| E2E | Pilot credentials |
| Acceptance | Manual browser checklist |
| Freeze | Explicit `accepted` in acceptance doc |

Cursor must **not** set `owner_acceptance=accepted` without owner confirmation.
