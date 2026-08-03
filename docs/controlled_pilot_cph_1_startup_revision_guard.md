# CPH.1 — Startup revision guard

## Behavior

On application lifespan (`app/main.py`):

1. `init_db` (engine only — **no** migrations).
2. If `ALEMBIC_REVISION_CHECK_ENABLED=true` (default): read `alembic_version`, classify vs code tree.
3. Log OK / behind / problem.
4. **Never** auto-stamp. **Never** auto-migrate.

## Settings

| Env | Default | Effect |
|-----|---------|--------|
| `ALEMBIC_REVISION_CHECK_ENABLED` | `true` | Run read-only diagnostic |
| `ALEMBIC_REVISION_FAIL_FAST` | `false` | When `true`, refuse startup on missing-from-tree / unknown / ahead / multiple heads |

Development: soft warn unless fail-fast.  
Pilot / staging / production: set `ALEMBIC_REVISION_FAIL_FAST=true`.

## States

| DB vs code | State | Dev (default) | Fail-fast / pilot |
|------------|-------|---------------|-------------------|
| Matches head | `current` | info | start |
| Ancestor of head | `behind` | warning | start (deploy should migrate offline first) |
| Orphan ID (e.g. `20260608_0033`) | `missing_from_tree` | error log | **refuse** |
| Unknown graph | `unknown` | error log | **refuse** |
| Ahead of code | `ahead` | error log | **refuse** |
| Multiple heads in code | `multiple_heads` | error log | **refuse** |
| No version rows | `empty` | warn | start (empty new DB needs offline migrate) |

## Local data DB note

With `.env` pointing at `botfazer` (`20260608_0033`), development warns; pilot fail-fast would refuse. Point pilot at `botfazer_cph1` / `botfazer_pilot` instead.

## Tests

- Classification of orphan revision → no auto-stamp flags
- Fail-fast soft vs hard settings
- Code refuses `auto_stamp_allowed` / `auto_migrate_allowed` always false
