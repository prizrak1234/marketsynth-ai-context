# Commercial MVP P0.6 — Strategy ↔ Verdict linkage

Every Strategy stores:

- `business_verdict_id` + `business_verdict_version`
- `evidence_snapshot_id` + `evidence_snapshot_hash`
- `verdict_conditions[]` as references (`verdict_condition_id`, status snapshot, blocking effect)

Strategy cannot mark Verdict conditions satisfied. Condition authority stays in BusinessVerdict domain.
