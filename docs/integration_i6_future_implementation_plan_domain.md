# Integration I6 — Future ImplementationPlan domain

Option B selected for I6 (handoff mapping). Option C remains the **long-term backend SoT** if delivery planning must persist server-side.

## Proposed entity (do not implement in I6)

```
ImplementationPlan
- id, owner_id, project_id
- strategy_reference
- version, status
- workstreams, milestones, tasks
- role assignments, dependencies
- deliverables, budget policy, gates
- risks, assumptions, readiness
- supersedes_plan_id
- created_at, updated_at
```

## Constraints

- No execution authorization on this entity.
- No provider action.
- No hidden chain-of-thought storage.
- MarketingPlan remains SoT for specialist_tasks until explicit versioned handoff.

## I6 preference

Adapters + explicit handoff specification **before** schema/migration.
