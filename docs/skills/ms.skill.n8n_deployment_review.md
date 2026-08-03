# ms.skill.n8n_deployment_review

**Version:** 0.1.0  
**Status:** Candidate (KB-WPL-01.4)  
**output_contract_type:** `research`  
**executable:** `false`

## Purpose

Review whether a proposed n8n workflow change is safe and sufficiently prepared for
**manual** deployment and activation. This Skill is not a deployment gateway.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Deployment readiness review | Deploy / activate workflows |
| Architecture conformance check | n8n API calls |
| Activation gate preparation | `approval_granted` output |
| Credential reference review (IDs only) | Credential values |

## Activation gate

Every output includes an activation gate with `final_manual_action_required=true`.
Deployment Review never authorizes execution itself.

## Key semantic rules

1. Publication without approval → blocked.
2. Billing without budget/approval → blocked.
3. Retry without idempotency → blocked.
4. Missing rollback or test evidence blocks ready states.
5. `deployed`, `activated`, `approval_granted` fields forbidden.

## Package location

`packages/skills/ms.skill.n8n_deployment_review/`

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_4_n8n_engineering_skills.py -q -k deployment
```

## Freeze audit

[KB-WPL-01.4C-n8n-deployment-review-freeze.md](../rfc/KB-WPL-01.4C-n8n-deployment-review-freeze.md)
