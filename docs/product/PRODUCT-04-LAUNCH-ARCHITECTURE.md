# PRODUCT-04 — Launch Architecture

> **Task:** PRODUCT-04-LAUNCH-ARCHITECTURE-FREEZE-01 (base: ARCHITECTURE-01 · PATCH-01)  
> **Title:** Marketsynth Launch Architecture  
> **Type:** Docs-only applied domain architecture  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **OD-LA-01…10:** **OWNER-ACCEPTED** (2026-08-02)  
> **Basis:** OD-LA-01…10 applied · hard blockers OD-LA-06/08 closed · consistency validation PASS · reviewers 5/5 PASS · code/runtime/research unchanged  
> **Audit:** `PRODUCT-04-LAUNCH-AUDIT-AND-FREEZE.md`  
> **Inherits (OWNER-FROZEN — do not reopen):** PRODUCT-02 · PRODUCT-03 · PRODUCT-04 EM · PRODUCT-04 Fabric · PRODUCT-04 Launch Domain Model  
> **Pack:** Lifecycle · Capability Catalog · Artifact Flow · Owner Journey · MVP Cut · Audit/Freeze  
> **Does not:** auto-start Content Architecture · Launch Runtime · code · UI · API · migrations · Registry · Research · new foundation · re-decide Domain Model / OD-LA

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-04 Launch Architecture
basis: OD-LA-01…10 OWNER-ACCEPTED; hard blockers OD-LA-06/08 closed; consistency matrix PASS; composite 5/5 PASS; code/runtime/research unchanged
```

### Frozen invariants (normative — Architecture pack)

1. Launch = `project.launch` capability (Project Command Center).  
2. Approved Launch Package = primary commercial deliverable.  
3. LaunchRun ≠ Package (approval / stale / published are not run statuses).  
4. CampaignFrame owned by Launch; inside Package; 1..N (MVP UI default one).  
5. OfferArtifact owned by Launch; 1..N per frame; ≠ Strategy Structure · ≠ ContentAsset.  
6. Budget = Package **section** in MVP (no BudgetArtifact).  
7. ContentRequest owned by Launch; required for MVP Package.  
8. VisualRequest owned by Launch; conditional.  
9. PublicationPlan owned by Launch (intent only).  
10. PublicationPackage belongs to Publication.  
11. OutcomeRecord belongs to Project Outcome Capture.  
12. Approved Package is immutable; edits → new version.  
13. Assets are downstream; never back-filled into Package.  
14. Single `launch_package_approval` covers whole Package (no per-section frame/offer/request approvals in MVP).  
15. Package version pinning for requests, handoff, export.  
16. In-flight supersession: **complete+stale** (OD-LA-06).  
17. **No** automatic cancellation of in-flight children.  
18. Explicit / safe cancel is a separate action (OD-LA-07).  
19. Retry ≠ rerun (Fabric carve-out; interrupt remains terminal).  
20. Canonical publish path: PublicationPackage → **PackageJob** → Delivery → DeliveryEvidence.  
21. PublicationJob (code-stack A) = **legacy** migration source — not a second canonical send.  
22. Export MVP: Markdown + JSON of approved Package version.  
23. Runtime implementation order: **R1→R6** (Package-first; no E2E monolith first).  
24. BusinessCampaign = **partial adapter only** — not canonical; no 1:1 to CampaignFrame.  
25. Registry ≠ authorization.  
26. Launch Runtime does **not** start automatically from this freeze.

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Accept Launch Architecture pack as OWNER-FROZEN | Start PRODUCT-05 Content Architecture automatically |
| Lock Architecture invariants 1–26 + OD-LA-01…10 | Start Launch / Content / Visual / Publication Runtime |
| Close applied Launch architecture before Content Architecture | Rewrite P02/P03/EM/Fabric/Domain Model · edit Registry · change code |
| Record PackageJob as canonical publish **target** | Execute dual-stack migration or delete legacy PublicationJob |

**Next priority:** **NOT SET** (owner kickoff required for PRODUCT-05).

---

## Pre-implementation check (compact)

| # | Result |
|---|--------|
| 1. Current inventory | LaunchPackRequest · OfferArtifact · Content Factory · PublicationPackage/Job dual stacks · BusinessCampaign · missing LaunchRun/Package/CampaignFrame/PublicationPlan/ExecutionApproval |
| 2. Frozen contracts | Domain Model 1–40 · EM 1–26 · Fabric 1–40 · P02/P03 |
| 3. Contradictions (honest) | CWF assets-before-Package; Launch Pack ≠ Package; dual publish (target closed OD-LA-08); BusinessCampaign ≠ CampaignFrame (OD-LA-02) |
| 4. Reuse | Hydration · OfferArtifact · Content Factory · **PackageJob path (canonical target)** · Telegram (B) via adapter · BusinessCampaign **partial adapter only** |
| 5. Legacy risks | LaunchPackRequest naming · **PublicationJob (A) = temporary migration source** · MarketingCampaign |
| 6. Owner decisions | OD-LA-01…10 **accepted** — see Audit |
| 7. Seven docs | This pack only |
| 8. In scope | Applied Launch capability architecture |
| 9. Out of scope | Runtime · tables · CWF rewrite · Content/Visual/Publication Architecture programs |
| 10. Freeze blockers | **Closed** for Architecture freeze (OD-LA-06/08). Runtime still blocked until dual-stack migration + dedup tests |

---

## 1. Place in the product

Launch lives in **Project Command Center** as `project.launch` — not a Workspace app, not a separate product (per PRODUCT-02 taxonomy).

```
Project
├── Research → Strategy (frozen)
└── Launch (capability)
    ├── LaunchRun (N)
    │     └── ApprovedLaunchPackage (versioned head)
    ├── issues → Content / Visuals (executors)
    └── handoff intent → Publication (separate contract)
```

**Strategy → Launch:** only via `LaunchInputSnapshot` pinned to an **Approved Strategy Package** version (`launch_eligible` / handoff). No dynamic “latest Strategy.”

---

## 2. Core objects (applied)

| Object | Role |
|--------|------|
| **LaunchRun** | Repeatable CapabilityRun under `project.launch` |
| **LaunchInputSnapshot** | Immutable pinned Strategy (+ constraints, budget posture inputs, assumptions) |
| **LaunchCandidate** | Draft Package version produced by a run |
| **ApprovedLaunchPackage** | Requirements-first commercial SKU after `launch_package_approval` |
| **CampaignFrame** | Execution context inside Launch (1..N per run; MVP UI default **one**) |
| **OfferArtifact** | Executable offer (1..N per frame; selected for requests/plan) |
| **Budget section** | Package section (MVP) — known/unknown · envelope/range · constraints · `paid_execution_allowed` · ack state · assumptions (**OD-LA-04 = A**; no BudgetArtifact) |
| **ContentRequest** | Launch-owned ask (required MVP) |
| **VisualRequest** | Launch-owned conditional ask |
| **PublicationPlan** | Launch-owned publish **intent** |
| **Outcome Capture** | Project-level consumer of DeliveryEvidence — not Launch-owned |

Downstream (not Launch-owned): ContentAsset · VisualAsset · PublicationPackage · PackageJob (canonical send path) · DeliveryEvidence · OutcomeRecord.  
Legacy (not Launch-owned, temporary): PublicationJob (code-stack A).

**BusinessCampaign** is **not** a Launch core object and is **not** CampaignFrame (OD-LA-02).

---

## 3. LaunchRun contract (OD-LA-01 = A)

LaunchRun = Fabric CapabilityRun specialization.

**Pinned to:** tenant · project · Approved Strategy version · LaunchInputSnapshot · owner decision refs · constraints · budget state · assumptions.

**Produces:** LaunchCandidate → (after approval) ApprovedLaunchPackage head; issues Content/Visual requests; authors PublicationPlan.

| Rule | |
|------|--|
| Project → N LaunchRuns | Yes |
| Strategy version → N LaunchRuns | Yes |
| **Interrupted** | **Terminal** — never silently reopened to `running` |
| **Retry** | New **attempt** of the **same** `run_id` + InputSnapshot — only while Fabric allows (pre-terminal or `interrupted` carve-out); does **not** reopen a closed terminal run as `running`; `failed`/`cancelled` → **rerun** |
| **Rerun** | New LaunchRun + `rerun_of_run_id` (new owner intent) |
| Manual recovery | Explicit owner decision — not silent resurrection |
| Resume | Only with proven safe checkpoint; else retry attempt / rerun / manual recovery |
| Revision | New **Package version** (not automatic new run) |
| Succeeded + unapproved candidate | Allowed |
| Failed/interrupted + partial candidate | Allowed (`result_kind=partial`) |
| Pending approval | **Derived** (artifact awaiting ApprovalRecord) — **not** a run status |
| Approval / stale / published | **Not** run statuses |

Canonical run statuses (Fabric): `queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted`.

**Forbidden:** covertly “resurrecting” a terminal run into `running`.

---

## 4. Approval boundaries (OD-LA-03 = A)

### Single package approval

**`launch_package_approval`** (one per Package version) covers the whole Approved Launch Package:

- CampaignFrame collection  
- OfferArtifact references  
- budget **section**  
- ContentRequests  
- conditional VisualRequests  
- PublicationPlan  
- assumptions / limitations  

**No** per-section approvals for CampaignFrame / Offer / Requests in MVP.

### Separate domain approvals (frozen / retained)

| Approval | When |
|----------|------|
| `content_approval` | Content path uses ContentAsset |
| `visual_approval` | Visual used |
| `publication_package_approval` | Publication path |
| `external_execution_approval` | Real send / paid external |
| `budget_acknowledgement` | Paid external when unknown/limited |

Package approval **never** implies external send. No approval-per-LC-unit explosion.

---

## 5. Handoff + publication target (OD-LA-08 = A)

```
Approved Strategy → LaunchInputSnapshot → LaunchRun
  → LaunchCandidate → ApprovedLaunchPackage
  → ContentRequest ∥ VisualRequest (optional)
  → ContentAsset / VisualAsset (executors)
  → PublicationPlan (intent, in Package)
  → PublicationPackage (Publication selects assets)
  → PackageJob                    ← canonical send path (code-stack B)
  → Delivery / DeliveryEvidence
  → OutcomeRecord
```

**Canonical target for Launch Runtime:**  
`PublicationPackage → PackageJob → Delivery → DeliveryEvidence`.

**Legacy:** `PublicationJob` (code-stack A) = temporary migration source — retained, **not** canonical, **not** a second parallel canonical send path. One semantic external action → one fingerprint / idempotency boundary. No duplicate semantic publication.

Publication (**owner-guided**) selects concrete approved assets **within** Package requirements. Launch does not create PublicationPackage.

**Runtime blocker (not Architecture freeze):** Launch Runtime cannot be owner-frozen until dual-stack migration + deduplication tests pass.

---

## 6. Multiplicity / versioning / restore

| Axis | Rule |
|------|------|
| CampaignFrame | 1 LaunchRun → **1..N** (MVP UI **default one**; OD-LA-05 = A; never “exactly one forever”) |
| OfferArtifact | 1 CampaignFrame → 1..N (selected offer for request/plan) |
| ContentRequest | 1..N; pinned to Package version |
| PublicationPackage | 1 LaunchRun → N (Publication-owned) |
| Package pointers | `latest_created` · `current_candidate` · `current_approved` (Fabric) |
| Restore | Persisted domain state — not browser storage (see Lifecycle) |

---

## 7. Stale / invalidation (Launch-specific)

| Trigger | Effect |
|---------|--------|
| Strategy superseded | Package `stale_*` per dependency rules |
| CampaignFrame / Offer change | New Package version; dependent requests stale |
| ContentRequest change | Dependent ContentAsset may be stale_viewable |
| PublicationPlan change | Dependent PublicationPackage stale_blocking for new handoff |
| Budget ack expired | Blocks paid external only |
| Explicit invalidation | Actor/reason/timestamp; history kept; no cascade delete |
| In-flight after Package v2 | See Lifecycle OD-LA-06 — child may complete; asset stale vs v2 |

Completed external history is **never** undone by Package invalidation (EM/Fabric).

---

## 8. Export / ownership (OD-LA-09 = A)

Export **approved Package version only**:

| Format | Role |
|--------|------|
| **Markdown** | Customer-readable, structured |
| **JSON** | Machine-readable: artifact/version metadata · Strategy pin · CampaignFrames · OfferArtifacts · budget section · requests · PublicationPlan · assumptions/limitations · approval metadata |

ACL: tenant/project. **No** secrets / internal diagnostics in export.  
**Out of MVP:** PDF / DOCX / Slides.

Ownership: tenant/project bound · cross-project and cross-tenant handoff **denied by default**.

---

## 9. BusinessCampaign boundary (OD-LA-02 = B)

**Partial reuse via adapter only.** Not canonical. No 1:1 mapping to CampaignFrame.

Reusable **candidates** (only after field-level compatibility proof): project binding · objective · audience references · selected operational metrics · publication relationships where valid.

**Not** reusable automatically: lifecycle · status model · ownership · CampaignFrame identity · Strategy/Package pinning · approvals · artifact lineage.

Incompatible lifecycle/ownership remain **legacy**. Final migration plan = **Launch Runtime** task (deferred).

---

## 10. Explicit non-goals

Physical tables · SDK · queues · brokers · DSL · workflow engine · UI layout · IA/Registry edits · Content/Visual/Publication Architecture packs · Launch Runtime start · CWF code changes · BudgetArtifact in MVP · declaring BusinessCampaign canonical · dual canonical publish stacks.

---

## Appendix — Normative inheritance

Domain Model invariants 1–40 · EM · Fabric · PRODUCT-02/03. Re-opening any listed frozen invariant → **STOP → OWNER DECISION**.

**OD-LA-01…10** recorded in `PRODUCT-04-LAUNCH-AUDIT-AND-FREEZE.md`.

---

## Freeze applied (PRODUCT-04-LAUNCH-ARCHITECTURE-FREEZE-01)

| Field | Value |
|-------|-------|
| Launch Architecture | **OWNER-FROZEN** (2026-08-02) |
| **`owner_freeze`** | **OWNER-FROZEN** |
| Pack docs | Architecture · Lifecycle · Catalog · Artifact Flow · Journey · MVP Cut · Audit (normative via this freeze) |
| Content Architecture | **NOT STARTED** |
| Launch Runtime | **NOT STARTED** |
| Next priority | **NOT SET** |
