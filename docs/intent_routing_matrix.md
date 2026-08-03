# Intent routing matrix (Phase H1)

Deterministic only (`app/domain/user_request_routing.py`). No LLM unless a future feature flag is added.

| Example input | Category | Kind | Specialist alias | Investigation |
|---------------|----------|------|------------------|---------------|
| Напиши 10 постов для Telegram | content | specialist_task | content_specialist | no |
| Составь контент-план | content_plan | specialist_task | content_planner | no |
| Создай Telegram-бота | telegram_bot | specialist_task | programmer | no |
| Сделай лендинг | website | specialist_task | programmer | no |
| Нужен сайт | website | clarify | — | — |
| Хочу SaaS для риелторов | saas | specialist_task | programmer | project required |
| Автоматизируй заявки | automation | specialist_task | programmer | no forced Investigation |
| Хочу открыть кафе | idea_validation | project_intake | researcher | after intake |
| Исследуй рынок | market_research | project_intake | researcher | after intake |
| Анализ конкурентов | competitor_analysis | project_intake | researcher | after intake |
| Маркетинговая стратегия | marketing_strategy | project_intake | strategist | after intake |
| Нужна реклама | general | clarify | — | — |

Frontend mirrors categories for labels via `web/src/lib/i18n`.
