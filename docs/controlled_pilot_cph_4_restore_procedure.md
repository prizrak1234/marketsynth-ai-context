# CPH.4 — Restore procedure

## Prerequisites

- Active app `DATABASE_URL` points at `botfazer_cph1` (identity check)
- Code Alembic head = `20260715_0037`
- Local PostgreSQL 17 tools (`pg_dump` / `pg_restore`)
- Superuser available for `CREATE DATABASE` (default local: `SUPERUSER_DATABASE_URL` or `postgres` on localhost)
- `CPH4_CONFIRM_RESTORE=1` required to drop/recreate disposable target

## One-shot drill

```powershell
$env:CPH4_CONFIRM_RESTORE = "1"
# Optional smoke creds (same as CPH.3 pilot users):
# $env:CPH3_E2E_EMAIL / $env:CPH3_E2E_PASSWORD
uv run python -m scripts.cph4_run_restore_drill `
  --out "$env:USERPROFILE\botfazer_backups\cph4" `
  --run-id <run_id>
```

## Step-by-step

1. **Backup**

```powershell
uv run python -m scripts.cph4_backup_pilot_db `
  --out "$env:USERPROFILE\botfazer_backups\cph4" `
  --require-db botfazer_cph1
```

2. **Verify checksum**

```powershell
uv run python -m scripts.cph4_verify_backup --manifest <path-to>.manifest.json
```

3. **Restore disposable**

```powershell
$env:CPH4_CONFIRM_RESTORE = "1"
uv run python -m scripts.cph4_restore_disposable `
  --manifest <path-to>.manifest.json `
  --target botfazer_cph4_restore_<run_id>
```

4. **Validate + invalidate sessions + smoke**

```powershell
uv run python -m scripts.cph4_verify_restored_db `
  --manifest <path-to>.manifest.json `
  --target botfazer_cph4_restore_<run_id>
```

5. **Optional cleanup**

Drop only `botfazer_cph4_restore_*` (never `botfazer_cph1`).

## Refused targets

`botfazer`, `botfazer_cph1`, `postgres`, `template0`, `template1`, any name not matching `botfazer_cph4_restore_[A-Za-z0-9_]+`.

## Do not

- `alembic stamp` on restored or source DB
- Auto-upgrade restored DB when revision matches head
- Point production traffic at restore DB without an explicit cutover decision (docs-only until CPH.5+)
