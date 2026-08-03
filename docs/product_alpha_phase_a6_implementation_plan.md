# Product Alpha Phase A6 — Implementation Plan Workspace

Local-only Marketsynth UI that turns an approved/reviewable marketing strategy into a structured operational plan. **No real execution, providers, spend, or backend.**

## Access rules

Route: `/workspace/projects/[projectId]/implementation`

| Verdict / state | Behavior |
|-----------------|----------|
| GO | Plan allowed; execution planning may become `ready_for_approval` |
| CONDITIONAL_GO | Plan allowed; mandatory conditions shown; acquisition/execution planning gated |
| NO_GO | Redirect → Pivot Workspace |
| INSUFFICIENT_DATA | Redirect → Investigation Workspace |
| Missing strategy | Redirect → Strategy Workspace |

Direct URL access cannot bypass these rules (`resolveImplementationAccess`).

## Plan model

`ImplementationPlan` is versioned, scoped by project, stored in:

`marketsynth.product_alpha.implementation_plan.v1.{projectId}`

Traceability fields: `verdictId` / `verdictVersion`, `strategyId` / `strategyVersion`, `evidenceSnapshotId`.

Statuses: `draft` | `under_review` | `approved` | `blocked` | `superseded`.

## Deterministic builder

`web/src/lib/implementation-plan/`

- `types.ts` — plan artifacts
- `build-plan.ts` — Strategy + Verdict → full plan (no LLM)
- `readiness.ts` — execution **planning** readiness
- `routing.ts` — access + redirects
- `storage.ts` — local versioning
- `mock-plans.ts` — prepare/regenerate helpers
- `selectors.ts` — labels/colors
- `build-plan.selfcheck.ts` — focused checks

## Workstreams / milestones / tasks

Workstreams include validation-first ordering for CONDITIONAL_GO; acquisition remains blocked until conditions/gates clear.

Milestones are operational (validation brief, positioning, offer, channel test package, analytics, pilot readiness) — not decorative labels.

Tasks carry roles, dependencies, acceptance criteria, budget impact modes, and approval flags. Mock statuses only; nothing is “in progress” unless explicitly set.

## Roles, dependencies, deliverables

Agency roles only (no named employees / avatars). Dependency table: finish-to-start, approval/evidence/budget/compliance/resource gates. Deliverables register lists artifacts without generating content.

## Budget plan & gates

Range / unknown / requires_approval — no invented exact amounts, no ROI. Budget gates are local Product Alpha semantics (not backend approval APIs).

## Approval gates

Local gates: strategy, validation, offer, budget, asset, pilot readiness, execution readiness.

## Conditions, risks, assumptions

CONDITIONAL_GO mandatory conditions surface at top and block planning readiness when open. Risks are strategy risks translated into operational consequences. Assumptions are explicit with validation milestones.

## Execution planning readiness

Statuses: `not_ready` | `conditionally_ready` | `ready_for_approval` | `blocked`.

Primary CTA «Подготовить пакет исполнения» is a Phase A7 placeholder; disabled when `not_ready` or `blocked`.

## Roadmap & task view

Relative horizons (Week 1–2, Month 1, Month 2, Quarter 1, TBD). Task filters for status/workstream/owner/milestone/priority/blocker/approval; desktop table + mobile cards.

## Versioning & local review

Save draft / Send for review / Approve plan / Create new version. New version supersedes previous; history remains viewable.

## Execution handoff

Placeholder section only: Execution Package, Campaign Planning, Asset Production, Provider Configuration, Budget Approval, Real Execution — all unavailable.

## Demo scenarios

- GO: `proj_inv_c_ready`
- CONDITIONAL_GO: `proj_inv_a_conditional`
- NO_GO: `proj_inv_d_no_go` → Pivot
- INSUFFICIENT_DATA: `proj_inv_b_not_ready` → Investigation

## Limitations

No backend persistence, real task management, LLM generation, campaign/asset production, providers, spend, publishing, notifications, collaboration, PDF, or calendar.

## Future backend contracts (later)

- Persist implementation plans with strategy/verdict FKs
- Gate approval APIs tied to execution readiness
- Budget release workflows
- Task assignment to workforce roles
- Execution package assembly (A7+)

## Browser verification

1. Open GO demo → Implementation Plan loads; readiness can be ready_for_approval.
2. Open CONDITIONAL demo → validation-first; mandatory conditions; acquisition blocked.
3. NO_GO / INSUFFICIENT / missing strategy redirect correctly.
4. Refresh preserves plan; Create new version supersedes.
5. Mobile: task cards readable; filters keyboard-accessible.
6. Landing / Workspace / Intake / Investigation / Verdict / Strategy unchanged.

## Selfcheck

```bash
cd web
npx --yes tsx src/lib/implementation-plan/build-plan.selfcheck.ts
```
