# CAPABILITY-CATALOG

> **Program:** PRODUCT-02  
> **Owns:** Capability cards + A–F classification + MVP band  
> **Patch:** PRODUCT-02-BLUEPRINT-PATCH-01 · OD-03 · OD-05 · OD-09  
> **Status:** OWNER-APPROVED · `owner_freeze` NOT SET  
> Registry IDs align with PRODUCT-01.5 where present. Catalog ≠ authorization.

---

## 1. Classification A–F (OD-03 · OWNER-APPROVED)

| Code | Class | Meaning |
|------|-------|---------|
| **A** | Project stage | Advances the commercial path of one Project |
| **B** | Project service | Optional service **inside** a Project after proven journey |
| **C** | Workspace service | Cross-project / account-level product surface |
| **D** | Settings/admin | Org admin (Billing, Team, Security, Integrations) |
| **E** | Reserved | Named, not in commercial spine until journey + owner approval |
| **F** | Internal-only | Developer / operator surfaces; not customer products |

**Rules**

1. HR is **not** a Project stage by default.  
2. Legal / Finance / Programmer / CRM are **not** automatic Project stages.  
3. Billing / Team are **D**, not spine.  
4. Capability without proven paid deliverable is **not** in MVP runtime roadmap.

---

## 2. Card schema (mandatory)

| Field | Purpose |
|-------|---------|
| `id` | Stable capability id (registry-aligned) |
| `canonicalName` | Product name |
| `classification` | A–F |
| `canonicalContainer` | Project / Launch subtree / Workspace / Settings / Reserved / Internal |
| `entryConditions` | When it may open |
| `exitConditions` | What counts as done for a run |
| `blockingConditions` | What blocks progress |
| `consumedArtifacts` | Typed inputs |
| `producedArtifacts` | Typed outputs |
| `runMultiplicity` | single / many / loop |
| `parallelism` | none / with-sibling / independent |
| `approvalRequirements` | ApprovalRecord types required |
| `recoverability` | Restore / retry policy |
| `commercialDeliverable` | What the customer pays for |
| `mvpBand` | `mvp` \| `post-mvp` \| `reserved` |
| `registryAvailability` | available / planned / reserved / internal |
| `runtimeStatus` | implemented \| blueprint \| frozen |

---

## 3. MVP band summary (OD-05)

| Band | Capabilities |
|------|----------------|
| **MVP** | Intake, Research, Strategy, thin Launch, limited Content, optional Visuals, Publication (one channel commercially), basic Outcome Capture |
| **Post-MVP** | Full Project Analytics, Optimization, multi-channel Publication, Portfolio Analytics, CRM (when journey), extended B services |
| **Reserved** | HR, Legal, Finance, Programmer, CRM (until journey), Billing expansion, Team workflows |

---

## 4. Project stages (A)

### 4.1 `project.intake`

| Field | Value |
|-------|-------|
| classification | **A** |
| canonicalContainer | Project Command Center |
| entryConditions | Authenticated user; new or editable draft |
| exitConditions | Owner confirms intake review |
| blockingConditions | Required fields missing; API unavailable |
| consumedArtifacts | — |
| producedArtifacts | `IntakePackage` |
| runMultiplicity | many (re-edit creates new version) |
| parallelism | none |
| approvalRequirements | Confirm before Research start |
| recoverability | Draft restore |
| commercialDeliverable | Structured idea capture |
| mvpBand | **mvp** |
| registryAvailability | available |
| runtimeStatus | implemented |

### 4.2 `project.research`

| Field | Value |
|-------|-------|
| classification | **A** |
| canonicalContainer | Project Command Center |
| entryConditions | Intake confirmed |
| exitConditions | Terminal run `succeeded` \| `failed` \| `cancelled` \| `interrupted`; partial honesty is a **produced** `PartialResearchPackage` on a succeeded run (not a CapabilityRunState) |
| blockingConditions | Provider failure; limits; Research Hardening freeze |
| consumedArtifacts | `IntakePackage` |
| producedArtifacts | `ResearchReport`, `EvidenceSet`, `VerdictPackage` \| `PartialResearchPackage` |
| runMultiplicity | many (reruns → new versions) |
| parallelism | none vs Strategy (gated) |
| approvalRequirements | Start; accept/continue; override for partial→Strategy |
| recoverability | latest-run / cold restore; no duplicate POST on hydrate |
| commercialDeliverable | Evidence-backed verdict or honest partial |
| mvpBand | **mvp** |
| registryAvailability | available (panel) |
| runtimeStatus | implemented (hardening frozen until 2026-08-18) |

**OD-08:** Partial does **not** open Strategy without explicit override ApprovalRecord; Strategy inherits gaps/limitations/confidence/assumptions.

### 4.3 `project.strategy`

| Field | Value |
|-------|-------|
| classification | **A** |
| canonicalContainer | Project Command Center |
| entryConditions | Accepted Research **or** explicit partial override |
| exitConditions | `StrategyPackage` approved (ApprovalRecord) |
| blockingConditions | No accepted Research path; unapproved package |
| consumedArtifacts | `VerdictPackage` / constrained Partial + Report + Evidence |
| producedArtifacts | `StrategyPackage` (versioned; may be assumption-constrained) |
| runMultiplicity | many (revision loop) |
| parallelism | none vs Launch (Launch waits on approval) |
| approvalRequirements | Strategy approval before Launch spend |
| recoverability | Last approved + draft versions |
| commercialDeliverable | Grounded positioning / offer / funnel outline |
| mvpBand | **mvp** |
| registryAvailability | planned |
| runtimeStatus | blueprint |

### 4.4 `project.launch` (container)

| Field | Value |
|-------|-------|
| classification | **A** (container) |
| canonicalContainer | Project → Launch subtree |
| entryConditions | Approved `StrategyPackage` |
| exitConditions | Thin Launch package ready for Content/Visuals |
| blockingConditions | Unapproved Strategy; empty channel plan |
| consumedArtifacts | `StrategyPackage` |
| producedArtifacts | `LaunchPackage` |
| runMultiplicity | many (revision; Strategy change may invalidate candidates) |
| parallelism | hosts parallel Content ∥ Visuals |
| approvalRequirements | Confirm launch pack before content factory spend |
| recoverability | Draft/approved launch versions |
| commercialDeliverable | Thin launch plan (offer/channels/budget/checklist) |
| mvpBand | **mvp** (thin) |
| registryAvailability | planned |
| runtimeStatus | blueprint |

**Subtree:** Offer · Channels · Budget · Checklist · Content · Visuals · Approval · Publication.

### 4.5 `launch.content`

| Field | Value |
|-------|-------|
| classification | **A** (under Launch) |
| canonicalContainer | Project → Launch → Content |
| entryConditions | Launch brief sufficient |
| exitConditions | Required assets draft + reviewable |
| blockingConditions | Strategy/launch drift |
| consumedArtifacts | `LaunchPackage`, `StrategyPackage` |
| producedArtifacts | `ContentPackage` |
| runMultiplicity | many |
| parallelism | **parallel with Visuals** (OD-04) |
| approvalRequirements | Content ApprovalRecord before publish package |
| recoverability | Asset versions |
| commercialDeliverable | Limited channel-ready drafts (MVP) |
| mvpBand | **mvp** (limited) |
| registryAvailability | planned |
| runtimeStatus | blueprint |

### 4.6 `launch.visuals`

| Field | Value |
|-------|-------|
| classification | **A** (under Launch) |
| canonicalContainer | Project → Launch → Visuals |
| entryConditions | Launch brief; may start without Content complete |
| exitConditions | Required visuals attached **or** explicitly skipped |
| blockingConditions | Video freeze; provider not ready |
| consumedArtifacts | `LaunchPackage`, optional `ContentPackage` |
| producedArtifacts | `VisualPackage` |
| runMultiplicity | many |
| parallelism | **parallel with Content** (OD-04) |
| approvalRequirements | Visual ApprovalRecord when used in publish |
| recoverability | Asset library refs |
| commercialDeliverable | Optional visuals (MVP) |
| mvpBand | **mvp** (optional) |
| registryAvailability | planned |
| runtimeStatus | blueprint (video frozen) |

### 4.7 `launch.publication`

| Field | Value |
|-------|-------|
| classification | **A** (under Launch) |
| canonicalContainer | Project → Launch → Publication |
| entryConditions | Approved necessary artifact set for package |
| exitConditions | `DeliveryEvidence` stored (success or honest failure) per job |
| blockingConditions | Missing approvals; dry-run only; channel not configured |
| consumedArtifacts | Approved Content (+ Visual if required), Launch channel config |
| producedArtifacts | `PublicationPackage`, `PublicationJob`, `DeliveryEvidence` |
| runMultiplicity | **many** (jobs, channels, schedules, retries) — OD-07 |
| parallelism | multiple jobs; not a single `published=true` |
| approvalRequirements | Package + External execution ApprovalRecords |
| recoverability | Job status + evidence |
| commercialDeliverable | One real channel publish (MVP); multi-channel post-MVP |
| mvpBand | **mvp** (one channel commercially) / multi-channel **post-mvp** |
| registryAvailability | planned (Telegram foundation gated) |
| runtimeStatus | blueprint / partial foundation |

### 4.8 `project.outcome_capture` (basic) / `project.analytics`

| Field | Value |
|-------|-------|
| classification | **A** |
| canonicalContainer | Project Command Center |
| entryConditions | At least one PublicationJob / DeliveryEvidence preferred |
| exitConditions | Basic outcome recorded **or** MonitoringSnapshot |
| blockingConditions | No publish yet; connector missing (honest empty) |
| consumedArtifacts | `DeliveryEvidence`, PublicationJob refs |
| producedArtifacts | `OutcomeCapture` (MVP) / `MonitoringSnapshot` (full) |
| runMultiplicity | continuous / many snapshots |
| parallelism | independent of Optimization until post-MVP |
| approvalRequirements | — (capture); Optimization has its own |
| recoverability | Last snapshot / capture |
| commercialDeliverable | MVP: **basic Outcome Capture**; full Analytics platform **post-mvp** |
| mvpBand | Outcome Capture **mvp**; full Project Analytics **post-mvp** |
| registryAvailability | reserved (`workspace.analytics` today — realign after freeze) |
| runtimeStatus | blueprint |

**OD-02:** Project Analytics = operational truth. Workspace Portfolio Analytics = **C / reserved** — separate card below.

### 4.9 `project.optimization`

| Field | Value |
|-------|-------|
| classification | **A** (cyclic) |
| canonicalContainer | Project Command Center |
| entryConditions | Outcome / monitoring signal **or** explicit start |
| exitConditions | Optimization candidate approved → new versioned Strategy/Launch/Content |
| blockingConditions | No signal; unclear goals |
| consumedArtifacts | `OutcomeCapture` / `MonitoringSnapshot`, prior packages |
| producedArtifacts | `OptimizationCandidate` / `OptimizationPlan` |
| runMultiplicity | **loop** (post-MVP) — OD-06 |
| parallelism | produces candidates; does not rewrite history |
| approvalRequirements | Optimization candidate ApprovalRecord |
| recoverability | Prior plans + lineage |
| commercialDeliverable | Versioned improvement proposals |
| mvpBand | **post-mvp** |
| registryAvailability | not in registry — add after freeze if prioritized |
| runtimeStatus | blueprint |

---

## 5. Services / settings / reserved

### 5.1 Knowledge

| Field | Value |
|-------|-------|
| classification | **B** (project attach) + **C** (cross-project library when productized) |
| canonicalContainer | Project service; Workspace library optional |
| mvpBand | **reserved** for commercial spine attach; KG foundation may exist separately |
| commercialDeliverable | None in MVP first-payment path |
| registryAvailability | internal/reserved |
| runtimeStatus | blueprint for commercial attachment |

### 5.2 CRM (OD-09)

| Field | Value |
|-------|-------|
| classification | **E** Reserved — final A/B/C deferred until proven journey |
| canonicalContainer | Undecided: future project service **or** workspace service |
| mvpBand | **reserved** |
| commercialDeliverable | None until journey |
| registryAvailability | reserved |
| runtimeStatus | blueprint |

### 5.3 Legal / Finance / Programmer

| Field | Value |
|-------|-------|
| classification | **E** (default) → possible **B** after journey + owner approval |
| canonicalContainer | Not Settings-as-product-apps; attach as project services when justified |
| mvpBand | **reserved** |
| rule | Never auto-promote to Project stage |

### 5.4 HR

| Field | Value |
|-------|-------|
| classification | **E** / future **D** — **not** Project stage |
| canonicalContainer | Settings/org when productized |
| mvpBand | **reserved** |

### 5.5 Billing / Team / Security / Integrations

| Field | Value |
|-------|-------|
| classification | **D** |
| canonicalContainer | Settings / Admin |
| mvpBand | Billing/Team workflows expansion **reserved**; basic settings may exist |
| rule | Not commercial Project spine |

### 5.6 `workspace.portfolio_analytics`

| Field | Value |
|-------|-------|
| classification | **C** |
| canonicalContainer | Workspace |
| mvpBand | **reserved** — not public |
| commercialDeliverable | Future multi-project aggregation |
| registryAvailability | reserved (do not expose as available) |

### 5.7 Internal (F)

Assistant, Review, Channels, Assets (dev) — map into Launch/Project semantics when exposed; remain **F** until productized.

---

## 6. Consistency rules

1. No capability enters MVP runtime roadmap without `mvpBand = mvp` and a commercial deliverable.  
2. No public CTA unless Registry `available` **and** entryConditions true **and** authz allows (Registry ≠ authz).  
3. Artifacts named here must appear in [ARTIFACT-FLOW.md](./ARTIFACT-FLOW.md).  
4. Registry id drift (Analytics workspace→project; Portfolio reserved) = **post-freeze** follow-up only.
