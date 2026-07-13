# RUNTIME_INVARIANTS.md

**Project:** Marketsynth  
**Document Type:** Runtime Invariants Specification  
**Authority:** Derived from `PROJECT_CONSTITUTION.md`  
**Status:** FROZEN  
**Version:** 1.0.0  

---

# 1. Purpose

This document defines runtime laws that MUST remain true across all valid Marketsynth states.

An invariant violation is a blocking architectural defect.

Implementation, tests, AI-generated code, workflows, integrations, migrations, and runtime behavior MUST preserve these invariants.

---

# 2. Invariant Severity

Severity levels:

- **CRITICAL** — violation blocks execution/release.
- **MAJOR** — violation requires remediation before production use.
- **MINOR** — violation requires planned correction.
- **ADVISORY** — recommended architectural guardrail.

---

# 3. Core Invariants

## INV-001 — Constitutional Supremacy

**Severity:** CRITICAL

`PROJECT_CONSTITUTION.md` is the highest authority.

No implementation, prompt, chat history, local code, or AI instruction may override it.

## INV-002 — Architecture as Source of Truth

**Severity:** CRITICAL

Architecture defines implementation semantics.

Implementation does not define architecture.

## INV-003 — Technology Independence

**Severity:** CRITICAL

Changing framework, database, LLM provider, orchestration library, vector store, queue, or hosting environment MUST NOT change Source of Truth semantics.

## INV-004 — Legacy Code Non-Authority

**Severity:** CRITICAL

BotFazer v3 legacy code is not architectural truth.

It may be migrated, audited, reused, or discarded, but it MUST NOT override Marketsynth architecture.

## INV-005 — Tenant Isolation

**Severity:** CRITICAL

Tenant-owned data MUST NOT be visible, retrievable, inferred, merged, or reused across tenant boundaries.

## INV-006 — Knowledge Candidate Tenant Boundary

**Severity:** CRITICAL

Knowledge Candidate never crosses tenant boundary.

## INV-007 — No Cross-Tenant Memory

**Severity:** CRITICAL

Memory MUST NOT cross tenant boundary.

## INV-008 — Ownership Validation

**Severity:** CRITICAL

Any read, write, approval, execution, evidence, outcome, or knowledge promotion involving tenant-owned data MUST validate ownership.

## INV-009 — Readiness Is Not Approval

**Severity:** CRITICAL

Readiness indicates technical eligibility only.

Readiness MUST NOT trigger real execution.

## INV-010 — Human Approval Before Real Execution

**Severity:** CRITICAL

Real execution MUST require valid Human Approval unless explicitly classified as safe internal simulation.

## INV-011 — Approval Scope

**Severity:** CRITICAL

Approval MUST be scoped to action, artifact, tenant, target, and expiration where applicable.

## INV-012 — No Invented Approval

**Severity:** CRITICAL

If owner is unavailable, runtime MUST wait, escalate, expire, or follow explicit delegation policy.

Runtime MUST NOT invent approval.

## INV-013 — Approval State Integrity

**Severity:** CRITICAL

Approval states MUST be explicit and finite.

Canonical states: pending, approved, rejected, expired.

## INV-014 — Execution Preconditions

**Severity:** CRITICAL

Real execution requires:

- tenant validation;
- valid artifact;
- readiness;
- approval;
- active target/provider;
- evidence capture.

## INV-015 — Execution Evidence

**Severity:** CRITICAL

Every real execution attempt MUST produce evidence where technically possible.

## INV-016 — Failure Evidence

**Severity:** MAJOR

Failed execution SHOULD produce safe failure evidence.

## INV-017 — Idempotent External Effects

**Severity:** MAJOR

Execution SHOULD be idempotent where duplicate attempts could create duplicate external effects.

## INV-018 — Explicit Replay

**Severity:** MAJOR

Replay MUST be explicit, validated, scoped, and auditable.

## INV-019 — Runtime Lineage

**Severity:** CRITICAL

Runtime lineage SHOULD preserve:

Context → Decision → Approval → Execution → Evidence → Outcome → Knowledge Candidate.

## INV-020 — Context Safety

**Severity:** CRITICAL

Context MUST NOT include secrets, unrelated tenant data, deprecated architecture as authority, or raw provider dumps.

## INV-021 — Context Determinism

**Severity:** MAJOR

Context construction SHOULD be deterministic where feasible.

## INV-022 — Decision Is Not Approval

**Severity:** CRITICAL

AI-generated decisions, recommendations, plans, or routes do not equal Human Approval.

## INV-023 — Orchestrator Authority Limit

**Severity:** CRITICAL

Orchestrator/COO Runtime may route, schedule, assign, coordinate, and escalate.

It MUST NOT define business truth or approve execution.

## INV-024 — Supervisor Execution Limit

**Severity:** CRITICAL

Supervisor Runtime may monitor, review, produce findings, and escalate.

It MUST NOT execute business actions directly.

## INV-025 — Programmer Agent Write Restriction

**Severity:** CRITICAL

Programmer Agent has no autonomous codebase write authority by default.

## INV-026 — Tool Allowlist

**Severity:** CRITICAL

Agent tool access MUST be allowlisted.

## INV-027 — No Unbounded Autonomy

**Severity:** CRITICAL

No agent may have unrestricted authority over execution, memory, credentials, tenant data, or codebase mutation.

## INV-028 — Contract Stability

**Severity:** MAJOR

Contract semantics MUST NOT be silently changed.

## INV-029 — Typed Lifecycle States

**Severity:** MAJOR

Core lifecycle states SHOULD use explicit finite enums or equivalent typed structures.

## INV-030 — Invalid Transition Rejection

**Severity:** CRITICAL

Invalid runtime transitions MUST be rejected explicitly.

## INV-031 — No Silent State Repair

**Severity:** MAJOR

The system MUST NOT silently repair illegal runtime transitions in ways that hide defects.

## INV-032 — Secrets Boundary

**Severity:** CRITICAL

Secrets MUST NOT leak into prompts, logs, errors, evidence, docs, contracts, or LLM payloads.

## INV-033 — Provider Boundary

**Severity:** MAJOR

External provider behavior MUST be isolated behind adapters.

## INV-034 — Provider Error Normalization

**Severity:** MAJOR

Provider failures SHOULD be normalized into safe domain errors.

## INV-035 — Safe Logging

**Severity:** CRITICAL

Logs MUST NOT contain credentials, secrets, unrelated tenant data, or raw provider dumps.

## INV-036 — Evidence Safety

**Severity:** CRITICAL

Evidence MUST NOT contain secrets or unrelated tenant data.

## INV-037 — Outcome Derivation

**Severity:** MAJOR

Outcome MUST be derived from evidence and MUST NOT replace evidence.

## INV-038 — Knowledge Promotion

**Severity:** CRITICAL

Promoted knowledge requires evidence, outcome linkage, validation, scope decision, policy check, and audit record.

## INV-039 — Global Knowledge Safety

**Severity:** CRITICAL

Global knowledge MUST NOT contain tenant-private information.

## INV-040 — Domain Boundary

**Severity:** MAJOR

Domains MUST NOT directly mutate another domain's internal state.

## INV-041 — Cross-Domain Contracts

**Severity:** MAJOR

Cross-domain interaction MUST occur through contracts, events, or orchestrated workflows.

## INV-042 — Future Domain Compatibility

**Severity:** MAJOR

New domains MUST be addable without global rewrite.

## INV-043 — Router Thinness

**Severity:** MAJOR

API routers MUST NOT contain business policy.

## INV-044 — Service Authority

**Severity:** MAJOR

Services own business rules, ownership checks, state transitions, and orchestration.

## INV-045 — Repository Purity

**Severity:** MAJOR

Repositories own persistence only and MUST NOT contain business policy.

## INV-046 — Adapter Isolation

**Severity:** MAJOR

Adapters isolate providers and infrastructure.

## INV-047 — Test Protection

**Severity:** CRITICAL

Critical invariants MUST be protected by tests before production release.

## INV-048 — Audit Events

**Severity:** MAJOR

Important state transitions SHOULD generate audit events.

## INV-049 — AI Context Loading

**Severity:** MAJOR

AI coding agents MUST load relevant Source of Truth documents before implementation.

## INV-050 — AI No Guessing

**Severity:** MAJOR

If architecture is missing or contradictory, AI MUST ask or propose ADR/RFC instead of guessing.

## INV-051 — No Chat Authority

**Severity:** CRITICAL

Chat history is not Source of Truth.

## INV-052 — Frozen Document Protection

**Severity:** CRITICAL

FROZEN documents MUST NOT be changed semantically without formal amendment.

## INV-053 — ADR for Architecture Change

**Severity:** MAJOR

Material architecture changes SHOULD be recorded in ADR.

## INV-054 — RFC for Proposed Change

**Severity:** MAJOR

Large proposed changes SHOULD be described in RFC before implementation.

## INV-055 — Cost Observability

**Severity:** MINOR

LLM and provider costs SHOULD be tracked where external providers are used.

## INV-056 — No Sleep-Based Runtime Default

**Severity:** MAJOR

Sleep-based waiting MUST NOT be default production runtime architecture.

## INV-057 — Execution Target Active

**Severity:** CRITICAL

Real execution MUST NOT target inactive, revoked, unauthorized, or unknown provider/channel.

## INV-058 — Approval Expiry

**Severity:** MAJOR

Approval SHOULD expire when action, artifact, target, tenant, or time window no longer matches.

## INV-059 — Context Snapshot

**Severity:** MAJOR

Material runtime operations SHOULD preserve context snapshot or reference.

## INV-060 — Architecture Traceability

**Severity:** MAJOR

Material implementation SHOULD be traceable to architecture, contract, ADR/RFC, or invariant.

---

# 4. Invariant Test Policy

Each CRITICAL invariant MUST have at least one test or documented enforcement mechanism before production release.

Each MAJOR invariant SHOULD have automated tests or review gates.

Invariant tests SHOULD cover:

- happy path;
- invalid transition;
- tenant boundary;
- approval boundary;
- execution blocking;
- safe errors;
- evidence capture;
- knowledge promotion boundary.

---

# 5. Runtime Invariant Audit Report

Status: PASSED.

This document is consistent with `PROJECT_CONSTITUTION.md`.

No invariant contradicts Human Approval, Tenant Isolation, Knowledge Candidate boundary, Orchestrator authority, or legacy migration policy.

This document is FROZEN v1.0.0.
