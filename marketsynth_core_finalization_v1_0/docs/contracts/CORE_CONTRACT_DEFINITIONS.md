# CORE_CONTRACT_DEFINITIONS.md

**Project:** Marketsynth  
**Document Type:** Core Contract Definitions  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from CONTRACT_GUIDELINES.md, RUNTIME_MODEL.md

---

# 1. Purpose

This document defines canonical core contract shapes for Marketsynth.

It is technology-independent and may be translated into DTOs, schemas, database models, or API contracts.

# 2. Global Rules

All tenant-owned contracts MUST include ownership context. All lifecycle contracts MUST use explicit statuses. All public errors MUST be safe. All material contracts SHOULD include timestamps.

# 3. Common Fields

```yaml
id:
tenant_id:
project_id:
status:
created_at:
updated_at:
metadata:
```

`metadata` MUST be safe and MUST NOT contain secrets.

# 4. Project

```yaml
Project:
  id:
  tenant_id:
  owner_id:
  name:
  description:
  status: active | paused | archived
  metadata:
  created_at:
  updated_at:
```

# 5. Task

```yaml
Task:
  id:
  tenant_id:
  project_id:
  owner_id:
  title:
  description:
  status: draft | queued | running | blocked | completed | cancelled | archived
  domain:
  priority:
  metadata:
  created_at:
  updated_at:
```

# 6. Agent

```yaml
Agent:
  id:
  tenant_id:
  project_id:
  type:
  name:
  status: draft | active | paused | archived
  capabilities:
  permissions:
  tool_allowlist:
  memory_scope:
  config:
  created_at:
  updated_at:
```

`config` MUST NOT contain secrets.

# 7. AgentRun

```yaml
AgentRun:
  id:
  tenant_id:
  project_id:
  task_id:
  agent_id:
  status: queued | running | succeeded | failed | cancelled
  input_payload:
  output_payload:
  error:
  context_id:
  started_at:
  finished_at:
  created_at:
  updated_at:
```

# 8. ContextSnapshot

```yaml
ContextSnapshot:
  id:
  tenant_id:
  project_id:
  purpose:
  source_references:
  policy_references:
  redaction_summary:
  fingerprint:
  created_by:
  created_at:
```

# 9. DecisionRecord

```yaml
DecisionRecord:
  id:
  tenant_id:
  project_id:
  context_id:
  decision_type:
  actor:
  target_domain:
  rationale:
  confidence:
  status: proposed | accepted | rejected | superseded
  created_at:
```

DecisionRecord is not approval.

# 10. ApprovalRequest

```yaml
ApprovalRequest:
  id:
  tenant_id:
  project_id:
  artifact_id:
  artifact_version:
  action:
  target:
  risk_summary:
  requester:
  status: pending | approved | rejected | expired
  expires_at:
  created_at:
  updated_at:
```

# 11. ApprovalDecision

```yaml
ApprovalDecision:
  id:
  tenant_id:
  project_id:
  approval_request_id:
  decision: approved | rejected
  actor:
  reason:
  decided_at:
```

# 12. ExecutionJob

```yaml
ExecutionJob:
  id:
  tenant_id:
  project_id:
  approval_request_id:
  artifact_id:
  artifact_version:
  action:
  target:
  idempotency_key:
  status: queued | running | succeeded | failed | cancelled
  attempts_count:
  error:
  created_at:
  started_at:
  finished_at:
```

# 13. ExecutionAttempt

```yaml
ExecutionAttempt:
  id:
  tenant_id:
  project_id:
  execution_job_id:
  attempt_number:
  provider:
  safe_request_metadata:
  safe_response_metadata:
  status: running | succeeded | failed
  error:
  started_at:
  finished_at:
```

# 14. EvidenceRecord

```yaml
EvidenceRecord:
  id:
  tenant_id:
  project_id:
  execution_job_id:
  execution_attempt_id:
  evidence_type:
  safe_payload:
  external_reference:
  created_at:
```

# 15. OutcomeRecord

```yaml
OutcomeRecord:
  id:
  tenant_id:
  project_id:
  evidence_id:
  outcome_type:
  interpretation:
  metrics:
  confidence:
  limitations:
  created_at:
```

# 16. KnowledgeCandidate

```yaml
KnowledgeCandidate:
  id:
  tenant_id:
  project_id:
  outcome_id:
  evidence_id:
  claim:
  scope: session | project | tenant | global_candidate
  status: proposed | validating | promoted | rejected | archived
  validation_result:
  created_at:
  updated_at:
```

KnowledgeCandidate MUST NOT cross tenant boundary.

# 17. MemoryItem

```yaml
MemoryItem:
  id:
  tenant_id:
  project_id:
  scope:
  memory_type:
  content:
  source_reference:
  status: proposed | active | superseded | deprecated | archived
  version:
  created_at:
  updated_at:
```

# 18. SupervisorFinding

```yaml
SupervisorFinding:
  id:
  tenant_id:
  project_id:
  finding_type:
  severity: info | warning | major | critical
  target_reference:
  description:
  recommendation:
  status: open | acknowledged | resolved | dismissed
  created_at:
  updated_at:
```

Critical findings may block execution.

# 19. AuditEvent

```yaml
AuditEvent:
  id:
  tenant_id:
  project_id:
  event_type:
  actor:
  target_reference:
  correlation_id:
  safe_payload:
  occurred_at:
```

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
