# Commercial MVP P0.4 — Migration and rollback

- `20260614_0032_evidence_commercial_mvp_p0_4.py` revises `20260614_0031`
- Tables: `investigation_evidence`, `evidence_source_links`

```bash
uv run alembic upgrade 20260614_0032
uv run alembic downgrade 20260614_0031
```

Local Postgres drift (`20260608_0033`) remains documented; not repaired.
