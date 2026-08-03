# Architecture & Product Decisions (Index)

> **Rule:** Never delete history. New decisions get a file in [decisions/](decisions/).  
> **Format:** Date · Reason · Alternatives · Consequences · Status

---

## Quick index

| ID | Title | Date | Status | File |
|----|-------|------|--------|------|
| ADR-001 | Subsystem Standard | 2026 | Accepted | [decisions/adr-001-subsystem-standard.md](decisions/adr-001-subsystem-standard.md) |
| ADR-002 | Knowledge Governance | 2026 | Accepted | [decisions/adr-002-knowledge-governance.md](decisions/adr-002-knowledge-governance.md) |
| DEC-003 | CWF.1 Launch Pack boundary | 2026-07 | Active | [decisions/dec-003-cwf1-launch-pack-boundary.md](decisions/dec-003-cwf1-launch-pack-boundary.md) |
| DEC-004 | VIDEO track frozen | 2026-07-22 | Accepted | [decisions/dec-004-video-frozen.md](decisions/dec-004-video-frozen.md) |
| DEC-005 | DIS deferred until CGP.10C | 2026 | Accepted w/ condition | [decisions/dec-005-dis-ui-decoupling.md](decisions/dec-005-dis-ui-decoupling.md) |
| DEC-006 | No LangGraph marketing default | 2026 | Accepted | [decisions/dec-006-no-langgraph-default.md](decisions/dec-006-no-langgraph-default.md) |
| DEC-007 | KB-WPL-01 closed; KB-WPL-02 gated | 2026-07-24 | Accepted | [decisions/dec-007-kb-wpl-01-closed.md](decisions/dec-007-kb-wpl-01-closed.md) |
| DEC-008 | PRODUCT-01.2 rejected | 2026-07-24 | Rejected w/ findings | [decisions/dec-008-product-01-2-rejected.md](decisions/dec-008-product-01-2-rejected.md) |
| DEC-009 | Explicit execution only | 2026 | Accepted | [decisions/dec-009-explicit-execution-only.md](decisions/dec-009-explicit-execution-only.md) |
| DEC-010 | BotFazer name retained in code | 2026-07 | Active | [decisions/dec-010-botfazer-legacy-label.md](decisions/dec-010-botfazer-legacy-label.md) |

---

## Decision template (for new entries)

Create `decisions/dec-NNN-short-title.md`:

```markdown
# DEC-NNN: Title

**Date:** YYYY-MM-DD
**Status:** proposed | accepted | rejected | superseded
**Supersedes:** (optional)

## Context

## Decision

## Alternatives considered

## Consequences

## Verification
```

Also add a row to this index.

---

## Full ADR corpus in docs/

- [docs/architecture/adr_subsystem_standard.md](../docs/architecture/adr_subsystem_standard.md)
- [docs/architecture/adr_knowledge_governance.md](../docs/architecture/adr_knowledge_governance.md)
- [docs/identity_architecture_decision_log.md](../docs/identity_architecture_decision_log.md)
- [docs/rfc/](../docs/rfc/) — skill and KB RFCs
