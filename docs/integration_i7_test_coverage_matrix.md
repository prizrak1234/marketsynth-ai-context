# Integration I7 — Test coverage matrix

| Capability | Unit / Selfcheck | Integration / API | UI | Missing |
|------------|------------------|-------------------|----|---------|
| Project creation / ownership | I2 project-write | Project API tests | Intake review | fuller brief fields |
| Duplicate prevention | I2 fingerprint | I2 | review CTA | — |
| Workspace backend mode | I1 integration | — | Workspace | exhaustive browser matrix |
| Investigation projection | I3 investigation | — | Investigation | Source/Evidence API later |
| Evidence origin | I3 qualitySignalsAreNotEvidence | — | labels | durable Evidence tests |
| Verdict semantics | I4 verdict | — | Verdict | BusinessVerdict API |
| Strategy eligibility | I5 strategy-plan | — | Strategy | Strategy API |
| MarketingPlan mapping | I5 | AI.28/29 MarketingPlan | ops panel | handoff write |
| Implementation handoff | I6 implementation-handoff | — | Impl panel | draft create API |
| Approval separation | I6/I7 approval-boundary | publishing/asset approve tests | labels | ApprovalRequest suite |
| Execution boundary | I7 pageLoadSideEffects | execution flags / runs | A7 paused | V2.2 |
| Routing guards | strategy/impl routing modules | — | client redirects | Next middleware (none) |
| Integration modes | adapter mode branches | — | headers/notices | automated mode matrix |
| No silent fallback | I7 patches + mode comments | — | backend empty states | systemic lint rule |

Selfchecks: `web/src/lib/integration/*.selfcheck.ts`, Alpha builders under `verdict|strategy|implementation-plan|…`.

New in I7: `integration-i7.selfcheck.ts`.
