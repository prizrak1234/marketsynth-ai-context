# Engineering routing fixtures

**Phase:** KB-WPL-01.8

| Task | Expected capability chain |
|------|---------------------------|
| Спроектировать n8n workflow | `engineering.workflow_architecture` |
| Найти ошибку в n8n workflow | `engineering.workflow_debugging` |
| Проверить workflow перед деплоем | `engineering.deployment_review` |
| Найти паттерн retry | `engineering.error_recovery` + pattern `retry_with_idempotency` |

Platform constraint `n8n` binds engineering workflow capabilities.

Safe actions: `use_internal_skill_contract`, `review_workflow_pattern`, `request_connector_design`.

Connector classes remain conceptual — no activation in discovery phase.
