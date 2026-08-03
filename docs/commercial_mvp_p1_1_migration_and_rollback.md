# Commercial MVP P1.1 — Migration and Rollback

| Item | Value |
|------|-------|
| Revision | `20260614_0035` |
| Revises | `20260614_0034` |
| Table | `implementation_plans` |
| Unique | `(project_id, version)` |

Downgrade: drop indexes + table.  
Local Postgres drift (`20260608_0033`) unrelated — not repaired.  
Pytest: SQLite `create_all`.
