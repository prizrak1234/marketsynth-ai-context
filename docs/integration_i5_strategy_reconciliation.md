# Integration I5 — Strategy reconciliation

## Modes

| Mode | Strategy body | MarketingPlan |
|------|---------------|---------------|
| mock | Alpha deterministic | not fetched |
| hybrid | local preview labelled | related plans as ops context |
| backend | empty/unsupported Strategy body | related plans only; no mock Strategy |

## Eligibility

I4 rules stand. MarketingPlan existence does **not** unlock Strategy for NO_GO / INSUFFICIENT_DATA / draft. Legacy plans shown as conflict notice.

## Multi-plan rule

Non-archived, `created_at` desc; primary = newest — labelled **related ops plan**, never current Strategy.

## Local key

`marketsynth.product_alpha.strategy.v1.{projectId}` — no auto-upload; no dual-write; optional future link metadata documented in adapter policy.
