# CPH.4 — Operational runbook (data loss / DB failure)

## 1. Detect incident

- App cannot connect / checksum alarms / operator reports missing projects
- Confirm identity: which DB is active (`botfazer_cph1` vs restore vs legacy)

## 2. Stop writes (pilot)

- Stop uvicorn / frontend workers writing to the failed DB
- Do not run migrations or stamps while uncertain

## 3. Identify restore point

- List `%USERPROFILE%\botfazer_backups\cph4\*.manifest.json`
- Prefer latest `restore_test_status=passed` or newest verified checksum
- Confirm `source_revision` matches code head (or have an explicit upgrade plan)

## 4. Verify backup

```powershell
uv run python -m scripts.cph4_verify_backup --manifest <manifest>
```

## 5. Provision restore DB

```powershell
$env:CPH4_CONFIRM_RESTORE = "1"
uv run python -m scripts.cph4_restore_disposable --manifest <manifest> --target botfazer_cph4_restore_<run>
```

## 6–10. Validate

```powershell
uv run python -m scripts.cph4_verify_restored_db --manifest <manifest> --target botfazer_cph4_restore_<run>
```

Includes: revision, schema, counts, lineage, **session revoke**, login smoke, execution firewall.

## 11. Switch application DB (documentation-only until approved)

1. Point `DATABASE_URL` at restored DB **only** after owner approval
2. Restart backend
3. Confirm `/auth/login` + Workspace
4. Monitor errors for 15–30 minutes

## 12. Rollback switch

- Revert `DATABASE_URL` to previous healthy DB if available
- Preserve restore DB for forensics

## 13. Incident record

Capture: time detected, backup_id, sha256, restore target, RPO/RTO actuals, whether pilot source was untouched.

## Failed restore signals

Tooling exits nonzero with explicit `error=<code>` (checksum, unsafe target, lineage, smoke, etc.). Do not promote a failed restore.
