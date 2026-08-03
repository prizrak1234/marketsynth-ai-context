# Integration I4 — Business Verdict domain (Option C)

## Definition

Business Verdict answers only:

> Should this business project proceed in its current form, under stated conditions and evidence?

Types: `GO` | `CONDITIONAL_GO` | `NO_GO` | `INSUFFICIENT_DATA`  
(`VerdictKind` in `contracts.py` reserved; FE uses `BusinessVerdictType`).

Does **not**: approve budget, execution, publication; assign agents; alter campaigns; replace strategy.

## Semantic chain

```
Investigation snapshot → Evidence assessment → Risks/assumptions
→ Verdict readiness → Business Verdict → Human review (local status)
→ Strategy eligibility (frontend guard)
```

## Source of Truth (I4)

| Mode | SoT |
|------|-----|
| mock | Product Alpha deterministic scenarios |
| hybrid | Local deterministic preview labelled «Локальный предварительный вердикт» |
| backend | Empty — unsupported capability (no mock fallback) |

Origins: `mock` | `deterministic_local` | `backend` | `derived` | `imported`  
Authority never claims `evidence_verified` while Evidence SoT absent.

## Future Option B (docs only)

Additive `BusinessVerdict` aggregate (versioned, project-scoped, draft→approved→superseded) with nullable investigation/evidence refs.  
API sketch: [integration_i4_verdict_api.md](integration_i4_verdict_api.md).  
**Not implemented in I4** — no migration.

## Versioning (local)

Existing `commitVerdictVersion` supersedes prior current; local history retained. Approved local status ≠ backend approval ≠ execution approval.
