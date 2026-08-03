# ms.skill.n8n_workflow_debugging

**Version:** 0.1.0  
**Status:** Candidate (KB-WPL-01.4)  
**output_contract_type:** `research`  
**executable:** `false`

## Purpose

Produce an evidence-backed diagnostic report and safe **sandbox plan** for a failed or
unstable n8n workflow. No live mutation, no node execution, no credential rotation.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Failure localization and classification | Live patch / workflow update |
| Probable cause analysis | Node execution |
| Sandbox plan (disabled pub/billing) | Credential rotation |
| Remediation candidates (manual) | Deployment / activation |

## Error taxonomy

Finite classes include: `input_contract_error`, `expression_error`, `provider_rate_limit`,
`duplicate_event`, `unknown_outcome`, `prompt_injection_risk`, `code_node_error`, etc.

## Frozen knowledge

References patterns and practices from frozen WPL. Sandbox plan must keep publication
and billing disabled/mocked.

## Key semantic rules

1. Missing evidence prevents high diagnostic confidence.
2. Unknown-outcome write cannot recommend blind retry.
3. Unsanitized logs rejected at input validation.

## Package location

`packages/skills/ms.skill.n8n_workflow_debugging/`

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_4_n8n_engineering_skills.py -q -k debugging
```

## Freeze audit

[KB-WPL-01.4B-n8n-workflow-debugging-freeze.md](../rfc/KB-WPL-01.4B-n8n-workflow-debugging-freeze.md)
