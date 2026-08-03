# Integration I6 — ImplementationPlan ↔ MarketingPlan audit

**Decision: Option B** — ImplementationPlan is a higher-level project delivery plan; MarketingPlan is its executable specialist-task projection (not a substitute delivery plan).

**Write policy: READ-ONLY** — conversion preview only; draft create blocked (no generic `POST /marketing-plans` for handoff).

## Domain chain (product)

```
Business Verdict → MarketingStrategy → ImplementationPlan → MarketingPlan → Approval → Execution
```

Semantics are split across layers; authority is not merged in UI.

## Backend MarketingPlan (actual)

| Aspect | Fact |
|--------|------|
| Purpose | Ops/execution spine: `title`, `goal`, `specialist_tasks`, versions |
| Persistence | DB `MarketingPlan` + `MarketingPlanVersion` |
| Authority | Project-scoped SoT for specialist work instructions |
| Status | `draft` → `approved` → `archived` |
| Side effects on approve | Status/version only — **does not** start Agent Runs or providers |
| Execution | Separate `execution-runs` endpoints |
| Workstreams / milestones / deps graph / budget gates | **Absent** |
| Create API for Alpha handoff | **Absent** (create via scenario / chat / wizard only) |

## Product Alpha ImplementationPlan (actual)

| Section | Classification |
|---------|----------------|
| overview / strategic objective | strategic→ops decomposition |
| workstreams, milestones, roadmap | project-management view |
| tasks / roles / deps / deliverables / acceptance | PM view; **partial** MarketingPlan input candidates |
| budget plan / budget gates | approval + execution prerequisites (local) |
| approval gates / conditions | approval prerequisites (local) |
| risks / assumptions | planning metadata |
| PlanningReadinessResult | planning readiness ≠ execution readiness |
| local status / versions | frontend SoT until dedicated backend domain |

## Stop conditions applied

- No generic create → **I6 stays read-only** (document blocker).
- Dependency loss + unsupported CEO/PM/Designer roles → preview shows excluded; write would be unsafe.
- MarketingPlan approve ≠ execution → boundary documented + invariants.
- No second planner / task engine / approval engine created.

## Confirmations

- No Campaign created by I6.
- No Agent Run from conversion (conversion not executed).
- No execution/publication approval created.
- A7, AI.592, V2.2 remain paused.
