# ADR_RFC_GOVERNANCE.md

**Project:** Marketsynth  
**Document Type:** Decision Governance Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from `PROJECT_CONSTITUTION.md`

---

# 1. Purpose

This document defines when to use ADR and RFC in Marketsynth.

ADR records accepted architectural decisions.

RFC proposes significant changes before implementation.

---

# 2. ADR Definition

ADR means Architecture Decision Record.

ADR is used when a decision:

- changes architecture;
- freezes a tradeoff;
- affects runtime invariants;
- changes domain boundary;
- changes contract semantics;
- affects approval/execution/tenant/knowledge rules;
- changes migration strategy.

---

# 3. RFC Definition

RFC means Request for Comments.

RFC is used for proposals that require review before acceptance.

RFC SHOULD precede ADR when the decision is large, risky, ambiguous, or cross-domain.

---

# 4. ADR Template

```markdown
# ADR-XXX — Title

Status: Proposed / Accepted / Superseded / Rejected
Date:
Scope:
Related Documents:

## Context
## Decision
## Consequences
## Alternatives Considered
## Risks
## Migration Impact
## Constitutional Compatibility
## Audit Result
```

---

# 5. RFC Template

```markdown
# RFC-XXX — Title

Status: Draft / Review / Accepted / Rejected
Author:
Scope:
Related Documents:

## Problem
## Proposal
## Non-Goals
## Design
## Compatibility
## Risks
## Open Questions
## Review Checklist
```

---

# 6. Required ADR Cases

ADR is REQUIRED for:

- semantic changes to FROZEN documents;
- breaking contract changes;
- new execution authority;
- new cross-domain dependency;
- new tenant-boundary exception;
- new global knowledge promotion rule;
- major legacy migration strategy;
- new high-risk domain.

---

# 7. Required RFC Cases

RFC is REQUIRED for:

- new domain;
- new provider class;
- new execution channel;
- major memory model change;
- new AI agent class with tools;
- new approval delegation model;
- new knowledge promotion pipeline.

---

# 8. Prohibited Decision Practices

The project MUST NOT:

- make architectural decisions only in chat;
- accept implementation as ADR substitute;
- use PR comments as sole decision record;
- change contracts without decision record;
- allow AI to invent decisions.

---

# 9. Audit Status

PASSED.

This document is FROZEN v1.0.0.
