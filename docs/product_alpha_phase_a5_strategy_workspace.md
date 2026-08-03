# Product Alpha Phase A5 — Strategy Workspace

**Status:** COMPLETED (local)  
**Date:** 2026-07-13  
**Constraints:** Verdict-based routing · deterministic mock strategy · no LLM · no execution

## Verdict-based routing

| Verdict | Behavior |
|---|---|
| GO | `/strategy` allowed |
| CONDITIONAL_GO | `/strategy` with mandatory conditions; execution often `blocked` |
| NO_GO | `/strategy` redirects to `/pivot` |
| INSUFFICIENT_DATA | `/strategy` redirects to `/investigation` |

Routes:

- `/workspace/projects/[projectId]/strategy`
- `/workspace/projects/[projectId]/pivot`

Direct URL bypass is blocked by client-side deterministic checks (`resolveStrategyAccess`).

## Lib

`web/src/lib/strategy/` — types, build-strategy, execution-readiness, routing, storage, mock-strategies, selectors

Storage key: `marketsynth.product_alpha.strategy.v1.{projectId}`

## Scenarios

- GO → `proj_inv_c_ready`
- CONDITIONAL_GO → `proj_inv_a_conditional`
- NO_GO pivot → `proj_inv_d_no_go`
- INSUFFICIENT → `proj_inv_b_not_ready`

## Execution readiness

`not_ready` | `conditionally_ready` | `ready_for_planning` | `blocked`  
Mandatory unresolved CONDITIONAL_GO conditions → `blocked`. Not real execution approval.

## Checks

```bash
cd web
npx eslint "src/lib/strategy/**/*.{ts,tsx}" "src/components/strategy/**/*.{ts,tsx}" --max-warnings 0
npx --yes tsx src/lib/strategy/build-strategy.selfcheck.ts
```

## Out of scope / later

Implementation Plan (A6), campaigns, content generation, real budgets, publishing, backend persistence.
