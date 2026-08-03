# Commercial MVP P1.2 — Controlled MarketingPlan Draft Handoff

## Outcome

Approved ImplementationPlan → preview → explicit confirm → **MarketingPlan draft only**.

## Safe draft option

**Option A** — reuse `MarketingPlanService.create_from_execution_plan(...)` with `source_run_id=None`. Status always `draft`. No approve, dispatch, Agent Run, Campaign.

## Mapping version

`implementation_to_marketing_plan.v1`

## APIs

- `POST /projects/{id}/implementation-plans/{plan_id}/marketing-plan-handoff/preview`
- `POST /projects/{id}/implementation-plans/{plan_id}/marketing-plan-handoff/confirm`

## Boundaries

- Handoff confirm ≠ MarketingPlan approval
- ImplementationPlan approval ≠ MarketingPlan approval
- MarketingPlan approval ≠ execution / publication / budget approval
- No provider / budget / scheduler / planner / Agent Run

## Durable entity

`implementation_marketing_plan_handoffs` (migration `20260614_0036`)

## Tests

`uv run pytest tests/test_commercial_mvp_p1_2_marketing_plan_handoff.py -q`
