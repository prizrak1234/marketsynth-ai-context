# Product Alpha Phase A7 — Execution Package & Approval Preview

Local-only Marketsynth UI that consolidates Verdict → Strategy → Implementation Plan into a pre-execution **Execution Package**. Dry run is deterministic and local. **No real execution, providers, credentials, spend, or publishing.**

## Access rules

Route: `/workspace/projects/[projectId]/execution-package`

| State | Behavior |
|-------|----------|
| GO + strategy + plan | Package allowed |
| CONDITIONAL_GO | Package allowed; conditions/blockers visible; readiness may stay blocked |
| NO_GO | → Pivot |
| INSUFFICIENT_DATA | → Investigation |
| Missing strategy | → Strategy |
| Missing implementation plan | → Implementation Plan |

## Package model

`ExecutionPackage` versioned in:

`marketsynth.product_alpha.execution_package.v1.{projectId}`

Statuses: `draft` | `under_review` | `approval_pending` | `approved` | `blocked` | `superseded`.

## Deterministic builder

`web/src/lib/execution-package/`

- `types.ts`, `build-package.ts`, `readiness.ts`, `routing.ts`
- `preflight.ts`, `dry-run.ts`, `verification.ts`, `rollback.ts`
- `storage.ts`, `mock-packages.ts`, `selectors.ts`
- `build-package.selfcheck.ts`

## Scope & items

Scope register with action classes. Publication, budget_change, and provider_configuration are **excluded/blocked** in Product Alpha. Content/asset preparation are placeholders.

## Providers

Requirements listed (Yandex Direct, Telegram, Analytics, CMS, …). States include `mock_ready` / `credentials_required`. **No secret fields; no credential storage.**

## Approvals & budget

Local approval matrix (verdict → execution). Budget authorization uses range/unknown/requires_approval — never invents exact spend; no transactions.

## Preflight / verification / rollback

Deterministic preflight categories. Verification methods align conceptually with future V2.2 Verified Execution. High-risk items without rollback fail preflight. Unavailable verification requires acknowledgment when retained.

## Dry run

Validates package completeness only. `externalActionsPerformed: false` always. Results: `passed` | `passed_with_warnings` | `blocked`.

## Readiness

`not_ready` | `conditionally_ready` | `ready_for_approval` | `approved_for_dry_run` | `blocked`.

CTAs: «Запустить dry run», «Подготовить к утверждению». **No «Выполнить» / «Запустить кампанию».**

## Execution Boundary panel

Visible on-page statement that Product Alpha does not execute external actions.

## Future Architecture V2.2 handoff

Intent → Readiness Gate → Human Approval → Provider Adapter → Command → Verification → Evidence → Outcome → Knowledge Candidate — displayed as future boundary only.

## Demo scenarios

- GO: `proj_inv_c_ready`
- CONDITIONAL_GO: `proj_inv_a_conditional`

## Limitations

No backend persistence, real approvals, provider adapters, campaign creation, publication, budget changes, asset upload, or real verification/rollback.

## Future backend contracts

- Persist execution packages linked to plan/strategy/verdict
- Human approval + readiness gate APIs
- Provider adapters with verified execution
- Evidence and outcome writeback

## Selfcheck

```bash
cd web
npx --yes tsx src/lib/execution-package/build-package.selfcheck.ts
```
