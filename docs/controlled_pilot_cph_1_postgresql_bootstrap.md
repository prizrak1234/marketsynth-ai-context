# CPH.1 — PostgreSQL pilot bootstrap

## Goal

Reproducible empty PostgreSQL → Commercial MVP schema at `20260614_0036` (or authorized successor). **Not SQLite.**

## Preconditions

- PostgreSQL 15+ (validated on 17.10 Windows).
- App role can connect; **CREATEDB not required** if a superuser creates the DB once.
- Code at Commercial MVP freeze / CPH.1 (Alembic head `20260614_0036`).
- Do **not** bootstrap into `botfazer`, `postgres`, `template0`, `template1`.

## One-time create (superuser)

```sql
CREATE DATABASE botfazer_cph1 OWNER botfazer;
-- optional: CREATE DATABASE botfazer_pilot OWNER botfazer;
```

Or:

```bash
# SUPERUSER_DATABASE_URL must not be committed; local env only
uv run python scripts/cph1_try_create_disposable.py
# or
uv run python scripts/cph1_db_tools.py create-disposable --db botfazer_cph1
```

(`create-disposable` refuses forbidden names.)

## Bootstrap

PowerShell:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://botfazer:<pwd>@localhost:5432/botfazer_cph1"
uv run powershell -File scripts/cph1_bootstrap_pilot.ps1
```

Shell:

```bash
export DATABASE_URL="postgresql+asyncpg://botfazer:<pwd>@localhost:5432/botfazer_cph1"
bash scripts/cph1_bootstrap_pilot.sh
```

Steps performed:

1. `alembic upgrade head`
2. `cph1_db_tools.py check-revision` → expect `current` / `20260614_0036`
3. `cph1_db_tools.py schema-parity` → commercial tables present

## Extensions

Default public schema is enough for this codebase (no custom extension required in CPH.1). If future phases need `pgcrypto` / `uuid-ossp`, add explicitly and document.

## Application

Point `.env` `DATABASE_URL` at the disposable/pilot DB. Start API:

```bash
uv run uvicorn app.main:app --reload
```

Startup runs **read-only** Alembic revision check (never auto-migrate / auto-stamp). For pilot/staging set:

```
ALEMBIC_REVISION_CHECK_ENABLED=true
ALEMBIC_REVISION_FAIL_FAST=true
```

## Seed

Only non-sensitive demo if explicitly supported (e.g. `scripts/seed_e2e_demo.py`). Do not dump production PII into pilot DB.

## Health / validation

```bash
uv run python scripts/cph1_db_tools.py check-revision
uv run python scripts/cph1_db_tools.py schema-parity
$env:CPH1_POSTGRES_URL=$env:DATABASE_URL
uv run pytest tests/test_controlled_pilot_cph_1_postgresql_smoke.py -q
```

## Validated on this machine

| Check | Result |
|-------|--------|
| `botfazer_cph1` upgrade head | OK → `20260614_0036` |
| Schema parity commercial tables | OK |
| Partial downgrade `0036→0034` + re-upgrade | OK |
| ORM ProjectBrief smoke | OK |
| SQLite as pilot baseline | **Rejected** |
