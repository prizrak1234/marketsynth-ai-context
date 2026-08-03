# Commercial MVP P0.6 — MarketingPlan boundary

Existing MarketingPlan schema/API untouched.

Read-only future handoff fields on Strategy:

- `related_marketing_plan_ids` (empty in P0.6)
- `handoff_status` = `not_started` | `future` | `unsupported`

No MarketingPlan create/update/approve from Strategy paths.
