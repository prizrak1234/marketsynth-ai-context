# AI.592 — Entry criteria (`execution_mode`)

Proposed: `execution_mode = done_for_you | copilot`

## Classification (I7 decision)

| Question | Answer |
|----------|--------|
| Semantic owner | **Execution / approval policy** (not mere UI chrome) |
| Persisted scope | Prefer **project policy** (or campaign policy) once Verified Execution exists — not localStorage-only |
| Interaction with approvals | Mode may change **defaults and UX prompts**, never skip required approval categories |
| Interaction with V2.2 | Mode selects assistance level **within** Intent→Approval→Provider→Verification |
| Default | Prefer **copilot** until Verified Execution + approvals proven |
| Safety | `done_for_you` must not imply auto provider calls without execution approval |
| Ordering | **AI.592 follows execution semantics (V2.2)**, does not define them |

## Status

**Do not implement in I7.**  
Entry: after V2.2 Intent/Approval/Provider boundaries are defined, or simultaneously only if scoped as preference flag with no side effects.

## Anti-pattern

Treating `execution_mode` as a substitute for MarketingPlan approval, execution approval, or Evidence verification.
