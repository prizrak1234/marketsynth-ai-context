# Commercial MVP P0.1 — Migration and rollback

## Alembic

- Append-only: `20260614_0029_project_briefs_commercial_mvp_p0_1.py`
- Revises: `20260603_0028`
- Creates `project_briefs` + indexes
- No edits to historical migrations
- No Project column changes

## Rollback

1. Downgrade alembic revision `20260614_0029`
2. Remove FE brief CTAs / adapters
3. Local intake drafts remain intact

## Safety confirmations

- No secrets in brief schema
- Materials metadata only
- Owner/project isolation enforced server-side
