# Marketing routing fixtures

**Phase:** KB-WPL-01.8

| Task | Expected capability chain |
|------|---------------------------|
| Проверить бизнес-идею | `marketing.market_validation` |
| Исследовать рынок | `marketing.market_research` |
| Проанализировать конкурентов | `marketing.competitive_intelligence` |
| Определить ICP | `marketing.customer_intelligence` |
| Сделать позиционирование | `marketing.positioning` |
| Создать оффер | `marketing.offer_architecture` |
| Сделать пост в Telegram | `marketing.distribution` |
| Запустить рекламу | `marketing.distribution` + billing blockers |
| Опубликовать пост | `marketing.distribution` + publication approval gap |

Dependency ordering when both present: `market_validation` before `positioning`; `claim_substantiation` before `offer_architecture`.

Safe actions: `use_internal_skill_contract`, `review_workflow_pattern`, `request_human_review` (for billing/publication).
