# Commercial MVP P0.2 — Frontend integration

## Adapters

- `web/src/lib/api/types/investigations.ts`
- `web/src/lib/api/endpoints/investigations.ts`
- `investigation-api-adapter.ts` — DTO → lifecycle view model
- `investigation-sync.ts` — explicit create/start + GET-only load
- `investigation-reconciliation.ts` — local vs backend lifecycle
- `investigation-domain-errors.ts` — error codes

## Modes

| Mode | Behavior |
|------|----------|
| MOCK | Product Alpha local scenarios; backend Investigation calls off |
| BACKEND | Load Project + latest Investigation (if any); Source/Evidence unavailable; no mock evidence claim |
| HYBRID | Backend lifecycle SoT; Source/Evidence may stay local preview with labels |

## Route

`/workspace/projects/{projectId}/investigation`  
Optional `?investigationId=`

- GET / page load: **does not** create Investigation
- CTA «Создать исследование» → draft
- CTA «Начать исследование» → active (lifecycle only)
- Notice: «Автоматический исследовательский контур пока не подключён.»

## localStorage

Keep `marketsynth.product_alpha.investigation.v1.{projectId}`.  
Add link meta key `marketsynth.product_alpha.investigation.link.v1.{projectId}` (`backendInvestigationId`, version, brief id).  
No automatic upload; backend wins lifecycle; conflict surfaced when local stage differs.

## Selfcheck

`npx --yes tsx src/lib/integration/investigation-p0-2.selfcheck.ts`
