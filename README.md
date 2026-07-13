# Marketsynth AI Context Repository

> **Official Governance & Source of Truth for AI-assisted Development**

---

## Purpose

This repository contains the official architectural and governance knowledge for the **Marketsynth** platform.

Its purpose is to preserve project knowledge independently from chat history and provide a stable development context for AI coding assistants such as:

* Cursor
* ChatGPT
* Claude Code
* Codex
* Gemini CLI
* future AI development agents

This repository **does not contain application code**.

Application code belongs in the main Marketsynth repository.

---

# Repository Philosophy

The project follows one fundamental rule:

> **Architecture is the Source of Truth.**

Not chat history.

Not temporary prompts.

Not generated code.

Not assumptions.

Every architectural decision must eventually be represented inside this repository.

---

# Repository Structure

```text
/
  README.md
  PROJECT_CONSTITUTION.md
  PROJECT_INDEX.md

  docs/
    architecture/
    runtime/
    domain/
    contracts/
    engineering/
    governance/
    knowledge/
    security/
    context/
    memory/
    events/
    observability/
    errors/
    integrations/
    data/
    api/
    testing/
    quality/
    operations/
    migration/

  archive/
    imported-packs/   # historical uploaded packs (not deleted)
```

Canonical FROZEN documents live under `docs/` and at the repository root.

Historical package uploads (e.g. `marketsynth-runtime-pack/`, `marketsynth_core_*_v1_0/`) are preserved under `archive/imported-packs/`.

---

# Entry Point for AI

Every AI agent working on Marketsynth should begin here:

1. `PROJECT_CONSTITUTION.md`
2. `PROJECT_INDEX.md`
3. `docs/architecture/ARCHITECTURE_CORE.md`
4. `docs/runtime/RUNTIME_INVARIANTS.md`
5. `docs/runtime/RUNTIME_MODEL.md`
6. `docs/domain/DOMAIN_MODEL.md`
7. `docs/engineering/AI_DEVELOPMENT_RULES.md`

Full reading order and loading profiles: see `PROJECT_INDEX.md`.

Only after reading these documents may an AI modify or generate implementation.

---

# Document Status

Each document must contain one of the following statuses.

## FROZEN

Foundational document.

May only change after a formal architectural review.

Examples:

* Constitution
* Runtime Invariants

---

## ACTIVE

Current authoritative version.

May evolve while preserving constitutional compatibility.

---

## DRAFT

Work in progress.

Cannot be treated as implementation authority.

---

## SUPERSEDED

Replaced by a newer document.

Kept for historical reference.

---

## DEPRECATED

No longer relevant.

Stored only for historical purposes.

---

# Engineering Principles

Marketsynth follows several mandatory engineering principles.

* Architecture first
* Explicit contracts
* Runtime auditability
* Human Approval before real execution
* Tenant isolation
* Evidence-driven decisions
* Small, reviewable implementation changes
* Backward-compatible architectural evolution

---

# AI Development Rules

AI agents must never:

* bypass Human Approval;
* violate Runtime Invariants;
* ignore Constitution;
* infer architecture from code alone;
* cross tenant boundaries;
* silently change architectural meaning;
* treat chat conversations as project truth.

---

# Weekly Governance Audit

Repository maintenance is performed continuously.

Recommended audit frequency:

* once per week;
* before every implementation milestone;
* before every major architectural change.

Audit should verify:

* document consistency;
* obsolete decisions;
* broken references;
* architecture/code divergence;
* roadmap relevance;
* runtime invariants.

---

# Long-Term Vision

This repository is intended to become the permanent knowledge base for the Marketsynth ecosystem.

Future goals include:

* automatic AI context generation;
* context routing for different AI systems;
* architecture indexing;
* decision lineage;
* implementation traceability;
* governance automation.

---

# Relationship Between Repositories

```
marketsynth-ai-context
        │
        │  Source of Truth
        ▼
Marketsynth Core Repository
        │
        ▼
Cursor / ChatGPT / Claude Code
        │
        ▼
Implementation
```

Knowledge always flows from this repository into implementation.

Implementation must never redefine the architecture.

---

# Project Motto

> **Stable architecture. Controlled evolution. Auditable intelligence.**
