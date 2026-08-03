# Integration I5 — Strategy ↔ MarketingPlan semantics

| Capability | Alpha Strategy | MarketingPlan | Relationship | SoT | Action |
|------------|----------------|---------------|--------------|-----|--------|
| Strategic objectives | objectives[] | task.objective | semantic conflict | local Strategy | do not map |
| Positioning / offers / segments | yes | absent | absent | local Strategy | unsupported on plan |
| Channels / funnel / budget / KPIs | yes | absent | absent | local Strategy | unsupported |
| Ops work queue | n/a | specialist_tasks | backend lower-level | MarketingPlan | show as ops panel |
| Plan approve | local status | POST approve | conflict if collapsed | split | separate |
| Execution readiness | FE planning meter | approved + runs | conflict | split | never equate |
| Scope | project | project (+ soft campaign) | partial | split | Strategy stays project-level |

**Decision: Option B** (docs + adapters). Thin awareness of plan title/goal/status as ops context only — not Option C field fill of Strategy.

Chain preserved:

```
Business Verdict → Strategy (local/GTM) → MarketingPlan (ops) → Implementation (I6) → Execution
```
