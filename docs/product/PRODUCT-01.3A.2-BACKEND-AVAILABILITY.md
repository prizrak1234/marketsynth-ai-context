# PRODUCT-01.3A.2 — Backend Availability and Migration Repair

**Status:** implemented (awaiting owner re-smoke)  
**Blocks:** PRODUCT-01.3A re-smoke PASS, PRODUCT-01.3B

## Root cause (re-smoke FAIL)

Two independent failures were confirmed:

1. **Stale Uvicorn on port 8000** — process started 2026-07-23 from commit `006b087`, before PRODUCT-01.3A routes. `/openapi.json` on that process has **no** `analysis-contexts` paths.
2. **Database behind code head** — PostgreSQL `botfazer_cph1` at `20260723_0057`; required head is `20260724_0060` (`analysis_contexts` table + BIV bridge columns).

Frontend 01.3A.1 behaved correctly (intake form, customer-safe error). Failure was backend availability, not intake UX.

## Owner repair checklist

### A. Stop stale backend

Ensure only one process binds `127.0.0.1:8000`. Check:

```http
GET http://127.0.0.1:8000/health/runtime
```

If `git_commit` is older than current checkout or `analysis_context_subsystem.ready` is false — stop that process and restart from repo root.

### B. PostgreSQL (pilot / CPH local)

```powershell
uv run alembic current
uv run alembic heads          # expect 20260724_0060
uv run alembic upgrade head
```

### C. SQLite (development only)

Full Alembic chain may fail on legacy SQLite FK migrations. Use repair bootstrap:

```powershell
uv run python scripts/repair_product_01_3a_dev_db.py --fresh
```

This runs `SQLModel.metadata.create_all`, stamps Alembic head, and verifies `analysis_contexts` + BIV bridge columns.

### D. Start backend

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Startup log must include:

- `Application startup complete`
- `analysis_context_subsystem_ready`

### E. Verify before smoke

| Check | URL / command | Pass |
|-------|----------------|------|
| OpenAPI | `http://127.0.0.1:8000/openapi.json` | JSON loads |
| Routes | paths contain `/projects/{project_id}/analysis-contexts` | yes |
| Runtime | `GET /health/runtime` | `expected_alembic_head=20260724_0060`, `analysis_context_subsystem.ready=true` |
| Readiness | `GET /health/ready` | `analysis_context_subsystem` component ok/warn |

## What was added in code

| Artifact | Purpose |
|----------|---------|
| `scripts/repair_product_01_3a_dev_db.py` | SQLite dev repair (create_all + stamp head) |
| `app/services/analysis_context_subsystem_readiness.py` | Table/column probe |
| `app/db/migration_helpers.py` | Idempotent Alembic helpers |
| `app/services/pilot_readiness.py` | `analysis_context_subsystem` component |
| `app/main.py` lifespan | startup log + repair hint |
| `app/api/health.py` `/health/runtime` | owner diagnostics |
| `tests/test_product_01_3a_backend_availability.py` | migrated DB integration |
| Alembic `20260602_0003`, `20260724_0060` | SQLite-safe / idempotent upgrades |

## Regression

```powershell
uv run pytest tests/test_product_01_3a_backend_availability.py tests/test_product_01_3a_biv_intake_gate.py -q
```

## Next

1. Owner re-smoke PRODUCT-01.3A (intake → confirm → BIV blocked until confirmed).
2. Only after PASS → PRODUCT-01.3B evidence integrity.
