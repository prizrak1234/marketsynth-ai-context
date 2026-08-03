# Manual Audit Records — Pilot

Each pattern has an audit record in `pilot_audit_records.json`.

| Audit ID | Pattern | Decision | Summary |
|----------|---------|----------|---------|
| audit-human_approval_before_publication | human_approval_before_publication | approved_for_pilot | Publication + explicit approval signals in catalog metadata |
| audit-structured_LLM_to_API_request | structured_LLM_to_API_request | approved_for_pilot | Agent orchestration with transport write after generation |
| audit-retry_with_idempotency | retry_with_idempotency | approved_for_pilot | Alert workflows with webhook trigger and publication side effects |
| audit-evidence_grounded_generation | evidence_grounded_generation | approved_for_pilot | RAG category + agent stack without publication |
| audit-lead_capture_to_qualification | lead_capture_to_qualification | approved_for_pilot | Lead generation with qualification before write |
| audit-draft_to_human_approval | draft_to_human_approval | approved_for_pilot | Moderation/legal review human_approval signals |
| audit-workflow_backup | workflow_backup | approved_for_pilot | Explicit workflow_backup capability in catalog |
| audit-error_workflow_or_recovery | error_workflow_or_recovery | approved_for_pilot | Failure alert + API refresh recovery topology |

All audits: `reviewer=KB-WPL-01.3A-pilot`, `program_phase=KB-WPL-01.3A`.

Patterns are **not** production eligible. Manual audit confirms architecture abstraction only.
