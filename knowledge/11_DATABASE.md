# Database (Conceptual)

> **No SQL.** Entity concepts and relations only.  
> **Schema SoT:** [app/schemas/contracts.py](../app/schemas/contracts.py)  
> **Persistence:** `app/db/`  
> **Last updated:** 2026-07-29

---

## Core workspace entities

| Entity | Purpose | Key relations |
|--------|---------|---------------|
| **User** | Account, role, onboarding | → Projects, ApiKeys |
| **Project** | Workspace container | → all project-scoped artifacts |
| **Agent** | Registered agent definition | → AgentRuns |
| **AgentRun** | Execution instance | → Project, Task |
| **Task** | Work unit | → Project |
| **UserRequest** | Inbound user ask | → Project, routing metadata |
| **BrowserSession** | Browser automation session | → User |

---

## Commercial / BIV entities

| Entity | Purpose |
|--------|---------|
| **AnalysisContext** | Confirmed intake context for analysis |
| **Evidence** | Research evidence items with lineage |
| **BusinessVerdict** | GO/CONDITIONAL/PILOT/HOLD/NO_GO |
| **LaunchPackRequest** | Launch pack assembly request |
| **Offer** | Offer Builder artifact |
| **MarketingStrategy** | Strategy document |
| **ImplementationPlan** | Post-verdict plan |

---

## Marketing conveyor entities

| Entity | Purpose |
|--------|---------|
| **MarketingPlan** | Draft/approved plan |
| **MarketingPlanExecutionRun** | Plan execution instance |
| **MarketingSpecialistOutput** | Specialist artifact |
| **MarketingScenario** | Scenario registry entry |
| **ScenarioWizardRun** | Wizard step state |
| **BusinessCampaign** | Campaign container (BOS) |
| **ProjectBrief** / **MarketingBrief** | Brief intake |
| **MarketingSkillRun** | Explicit skill execution |
| **MarketingToolInvocation** | Tool call log |

---

## Content & media entities

| Entity | Purpose |
|--------|---------|
| **ContentAsset** | Produced content unit |
| **MediaBrief** | Approved media intent |
| **MediaGenerationJob** | Generation run |
| **MediaAsset** | Stored media |
| **GeneratedVisualAsset** | Visual output |
| **ReferenceSet** / **ReferenceVisualAsset** | Identity/reference inputs |
| **VideoClipRequest** | Video generation request |

---

## Publishing entities

| Entity | Purpose |
|--------|---------|
| **PublicationPackage** | Approved publish bundle |
| **PublicationJob** | Publish execution (dry/real) |
| **PublishingFoundationChannel** | Channel config |
| **ScheduledPublication** | Scheduler entry |

---

## Identity subsystem (H2.8E)

| Entity | Purpose |
|--------|---------|
| **IdentityReferenceManifest** | Immutable selected/excluded refs |
| **IdentityGenerationReadiness** | Preflight state |
| **IdentityQualificationRun** | Qualification session |
| **IdentityPaidApprovalRequest** | Paid gate |
| **IdentityRecipe** | Generation recipe |

---

## Knowledge governance entities

| Entity | Purpose |
|--------|---------|
| **KnowledgeItem** | Governed knowledge unit |
| **KnowledgeSnapshot** | Published snapshot |
| **SourceCandidate** | Draft from web collection |
| **Citation** | Evidence link for answers |

Types: `KnowledgeType`, `KnowledgeItemStatus` enums in contracts.

---

## Beta & demo entities

| Entity | Purpose |
|--------|---------|
| **BetaFeedbackReport** | Tester feedback |
| **DemoFlowStatus** | E2E demo state markers |

---

## Entity relationship (simplified)

```
User
 └── Project
      ├── AnalysisContext → Evidence → BusinessVerdict
      ├── LaunchPackRequest → Offer
      ├── BusinessCampaign
      │    ├── ProjectBrief
      │    ├── MarketingSkillRun
      │    └── CampaignWorkflowRun (checklist)
      ├── ContentAsset → MediaBrief → MediaGenerationJob
      ├── PublicationPackage → PublicationJob
      ├── ReferenceSet → GeneratedVisualAsset
      └── KnowledgeItem → KnowledgeSnapshot
```

---

## Migrations

- Alembic migrations in `app/db/migrations/` (if present) or project migration path
- **Rule:** Add to `contracts.py` first, then model, then migration
- Never migrate without contract update

---

## Indexes (conceptual)

| Area | Index need |
|------|------------|
| Project-scoped queries | `project_id` on all child entities |
| User requests | Status + created_at for queue |
| Publication scheduler | Due date + status |
| Agent runs | Project + status |
| Knowledge | Type + status + freshness for governed lookup |

Exact indexes — inspect DB models in `app/db/`.
