# Engineering Knowledge

Status: ACTIVE

## Backend Principles

- typed DTOs;
- explicit enums;
- explicit state transitions;
- thin routers;
- service-layer business logic;
- repository-layer persistence;
- provider adapters;
- safe error handling;
- no secret leakage;
- idempotent external execution;
- invariant tests.

## Error Handling

Errors must be safe:

- no secrets;
- no raw credentials;
- no full provider dumps;
- deterministic domain error codes where possible.

## Testing

Minimum tests for affected logic:

- happy path;
- invalid state;
- ownership isolation;
- tenant isolation;
- approval required;
- execution blocked when not ready;
- provider failure normalization;
- no secret leakage.
