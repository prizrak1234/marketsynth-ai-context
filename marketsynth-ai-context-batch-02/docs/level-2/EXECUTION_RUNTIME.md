# Execution Runtime

Status: ACTIVE

## Required Flow

```text
Candidate → Quality Gate → Readiness Gate → Human Approval → Execution → Evidence → Outcome → Knowledge Candidate
```

## Preconditions

Real execution requires:

- candidate exists;
- quality gate passed;
- readiness status is ready;
- no critical policy violations;
- approval exists;
- approval is valid;
- provider/channel is active;
- tenant ownership is valid.

## Prohibited

- direct provider mutation from router;
- execution without approval;
- execution based only on readiness;
- blind repeated publish;
- hidden external state mutation.
