# Integration I7 — Execution boundary audit

## Implemented backend chain (ops)

```
MarketingPlan (draft)
→ approve MarketingPlan
→ create execution-run
→ start run
→ execute-specialist (task_index)
→ tools / Agent Runs (internal)
→ publication packages / jobs (Telegram flag-gated)
```

Also: execution readiness, execution-approvals (`REAL_EXECUTION_EXPANSION_ENABLED`), workflow n8n dry-run flags — **orthogonal** to Product Alpha Implementation Plan.

## Product Alpha today

```
ImplementationPlan (local)
→ handoff preview (read-only)
→ [blocked] MarketingPlan draft create
→ A7 Execution Package (paused / mock|hybrid only)
```

I6 write policy: no generic handoff create API → **read-only**.

## Target V2.2 (not implemented)

```
Intent → Readiness → Approval → Provider Execution → Verification → Evidence → Outcome → Knowledge Candidate
```

### Missing links (to V2.2)

| Link | Status |
|------|--------|
| Intent model | unmet |
| Unified readiness before provider | partial (execution_readiness exists; not Alpha-wired) |
| Approval before provider | partial (execution-approvals) |
| Provider Execution | partial / gated (Telegram, n8n dry-run) |
| Verification | unmet as first-class |
| Evidence/Outcome linkage | unmet (Evidence domain absent) |
| Knowledge Candidate | unmet |

## Feature flags (representative)

`REAL_EXECUTION_EXPANSION_ENABLED`, `TELEGRAM_PUBLISHING_ENABLED`, `WORKFLOW_*`, `LLM_AGENCY_REASONING_ENABLED`, write-tool flags — all default-off or gated; Alpha journey must not enable them implicitly.

## I7 rule

Do not call execution/publication endpoints from Product Alpha Workspace pages.
