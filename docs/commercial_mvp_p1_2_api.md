# P1.2 API

## Preview

`POST /projects/{project_id}/implementation-plans/{plan_id}/marketing-plan-handoff/preview`

Does not create MarketingPlan. Returns handoff_id, mapping_fingerprint, classifications, blockers, warnings, existing plans, side_effects=[].

## Confirm

`POST /projects/{project_id}/implementation-plans/{plan_id}/marketing-plan-handoff/confirm`

Body:

```json
{
  "handoff_preview_id": "...",
  "mapping_fingerprint": "...",
  "expected_implementation_plan_version": 1,
  "explicit_confirmation": true,
  "existing_plan_policy": "create_new_draft",
  "note": "optional"
}
```

Creates MarketingPlan `status=draft` only.
