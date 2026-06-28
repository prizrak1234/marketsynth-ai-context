# DATA_MODEL.md

**Project:** Marketsynth  
**Document Type:** Data Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from PROJECT_CONSTITUTION.md, ARCHITECTURE_CORE.md, CONTRACT_GUIDELINES.md

---

# 1. Purpose

This document defines high-level data architecture for Marketsynth.

It is technology-independent and does not prescribe a specific database.

# 2. Core Law

Data model MUST preserve tenant isolation, ownership, runtime lineage, approval boundaries, evidence safety, knowledge scope, and contract stability.

# 3. Core Entity Families

1. Identity / Ownership
2. Tenant / Project
3. Task / Work Item
4. Agent / Agent Run
5. Context / Decision
6. Approval
7. Execution
8. Evidence
9. Outcome
10. Knowledge Candidate
11. Memory
12. Domain Registry
13. Provider Integration
14. Audit Event
15. Supervisor Finding
16. Cost Record

# 4. Ownership Fields

Tenant-owned entities MUST include ownership linkage.

Minimum:

```yaml
tenant_id:
owner_id or account_id:
project_id where applicable:
```

# 5. Runtime Lineage Fields

Runtime entities SHOULD preserve reconstructable lineage via context_id, decision_id, approval_id, execution_job_id, execution_attempt_id, evidence_id, outcome_id, knowledge_candidate_id, correlation_id, and causation_id where applicable.

# 6. Status Fields

Core lifecycle objects MUST use explicit status enums. Free-form status strings are prohibited for core runtime entities.

# 7. Metadata

Metadata MUST be safe and MUST NOT contain secrets.

# 8. Versioning

Versioning SHOULD apply to documents, contracts, artifacts, memory, knowledge, execution packages, and approvals tied to artifact version.

# 9. Deletion and Retention

Retention policy SHOULD define deletion, archival, anonymization, audit retention, and tenant data deletion.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
