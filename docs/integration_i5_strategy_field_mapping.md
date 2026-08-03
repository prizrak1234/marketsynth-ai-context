# Integration I5 — Strategy field mapping

Canonical code matrix: `STRATEGY_PLAN_FIELD_MATRIX` in `web/src/lib/integration/strategy-plan-mapping.ts`.

| Strategy field | MarketingPlan field | Transform | Authority | Conflict rule |
|----------------|---------------------|-----------|-----------|---------------|
| objectives | specialist_tasks.objective | **none** | Strategy | never treat task prompt as objective |
| summary | title/goal | display ops context | split | plan goal ≠ strategic narrative |
| segments | — | unsupported | Strategy | never invent |
| positioning | — | unsupported | Strategy | never invent |
| offers | — | unsupported | Strategy | never invent |
| channels / funnel / assets / budget / metrics | — | unsupported | Strategy | never invent |
| conditions / risks / assumptions | — | Verdict/Strategy | Strategy | keep separate from supervisor |
| readiness | plan.status / runs | none | split | plan approve ≠ strategy ready |
| version | plan versions | link ids only later | split | no auto-sync |

Write policy I5: **read-only** MarketingPlan from Strategy Workspace. Dual-write forbidden.
