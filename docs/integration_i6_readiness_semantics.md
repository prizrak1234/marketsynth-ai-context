# Integration I6 — Readiness semantics

Code: `READINESS_SEMANTICS` in `approval-boundary.ts`.

| Kind | Meaning | Must not equal |
|------|---------|----------------|
| strategy_readiness | GTM completeness (local) | MarketingPlan approve |
| implementation_planning_readiness | A6 PlanningReadinessResult (`notRealExecution`) | ready_for_execution |
| marketing_plan_readiness | draft / approved / archived | approved_for_execution |
| approval_readiness | per approval category | other categories |
| execution_readiness | backend execution readiness gate | plan approve |
| publication_readiness | package / schedule path | MarketingPlan approve |

## Forbidden collapses

- `ready_for_approval` → `ready_for_execution`
- `MarketingPlan approved` → `approved_for_execution`

Product Alpha CTA may open handoff **preview** only; it must not expose real execution.

A7 Execution Package remains paused; page documents future chain without calling execution endpoints.
