# OBSERVABILITY_MODEL.md

**Project:** Marketsynth  
**Document Type:** Observability Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from RUNTIME_MODEL.md, SECURITY_MODEL.md, EVENT_ARCHITECTURE.md

---

# 1. Purpose

This document defines how Marketsynth observes runtime behavior safely.

Observability supports reliability, auditability, cost control, debugging, governance, and supervisor review.

# 2. Pillars

Marketsynth SHOULD support logs, metrics, traces, audit events, supervisor findings, cost records, and health checks.

# 3. Safe Observability Law

Observability MUST NOT leak secrets, credentials, raw provider dumps, unrelated tenant data, private tenant content, or sensitive prompts.

# 4. Logs

Logs SHOULD include event name, status, tenant-safe identifiers, correlation id, duration, safe error code, actor type, and component.

# 5. Metrics

Core metrics SHOULD include runtime jobs by status, pending approvals, execution attempts, failed executions, retry count, queue age, provider latency, provider error rate, LLM usage, cost by tenant/project/provider, and supervisor critical findings.

# 6. Traces

Traces SHOULD connect Context → Decision → Approval → Execution → Evidence → Outcome → Knowledge Candidate.

# 7. Audit Events

Audit Events MUST be generated for approval decisions, real execution, execution failures, tenant boundary violations, security violations, knowledge promotion, and frozen document changes.

# 8. Health Checks

Health checks SHOULD cover API availability, storage connectivity, queue state, provider adapter availability, stuck executions, old pending approvals, and failed job accumulation.

# 9. Cost Observability

LLM and provider usage SHOULD be tracked by tenant, project, agent, provider, model, operation type, and estimated cost.

# 10. Supervisor Integration

Supervisor Runtime SHOULD consume observability signals and create findings for invariant failure, provider failures, suspicious tenant access, execution anomalies, and approval bypass attempts.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
