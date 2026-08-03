# CPH.1 — Backup and restore

## Policy

- Logical backup **before** any local reconciliation.
- Store backups **outside** the git repo (`%USERPROFILE%\botfazer_backups` recommended).
- `.gitignore` includes `*.sql`, `backups/`, `botfazer_backups/`.
- Never commit credentials or full business dumps.
- Scripts redact passwords in printed URLs.

## Backup command

```powershell
# Uses current DATABASE_URL
uv run python scripts/cph1_db_tools.py backup --out $env:USERPROFILE\botfazer_backups
```

Produces:

- `backup_<db>_<UTC>.sql` — `pg_dump` plain SQL when available
- `backup_meta_<db>_<UTC>.json` — timestamp, DB name, Alembic revisions, table row counts, size, checksum metadata fields, dump status

## Verified backup (local data DB)

| Field | Value |
|-------|--------|
| File | `%USERPROFILE%\botfazer_backups\backup_botfazer_20260715T164718Z.sql` |
| Meta | `backup_meta_botfazer_20260715T164718Z.json` |
| Database | `botfazer` |
| Alembic at backup | `20260608_0033` |
| SHA256 | `1986E1C74DFA562467DA05A1D6F6276A84774A66E45AA4F4A96FF744CAC1908D` |
| Size (dump) | ~289 KB |

## Restore (disposable only)

```powershell
$env:PGPASSWORD = "<local>"
# Prefer helper (refuses non-disposable names):
uv run python scripts/cph1_restore_verify.py
```

Manual sketch:

```text
CREATE DATABASE botfazer_cph1_restore OWNER botfazer;
psql -h localhost -U botfazer -d botfazer_cph1_restore -f backup_botfazer_….sql
```

**Refuse** restoring into production-like names without explicit owner authorization.

## Restore verification (executed in CPH.1)

| Check | Result |
|-------|--------|
| Target | `botfazer_cph1_restore` (disposable) |
| Restore exit | OK |
| `alembic_version` | `20260608_0033` |
| `campaign_learnings` present | True |
| `project_briefs` present | False |

Confirms backup fidelity for the drifted state — **not** a commercial head schema.

## Rollback after failed experiments

1. Stop app processes using the disposable DB.
2. Drop disposable DB.
3. Recreate and restore from `.sql`, or re-bootstrap with `alembic upgrade head` for a clean pilot.

## Error codes

- `backup_required` — reconciliation attempted without verified backup
- `restore_verification_failed` — post-restore revision/table checks fail
