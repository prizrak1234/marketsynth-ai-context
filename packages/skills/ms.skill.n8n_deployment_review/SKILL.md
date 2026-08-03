# n8n Deployment Review

**Skill ID:** `ms.skill.n8n_deployment_review` v0.1.0  
**Status:** candidate · non-executable · `production_eligible=false`

## Purpose

Review whether a proposed n8n workflow change is safe for **manual** deployment and
activation. Produces an activation gate — never authorizes execution itself.

## Activation gate

`final_manual_action_required` must always be `true`. Forbidden output: `deployed`,
`activated`, `approval_granted`, `deployment_id`.

## Consumes

Architecture specifications from `ms.skill.n8n_workflow_architecture` and diagnostic
evidence from `ms.skill.n8n_workflow_debugging` as review inputs.
