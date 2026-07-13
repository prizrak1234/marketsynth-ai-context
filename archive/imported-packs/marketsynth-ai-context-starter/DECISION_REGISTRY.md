# Decision Registry

Status: ACTIVE

## Frozen Decisions

### D-001 — Marketsynth is the official product name

Previous working name BotFazer is deprecated for interface and official project naming.

### D-002 — Source of Truth is architecture, not chat

Chat discussions are historical input. Implementation authority belongs to this repository.

### D-003 — Human Approval is mandatory for real execution

Any action affecting external systems, publication, money, user accounts, credentials or irreversible state requires explicit approval.

### D-004 — Tenant boundary is non-negotiable

Knowledge Candidate, memory, runtime evidence and execution context must never cross tenant boundaries.

### D-005 — COO Runtime routes, schedules and assigns; it does not decide business truth

Terminology such as `decide` must not be used for COO Runtime authority where route/schedule/assign is intended.

### D-006 — Programmer Agent has no autonomous codebase write authority by default

Programmer domain may draft technical tasks and analysis. Code changes require explicit implementation phase and approval.

### D-007 — Architecture must support expansion to HR, Legal and future domains

Domain model must allow new specialist domains without global rewrite.
