# Controlled Pilot Hardening CPH.1 — Database & Migration Baseline

**Phase:** CPH.1  
**Date:** 2026-07-15  
**Scope:** PostgreSQL / Alembic inventory, backup, disposable bootstrap, policy, startup guard  
**Out of scope:** V2.2, A7, AI.592, destructive repair of local `botfazer`, silent `alembic stamp head`

## Checkpoint

| Item | Value |
|------|--------|
| Branch | `master` (local only) |
| P1.3 freeze commit | `b1cade2` — `chore: freeze commercial MVP backend baseline v1` |
| Code Alembic head | `20260614_0036` |
| Remote ops | **none** (no fetch/pull/push) |

## Baseline snapshot (2026-07-15)

| Target | PostgreSQL | DB | Alembic revision | Commercial MVP tables | Size |
|--------|------------|-----|------------------|----------------------|------|
| Local data | 17.10 Windows | `botfazer` | **`20260608_0033` (missing from code tree)** | **absent** (except legacy `marketing_plans`) | ~14 MB |
| Disposable pilot | 17.10 Windows | `botfazer_cph1` | **`20260614_0036` (current)** | **all present** | ~13 MB |

Connection target recorded as `postgresql+asyncpg://botfazer:***@localhost:5432/<db>` — credentials not logged.

## Phase outcomes

1. Local schema + Alembic state inventoried (`scripts/cph1_inventory_postgresql.py`).
2. Revision `20260608_0033` classified (see investigation doc) — **do not stamp to head**.
3. No production/local business data destroyed; data DB left unchanged after backup.
4. Reconciliation plan documented; requires owner approval for rebuild.
5. Clean PostgreSQL bootstrap: empty DB → `alembic upgrade head` → `20260614_0036` **succeeds**.
6. Migrations **0029–0036** validated on PostgreSQL disposable DB.
7. ORM smoke (Project + ProjectBrief) on migrated PG (no `create_all`).
8. Upgrade/downgrade limits documented (head↔0034 verified; full legacy downgrade **not** claimed).
9. Verified logical backup + restore on disposable DB.
10. Pilot bootstrap scripts: `scripts/cph1_bootstrap_pilot.ps1` / `.sh`.
11. Historical migrations **not** rewritten.
12. V2.2 / A7 / AI.592 remain paused.

## Commands

```bash
# Inventory (uses DATABASE_URL; passwords redacted in output)
uv run python scripts/cph1_inventory_postgresql.py

# Disposable bootstrap (after CREATE DATABASE botfazer_cph1 OWNER botfazer)
$env:DATABASE_URL="postgresql+asyncpg://botfazer:***@localhost:5432/botfazer_cph1"
uv run powershell -File scripts/cph1_bootstrap_pilot.ps1

# Revision / parity
uv run python scripts/cph1_db_tools.py check-revision
uv run python scripts/cph1_db_tools.py schema-parity

# Backup (default: %USERPROFILE%\botfazer_backups)
uv run python scripts/cph1_db_tools.py backup --out $env:USERPROFILE\botfazer_backups

# Optional PG smoke
$env:CPH1_POSTGRES_URL="postgresql+asyncpg://botfazer:***@localhost:5432/botfazer_cph1"
uv run pytest tests/test_controlled_pilot_cph_1_postgresql_smoke.py tests/test_controlled_pilot_cph_1_revision_guard.py -q
```

## Related docs

- [Revision 20260608_0033 investigation](controlled_pilot_cph_1_revision_20260608_0033_investigation.md)
- [Schema diff](controlled_pilot_cph_1_schema_diff.md)
- [Repair options](controlled_pilot_cph_1_migration_repair_options.md)
- [PostgreSQL bootstrap](controlled_pilot_cph_1_postgresql_bootstrap.md)
- [Backup & restore](controlled_pilot_cph_1_backup_and_restore.md)
- [Migration policy](controlled_pilot_cph_1_migration_policy.md)
- [Startup revision guard](controlled_pilot_cph_1_startup_revision_guard.md)
- [Reconciliation plan](controlled_pilot_cph_1_reconciliation_plan.md)

## Roadmap

| Status | Track |
|--------|--------|
| **Completed** | Commercial MVP Backend Baseline v1.0 |
| **Current** | CPH.1 Database and Migration Baseline |
| **Next** | CPH.2 Browser End-to-End → CPH.3 Auth/Session → CPH.4 Backup/Restore ops → CPH.5 Observability |
| **Paused** | Product Alpha A7 · AI.592 · Architecture V2.2 |
