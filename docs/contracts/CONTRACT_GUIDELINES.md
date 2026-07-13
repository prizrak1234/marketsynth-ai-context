# CONTRACT_GUIDELINES.md

**Project:** Marketsynth  
**Document Type:** Contract Design Guidelines  
**Authority:** Derived from `PROJECT_CONSTITUTION.md` and `ARCHITECTURE_CORE.md`  
**Status:** FROZEN  
**Version:** 1.0.0  

---

# 1. Purpose

This document defines how Marketsynth contracts MUST be designed.

Contracts define public semantics.

Implementation conforms to contracts.

---

# 2. Contract Definition

A contract is a formal agreement describing:

- identity;
- ownership;
- lifecycle;
- input;
- output;
- status;
- metadata;
- errors;
- transitions;
- audit behavior.

Contracts MAY be represented as schemas, DTOs, service interfaces, events, or state definitions.

---

# 3. Contract Principles

Contracts MUST be:

- explicit;
- typed where possible;
- tenant-aware where applicable;
- lifecycle-aware;
- versionable;
- testable;
- stable;
- safe.

Contracts MUST NOT hide business semantics in free-form text.

---

# 4. Required Contract Fields

Core runtime contracts SHOULD define:

- id;
- tenant_id or owner scope;
- project_id where applicable;
- status;
- created_at;
- updated_at;
- metadata;
- error field where applicable;
- lineage references where applicable.

---

# 5. Ownership

Any contract tied to tenant data MUST include enough ownership context to enforce isolation.

Contracts MUST NOT rely on caller honesty for tenant isolation.

---

# 6. Lifecycle States

Lifecycle states SHOULD be explicit finite enums.

Invalid transitions MUST be rejected.

Free-form lifecycle strings are prohibited for core runtime contracts.

---

# 7. Error Contracts

Public error contracts MUST be safe.

They MUST NOT expose:

- secrets;
- credentials;
- raw provider errors;
- unrelated tenant data;
- stack traces in user-facing payloads.

---

# 8. Versioning

Contract changes:

- patch: clarification;
- minor: compatible addition;
- major: breaking semantic change.

Breaking changes require ADR/RFC and migration plan.

---

# 9. Core Contract Families

Core families:

- Project
- Task
- Agent
- AgentRun
- ContextSnapshot
- DecisionRecord
- ApprovalRequest
- ApprovalDecision
- ExecutionJob
- ExecutionAttempt
- EvidenceRecord
- OutcomeRecord
- KnowledgeCandidate
- MemoryItem
- SupervisorFinding
- AuditEvent
- ProviderAdapter

---

# 10. Contract Testing

Contracts SHOULD be tested for:

- serialization;
- validation;
- ownership;
- invalid state;
- transition rules;
- backward compatibility;
- safe errors.

---

# 11. AI Contract Rules

AI agents MUST NOT:

- silently rename contract fields;
- silently change DTO meaning;
- remove ownership fields;
- loosen tenant boundaries;
- replace finite states with strings;
- expose provider internals;
- add breaking changes without ADR/RFC.

---

# 12. Audit Report

Status: PASSED.

This document preserves Source of Truth hierarchy, tenant isolation, safe errors, lifecycle discipline, and AI implementation safety.

This document is FROZEN v1.0.0.
