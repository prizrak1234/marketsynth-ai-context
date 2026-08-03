# P1.2 Idempotency and conflicts

Fingerprint = sha256(plan_id + plan_version + mapping_version + existing_plan_policy + normalized mapped tasks).

Rules:

- Same completed fingerprint → return existing handoff + MarketingPlan (`idempotent_replay=true`)
- Preview row reused for same fingerprint while still `preview`
- Approved MarketingPlans never overwritten; default policy `create_new_draft`
- Policy `cancel` rejected as conflict
- Stale version / fingerprint mismatch / missing preview → 409
