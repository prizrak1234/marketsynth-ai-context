# Commercial MVP P1 — ImplementationPlan Decision

## Options

| Opt | Meaning |
|-----|---------|
| **A** | ImplementationPlan needs its **own backend domain** (durable SoT) |
| B | Remain frontend view over Strategy + MarketingPlan |
| C | Composed project-delivery **read model** only (no writes) |

## Evidence from A6 / I6 / I7

- A6/I6 model: workstreams, tasks, gates, role mapping, acceptance criteria, dependencies, budget policy modes — richer than MarketingPlan specialist-task spine.
- Adapter (`implementation-plan-adapter.ts`): **Option B read-only handoff** today; write blocked (`writeBlockedNoCreateApi`); MarketingPlan is ops context only.
- SoT: localStorage key `marketsynth.product_alpha.implementation_plan.v1.{projectId}` — not durable, not version-governed like P0 domains.
- MarketingPlan already exists as **ops** spine — equating them collapses Strategy→execution risk.

## Decision

**Choose A — durable ImplementationPlan Domain (Commercial MVP P1.1).**

Rationale:

1. Delivery plan is a first-class commercial artifact between approved Strategy and ops MarketingPlan.
2. Safe handoff requires exact version pins, immutability on approve, and owner/project isolation — same pattern as Verdict/Strategy.
3. Option B alone cannot prevent silent local drift or contested SoT during handoff.
4. Option C is useful as a **read composition later**, but still needs a durable write SoT underneath for approval and handoff.

## Explicit non-goals for this review

Do **not** implement ImplementationPlan in P1 Architecture Review.

## Prerequisite for P1.1

- Approved MarketingStrategy on eligible Verdict  
- Contracts in `contracts.py` first  
- No auto MarketingPlan create on Impl approve  
- A7 / AI.592 / V2.2 remain paused  
