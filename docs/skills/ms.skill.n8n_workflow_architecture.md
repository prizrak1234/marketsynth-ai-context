# ms.skill.n8n_workflow_architecture

**Version:** 0.1.0  
**Status:** Candidate (KB-WPL-01.4)  
**output_contract_type:** `research`  
**executable:** `false`

## Purpose

Transform a business automation requirement into a safe, provider-aware,
**non-executable** n8n workflow architecture specification. Designs architecture only —
no workflow JSON, no deployment, no activation.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Trigger/boundary/node-role planning | Workflow JSON generation |
| Pattern and practice references | n8n API / import / execution |
| Approval, evidence, idempotency design | Credential values |
| Deployment prerequisite review | Runtime authorization |

## Frozen knowledge

Consumes Workflow Pattern Library v0.1.0-frozen (`1ddd0d0…`). Pattern references use
`PatternSelectionReference` with `runtime_authorized=false`.

## Key semantic rules

1. Publication workflow requires `human_approval_before_publication`.
2. Retry on write requires `retry_with_idempotency`.
3. LLM-to-API requires structured validation pattern.
4. Missing error path blocks `ready_for_implementation_review`.

## Package location

`packages/skills/ms.skill.n8n_workflow_architecture/`

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_4_n8n_engineering_skills.py -q -k architecture
```

## Freeze audit

[KB-WPL-01.4A-n8n-workflow-architecture-freeze.md](../rfc/KB-WPL-01.4A-n8n-workflow-architecture-freeze.md)
