# Commercial MVP P1.1 — Strategy Lineage

ImplementationPlan stores:

- `marketing_strategy_id`
- `marketing_strategy_version` (exact)
- `business_verdict_id` / `business_verdict_version` (copied from Strategy)
- `evidence_snapshot_id` / `evidence_snapshot_hash`

Errors: `strategy_not_found`, `strategy_not_approved`, `strategy_version_mismatch`, `strategy_superseded`.

Children do not float to a newer Strategy version. Supersede creates a new plan row that may pin a newer Strategy.
