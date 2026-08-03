# Integration I4 — Decision Semantics Audit

**Decision: Option C** — Business Verdict Source of Truth remains **labelled Product Alpha local / deterministic_local** until durable Evidence SoT + additive BusinessVerdict domain are approved.

**Not chosen:** Option A (no exact entity). **Deferred:** Option B migration (would risk fake evidence-verified authority without Evidence SoT).

## Baseline

- Branch: `master`
- Tip: `0524316`
- I1–I3 + verdict builder selfchecks green

## Inventory summary

| Object | Persistence | ↔ Business Verdict |
|--------|-------------|-------------------|
| `VerdictKind` stub | enum only | vocabulary only |
| Product Alpha `BusinessVerdict` | localStorage | **SoT in I4 (labelled)** |
| CampaignSupervisorFinding | derived | input signal |
| CC `next_action` | derived | operational recommendation |
| Resource `/approve` | DB status | artifact/human approval — **not** viability |
| ExecutionApproval | gated flags | execution governance — **not** verdict |
| Verdict readiness (FE) | derived | readiness ≠ verdict |
| ProjectDecision registry | absent | — |

## Sufficiency

No persisted GO/CONDITIONAL_GO/NO_GO/INSUFFICIENT_DATA record exists beyond FE.  
Evidence graph absent (I3). Therefore **do not** claim backend-approved evidence-verified verdicts.

## Forbidden collapses

SupervisorFinding ↛ BusinessVerdict  
ControlCenter.next_action ↛ Verdict  
ready_for_review ↛ GO  
execution readiness ↛ business viability  
verdict review ↛ execution approval

Full matrix: code `DECISION_SEMANTICS_MATRIX` + [integration_i4_business_verdict_domain.md](integration_i4_business_verdict_domain.md).
