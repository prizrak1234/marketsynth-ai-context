# P1.3 Migration Audit

## Chain (append-only)

0029 → 0030 → 0031 → 0032 → 0033 → 0034 → 0035 → 0036

Static test: `test_alembic_commercial_mvp_revision_chain` (+ P1.3 duplicate through 0036).

## Runtime notes

- Code head: `20260614_0036`
- Local Postgres: may still report missing `20260608_0033` — **do not repair in P1.3**
- Full `alembic upgrade` from base on SQLite fails on legacy Alter constraints (pre-commercial migrations)
- Pytest uses SQLite `SQLModel.metadata.create_all` (schema parity for tests)

## Recommended pilot hardening

Disposable Postgres: upgrade base→head, downgrade to 0034, upgrade again — outside drifted local DB.
