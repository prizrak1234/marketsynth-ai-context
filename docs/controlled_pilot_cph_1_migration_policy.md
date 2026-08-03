# CPH.1 — Alembic / migration policy

## Rules

1. **One linear production head** unless an owner explicitly approves a temporary branch merge.
2. **No reused revision IDs.**
3. **No missing revisions** in the code tree for any DB that will be upgraded with that tree.
4. **Do not edit applied migrations** after shared / pilot / production use — **append-only** corrections.
5. Prefer **new migrations** (Option A) over historical edits (Option B).
6. **PostgreSQL migration test required** for schema changes before claiming readiness.
7. **SQLite `create_all` is not migration proof.**
8. Schema changes require a migration + test under `tests/` (static chain and/or disposable PG profile).
9. **Downgrade support:** commercial 0034↔0036 verified on PG; full base↔head downgrade **not** guaranteed — document per-phase.
10. **Startup/deployment:** read-only revision diagnostic (`ALEMBIC_REVISION_CHECK_*`); never auto-migrate / auto-stamp on app start.
11. **Backups before production migrations.**
12. **Remote / pilot deploy blocked** on `database_revision_missing_from_tree`, `unknown`, `ahead`, `multiple_heads` when fail-fast is on.

## Forbidden

- `alembic stamp head` on unknown / orphan revisions without schema proof and owner approval.
- Silent rewrite of historical migration files “to fix local drift.”
- Pointing pilot traffic at a drifted DB.

## Error conditions (explicit)

| Code | Meaning |
|------|---------|
| `database_revision_unknown` | Cannot classify relationship |
| `database_revision_missing_from_tree` | DB revision ID not in code |
| `database_behind` | Ancestor of head |
| `database_ahead` | Descendant beyond code head |
| `multiple_heads` | >1 head in code |
| `migration_failed` | Upgrade/downgrade SQL error |
| `schema_mismatch` | Tables/columns diverge from expected head |
| `backup_required` | Destructive step without backup |
| `restore_verification_failed` | Restore checks failed |
| `reconciliation_requires_owner_approval` | Data-lossy or rebuild path |

## Enforcement helpers

- Domain: `app/domain/alembic_revision_guard.py`
- Startup: `app/services/alembic_revision_startup.py`
- CLI: `scripts/cph1_db_tools.py check-revision`
- Tests: `tests/test_controlled_pilot_cph_1_revision_guard.py`
