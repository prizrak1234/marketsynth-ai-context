# AI Implementation Rules

Status: ACTIVE

## Priority Order

If documents, code and chat disagree, use this order:

1. Project Constitution
2. Runtime Invariants
3. Architecture Core
4. Accepted ADR
5. Accepted RFC
6. Contracts
7. Current implementation
8. Chat history

## Mandatory Behavior

Before writing code:

1. Identify affected domain.
2. Read relevant route in `AI_MANIFEST.md`.
3. Check `DECISION_REGISTRY.md`.
4. Check contracts.
5. Preserve tenant isolation.
6. Preserve approval boundaries.
7. Add or update invariant tests.

## Forbidden

- bypass Human Approval;
- treat readiness as approval;
- create hidden global state;
- put business logic in routers;
- leak secrets into logs/errors/payloads;
- silently change DTO semantics;
- silently rename core concepts;
- create cross-tenant memory;
- persist global knowledge without validation;
- implement real execution without idempotency;
- use `sleep` as production architecture;
- change frozen documents through code.

## Required Shape

```text
API Router
  ↓
Service
  ↓
Repository
  ↓
Database / Provider Adapter
```

Routers handle transport. Services handle business rules. Repositories handle persistence. Adapters isolate providers.
