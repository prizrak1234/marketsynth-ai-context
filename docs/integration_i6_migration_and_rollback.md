# Integration I6 — Migration and rollback

## LocalStorage

Key: `marketsynth.product_alpha.implementation_plan.v1.{projectId}`

| Mode | Behavior |
|------|----------|
| mock | local plan unchanged; no MarketingPlan fetch |
| backend | no pretend full ImplementationPlan; show ops panel only |
| hybrid | local plan + backend MarketingPlan relationship; link metadata FE-only |

Rules: no automatic upload; no silent overwrite; no deletion of local plan by I6; stale mapping detection reserved for future `mappingFingerprint` when write exists.

## Rollback

1. Remove / disable `ImplementationHandoffPanel` and adapter load from workspace.
2. Keep local A6 plan storage intact.
3. MarketingPlan backend unchanged (I6 did not migrate DB).

## What I6 did not do

- No backend entity / Alembic migration for ImplementationPlan.
- No draft MarketingPlan write from Alpha.
- No Campaign / Agent Run / execution-approval / publication / budget actions.
- No A7 Execution Package activation.

## Next

I7 end-to-end audit before unfreezing V2.2 Verified Execution.
