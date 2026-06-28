# EVENT_ARCHITECTURE.md

**Project:** Marketsynth  
**Document Type:** Event Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from RUNTIME_MODEL.md, EXECUTION_MODEL.md, OBSERVABILITY_MODEL.md

---

# 1. Purpose

This document defines event architecture for Marketsynth.

Events represent meaningful facts that occurred inside runtime and MAY drive orchestration, audit, supervisor findings, observability, retries, knowledge candidate creation, and notifications.

# 2. Event Principles

Events MUST be tenant-aware where applicable, use explicit type names, include timestamp, include correlation id where feasible, avoid secrets, and preserve safe lineage.

# 3. Event Categories

1. Context Events
2. Decision Events
3. Approval Events
4. Execution Events
5. Evidence Events
6. Outcome Events
7. Knowledge Events
8. Supervisor Events
9. Governance Events
10. Security Events
11. Integration Events

# 4. Event Envelope

```yaml
event_id:
event_type:
event_version:
tenant_id:
project_id:
actor:
source:
correlation_id:
causation_id:
occurred_at:
payload:
safe_metadata:
```

# 5. Event Naming

Recommended format:

```text
domain.object.action.vN
```

Examples:

```text
approval.request.created.v1
approval.decision.approved.v1
execution.job.queued.v1
execution.attempt.failed.v1
knowledge.candidate.created.v1
supervisor.finding.critical.v1
```

# 6. Event Safety

Events MUST NOT contain secrets, credentials, raw provider dumps, unrelated tenant data, or private content unless scoped and allowed.

# 7. Event Ordering

Events SHOULD support ordering within a correlation chain. Strict global ordering is not required unless explicitly needed.

# 8. Idempotency

Event consumers SHOULD be idempotent. Duplicate events MUST NOT create duplicate external effects.

# 9. Compatibility

Breaking event changes require version bump.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
