# Automation Engineering Profession Map

**Profession:** `profession.automation_architect`  
**Phase:** KB-WPL-01.7

## Path

```
workflow_architecture → deployment_review → (future controlled implementation)
→ debugging / recovery
```

## Skill bindings

| Capability | Skill |
|------------|-------|
| workflow_architecture | `ms.skill.n8n_workflow_architecture` |
| workflow_debugging | `ms.skill.n8n_workflow_debugging` |
| deployment_review | `ms.skill.n8n_deployment_review` |

## Pattern-backed capabilities

pattern_selection, workflow_backup, error_recovery, observability, connector_integration_design, runtime_safety, test_and_replay_design.

## Deferred

workflow_documentation, provider_version_review.

## Forbidden

Deploy, activate, access credentials, mutate live workflows, grant Connector permissions.

Native Telegram publication boundary preserved in existing publishing foundation — no Telegram MCP.
