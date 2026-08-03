# P1.2 Frontend flow

Adapters:

- `marketing-plan-handoff-api-adapter.ts`
- `marketing-plan-handoff-preview-adapter.ts`
- `marketing-plan-handoff-errors.ts`
- `marketing-plan-lineage-adapter.ts`

UI (frozen A6 Implementation workspace panel):

1. Проверить готовность к передаче
2. Preview classifications + existing plans + side effects=none
3. Checkbox: Создать только черновик MarketingPlan
4. Создать черновик MarketingPlan
5. Result: draft id/version/status + no-execution notice

Modes: MOCK blocks write; BACKEND/HYBRID use durable approved ImplementationPlan only.
