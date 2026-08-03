# CPH.4 — Backup / restore architecture

## Scope

Operational recovery drill for the Marketsynth controlled pilot database `botfazer_cph1` at Alembic revision `20260715_0037`.

This phase proves: **backup → checksum → restore into disposable DB → schema/lineage/auth smoke**, not documentation alone.

## Components

| Piece | Role |
|-------|------|
| `scripts/cph4_backup_pilot_db.py` | Logical `pg_dump -Fc` of source pilot DB + baseline + manifest |
| `scripts/cph4_verify_backup.py` | SHA-256 + size + revision gate |
| `scripts/cph4_restore_disposable.py` | Create `botfazer_cph4_restore_*` and `pg_restore` |
| `scripts/cph4_verify_restored_db.py` | Parity, counts, lineage, session policy A, auth smoke, firewall |
| `scripts/cph4_run_restore_drill.py` | End-to-end orchestrator + corruption/unsafe-target checks |

## Source vs restore

| Database | Role |
|----------|------|
| `botfazer_cph1` | Pilot source — **never** drop/overwrite in CPH.4 |
| `botfazer` | Legacy drifted — **never** use/stamp |
| `botfazer_cph4_restore_<run_id>` | Disposable restore target only |

## Backup format

- PostgreSQL **custom format** (`-Fc`) via local `pg_dump`
- Stored under `%USERPROFILE%\botfazer_backups\cph4\` (outside git)
- Companion files: `*.manifest.json`, `*.baseline.json`
- Git ignores `*.dump`, `*.sql`, `botfazer_backups/`

## Session policy

**Policy A:** restore session rows for forensic completeness, then **revoke all** before opening the restored environment. Users must sign in again.

See [controlled_pilot_cph_4_session_restore_policy.md](controlled_pilot_cph_4_session_restore_policy.md).

## Partial restore

**Not supported** for normal pilot recovery. Full database restore only. Table-level restore breaks lineage FKs and ownership and is expert-only.

## Related

- [controlled_pilot_cph_4_restore_procedure.md](controlled_pilot_cph_4_restore_procedure.md)
- [controlled_pilot_cph_4_rpo_rto.md](controlled_pilot_cph_4_rpo_rto.md)
- CPH.1 baseline: [controlled_pilot_cph_1_backup_and_restore.md](controlled_pilot_cph_1_backup_and_restore.md)
