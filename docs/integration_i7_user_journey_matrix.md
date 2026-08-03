# Integration I7 — User journey matrix

| Stage | Route | Source of Truth | Persisted | Mock/Derived | Next Gate | Current Gap |
|-------|-------|-----------------|-----------|--------------|-----------|-------------|
| Landing / home | `/` | Brand / frozen home | n/a | static | Workspace | Product landing vs internal dashboard coexistence |
| Workspace | `/workspace` | Project (backend) | Projects | Runtime Monitor derived; mock widgets in mock/hybrid | Create / open project | N+1 campaign fetches |
| Intake wizard | `/workspace/projects/new…` | Intake Draft (local) | localStorage | mock demo drafts | Review → sync Project | Full brief fields not on Project |
| Backend Project create | review CTA | Project | backend | none in backend/hybrid on success | Investigation | Duplicate prevention via I2 fingerprint |
| Investigation | `.../investigation` | Derived + local | local investigation | stages/artifacts projected | Verdict readiness | Source/Evidence domain |
| Verdict preview | `.../verdict` | Business Verdict (local) | localStorage | deterministic_local / mock | Strategy eligibility | Durable Verdict |
| Strategy preview | `.../strategy` | MarketingStrategy (local) | localStorage | labelled local | Implementation eligibility | Durable Strategy; MP ops panel only |
| Pivot | `.../pivot` | local Verdict (NO_GO) | local | ensureVerdict only mock/hybrid | Rework / investigation | Backend: empty unless local residual |
| Implementation Plan | `.../implementation` | ImplementationPlan (local) | localStorage | hybrid + MP panel | Handoff preview | Write conversion blocked |
| MarketingPlan relation | Impl handoff panel | MarketingPlan (backend) | backend | related plans read-only | Future draft API | No handoff create API |
| Approval boundary | documented | per category | mixed | Alpha local reviews | Execution boundary | Unified ApprovalRequest absent |
| Execution boundary | docs + gated APIs | execution services | backend | A7 paused local | V2.2 Verified Execution | Alpha must not call providers |

## Prohibited side effects on Alpha page load

No Campaign create · no Agent Run · no provider · no publication · no budget change · no MarketingPlan approve · no execution approval create.
