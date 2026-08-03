# Integration I5 — Migration and rollback

**No Alembic migration.** Option B adapters + docs only.

Rollback: revert frontend integration modules. MarketingPlan backend unchanged.

Future Strategy domain: append-only migration later; never dump Strategy into `project_context` JSON as SoT.
