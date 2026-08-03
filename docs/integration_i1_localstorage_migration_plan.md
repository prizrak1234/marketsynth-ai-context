# Integration I1 — localStorage Migration Plan

**I1 does not delete keys.** Adapters remain version-safe.

| Key | Ownership | I1 behavior | Later |
|---|---|---|---|
| `marketsynth.product_alpha.intake_draft.v1` | draft / future backend | Alpha wizard only | I2 → Project+Brief; discard after sync |
| `marketsynth.product_alpha.mock_projects.v1` | mock | demos only; Workspace list uses API/mock snapshot | eventual removal |
| `...investigation.v1.{id}` | draft / additive | Alpha screens only | I3 entity |
| `...verdict.v1.{id}` | draft / additive | Alpha only | I4 |
| `...strategy.v1.{id}` | draft / additive | Alpha only | I5 |
| `...implementation_plan.v1.{id}` | draft / migration | Alpha only — no dual-write MarketingPlan | I6 handoff |
| `...execution_package.v1.{id}` | parked A7 | preserve; not SoT | after V2.2 path |
| `marketsynth.integration.mode.v1` | I1 config | mode override | keep |

### Conflict policy (backend / hybrid)

- Never overwrite backend objects with local mock facts.
- Never silently merge conflicting business facts.
- Local draft ≠ persisted backend object — keep labels explicit when both exist (I2+).
