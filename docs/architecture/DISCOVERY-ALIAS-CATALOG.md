# Discovery Alias Catalog

**Phase:** KB-WPL-01.8  
**Version:** 0.1.0  
**Source:** `packages/knowledge/discovery/0.1.0/aliases.json`

Governed alias map for deterministic RU/EN task → capability routing. Aliases do not grant
execution permission.

## Matching rules

1. **Substring match** — normalized alias phrase contained in task text
2. **Stem overlap** — deterministic local suffix normalization for RU inflection
   (e.g. `презентацию` ↔ `презентация`)
3. **Exact ID** — `required_capability_ids` always outrank alias matches

## Alias table

| Alias (RU/EN) | capability_ids |
|---------------|----------------|
| проверить идею / проверить бизнес-идею | `marketing.market_validation` |
| исследовать рынок | `marketing.market_research` |
| конкуренты / проанализировать конкурентов | `marketing.competitive_intelligence` |
| целевая аудитория / icp | `marketing.customer_intelligence` |
| позиционирование / positioning | `marketing.positioning` |
| оффер / offer | `marketing.offer_architecture` |
| пост в telegram / telegram post / опубликовать пост | `marketing.distribution` |
| youtube script / сценарий youtube | `deliverables.content_architecture` |
| презентация / presentation / создать презентацию | `marketing.presentation_architecture`, `deliverables.presentation_architecture` |
| n8n workflow / спроектировать n8n workflow / n8n | `engineering.workflow_architecture`, `engineering.workflow_debugging` |
| ошибка n8n / n8n debugging | `engineering.workflow_debugging` |
| deployment review | `engineering.deployment_review` |
| связать знания / связать документы / найти дубли | `knowledge.knowledge_linking` |
| knowledge linking | `knowledge.knowledge_linking` |
| retry pattern | `engineering.error_recovery` + pattern `retry_with_idempotency` |
| approval pattern | `marketing.distribution` + pattern `human_approval_before_publication` |
| запустить рекламу / advertising | `marketing.distribution` |
| workflow | `engineering.workflow_architecture` |

## Platform bindings

| Platform | Bound capabilities |
|----------|-------------------|
| `n8n` | `engineering.workflow_architecture`, `engineering.workflow_debugging`, `engineering.deployment_review`, `engineering.error_recovery` |

Platform constraints apply when query mentions platform or related tokens (`workflow`, `debug`, etc.).

## Versioning

Alias changes require bundle regeneration:

```bash
uv run python scripts/generate_discovery_bundle.py
```

Update `FROZEN_DISCOVERY_BUNDLE_HASH` in `app/knowledge/discovery/serialization.py` after regeneration.
