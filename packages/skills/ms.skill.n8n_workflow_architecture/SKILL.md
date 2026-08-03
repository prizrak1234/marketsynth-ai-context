# n8n Workflow Architecture

**Skill ID:** `ms.skill.n8n_workflow_architecture` v0.1.0  
**Status:** candidate · non-executable · `production_eligible=false`

## Purpose

Design n8n workflow **architecture specifications** only. Consumes the frozen
Workflow Pattern Library (`0.1.0-frozen`) as read-only knowledge.

## Allowed

- Normalize requirements into workflow boundaries, triggers, node roles
- Reference frozen Workflow Patterns and PracticeRecords with explainable selection
- Design approval, evidence, idempotency, retry, error, and monitoring plans
- Record provider version scope with `requires_reverification`

## Forbidden

- n8n API calls, workflow import, workflow JSON output
- Credential values, deployment, activation, execution
- Inferring runtime authorization from pattern references

## Pattern library binding

Every pattern reference must include `library_semantic_hash` matching frozen library.
`runtime_authorized` must be `false`. Maturity must be `reviewed`.

## Output readiness

`architecture_readiness=ready_for_implementation_review` requires error paths and
applicable pattern references (publication → approval pattern, write retry → idempotency).
