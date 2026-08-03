# P1.2 Migration and rollback

Append-only: `20260614_0036` after `20260614_0035`.

Table: `implementation_marketing_plan_handoffs`

Local PostgreSQL may still show unrelated drift (`20260608_0033`) — do not repair in this phase.

Rollback: drop new table only via alembic downgrade of `20260614_0036`. Do not edit prior migrations or MarketingPlan history.
