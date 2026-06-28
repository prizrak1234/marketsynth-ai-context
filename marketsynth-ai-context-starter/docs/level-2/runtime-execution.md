# Runtime Execution

Status: ACTIVE

## Rule

No real execution may happen without approved readiness and human approval.

## Pipeline

Ready Candidate → Quality Gate → Readiness Gate → Approval Request → Human Decision → Execution → Evidence → Outcome.

## Failure Behavior

If gate fails:

- return safe error;
- do not execute;
- persist reason;
- preserve audit trail.

## Prohibited

- sleep-based execution as architectural default;
- blind retries without policy;
- execution without idempotency;
- hidden provider-side state mutation.
