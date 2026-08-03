# Product Alpha ↔ Existing Runtime Reconciliation Audit

**Status:** audit only — no production code changed  
**Scope:** Product Alpha A1–A6 vs actual backend on this checkout  
**Stop line:** Product Alpha A7 not started as integration work; AI.592 not started  
**Date:** 2026-07-13

---

## 0. Premise correction (critical)

The audit brief assumed **AI.591** already shipped a read-only Control Center **workspace overlay** with:

`workforce`, `current_stage`, `current_owner_role`, `next_recommended_step`, `decisions_summary`, `latest_decisions`, `timeline_summary`, `latest_timeline_events`.

**On this tree that implementation is absent.**

Evidence:

| Claimed artifact | On-disk result |
|---|---|
| `project_workspace_service` / engine | Missing |
| `agency_workforce` routes/registry | Missing |
| `project_decision` / `project_timeline` | Missing |
| Fields `workforce`, `current_stage`, `current_owner_role`, `next_recommended_step`, `decisions_summary`, `latest_*` | Zero matches under `app/` |
| Docs `phase_ai_591_*` / tests `test_phase_ai_591_*` | Missing |
| `AGENTS.md` (repo) | Documents frozen conveyor through **AI.265** Campaign Workflow + V2.1 Architecture contracts — **not** AI.586–595 |

**What does exist and is mature:**

- **Campaign Control Center (AI.156–AI.165)** — real aggregate API
- Campaign Action Center, Supervisor, Business Campaigns, Brief Intake, Skills, Workflows
- Marketing department specialists (`MarketingSpecialistType`, 14 roles)
- Marketing plan + execution-run spine (planning / specialist execute)
- **Architecture V2.1 stubs** in `contracts.py`: `VerdictKind`, `ApprovalState`, `ExecutionLifecycleState`, compatibility map

**Audit stance:** treat Campaign Control Center + campaign runtime as the **nearest existing Source of Truth**, and treat claimed AI.591 overlay as **documented intent / gap**, not present code. Product Alpha A1–A6 must continue this system via adapters — not by inventing a second Runtime.

---

## 1. Baseline

### `git status --short` (abbreviated)

```
 M web/src/components/brand/marketsynth-home-hero.tsx
?? docs/product_alpha_phase_a1_workspace.md
?? docs/product_alpha_phase_a2_project_intake.md
?? docs/product_alpha_phase_a3_investigation_workspace.md
?? docs/product_alpha_phase_a4_business_verdict.md
?? docs/product_alpha_phase_a5_strategy_workspace.md
?? docs/product_alpha_phase_a6_implementation_plan.md
?? docs/product_alpha_phase_a7_execution_package.md   # present on disk; freeze out of preferred path
?? web/src/app/(product)/
?? web/src/components/{workspace,project-intake,investigation,verdict,strategy,implementation-plan,execution-package}/
?? web/src/lib/{workspace,project-intake,investigation,verdict,strategy,implementation-plan,execution-package}/
```

### `git log -3 --oneline`

```
70fc4b8 feat: establish Marketsynth Architecture v2.1 contracts and brand foundation
ee113ad Freeze approved Marketsynth home screen and Phase V2.1 brand foundation.
928a357 docs: note workflow raw inventory in DEVELOPMENT.md
```

### Phase / commit identification

| Milestone | Exact commit on this branch | Notes |
|---|---|---|
| AI.591 | **Not found** | No commit, no code, no phase doc in tree |
| Product Alpha A1 | **Uncommitted** local UI + `docs/product_alpha_phase_a1_workspace.md` | |
| A2 | **Uncommitted** | |
| A3 | **Uncommitted** | |
| A4 | **Uncommitted** | |
| A5 | **Uncommitted** | |
| A6 | **Uncommitted** | |
| Architecture V2.1 (related) | `70fc4b8` | Stub enums incl. `VerdictKind` aligned with Alpha vocabulary |
| Landing freeze | `ee113ad` | Product Alpha consumes frozen landing CTA paths |

No checkout/branch switch performed.

---

## 2. Existing backend inventory (actual code)

### 2.1 Campaign Control Center (nearest “control room”)

| Item | Location |
|---|---|
| Contract | `app/schemas/contracts.py` → `CampaignControlCenter` |
| Service | `app/services/campaign_control_center_service.py` |
| API | `GET /projects/{project_id}/business-campaigns/{campaign_id}/control-center` |
| List | `GET .../business-campaigns?view=control` → `CampaignControlCenterSummary` |
| Docs | `docs/phase_ai_156_*`, `docs/phase_ai_165_*` |

**Returned fields (real):** `campaign`, `health`, `next_action`, `timeline[]`, `metrics`, `resource_ids`, `safe_warnings`, `recovery_hint`, `primary_action`, `available_actions`, tool/skill suggestions, supervisor summary (`supervisor_health_score`, `top_findings`, …), workflow suggestions, `active_workflow`.

**Not returned:** workforce overlay, `current_stage`, `current_owner_role`, `decisions_summary`, `latest_decisions`, project-level timeline summary wrappers.

### 2.2 Project model

- `Project` / `ProjectTable` — ownership container (`owner_id`, `name`, `description`, `config`)
- API: `app/api/projects.py`
- **No** Product Alpha pipeline status on Project

### 2.3 Campaign model

- BOS `Campaign` at `/projects/{id}/business-campaigns` (AI.146–155)
- Statuses, metadata, scenario linkage
- Distinct from Product Alpha “project investigation journey”

### 2.4 Supervisor / executive / autonomous

| Capability | Status |
|---|---|
| Campaign Supervisor | **Present** — `CampaignSupervisorService`, `GET .../supervisor-report` |
| Executive decision layer | **Absent** as named service/API on this tree |
| Autonomous planner | **Absent**. Closest: marketer planning mode (`MarketingExecutionMode.PLANNING` only) |

### 2.5 Approvals & execution spine

- Resource `/approve` on plans, specialist outputs, content assets, media briefs, packages
- Action Center: `POST .../actions/{action_type}/execute`
- Execution: marketing plan execution runs + `execute-specialist`
- V2.1 stubs: `ApprovalState`, `ExecutionLifecycleState` — **not wired to APIs**
- Notes in compatibility map: *“No ApprovalRequest entity yet.”*

### 2.6 Roles

| Model | Values / purpose |
|---|---|
| `AgentType` | general, programmer, media, strategist, researcher, copywriter, content_planner, critic, analyst, orchestrator |
| `MarketingSpecialistType` | 14 marketing department roles (pipeline executables) |
| Product Alpha `AgencyRole` | Frontend management roles (CEO, Research Director, … Client Owner) — **not** backend enums |

### 2.7 Investigation / verdict / strategy / implementation (backend)

| Domain | Backend |
|---|---|
| Investigation workspace | **Absent** (skills/tools/researcher specialist exist as adjacent pieces) |
| Business verdict entity | **Absent**; V2.1 `VerdictKind` stub only |
| MarketingStrategy entity | **Absent**; strategist specialist + skill context only |
| ImplementationPlan (Alpha) | **Absent**; closest = `MarketingPlan` / `MarketingExecutionPlan` |

### 2.8 API surface (selected)

Registered in `app/main.py` among others:

- `/projects`, agents, chat, memory, tasks
- `/projects/{id}/business-campaigns` (+ control-center, supervisor, workflows, actions)
- business-operator, marketing-skills, marketing-tools
- marketing-plans, plan-execution-runs, specialist-outputs
- content/media/publishing, scenario-wizard, briefs

---

## 3. Product Alpha A1–A6 inventory

Commercial UX prototype under `web/` — **deterministic mocks + localStorage**. No FastAPI persistence.

### Routes

| Phase | Route |
|---|---|
| A1 | `/workspace` (+ nav placeholders) |
| A2 | `/workspace/projects/new` … `/review` |
| A3 | `/workspace/projects/[id]/investigation` |
| A4 | `/workspace/projects/[id]/verdict` |
| A5 | `/strategy`, `/pivot` |
| A6 | `/implementation` |

(A7 files/`execution-package` exist locally but are **out of preferred integration sequence** until this reconciliation lands.)

### localStorage keys

```
marketsynth.product_alpha.intake_draft.v1
marketsynth.product_alpha.mock_projects.v1
marketsynth.product_alpha.investigation.v1.{projectId}
marketsynth.product_alpha.verdict.v1.{projectId}
marketsynth.product_alpha.strategy.v1.{projectId}
marketsynth.product_alpha.implementation_plan.v1.{projectId}
```

### Status / readiness (summary)

| Layer | Statuses / readiness |
|---|---|
| Workspace project | `intake|research|investigation|verdict_pending|strategy|execution|paused` |
| Investigation | stage machine + `not_ready|conditionally_ready|ready_for_review` (≠ verdict) |
| Verdict type | `GO|CONDITIONAL_GO|NO_GO|INSUFFICIENT_DATA` (matches V2.1 `VerdictKind` vocabulary) |
| Verdict lifecycle | `draft|under_review|approved|superseded` |
| Strategy | `draft|under_review|approved|blocked|superseded` + execution-planning readiness |
| Implementation plan | same lifecycle + `PlanningReadinessStatus` |

### Routing rules

```
NO_GO → Pivot
INSUFFICIENT_DATA → Investigation
GO|CONDITIONAL_GO → Strategy → Implementation
Missing strategy → Strategy (from implementation)
```

### Roles

UI uses agency-style titles; A6 formalizes `AgencyRole` union. See role-mapping section / SoT matrix.

### Demo IDs

`proj_inv_a_conditional`, `proj_inv_b_not_ready`, `proj_inv_c_ready`, `proj_inv_d_no_go`

---

## 4. Reconciliation matrix

| Product Alpha capability | Existing backend capability | Relationship | Source of Truth | Integration action | Duplication risk |
|---|---|---|---|---|---|
| Workspace `/workspace` | Project list + campaign list APIs | **frontend-only view model** → becomes **direct UI projection** | Backend `Project`/`Campaign` after adapter | Replace mock list with existing APIs; keep Alpha UX shell | Medium — parallel “home” if old admin UIs remain |
| Agency Runtime Monitor | Campaign Control Center + specialist outputs + supervisor | **requires adapter** | `CampaignControlCenter` + specialist run state | Map health/`next_action`/findings/timeline → Monitor cards; do **not** invent second runtime store | **High** if Monitor grows its own state machine |
| Active Projects | `GET /projects`, business-campaigns | **compatible extension** | Backend | Project cards show Alpha pipeline as **derived** status | Medium |
| Project Intake | Campaign Brief Intake (AI.206–215) + Project create | **requires adapter** (+ possible additive fields) | Backend Project + Brief | Map Alpha draft → brief/project create; keep wizard UX | Medium — two intake stories |
| Investigation pipeline | Researcher/skills/tools; no investigation entity | **missing backend capability** | Future additive entity *or* campaign skill runs as interim | Prefer additive Investigation/Evidence later; interim: skill-run evidence projection | High if separate fake “investigation runtime” |
| Specialists / workforce | `MarketingSpecialistType` + AgentType | **semantic conflict** if AgencyRole becomes AgentType | Backend specialist/AgentType | AgencyRole = **UI alias / RACI label**; map to specialists where possible | **High** if new AgentTypes for CEO/Client Owner |
| Decisions (CC style) | Absent project decision ledger; resource approvals exist | **missing backend capability** | Future Decision Registry **after** design; until then approvals only | Do not treat Alpha verdict as CampaignDecision | Medium |
| Business Verdict | `VerdictKind` stub only | **compatible extension** / **missing entity** | Future Verdict entity; enum already reserved in V2.1 | Persist Alpha verdict model against `VerdictKind` | Low if enum reused |
| Strategy | Strategist output / skill context | **requires adapter** / **missing entity** | Future Strategy entity or specialist artifact package | Avoid second “strategy” inside campaign metadata only | Medium |
| Implementation Plan | `MarketingPlan` / execution plan tasks | **requires adapter** | `MarketingPlan` as executable spine; Alpha plan as planning view | Map workstreams/tasks → plan tasks carefully | **High** if two plan engines |
| Readiness | Brief completeness, operator confidence, action availability; V2.1 lifecycle stub | **frontend-only** → **compatible extension** | Backend gates when wired | Keep Alpha readiness as derived UI until gate contracts exist | Medium |
| Conditions | Supervisor findings / brief gaps | **compatible extension** | Supervisor + future verdict conditions | Map Alpha conditions → findings/conditions entity | Low |
| Risks | Supervisor risks list | **compatible extension** | Supervisor + future risk register | | Low |
| Approvals | Resource `/approve` endpoints | **requires adapter** | Existing approve APIs; future `ApprovalRequest` | Alpha local approve = preview only until wired | Medium |
| Timeline | `CampaignTimelineEvent[]` | **direct UI projection** (campaign scope) | Campaign Control Center timeline | Project-level timeline may need extension | Low for campaign; gap for project journey |
| Recommended Next Step | `next_action` / `CampaignNextAction` | **direct UI projection** | Control Center | Drive Alpha CTAs from `next_action` after mapping | Medium if Alpha has separate CTA rules |
| Execution handoff | Action Center + publishing + plan runs | **compatible extension** | Existing execution spine | A7/Verified Execution **later** | High if Alpha dry-run claims real execution |

---

## 5. Control Center decision

### Options

| Option | Verdict |
|---|---|
| **A** — Alpha Workspace replaces old Control Center UI, uses its backend | **Recommended (refined)** |
| B — Embed Alpha inside existing Control Center screen | Rejected — scopes differ (agency journey vs campaign cockpit) |
| C — Both screens forever separate with no shared SoT | Rejected — creates dual Runtime |
| D — Alpha is pure duplicate and must be discarded | Rejected — Alpha defines commercial journey UX that CC does not cover |

### Recommendation: **A (refined)**

1. **Backend Source of Truth** for campaign health / next action / timeline / supervisor = **Campaign Control Center (AI.156–165)** and related campaign APIs.  
2. **Marketsynth `/workspace`** = commercial **frontend projection** and intake→verdict→strategy→plan journey.  
3. **Agency Runtime Monitor** must become an **adapter view** over Control Center + specialist/plan state — not an independent runtime.  
4. Claimed **AI.591 workspace overlay** is **not present**; if still desired, it must be designed as an **extension of Campaign Control Center / project aggregate**, not a parallel system. Prefer implementing that extension **after** wiring Alpha read models to existing CC.

**Treatment of “old” Control Center UI:** keep API; any legacy UI becomes campaign detail panel inside Marketsynth Workspace (or deep-link), not a competing home.

---

## 6. State machine mapping

| Product Alpha state | Backend equivalent | Classification |
|---|---|---|
| Workspace `ProjectStatus` | None on `Project` | **currently absent** (derive UI from artifacts) |
| Pipeline strip stages | None single enum | **derived UI state** |
| Investigation status/stages | None | **currently absent** |
| Verdict readiness | None (≠ brief completeness) | **derived UI** / future entity |
| `BusinessVerdictType` | `VerdictKind` (stub) | **exact vocabulary match**; entity **absent** |
| Verdict `draft/under_review/approved` | Partial overlap with plan/asset approve patterns | **compatible**; no Verdict store |
| Strategy status | None | **currently absent** |
| Implementation plan status | Loose analogy to `MarketingPlanStatus` | **partially conflicting semantics** (Alpha planning ≠ marketing plan) |
| Planning readiness | Action availability / gates | **derived UI** |
| Approval local gates | Resource approve + future `ApprovalState` | **UI preview** vs **backend approve** |
| Campaign `next_action` | `CampaignNextAction` | **exact backend equivalent** (campaign scope) |
| Campaign health | `CampaignHealth` | **exact** |
| Campaign timeline events | `CampaignTimelineEvent` | **exact** |
| Specialist run progress | Specialist outputs / execution run task index | **compatible** |
| `ExecutionLifecycleState` | V2.1 stub only | **reserved**; not Alpha’s mock statuses |
| MarketingExecutionMode | `PLANNING` only | **conflicts** with Alpha “execution” stage label (label ≠ real mode) |

**Rule:** do not create new backend states in this audit; any Alpha-only status must stay UI-derived until a designed additive contract.

---

## 7. Role mapping

| Product Alpha role | Existing role/AgentType | Exact match | UI alias allowed | Backend change required |
|---|---|---|---|---|
| Research Director | — / orchestration label | No | Yes | No — do not add AgentType |
| Market / Competitor / Audience Analyst | `analyst` + researcher skills | Partial | Yes | No |
| Risk Officer | — (supervisor findings owner conceptually) | No | Yes | No |
| Chief Marketing Strategist | `strategist` / `MarketingSpecialistType.STRATEGIST` | Partial | Yes | No |
| Performance Marketer | `ad_creative_strategist` / skills | Partial | Yes | No |
| Content Strategist / Copywriter / Designer | `content_planner` / `copywriter` / media | Partial | Yes | No |
| Analyst | `analyst` | Yes (specialty) | Yes | No |
| Project Manager | — | No | Yes | No |
| Client Owner / CEO | `UserRole.OWNER` (tenant) — not AgentType | No | Yes | No — never AgentType |
| Pipeline specialists (research/copy etc.) | `MarketingSpecialistType` | Yes for executables | Prefer exact specialist ids in runtime | No |

**Hard rule:** frontend AgencyRole must not silently become new backend AgentType values.

---

## 8. Decision model mapping

| Concept | Separate domain object? | Notes |
|---|---|---|
| Campaign Control Center `next_action` | Derived recommendation | Not a Decision record |
| Resource `/approve` | Operational approval | Exists today |
| Business Verdict (Alpha) | **Should become** domain object | Soft-aligned with `VerdictKind`; not CC decision |
| Strategy / plan “Approve” (Alpha local) | UI preview | Map later to real approve APIs |
| Supervisor findings | Quality findings | Not verdicts |
| Project Decision Registry (claimed AI.589) | **Absent** | Do not conflate with Verdict |

---

## 9. Data ownership (summary)

Full detail: [`product_alpha_source_of_truth_matrix.md`](./product_alpha_source_of_truth_matrix.md)

| localStorage model | Future SoT class |
|---|---|
| ProjectIntakeDraft | maps to Project + CampaignBrief (+ additive fields) |
| InvestigationWorkspace | **requires additive backend entity** (interim: skill evidence projection) |
| BusinessVerdict | **requires additive entity**; enum reserved as `VerdictKind` |
| MarketingStrategy | **requires additive entity** or packaged specialist artifacts |
| ImplementationPlan | maps to **multiple** (`MarketingPlan` + planning metadata); careful adapter |

---

## 10. API gap analysis

### Already usable for Alpha projections

| Endpoint | Alpha use |
|---|---|
| `GET /projects` | Active projects |
| `GET/POST /projects` | Create/list |
| `GET .../business-campaigns` (+ `view=control`) | Campaign cards / health |
| `GET .../control-center` | Agency Runtime Monitor feed (adapter) |
| `GET .../supervisor-report` | Risks/conditions panel |
| Brief intake APIs | Seed from Alpha intake |
| Marketing plan + execution-run APIs | Post-strategy execution spine |
| Skill/tool run APIs | Investigation interim evidence |

### Proposed contracts only (do not implement now)

1. **`GET /projects/{id}/agency-overview`** — read aggregate for Workspace Monitor (projects/campaigns mapped to Alpha pipeline **derived** labels). Auth: owner. Read-only.

2. **`GET|PUT /projects/{id}/intake`** — persist intake draft ↔ brief fields. Auth: owner. Write with sanitize.

3. **`GET|POST /projects/{id}/investigations`** — investigation workspace + evidence. Additive. Read/write; no execution side effects.

4. **`GET|POST /projects/{id}/verdicts`** — BusinessVerdict versions using `VerdictKind`. Approval may require explicit approve endpoint later.

5. **`GET|POST /projects/{id}/strategies`** — strategy versions; approval gate separate.

6. **`GET|POST /projects/{id}/implementation-plans`** — planning artifact; mapping notes to `MarketingPlan` creation **only via explicit handoff API**, not silent dual-write.

Compatibility: extend `contracts.py` first; reuse owner/project scoping; no parallel Control Center schema that forks campaign health.

---

## 11. Recommended development sequence (revised)

See [`product_alpha_runtime_integration_plan.md`](./product_alpha_runtime_integration_plan.md).

Headline:

1. Freeze A1–A6 as UX prototype (do not expand mock surface).  
2. Reconcile Workspace with **Campaign Control Center** (real AI.156–165), not missing AI.591.  
3. Wire Agency Runtime Monitor **read-only** to control-center + supervisor.  
4. Replace mock project list with Project/Campaign APIs.  
5. Map intake → Project + Brief.  
6. Investigation read models (additive or interim skill projection).  
7. Verdict persistence (`VerdictKind`).  
8. Strategy persistence.  
9. Implementation plan ↔ MarketingPlan handoff.  
10. **Only then** A7 / Architecture V2.2 Verified Execution.  
11. **AI.592** (execution_mode) only after Workspace↔Runtime mapping is decided — **wait**.

---

## 12. Documents produced

- `docs/product_alpha_ai591_reconciliation_audit.md` (this file)
- `docs/product_alpha_runtime_integration_plan.md`
- `docs/product_alpha_source_of_truth_matrix.md`

---

## 13. Final report answers

1. **Does Product Alpha contradict AI.591?**  
   **AI.591 is not in this checkout**, so there is no direct code conflict with it. Alpha **does risk duplicating** Campaign Control Center **semantics** (next step, timeline, health, “runtime monitor”) if integrated carelessly.

2. **What continues existing code?**  
   Verdict vocabulary ↔ `VerdictKind`; commercial shell over Projects/Campaigns; eventual Monitor over CC; approvals/execution via existing spine.

3. **What duplicates?**  
   Parallel runtime monitor, parallel project status machine, parallel plan engine, agency roles as if AgentTypes, local approval semantics.

4. **Mock models with backend equivalents?**  
   Intake↔Brief/Project (partial); Plan↔MarketingPlan (partial/conflict); Monitor↔Control Center (adapter); Risks↔Supervisor (partial).

5. **Real backend gaps?**  
   Investigation entity, Verdict entity, Strategy entity, project decision/timeline/workforce overlay (claimed AI.586–591), unified project pipeline status, ApprovalRequest, Verified Execution.

6. **Role of new Workspace?**  
   Commercial frontend projection / agency journey OS — **not** a second backend runtime.

7. **Old Control Center UI?**  
   Keep **API** as SoT; surface as campaign cockpit inside Marketsynth; retire competing “command center” homes.

8. **Revised numbering:**  
   Freeze Alpha A1–A6 → Integration I1…I9 (see integration plan) → A7/V2.2 → then revisit AI.592-class execution_mode work.

9. **AI.592 now?** **Wait.**

10. **Product Alpha A7 now?** **Wait** (local A7 files may exist; do not expand/finish as product path until I1–I9).

11. **No production code changed** in this audit (docs only).

12. **No remote Git operations performed.**

---

AI.591 and Product Alpha reconciliation audit completed.  
No production code changed.  
Product Alpha A7 has not started.  
AI.592 has not started.  
Ready for architecture review.
