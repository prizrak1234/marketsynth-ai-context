# Commercial MVP P1.1 — ImplementationPlan Domain

## Purpose

Durable, versioned project delivery plan derived only from an **exact approved MarketingStrategy version**.

## Boundary

| Concept | Meaning |
|---------|---------|
| MarketingStrategy | Commercial GTM strategy |
| **ImplementationPlan** | Workstreams, milestones, tasks, gates, roles — delivery decomposition |
| MarketingPlan | Existing ops specialist-task spine |
| Specialist Task | Executable MarketingPlan instruction |
| Agent Run | Execution record |

**ImplementationPlan ≠ MarketingPlan.** Approve plan ≠ create MarketingPlan / specialist tasks / Campaign / Agent Run / execution.

## Eligibility

Allowed: **approved** MarketingStrategy.  
Blocked: draft / under_review / rejected / archived / **superseded** (default). Exact `marketing_strategy_version` required.

## Lineage pins

`marketing_strategy_id` + `marketing_strategy_version` + `business_verdict_id/version` + `evidence_snapshot_id/hash`

## Migration

`20260614_0035` → table `implementation_plans` (revises `20260614_0034`).
