# AI Manifest

Status: ACTIVE  
Project: Marketsynth  
Purpose: Mandatory navigation file for AI agents.

## Prime Rule

No AI agent may modify implementation logic before reading the required context for the affected area.

## Required Global Context

Always read:

1. `docs/constitution/PROJECT_CONSTITUTION.md`
2. `docs/constitution/RUNTIME_INVARIANTS.md`
3. `docs/architecture/ARCHITECTURE_CORE.md`
4. `DECISION_REGISTRY.md`
5. `CURRENT_PHASE.md`

## Context Routing

### If working on runtime execution

Read:

- `docs/architecture/ARCHITECTURE_CORE.md`
- `docs/constitution/RUNTIME_INVARIANTS.md`
- `docs/level-2/runtime-execution.md`
- `docs/level-2/approval-boundary.md`

### If working on agents

Read:

- `docs/level-2/agent-runtime.md`
- `docs/level-2/domain-boundaries.md`
- `docs/constitution/RUNTIME_INVARIANTS.md`

### If working on knowledge/memory

Read:

- `docs/level-2/knowledge-boundary.md`
- `docs/constitution/RUNTIME_INVARIANTS.md`
- `docs/architecture/ARCHITECTURE_CORE.md`

### If working on Cursor rules

Read:

- `.cursor/rules/00_project_constitution.mdc`
- `.cursor/rules/01_architecture_guardrails.mdc`
- `.cursor/rules/02_runtime_invariants.mdc`
- `.cursor/rules/03_coding_rules.mdc`

## Forbidden Behavior

AI agents must not:

- infer missing architecture from code alone;
- override frozen decisions silently;
- implement real execution without human approval gates;
- cross tenant boundaries for knowledge or memory;
- treat draft RFCs as implementation authority;
- rename core concepts without ADR;
- use chat history as Source of Truth.
