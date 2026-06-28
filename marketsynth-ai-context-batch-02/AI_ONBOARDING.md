# AI Onboarding

Status: ACTIVE

## What is Marketsynth

Marketsynth is a governed AI runtime for marketing operations, automation and future specialist domains.

It is not a simple chatbot, not a loose prompt chain and not a linear Make/n8n scenario.

## Mandatory Reading Before Coding

1. `AI_MANIFEST.md`
2. `docs/constitution/PROJECT_CONSTITUTION.md`
3. `docs/constitution/RUNTIME_INVARIANTS.md`
4. `docs/architecture/ARCHITECTURE_CORE.md`
5. `docs/implementation/AI_IMPLEMENTATION_RULES.md`
6. `DECISION_REGISTRY.md`
7. `CURRENT_PHASE.md`
8. Relevant documents from `DOCUMENT_INDEX.md`

## Non-Negotiables

- Architecture is Source of Truth.
- Chat history is not Source of Truth.
- Human Approval is mandatory before real execution.
- Readiness is not approval.
- Tenant isolation is mandatory.
- Knowledge Candidate never crosses tenant boundary.
- COO Runtime routes, schedules and assigns; it does not decide business truth.
- Programmer Agent has no autonomous codebase write authority by default.

## If Something Is Missing

Do not invent architecture.

Produce one of:

- clarification question;
- ADR proposal;
- RFC proposal;
- risk report.
