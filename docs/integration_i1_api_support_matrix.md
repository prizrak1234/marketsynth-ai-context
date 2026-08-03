# Integration I1 — API Support Matrix

| Product capability | Existing API | Read | Write | Adapter in I1 | Missing |
|---|---|---|---|---|---|
| Projects | `GET/POST /projects`, `GET /projects/{id}` | yes | yes (unused I1) | `project-adapter` + `load-workspace` | pipeline status |
| Campaigns (BOS) | `GET/POST .../business-campaigns` | yes | unused I1 | via summaries | — |
| Control Center | `GET .../business-campaigns/{id}/control-center` | yes | n/a | `control-center-adapter` | AI.591 overlay |
| CC list view | `GET .../search?view=control` | yes | n/a | enrich project cards | — |
| Agent Runs | `/agent-runs`, specialist outputs | yes (elsewhere) | — | not wired to Monitor I1 | Monitor specialist board as runs |
| Approvals | resource `/approve` endpoints | yes | yes | not in I1 UI | ApprovalRequest entity |
| Execution state | plan execution runs + Action Center | yes | yes | metrics/health only | full execution package |
| MarketingPlan | marketing-plans APIs | yes | yes | not wired | semantic ↔ ImplementationPlan |
| Intake | Campaign Brief APIs | yes | yes | **future I2** | Alpha draft mapping |
| Investigation | — | no | no | mock Alpha only | additive entity |
| Verdict | `VerdictKind` stub only | no API | no | mock Alpha only | additive entity |
| Strategy | specialist/skill only | partial | — | mock Alpha only | additive entity |
| Implementation plan | MarketingPlan (partial) | partial | — | mock Alpha only | handoff contract |
| Decisions ledger | — | no | no | gap | project decisions |
| Timeline | `CampaignTimelineEvent[]` on CC | yes | n/a | not yet on Workspace summary | project-level timeline |
| Workforce | — | no | no | gap listed | AI.591 absent |

**I1 rule:** do not add backend routes; adapt existing ones.
