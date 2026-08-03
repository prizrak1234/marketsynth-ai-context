# Commercial MVP P0.3 — Migration and rollback

## Migration

- `alembic/versions/20260614_0031_sources_commercial_mvp_p0_3.py`
- Revises: `20260614_0030`
- Tables: `sources`, `investigation_source_links`

```bash
uv run alembic upgrade 20260614_0031
```

## Rollback

```bash
uv run alembic downgrade 20260614_0030
```

## Local Postgres drift

If `alembic current` fails on missing `20260608_0033`, document only — do not rewrite history. Intentional chain: `0028 → 0029 → 0030 → 0031`.
