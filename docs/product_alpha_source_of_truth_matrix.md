# Product Alpha Source of Truth Matrix

**Companion to:** [`product_alpha_ai591_reconciliation_audit.md`](./product_alpha_ai591_reconciliation_audit.md)

This matrix states, for each Product Alpha local model and UI concept, what owns truth after integration.

---

## Classification legend

| Class | Meaning |
|---|---|
| `maps_existing` | Maps to one existing backend entity/API |
| `maps_multiple` | Maps across multiple existing entities |
| `additive_entity` | Needs new contracts.py → DB → API |
| `frontend_view` | Remains derived UI; no persistence |
| `discard_after_integration` | localStorage discarded once server write succeeds |

---

## A. Primary localStorage models (A1–A6)

| Product Alpha model | Storage key | Classification | Future Source of Truth | Notes |
|---|---|---|---|---|
| WorkspaceSnapshot (A1) | none (in-memory mock) | `frontend_view` | Composed from Project + Campaign Control Center + Supervisor | Never persist as own table |
| ProjectIntakeDraft (A2) | `marketsynth.product_alpha.intake_draft.v1` | `maps_multiple` → then `discard_after_integration` | `Project` + `CampaignBrief` (+ optional intake extension fields) | Closest existing: Brief Intake AI.206–215 |
| Mock projects list (A2) | `marketsynth.product_alpha.mock_projects.v1` | `discard_after_integration` | `GET /projects` (+ campaigns) | Demo IDs only for offline demos |
| InvestigationWorkspace (A3) | `...investigation.v1.{projectId}` | `additive_entity` (preferred) | New Investigation + Evidence records | Interim: skill/tool run projection = `maps_multiple` / incomplete |
| BusinessVerdict (A4) | `...verdict.v1.{projectId}` | `additive_entity` | New Verdict entity; type enum = existing `VerdictKind` | Do not store as Campaign.metadata blob long-term |
| MarketingStrategy (A5) | `...strategy.v1.{projectId}` | `additive_entity` (or packaged artifacts) | New Strategy entity **or** versioned specialist/skill package with strategy schema | Strategist specialist alone is insufficient SoT |
| ImplementationPlan (A6) | `...implementation_plan.v1.{projectId}` | `maps_multiple` | Planning artifact + explicit handoff to `MarketingPlan` / execution runs | Avoid dual engines |

*(Local A7 execution_package key is parked and not a SoT candidate until Arch V2.2.)*

---

## B. UI surfaces → SoT

| UI surface | SoT after integration | Notes |
|---|---|---|
| `/workspace` shell | Frontend layout | Brand/tokens stay frontend |
| Agency Runtime Monitor | **Campaign Control Center** (+ supervisor, specialist runs) | Adapter required; claimed AI.591 overlay **absent** |
| Active Projects | Projects API | Derived status labels only |
| Intake wizard | Project + Brief APIs | |
| Investigation | Additive Investigation API | |
| Verdict | Additive Verdict API (`VerdictKind`) | |
| Pivot | Verdict==NO_GO policy UI | May later link rework brief |
| Strategy | Additive Strategy API | |
| Implementation Plan | Planning API + MarketingPlan handoff | |
| Campaign cockpit (detail) | Existing Control Center API | Embedded or deep-linked from Workspace |

---

## C. Status & readiness ownership

| Alpha field | SoT | Class |
|---|---|---|
| Workspace `ProjectStatus` | Derived from artifacts (intake/verdict/strategy/campaign health) | `frontend_view` until explicit contract |
| Investigation stage/status | Investigation entity | `additive_entity` |
| Verdict readiness | Derived / Investigation completeness | `frontend_view` or fields on Investigation |
| Verdict type | Verdict.kind → `VerdictKind` | `additive_entity` + existing enum |
| Verdict lifecycle | Verdict.status | `additive_entity` |
| Strategy status | Strategy.status | `additive_entity` |
| Plan status | Plan.status | planning entity |
| Planning readiness | Derived from gates/conditions | `frontend_view` → later server |
| Campaign health / next_action | Campaign Control Center | `maps_existing` |
| Resource approvals | Existing `/approve` | `maps_existing` |
| `ExecutionLifecycleState` | V2.2+ execution | stub today; not Alpha mock |
| `MarketingExecutionMode` | Backend plan mode (`PLANNING`) | `maps_existing`; UI must not invent Autonomous |

---

## D. Roles ownership

| Concept | SoT | Rule |
|---|---|---|
| Executable marketing specialists | `MarketingSpecialistType` | Backend |
| Agent runtime types | `AgentType` | Backend |
| AgencyRole (CEO, Client Owner, …) | Frontend RACI / display alias | **Never** silent AgentType expansion |
| Tenant owner | `UserRole` / `owner_id` | Backend |

---

## E. Decision-like objects

| Object | SoT | Separate? |
|---|---|---|
| Business Verdict | Future Verdict entity | Yes |
| Resource approval | Existing approve endpoints | Yes |
| CC next_action | Control Center | Derived recommendation — not Decision |
| Supervisor finding | Supervisor report | Yes (quality) |
| Project Decision Registry | **Absent** | Do not invent in Alpha UI as if stored |
| Strategy/Plan local approve | Preview until ApprovalRequest | Temporary `frontend_view` |

---

## F. Duplicate-implementation watchlist

Must not become parallel SoT:

1. Agency Runtime Monitor state independent of Control Center  
2. Alpha ProjectStatus enum persisted without contract  
3. AgencyRole persisted as AgentType  
4. ImplementationPlan silently creating a second execution engine beside MarketingPlan  
5. Local approval replacing `/approve`  
6. A7 mock claiming Verified Execution  

---

## G. Claimed AI.586–591 vs this tree

| Claimed phase | On this checkout | SoT implication |
|---|---|---|
| AI.586–587 Workforce | Absent | Do not treat Alpha roles as workforce SoT |
| AI.588 Project Workspace | Absent | Workspace UI → compose from Project+CC |
| AI.589 Decisions | Absent | Verdict ≠ Decision Registry |
| AI.590 Timeline | Absent at project layer | Use Campaign timeline; project timeline additive later |
| AI.591 CC workspace overlay | Absent | Use Campaign Control Center as real overlay today |

If those phases exist on another branch/machine, merge/reconcile **before** implementing additive Project Workspace fields — still without forking Campaign Control Center health/`next_action`.

---

## H. Marketsynth Subsystem Standard (project-wide)

Canonical architecture SoT for substantial capabilities:

| Document | Role |
|----------|------|
| [rchitecture/marketsynth_subsystem_standard.md](./architecture/marketsynth_subsystem_standard.md) | Lifecycle + operator + manifest + recipes |
| [rchitecture/adr_subsystem_standard.md](./architecture/adr_subsystem_standard.md) | Accepted ADR |
| [rchitecture/subsystem_compliance_matrix.md](./architecture/subsystem_compliance_matrix.md) | Gap audit (no mass refactor) |

**Rule:** evaluate new domains/skills/integrations/execution paths against the Subsystem Standard before implementation. Identity Generation (H2.8E) is the reference mapping; it does not replace Product Alpha entity SoT rows above.
