# TESTING_ARCHITECTURE.md

**Project:** Marketsynth  
**Document Type:** Testing Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from RUNTIME_INVARIANTS.md, AI_DEVELOPMENT_RULES.md

---

# 1. Purpose

This document defines testing architecture for Marketsynth. Tests protect architecture and are not optional polish.

# 2. Test Categories

1. Unit Tests
2. Service Tests
3. Contract Tests
4. Runtime Invariant Tests
5. Tenant Isolation Tests
6. Approval Boundary Tests
7. Execution Safety Tests
8. Provider Adapter Tests
9. Security Tests
10. Regression Tests
11. Migration Tests
12. AI Output Validation Tests

# 3. Critical Invariant Tests

CRITICAL invariants MUST be protected by tests or explicit enforcement mechanisms before production.

Examples:

- no execution without approval;
- readiness is not approval;
- Knowledge Candidate never crosses tenant;
- tenant data isolation;
- no secret leakage;
- invalid transitions rejected.

# 4. Tenant Tests

Tenant tests MUST verify cross-tenant reads fail, writes fail, memory retrieval fails, knowledge promotion fails, and execution ownership mismatch fails.

# 5. Approval Tests

Approval tests MUST verify execution blocked without approval, expired approval blocked, rejected approval blocked, approval scope mismatch blocked, and owner unavailable does not imply approval.

# 6. Execution Tests

Execution tests SHOULD verify success path, failure evidence, replay validation, idempotency, inactive target, provider timeout, provider auth failure, and safe errors.

# 7. Contract Tests

Contract tests SHOULD verify required fields, ownership fields, lifecycle states, invalid transitions, serialization, backward compatibility, and safe error shape.

# 8. AI Coding Test Rule

AI agents SHOULD add or update tests when changing behavior and MUST NOT delete failing tests merely to pass CI.

# 9. Test Audit Report

Before release, report invariant coverage, missing critical tests, skipped tests, known risks, and migration gaps.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
