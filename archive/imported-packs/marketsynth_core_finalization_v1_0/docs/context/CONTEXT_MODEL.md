# CONTEXT_MODEL.md

**Project:** Marketsynth  
**Document Type:** Context Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from PROJECT_CONSTITUTION.md, ARCHITECTURE_CORE.md, RUNTIME_MODEL.md

---

# 1. Purpose

This document defines how Marketsynth builds, validates, scopes, snapshots, and uses context.

Context is the controlled input surface for AI reasoning and runtime decisions. Context MUST NOT become an uncontrolled bag of prompts, memory, files, secrets, and assumptions.

# 2. Core Law

Context MUST be tenant-safe, deterministic where feasible, explicit, auditable, and bounded by Source of Truth.

Context MUST NOT include secrets, unrelated tenant data, superseded architecture as authority, raw provider dumps, or unvalidated knowledge as final truth.

# 3. Context Sources

Allowed sources:

1. User request.
2. Tenant/project state.
3. Active runtime state.
4. Approved memory.
5. Approved knowledge.
6. Active contracts.
7. FROZEN/ACTIVE architecture documents.
8. Runtime invariants.
9. Security and approval policies.
10. Evidence and outcome references.

# 4. Forbidden Sources

Forbidden unless sanitized and explicitly permitted:

- credentials;
- API keys;
- OAuth tokens;
- raw provider dumps;
- unrelated tenant data;
- deprecated architecture as authority;
- superseded contracts as authority;
- chat history as Source of Truth;
- unvalidated generated claims.

# 5. Context Priority

```text
PROJECT_CONSTITUTION.md
↓
RUNTIME_INVARIANTS.md
↓
ARCHITECTURE_CORE.md
↓
Relevant FROZEN/ACTIVE models
↓
Contracts
↓
Runtime state
↓
Memory / Knowledge
↓
User request
```

User request defines task intent. User request cannot override constitutional rules.

# 6. Context Types

## 6.1 AI Development Context

Used by Cursor or coding agents. MUST include relevant Source of Truth documents.

## 6.2 Runtime Context

Used inside runtime lifecycle. MUST include tenant/project boundaries and runtime object references.

## 6.3 Approval Context

Used to present action to human owner. MUST include artifact, action, target, risk, and expiration.

## 6.4 Execution Context

Used to prepare execution. MUST include approval reference, target, idempotency, and evidence plan.

## 6.5 Knowledge Context

Used to create or validate Knowledge Candidate. MUST include evidence and outcome lineage.

# 7. Context Snapshot

A Context Snapshot SHOULD contain:

- id;
- tenant_id;
- project_id where applicable;
- purpose;
- source references;
- policy references;
- assembled_at;
- builder;
- hash/fingerprint where feasible;
- redaction summary.

# 8. Context Builder Rules

The Context Builder MUST enforce tenant boundaries, exclude secrets, respect document status, prefer FROZEN over ACTIVE, detect contradictory sources where possible, emit warnings when required Source of Truth is missing, and record source references.

# 9. Context Drift

Context Drift occurs when runtime work uses outdated or conflicting context. Drift SHOULD be detected when governing document, contract, approval, artifact version, tenant scope, or execution target changes.

# 10. AI Context Loading

AI coding agents MUST use `PROJECT_INDEX.md` loading profiles and MUST NOT load random files as authority.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
