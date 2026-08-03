# Commercial MVP P0.6 — Migration and rollback

Forward: Alembic `20260614_0034` → table `marketing_strategies`.

Do not edit older migrations. Do not repair Postgres drift `20260608_0033`. Do not modify MarketingPlan schema.

Rollback: drop `marketing_strategies` only.
