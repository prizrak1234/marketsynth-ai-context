# n8n Workflow Debugging

**Skill ID:** `ms.skill.n8n_workflow_debugging` v0.1.0  
**Status:** candidate · non-executable · `production_eligible=false`

## Purpose

Produce evidence-backed diagnostic reports and **sandbox plans** for failed or unstable
n8n workflows. No live mutation, no node execution.

## Sandbox boundary

Sandbox plans may specify isolated test input, mocked expensive steps, disabled publication
and billing, synthetic credential references. The Skill does **not** execute the sandbox.

## Forbidden output fields

`live_patch`, `workflow_update`, `node_execution`, `credential_rotation`, `activation_request`
