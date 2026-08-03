# PRODUCT-04 — Capability Pattern

> **Task:** PRODUCT-04-CAPABILITY-PATTERN-FREEZE-01 (base: PRODUCT-04-CAPABILITY-PATTERN-01)  
> **Title:** Marketsynth Capability Implementation Pattern  
> **Type:** Docs-only operational template (not a foundation layer)  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **Basis:** Doc created · frozen foundations not reopened · not a foundation layer · test oracles present · reviewers 5/5 PASS · code/Runtime unchanged · no open owner decisions  
> **Inherits (OWNER-FROZEN — do not reopen):** PRODUCT-02 · PRODUCT-03 · PRODUCT-04 Execution Model · PRODUCT-04 Execution Fabric · PRODUCT-04 Launch Domain Model · PRODUCT-04 Launch Architecture  
> **Worked example:** `project.launch` (Launch Architecture pack)  
> **Does not:** new foundation · new product invariants · Runtime · code · UI layout · API · migrations · Registry edits · Research · PRODUCT-05 auto-start · rewrite frozen freeze text · reopen Launch OD-LA

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-04 Capability Pattern
basis: PATTERN-01 docs_verified; reviewers 5/5 PASS; no open OD; no foundation creep; FREEZE-01
```

### Frozen Pattern rules (normative — operational form)

1. Pattern is the **normative structural template** for capability architecture packs.  
2. Pattern is **not** a separate capability.  
3. Pattern is **not** a Runtime framework.  
4. Pattern does **not** create new product invariants.  
5. Domain-specific decisions remain in the corresponding capability packs.  
6. Each new capability architecture **must** describe: purpose and customer value; inputs and immutable snapshots; CapabilityRun; produced artifacts and ownership; approvals; versioning; stale/invalidation; retry/rerun/resume; restore/recovery; handoff; evidence/outcome; export; security boundaries; UI placement; MVP cut; Runtime boundary; objective test oracles.  
7. Pattern does **not** authorize copying Launch-specific contracts into other capabilities.  
8. Pattern does **not** replace PRODUCT-02, PRODUCT-03, Execution Model, or Execution Fabric.  
9. Pattern is **not** justification for a general rewrite of existing Runtime.  
10. Deviation from Pattern is allowed **only** with a documented domain reason.  
11. New foundation layers before PRODUCT-05 are **forbidden** without proven P0.  
12. Freezing Pattern does **not** auto-start Content Runtime (or PRODUCT-05).

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Lock Pattern as OWNER-FROZEN operational form | Start PRODUCT-05 Content Architecture automatically |
| Require P05–P07 packs to fill Pattern checklist | Create new EM/Fabric/Domain invariants |
| Preserve Launch as worked example only | Copy Launch-specific contracts into Content/Visual/Publication |
| Close Pattern prelude before applied Content Architecture | Start any Runtime · rewrite code · reopen Launch OD-LA |

**Next priority:** **NOT SET**.

---

## 0. Framing

This document is the **mandatory form** for applied capability architecture packs (Content, Visual, Publication, and later siblings).

| This document **is** | This document **is not** |
|----------------------|--------------------------|
| Operational reference template | Seventh foundation layer |
| Anti-drift checklist for P05–P07 | Re-definition of Fabric / EM / Launch |
| Form every capability pack must fill | Workflow engine / scheduler / broker / DSL |
| Binding of Fabric semantics to pack structure | Physical schema or Runtime design |

**Rule:** Future capability packs **instantiate** this form. They may add **domain-only** fields and rules. They must **not** invent parallel run/approval/restore/evidence models.

```
Capability
  → CapabilityRun
  → InputSnapshot
  → Domain Artifact(s)
  → ApprovalRecord(s)
  → Handoff
  → Restore composition
  → DeliveryEvidence / ledger   (if external)
  → OutcomeRecord               (project-level, when evidence)
```

Normative sources: Fabric invariants 1–40 · EM invariants 1–26 · Launch Architecture invariants 1–26 · Launch Domain Model 1–40 · PRODUCT-02/03.

---

## 1. Purpose

1. Guarantee that Content / Visual / Publication architecture packs answer the **same structural questions**.  
2. Keep Fabric as the semantic contract; this pattern as the **documentation shape**.  
3. Use Launch as the only complete applied worked example so Cursor does not invent a second style.  
4. Separate **Domain MVP**, **Commercial E2E**, and **Runtime** without redefining EM contracts A/B/C.

---

## 2. Inputs

Every capability pack must declare:

| Input class | Requirement |
|-------------|-------------|
| Tenant / project binding | Mandatory; cross-tenant forbidden; cross-project handoff denied by default (Fabric) |
| Upstream approved pins | Version-pinned artifacts from prior capability (or eligibility gate) |
| InputSnapshot contents | Immutable for the run; no dynamic “latest project state” |
| Eligibility / entry | Domain gate (e.g. Strategy `launch_eligible`) |
| Constraints / assumptions | Explicit; owned by snapshot or candidate |
| Capability Registry | **Availability / UX exposure only** — not authorization |

**Launch worked example:** `LaunchInputSnapshot` pinned to Approved Strategy Package version; tenant/project; owner decision refs; budget posture inputs; assumptions.

---

## 3. Outputs

Separate three output classes — packs must not collapse them:

| Class | Owner | Examples |
|-------|-------|----------|
| **Domain deliverable** | Capability | Approved Launch Package; future ContentAsset; PublicationPackage |
| **Execution evidence** | Execution / Publication path | DeliveryEvidence / ledger after external action |
| **Outcome** | Project Outcome Capture | OutcomeRecord linked to evidence |

**Launch worked example:** Primary deliverable = Approved Launch Package (requirements-first). ContentAsset / VisualAsset / PublicationPackage / PackageJob / DeliveryEvidence / OutcomeRecord are **not** Launch Package contents.

---

## 4. CapabilityRun

Specialize Fabric CapabilityRun; do not invent a second lifecycle.

| Topic | Pattern rule |
|-------|----------------|
| Statuses | Only: `queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted` |
| Not run statuses | See Fabric §7 full exclusion list: `waiting_for_approval` · `partial` · `stale` · `approved` · `published` · `blocked` (and any approval/stale/published alias) |
| Pending approval | **Derived** (artifact + missing decided ApprovalRecord) |
| Succeeded | May leave **unapproved** candidate |
| Failed / interrupted | May preserve `result_kind=partial` |
| Interrupted | **Terminal** by default; never silently reopen as `running` |
| Identity | `run_id` + InputSnapshot; hosts **attempts** |

**Launch worked example:** `LaunchRun` = CapabilityRun with `capability_id = project.launch`. LaunchRun ≠ Package.

---

## 5. Snapshots

| Object | Pattern rule |
|--------|----------------|
| **InputSnapshot** | Required; immutable; version-pinned; tenant/project-bound |
| Dynamic latest | **Forbidden** |
| **HandoffSnapshot** | Conditional logical boundary; may equal next run’s InputSnapshot; not a mandatory universal table |
| Physical form | Runtime / domain pack decision — not this template |

**Launch worked example:** `LaunchInputSnapshot`; handoff to Content/Visual/Publication via requests + PublicationPlan pins (logical).

---

## 6. Artifact ownership

| Rule | |
|------|--|
| Producer / consumer | Explicit per artifact |
| Approved artifact | Immutable; edit → **new version** |
| Pointers | `latest_created` · `current_candidate` · `current_approved` (never one ambiguous “current”) |
| Back-fill | Forbidden after approval (e.g. no asset IDs into Launch Package) |
| History | Not deleted / rewritten |

**Launch worked example:** CampaignFrame · OfferArtifact · budget **section** · ContentRequest · VisualRequest · PublicationPlan owned by Launch. ContentAsset / VisualAsset / PublicationPackage owned downstream.

---

## 7. Approval points

| Pattern | When |
|---------|------|
| **Single deliverable gate** | One typed approval covers the capability’s primary package/deliverable (Launch: `launch_package_approval`) |
| **Path-dependent gates** | Content / visual / publication package / external execution / budget ack as required by path |
| Version pin | Approval does **not** transfer to a new version |
| Actor | Server-attested |
| External send | **Never** implied by package/deliverable approval |

**Forbidden:** approval-per-micro-unit explosion. Any deviation from single deliverable gate + path-dependent gates requires an **explicit owner decision** (OD-style), not a silent domain invention.

**Launch worked example:** OD-LA-03 — single package approval covers frames, offers, budget section, requests, PublicationPlan, assumptions/limitations. Separate: content · visual · publication_package · external_execution · budget_acknowledgement.

---

## 8. Restore

UI/state composition from **persisted** domain objects — browser storage is **not** SoT.

```
Project open
  → active/recent CapabilityRuns
  → latest_created / current_candidate / current_approved
  → derived stale
  → pending ApprovalRecords (derived)
  → child runs (each labeled with pinned upstream version)
  → external jobs / ledger / ambiguous flags
  → derived next actions
```

**Launch worked example:** Restore includes LaunchRun heads, Package pointers, child Content/Visual runs with **pinned Package version**, PublicationPlan/Package/PackageJob state, external ledger.

---

## 9. Retry / Rerun / Resume / Revision

Fabric carve-out — restated, not redefined:

| Term | Meaning |
|------|---------|
| **Retry** | New **attempt** of the **same** run (`run_id` + InputSnapshot). Valid pre-terminal (`queued`/`running`), **plus** interrupted carve-out per Fabric. Does **not** reopen other terminals as `running`. |
| **Rerun** | **New** CapabilityRun + `rerun_of_run_id`; new or re-pinned snapshot. After terminal failed/cancelled (and interrupted when resume not proven). |
| **Resume** | Only with proven safe checkpoint; else rerun / manual recovery. |
| **Revision** | New **artifact version** — not automatically a new run. |

**Forbidden:** covert resurrection of terminal runs; blind continue after ambiguous external side effect.

---

## 10. Handoff

| Rule | |
|------|--|
| Nature | Logical transition to next capability InputSnapshot |
| Domain | Defines required vs optional branches (Fabric join = domain) |
| ACL | Cross-project / cross-tenant handoff **denied by default** |
| Stale | `stale_blocking` blocks new handoff / external until revalidation |

**Launch worked example:** Issues ContentRequest / VisualRequest; exposes PublicationPlan. Does **not** create PublicationPackage. In-flight Package supersession: complete+stale, no auto-cancel (OD-LA-06).

---

## 11. Evidence

When the path includes critical external action:

| Mandatory | |
|-----------|--|
| Explicit external approval | Separate from deliverable approval |
| `external_action_fingerprint` | Fabric |
| `execution_idempotency_key` | Distinct from run-create key |
| Execution ledger + attempt history | Persisted |
| Result class | `confirmed_success` · `confirmed_failure` · `not_started` · `ambiguous` |
| Ambiguous | **No** blind retry; reconcile / human |

**Launch / Publication target:** Canonical path `PublicationPackage → PackageJob → Delivery → DeliveryEvidence` (OD-LA-08). Legacy PublicationJob = migration source, not second canonical send.

---

## 12. Outcome

| Rule | |
|------|--|
| OutcomeRecord | Project-level; links run · evidence · context |
| Not | Capability child artifact · full Analytics |
| Without evidence | Forbidden except explicit manual observation with actor + provenance |

**Launch worked example:** Outcome owned by Outcome Capture; Launch completion ≠ Publication completion ≠ Outcome.

---

## 13. Export

When the capability has an approved commercial deliverable:

| Format | Role |
|--------|------|
| Customer-readable (e.g. Markdown) | Human handoff |
| Machine-readable JSON | Metadata · pins · artifacts · approvals |

Export: approved version only · tenant/project ACL · **no** secrets / internal diagnostics · export ≠ new approval.

**Launch worked example:** OD-LA-09 — Markdown + JSON of approved Package version.

---

## 14. UI placement

| Rule | |
|------|--|
| Container | **Project Command Center** capability panel |
| Not | Separate Workspace micro-product / standalone app |
| This doc | Does **not** design layout, IA routes, or Design System tokens |

**Launch worked example:** Launch panel after Strategy readiness; not a Workspace Launch app.

---

## 15. MVP boundary

Do not conflate (EM / Launch triad — not redefined):

| Layer | Completes at |
|-------|----------------|
| **Domain / Architecture MVP** | Capability’s primary approved deliverable (Launch: Approved Package = A) |
| **Downstream execution** | Assets / jobs as pursued by sibling capabilities |
| **Commercial MVP E2E** | Real path to DeliveryEvidence (B) + product DoD (C) |

Post-MVP must be listed explicitly (no silent catalog expansion).

---

## 16. Runtime boundary

| Architecture pack | Runtime |
|-------------------|---------|
| Defines semantics, ownership, approvals, restore, MVP | Implements persistence, APIs, adapters |
| May recommend R-order | Does not ship queues/brokers/DSL/tables here |
| Freeze ≠ kickoff | Separate owner priority required |

**Launch worked example:** OD-LA-10 R1→R6 (Package-first). Dual-stack migration + dedup tests block Launch Runtime freeze — not this pattern doc.

---

## 17. Test oracles

Every capability architecture pack must attach a **testability matrix**: for each normative contract it introduces or specializes, name an **oracle** (assertable statement) that a future Runtime test can fail or pass without subjective judgment.

| Contract family | Oracle shape (required) |
|-----------------|-------------------------|
| CapabilityRun | Status enum membership; retry preserves `run_id`; rerun creates new `run_id`; interrupt remains terminal |
| InputSnapshot | Immutable; no dynamic latest; pin fields present |
| Artifacts | Approved immutable; pointers distinct; forbidden contents absent |
| Approvals | Version-pinned; deliverable approval ≠ external send |
| Handoff / stale | `stale_blocking` blocks new handoff; cross-project/tenant denied by default |
| Evidence (if any) | Fingerprint + ledger present; ambiguous → no blind retry |
| Restore | Same persisted heads after refresh; child runs labeled with pinned upstream version |
| Export (if any) | Approved version only; ACL; no secrets |

**Acceptance for Appendix A item 17:** pack lists ≥1 oracle per contract family it uses; each oracle names an assertable statement (and, where Runtime fixtures exist, the fixture/state that proves it). Vague DoD (“works correctly”) is **not** an oracle.

**Launch worked example (sample oracles — not exhaustive):** see Launch Architecture Audit testability matrix (oracles 1–26) and Appendix B row below.

---

## 18. Explicit non-goals

New foundation · new global enums · workflow engine · scheduler · broker · DSL · physical schema · CapabilityDefinition backend table as requirement · BusinessCampaign as canonical CampaignFrame · dual canonical publish stacks · code / UI / Registry / Journey edits · auto-start PRODUCT-05 or any Runtime.

---

## Appendix A — Checklist (every future capability pack must answer)

1. Capability id and Command Center placement?  
2. Inputs and InputSnapshot pins?  
3. Primary domain deliverable and forbidden contents?  
4. CapabilityRun specialization (no extra run statuses)?  
5. Artifact ownership map (producer/consumer)?  
6. Approval graph (single gate vs path gates)?  
7. Restore composition?  
8. Retry / rerun / resume / revision rules (Fabric-aligned)?  
9. Handoff to next capability (required/optional branches)?  
10. External evidence rules (if any)?  
11. Outcome linkage (if any)?  
12. Export shape (if commercial deliverable)?  
13. Domain MVP vs E2E vs post-MVP?  
14. Runtime order hint (not kickoff)?  
15. Reuse / legacy / adapter map (**honest** = name every reused/legacy object and state whether it is canonical, partial adapter, or migration-source only)?  
16. Security: tenant/project · ACL · Registry≠authz · approval≠send · server-attested actor · frontend≠authz?  
17. Test oracles for each contract family (§17)?  

---

## Appendix B — Launch worked-example mapping

| Pattern section | Launch instantiation |
|-----------------|----------------------|
| Capability | `project.launch` |
| CapabilityRun | LaunchRun |
| InputSnapshot | LaunchInputSnapshot → Approved Strategy version |
| Primary artifact | ApprovedLaunchPackage (requirements-first) |
| Ownership | Frames · offers · budget section · ContentRequest · VisualRequest · PublicationPlan |
| Downstream | ContentAsset · VisualAsset · PublicationPackage · PackageJob · DeliveryEvidence · OutcomeRecord |
| Approval | `launch_package_approval` (+ path gates) |
| In-flight | OD-LA-06 complete+stale · no auto-cancel |
| Cancel vs revise | OD-LA-07 |
| Publish target | PackageJob canonical · PublicationJob legacy |
| Export | Markdown + JSON |
| Runtime order | R1→R6 |
| Adapter note | BusinessCampaign = partial adapter only (not CampaignFrame); PublicationJob = migration-source only |
| Test oracles | Launch Architecture Audit matrix (e.g. Package immutable; assets not back-filled; retry≠rerun; PackageJob canonical; in-flight complete+stale) |

---

## Appendix C — How Content / Visual / Publication should use this

| Pack | Must fill this form | Must not |
|------|---------------------|----------|
| PRODUCT-05 Content | ContentRun · ContentRequest consumer · ContentAsset ownership · content_approval · restore · MVP | Redefine Fabric run statuses; own PublicationPackage |
| PRODUCT-06 Visual | Conditional VisualRequest · VisualAsset · visual_approval · optional-branch join | Make Visual required globally against Launch Package rules |
| PRODUCT-07 Publication | PublicationPackage · PackageJob path · external approval · evidence · dual-stack migration plan | Declare PublicationJob second canonical send |

**Next after this pattern is OWNER-FROZEN:** owner kickoff for `PRODUCT-05-CONTENT-ARCHITECTURE-01` only — **not** automatic. Current next priority = **NOT SET**.

---

## Appendix D — Normative inheritance

Re-opening Fabric 1–40, EM, Launch Domain 1–40, Launch Architecture 1–26 / OD-LA, or PRODUCT-02/03 freeze text → **STOP → OWNER DECISION**.

This pattern adds **documentation structure only**. Any conflict with frozen sources is a **defect** in this doc, not a license to change frozen layers.

---

## Freeze applied (PRODUCT-04-CAPABILITY-PATTERN-FREEZE-01)

| Field | Value |
|-------|-------|
| Capability Pattern | **OWNER-FROZEN** (2026-08-02) |
| **`owner_freeze`** | **OWNER-FROZEN** |
| Pattern rules | Freeze record **1–12** |
| PRODUCT-05 | **NOT STARTED** |
| Content Runtime | **NOT STARTED** |
| Next priority | **NOT SET** |
