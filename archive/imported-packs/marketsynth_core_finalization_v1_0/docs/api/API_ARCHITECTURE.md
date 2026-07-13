# API_ARCHITECTURE.md

**Project:** Marketsynth  
**Document Type:** API Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from ARCHITECTURE_CORE.md, CONTRACT_GUIDELINES.md

---

# 1. Purpose

This document defines API architecture principles for Marketsynth. It does not prescribe a specific framework.

# 2. API Role

API layer handles transport, authentication boundary, request validation, response mapping, error mapping, and routing to services.

API layer MUST NOT contain business policy.

# 3. Layer Rule

```text
API Router → Service → Repository / Adapter
```

API Router MUST NOT directly perform complex business rules or bypass Service for runtime operations.

# 4. API Contract Requirements

API endpoints SHOULD map to explicit contracts. Public payloads SHOULD include typed request, typed response, safe errors, status, ownership enforcement, and pagination where applicable.

# 5. Authentication and Authorization

API MUST validate identity, tenant access, project access, action permission, and approval authority where applicable.

# 6. Runtime API Families

Expected API families:

- projects
- tasks
- agents
- agent-runs
- context
- approvals
- execution
- evidence
- outcomes
- knowledge candidates
- memory
- audit
- supervisor
- integrations

# 7. Error Responses

API errors MUST be safe and MUST NOT expose raw provider errors, secrets, stack traces, or unrelated tenant data.

# 8. Idempotency

Mutating endpoints that can create duplicate external effects SHOULD accept or generate idempotency keys.

# 9. API Versioning

Breaking API changes require versioning, migration plan, and ADR/RFC where material.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
