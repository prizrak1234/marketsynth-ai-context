# KB-WPL-01.4B — n8n Workflow Debugging Skill Freeze

| Field | Value |
|-------|-------|
| **Skill** | `ms.skill.n8n_workflow_debugging` |
| **Version** | 0.1.0 |
| **Status** | candidate |
| **Package hash** | `e200b06ea6701f0667952b05e523077280e0238a9717787c8a096dc6dcd3d70f` |

## Verdict

Candidate non-executable diagnostic Skill. Sandbox plans are specification-only.
Forbidden outputs: `live_patch`, `workflow_update`, `node_execution`, `credential_rotation`,
`activation_request`, `deployment_result`, `approval_granted`.

## Readiness states

`ready_for_manual_fix`, `ready_for_sandbox_reproduction`, `partially_diagnosed`,
`blocked_by_missing_evidence`, `conflicted`, `out_of_scope`.

## Audit

Registry projection: candidate. Audit readiness: `ready_for_audit`. No execution lineage.
