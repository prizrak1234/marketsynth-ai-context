# Integration I6 — Handoff mapping

## Contract

```
ImplementationPlan → MarketingPlanDraftInput (preview only)
```

Code: `buildMarketingPlanHandoffPreview()` — `writeAllowed: false`.

## Mapped (when write becomes safe)

| Source | Target | Disposition |
|--------|--------|-------------|
| overview.strategicObjective | MarketingPlan.goal | transformed (text slice) |
| projectName + version | MarketingPlan.title | transformed |
| PlanTask + mappable role | specialist_tasks[].specialist | transformed via ROLE_MAPPINGS |
| title + description | specialist_tasks[].objective | transformed |
| expectedOutput (+ acceptance as note) | expected_output | transformed / text-only |

## Excluded / unsupported

| Source | Reason |
|--------|--------|
| CEO / Project Manager / Designer / similar | no MarketingSpecialistType |
| workstreams, milestones, roadmap | absent on MarketingPlan |
| dependency graph | incompatible — loss flagged `dependencyLoss: true` |
| budget gates, approval gates | must not map to plan approve / execution approve |
| local task status approved | must not map to Agent Run / execution |
| deliverable entities | not assets; text only |

## Role mapping

Reuse I1 `ROLE_MAPPINGS`. Unsupported roles → `disposition: unsupported` → excluded from included list. No new AgentType.

## Write blockers (I6)

1. No generic `POST /projects/{id}/marketing-plans` for handoff.
2. Dependency loss cannot be enforced on spine.
3. Acceptance criteria not first-class.
4. Existing create paths (scenario/chat/wizard) are orthogonal — not used for silent conversion.

## Conversion UI

Button label reserved: **«Создать черновик MarketingPlan»** — **disabled / blocked** in I6.

Side effects declared: `none`. Expected status if created later: `draft` only.
