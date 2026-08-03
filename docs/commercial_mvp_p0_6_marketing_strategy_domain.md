# Commercial MVP P0.6 — MarketingStrategy Domain

## Purpose

Durable commercial go-to-market strategy linked to an exact approved BusinessVerdict.

## Eligibility

| Verdict | Strategy |
|---|---|
| approved GO | allowed |
| approved CONDITIONAL_GO | allowed (Verdict conditions preserved by reference) |
| NO_GO / INSUFFICIENT_DATA | blocked |
| draft / under_review / rejected | blocked |

## Boundary

MarketingStrategy ≠ MarketingPlan ≠ ImplementationPlan ≠ Campaign ≠ Execution approval.

Approve Strategy confirms Strategy only — no MarketingPlan, Campaign, Agent Run, or execution.

## Migration

`20260614_0034` revises `20260614_0033`. Table: `marketing_strategies`.
