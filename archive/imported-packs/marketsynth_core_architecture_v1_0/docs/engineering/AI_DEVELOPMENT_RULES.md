# AI_DEVELOPMENT_RULES.md

**Project:** Marketsynth  
**Document Type:** AI Development Rules  
**Authority:** Derived from `PROJECT_CONSTITUTION.md`, `ARCHITECTURE_CORE.md`, `RUNTIME_INVARIANTS.md`  
**Status:** FROZEN  
**Version:** 1.0.0  

---

# 1. Purpose

This document defines how Cursor and other AI coding agents MUST work on Marketsynth.

AI agents are powerful implementation assistants.

They are not architectural authorities.

---

# 2. Mandatory Reading Order

Before implementation, AI agents MUST read:

1. `PROJECT_CONSTITUTION.md`
2. `ARCHITECTURE_CORE.md`
3. `RUNTIME_INVARIANTS.md`
4. relevant model document
5. relevant contract
6. relevant coding standard
7. current task/phase notes

---

# 3. Authority Order

If documents, code, and chat disagree:

1. Constitution wins.
2. Runtime Invariants win.
3. Architecture Core wins.
4. Accepted ADR/RFC wins.
5. Contracts win.
6. Tests guide implementation.
7. Current code is last.
8. Chat history is historical only.

---

# 4. Required Pre-Coding Checklist

AI MUST identify:

- affected domain;
- affected runtime objects;
- affected contracts;
- tenant boundary;
- approval boundary;
- evidence requirement;
- tests required;
- migration impact;
- whether ADR/RFC is needed.

---

# 5. Forbidden AI Behavior

AI MUST NOT:

- bypass Human Approval;
- treat readiness as approval;
- cross tenant boundaries;
- create cross-tenant memory;
- create cross-tenant Knowledge Candidate;
- leak secrets;
- mutate frozen documents;
- silently change contracts;
- put business logic in routers;
- put provider logic in services;
- treat legacy BotFazer v3 code as Source of Truth;
- invent missing architecture;
- remove tests to pass CI;
- hide invalid transitions.

---

# 6. Required Implementation Shape

Preferred shape:

```text
API Router
  ↓
Service
  ↓
Repository
  ↓
Provider Adapter
  ↓
Infrastructure
```

Routers are thin.

Services own business logic.

Repositories own persistence.

Adapters isolate external systems.

---

# 7. When Architecture Is Missing

AI MUST do one of:

- ask a clarification question;
- propose ADR;
- propose RFC;
- produce risk report;
- stop implementation.

AI MUST NOT guess.

---

# 8. Testing Requirements

For material changes, AI SHOULD add tests for:

- happy path;
- invalid state;
- tenant isolation;
- approval required;
- execution blocked when not ready;
- provider failure normalization;
- secret redaction;
- invariant preservation.

---

# 9. Legacy Code Handling

Legacy BotFazer v3 code may be referenced for implementation clues.

It MUST NOT override Marketsynth architecture.

Before adapting legacy code, AI SHOULD perform gap analysis:

```text
Constitution → Architecture → Invariants → Legacy Code → Migration Plan
```

---

# 10. Output Requirements

AI-generated work SHOULD include:

- files changed;
- reason for changes;
- architectural references;
- tests added;
- risks;
- remaining TODOs;
- migration notes.

---

# 11. AI Self-Audit

Before final answer, AI SHOULD verify:

- no approval bypass;
- no tenant leak;
- no secret leak;
- no cross-domain mutation;
- contracts preserved;
- tests updated;
- architecture respected.

---

# 12. Audit Report

Status: PASSED.

This document is compatible with Constitution, Architecture Core, Runtime Invariants, and Cursor workflows.

This document is FROZEN v1.0.0.
