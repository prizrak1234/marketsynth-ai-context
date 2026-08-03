# Product Alpha Phase A4 — Business Verdict Workspace

**Status:** COMPLETED (local)  
**Date:** 2026-07-13  
**Constraints:** Landing / Workspace / Intake / Investigation preserved · deterministic mock verdicts · no LLM · no strategy/execution

## Route

`/workspace/projects/[projectId]/verdict`

Entry: Investigation CTA **«Подготовить вердикт»** when readiness permits (`not_ready` disabled; `conditionally_ready` requires acknowledgment; `ready_for_review` direct).

## Demo projects

| Verdict | Project ID | Investigation scenario |
|---|---|---|
| GO | `proj_inv_c_ready` | ready_for_review |
| CONDITIONAL_GO | `proj_inv_a_conditional` | conditionally_ready |
| NO_GO | `proj_inv_d_no_go` | no_go (new) |
| INSUFFICIENT_DATA | `proj_inv_b_not_ready` | not_ready |

## Model

`BusinessVerdict` in `web/src/lib/verdict/types.ts`

## Rules (`build-verdict.ts`)

- **INSUFFICIENT_DATA** — readiness not_ready / critical gaps / low coverage with blockers  
- **NO_GO** — structural inviability (`scenarioId=no_go` or weak demand + bad economics + critical risk + contradiction) with enough coverage to judge  
- **GO** — ready_for_review + no critical gaps/contradictions + economics/market/audience covered + no critical open risk  
- **CONDITIONAL_GO** — otherwise viable-but-conditional  

Readiness ≠ verdict. Never auto-GO from readiness alone.

## Versioning

Key: `marketsynth.product_alpha.verdict.v1.{projectId}`  

Regenerate → new version; previous current → `superseded`.

## Local approval

`draft` → `under_review` → `approved` (local only; clearly labeled).

## Strategy handoff

Placeholders only (A5). NO_GO → pivot path; INSUFFICIENT_DATA → Investigation.

## Checks

```bash
cd web
npx eslint "src/lib/verdict/**/*.{ts,tsx}" "src/components/verdict/**/*.{ts,tsx}" --max-warnings 0
npx --yes tsx src/lib/verdict/build-verdict.selfcheck.ts
```

## Future backend

Persisted Verdict entity, evidence snapshot FK, real approval workflow, export, Strategy Workspace handoff API.
