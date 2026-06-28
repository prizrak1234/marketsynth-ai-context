# PROJECT_INDEX.md

**Project:** Marketsynth  
**Document Type:** Source of Truth Navigation Index  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from `PROJECT_CONSTITUTION.md`

---

# 1. Purpose

`PROJECT_INDEX.md` is the first document AI agents SHOULD read after opening the repository.

It defines:

- which documents exist;
- their authority;
- their reading order;
- what each document describes;
- what each document does not describe;
- which documents Cursor must load before coding.

This file does not override the Constitution.

---

# 2. Canonical Reading Order

```text
PROJECT_CONSTITUTION.md
PROJECT_INDEX.md
docs/architecture/ARCHITECTURE_CORE.md
docs/runtime/RUNTIME_INVARIANTS.md
docs/runtime/RUNTIME_MODEL.md
docs/domain/DOMAIN_MODEL.md
docs/engineering/AI_DEVELOPMENT_RULES.md
docs/contracts/CONTRACT_GUIDELINES.md
docs/governance/DOCUMENT_GOVERNANCE.md
docs/governance/ADR_RFC_GOVERNANCE.md
docs/runtime/APPROVAL_MODEL.md
docs/runtime/EXECUTION_MODEL.md
docs/knowledge/KNOWLEDGE_MODEL.md
docs/security/SECURITY_MODEL.md
docs/migration/BOTFAZER_TO_MARKETSYNTH_MIGRATION.md
```

---

# 3. Authority Matrix

| Document | Status | Authority | Purpose |
|---|---:|---:|---|
| `PROJECT_CONSTITUTION.md` | FROZEN | Highest | Project law |
| `ARCHITECTURE_CORE.md` | FROZEN | Foundational | System structure |
| `RUNTIME_INVARIANTS.md` | FROZEN | Foundational | Runtime laws |
| `RUNTIME_MODEL.md` | FROZEN | Foundational | Runtime lifecycle |
| `DOMAIN_MODEL.md` | FROZEN | Foundational | Domain boundaries |
| `AI_DEVELOPMENT_RULES.md` | FROZEN | Foundational | Cursor/AI coding rules |
| `CONTRACT_GUIDELINES.md` | FROZEN | Foundational | Contract design |
| `DOCUMENT_GOVERNANCE.md` | FROZEN | Governance | Document lifecycle |
| `ADR_RFC_GOVERNANCE.md` | FROZEN | Governance | Decision process |
| `APPROVAL_MODEL.md` | FROZEN | Runtime | Human approval |
| `EXECUTION_MODEL.md` | FROZEN | Runtime | Real execution |
| `KNOWLEDGE_MODEL.md` | FROZEN | Knowledge | Knowledge promotion |
| `SECURITY_MODEL.md` | FROZEN | Security | Secrets and isolation |
| `BOTFAZER_TO_MARKETSYNTH_MIGRATION.md` | FROZEN | Migration | Legacy transition |

---

# 4. Cursor Loading Profiles

## 4.1 Architecture Work

Cursor MUST load:

1. `PROJECT_CONSTITUTION.md`
2. `PROJECT_INDEX.md`
3. `ARCHITECTURE_CORE.md`
4. `RUNTIME_INVARIANTS.md`
5. relevant domain/runtime document

## 4.2 Runtime Code Work

Cursor MUST load:

1. `PROJECT_CONSTITUTION.md`
2. `RUNTIME_INVARIANTS.md`
3. `RUNTIME_MODEL.md`
4. `APPROVAL_MODEL.md`
5. `EXECUTION_MODEL.md`
6. `CONTRACT_GUIDELINES.md`

## 4.3 Agent / AI Work

Cursor MUST load:

1. `PROJECT_CONSTITUTION.md`
2. `AI_DEVELOPMENT_RULES.md`
3. `RUNTIME_INVARIANTS.md`
4. `DOMAIN_MODEL.md`
5. relevant contract

## 4.4 Knowledge Work

Cursor MUST load:

1. `PROJECT_CONSTITUTION.md`
2. `KNOWLEDGE_MODEL.md`
3. `RUNTIME_MODEL.md`
4. `SECURITY_MODEL.md`
5. `CONTRACT_GUIDELINES.md`

---

# 5. Repository Rule

The repository may temporarily contain uploaded package folders.

Canonical documents SHOULD eventually be normalized into:

```text
/
  PROJECT_CONSTITUTION.md
  PROJECT_INDEX.md
  README.md
  docs/
    architecture/
    runtime/
    domain/
    engineering/
    contracts/
    governance/
    knowledge/
    security/
    migration/
    adr/
    rfc/
```

---

# 6. Audit Status

This index is suitable for AI navigation and external audit.

Status: FROZEN v1.0.0.
