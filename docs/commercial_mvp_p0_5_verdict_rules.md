# Commercial MVP P0.5 — Verdict rules

## GO

- Investigation `under_review` or `completed`
- Readiness `ready_for_review`
- No unresolved critical missing/conflicting Evidence
- Supporting Evidence present
- No unresolved verdict-changing risk
- Confidence not `low` (convert/reject)

## CONDITIONAL_GO

- Explicit conditions required
- Supporting or condition_basis Evidence (or missing-critical gap basis)
- Conditions may remain open when approved (visible + mandatory)

## NO_GO

- Weakening/contradicting/risk-basis Evidence and/or critical risks
- Strategy blocked; pivot route allowed

## INSUFFICIENT_DATA

- Responsible GO/CONDITIONAL_GO/NO_GO impossible
- Strategy blocked; return to Investigation

## Deterministic builder

Explicit `build-draft` only. Origin `deterministic`. Lifecycle `draft`. No auto-approve. No Strategy/Execution.
