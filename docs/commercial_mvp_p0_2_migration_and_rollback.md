# Commercial MVP P0.2 — Migration and rollback

## Migration

- File: `alembic/versions/20260614_0030_investigations_commercial_mvp_p0_2.py`
- Revises: `20260614_0029` (P0.1 ProjectBrief)
- Append-only `investigations` table
- Indexes: `owner_id`, `project_id`, `project_brief_id`, `(project_id, version)`, `(project_id, status)`, `(project_id, current_stage)`
- FKs: users, projects, project_briefs, self-FK supersedes

## Apply

```bash
uv run alembic upgrade 20260614_0030
```

## Rollback

```bash
uv run alembic downgrade 20260614_0029
```

Drops `investigations` only. Does not touch ProjectBrief or Project.

## Note on local DB drift

If a local Postgres `alembic_version` points at a revision not in this repo (e.g. historical AI.60x heads), treat as local drift: do not rewrite history. App/pytest may use SQLite `create_all`. Align prod/staging to the intentional `0028 → 0029 → 0030` chain before applying.
