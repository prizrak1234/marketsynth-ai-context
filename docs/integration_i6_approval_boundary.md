# Integration I6 — Approval boundary

Code: `web/src/lib/integration/approval-boundary.ts` (`APPROVAL_BOUNDARY_MATRIX`).

## Categories (never flatten to `approved: boolean`)

| Category | Authorizes execution | Creates MarketingPlan approval | Creates execution approval |
|----------|---------------------|--------------------------------|----------------------------|
| implementation_plan_local_review | no | no | no |
| marketing_plan_approval | no | yes (its own) | no |
| execution_approval | yes | no | yes |
| publication_approval | no (publication only) | no | no |
| budget_approval | no | no | no |
| verdict_local_review | no | no | no |
| specialist_output_approval | no | no | no |
| content_asset_approval | no | no | no |

## Invariants

- Implementation Plan local review **does not** approve MarketingPlan.
- MarketingPlan approval **does not** create execution approval.
- MarketingPlan approval **does not** create publication approval.
- Verdict approval **does not** approve MarketingPlan.
- Budget approval **does not** imply execution approval.

## Required chain (tasks)

```
Implementation Task → approved mapping → MarketingPlan Specialist Task → Agent Run → optional Tool/Execution
```

Never: Implementation Task → Agent Run directly.
Never: local “approved” task status → execution authorization.
