# Commercial MVP P0.5 — Migration and rollback

## Forward

Alembic revision `20260614_0033` revises `20260614_0032`.

Tables:

- `business_verdict_evidence_snapshots`
- `business_verdicts`
- `business_verdict_evidence_links`

## Forbidden

- Editing older migrations
- Repairing unrelated PostgreSQL drift (`20260608_0033` remains documented)
- Destructive deletes of verdict history

## Rollback

`downgrade()` drops the three P0.5 tables/indexes only. No data backfill of Product Alpha local verdicts.
