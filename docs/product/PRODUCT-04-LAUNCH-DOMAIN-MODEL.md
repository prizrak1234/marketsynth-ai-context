# PRODUCT-04 — Launch Domain Model

> **Task:** PRODUCT-04-LAUNCH-DOMAIN-MODEL-01 · **Patch:** PRODUCT-04-LAUNCH-DOMAIN-MODEL-PATCH-01  
> **Title:** Marketsynth Launch Domain Model  
> **Type:** Docs-only · semantic domain model  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **OD-LDM-01…08:** **OWNER-APPROVED** (2026-08-02)  
> **Basis:** OD-LDM-01…08 applied · P0-LDM-01 closed · freeze-blocking P1 closed · consistency validation PASS · reviewers 5/5 PASS · code/runtime/research unchanged  
> **Audit:** `PRODUCT-04-LAUNCH-DOMAIN-MODEL-AUDIT.md` · PATCH validation §17 · freeze §18  
> **Inherits (OWNER-FROZEN — do not reopen):** PRODUCT-02 · PRODUCT-03 · PRODUCT-04 Execution Model · PRODUCT-04 Execution Fabric  
> **Does not:** auto-start Launch Architecture · Lifecycle pack · Runtime · API · UI · code · Registry edits · Research · rewrite P02/P03/EM/Fabric freeze text · new foundation

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-04 Launch Domain Model
basis: OD-LDM-01…08 applied; P0-LDM-01 closed; freeze-blocking P1 closed; consistency validation PASS; reviewers 5/5 PASS; code/runtime/research unchanged
```

### Frozen invariants (normative)

1. Launch — project-stage capability.  
2. Primary Launch deliverable — Approved Launch Package.  
3. Approved Launch Package is a requirements-first artifact.  
4. Package is approved before downstream Content/Visual assets are created.  
5. Approved Package is immutable.  
6. After assets appear, Package is not back-filled with their IDs.  
7. Requirement changes create a new Package version.  
8. Package contains a pinned Approved Strategy version.  
9. Package contains at least one CampaignFrame.  
10. Package contains at least one OfferArtifact.  
11. Package contains budget state/envelope/constraints.  
12. Package contains a required ContentRequest.  
13. VisualRequest is conditional.  
14. Package contains a Publication Plan.  
15. Package contains assumptions, limitations, approvals, and measurement criteria.  
16. ContentAsset does not belong to Launch Package.  
17. VisualAsset does not belong to Launch Package.  
18. PublicationPackage does not belong to Launch.  
19. PublicationJob, DeliveryEvidence, and OutcomeRecord are not part of Package.  
20. Publication Plan belongs to Launch.  
21. PublicationPackage belongs to Publication.  
22. Publication selects concrete approved assets within Launch requirements.  
23. Content belongs to the Content capability.  
24. Visual assets belong to the Visual capability.  
25. OutcomeRecord belongs to Outcome Capture.  
26. Content is required for the MVP Launch path.  
27. Visual is required only when channel/format requires it.  
28. Content-only path is allowed when the Package permits it.  
29. One LaunchRun may have 1..N CampaignFrame.  
30. One CampaignFrame may have 1..N OfferArtifact.  
31. OfferArtifact ≠ Strategy Offer Structure.  
32. OfferArtifact ≠ ContentAsset.  
33. Unknown budget does not block Package approval.  
34. Unknown budget blocks paid external execution without limit/acknowledgement.  
35. Launch Domain MVP completes at Approved Launch Package.  
36. Downstream execution produces assets, PublicationPackage, and DeliveryEvidence.  
37. Commercial MVP E2E must prove ≥1 real publication path.  
38. Launch completion ≠ Publication completion.  
39. Launch Domain Model does not define lifecycle/runtime/API/UI.  
40. After Domain Model freeze, the next stage is Launch Architecture only.

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Accept Launch Domain Model as OWNER-FROZEN | Start Launch Architecture pack automatically |
| Lock invariants 1–40 for Launch Architecture | Start Launch Runtime / Strategy Runtime / Research |
| Authorize applied Launch Architecture against this semantics | Rewrite PRODUCT-02/03/EM/Fabric · edit Registry · change code |
| Close domain prelude before Architecture | Re-decide what Launch/Package/ownership/MVP mean |

**Deferred:** version supersession for in-flight requests · BusinessCampaign compatibility · LaunchRun lifecycle · Publication ownership audit · dual publication stack audit  

**Next priority:** **NOT SET** (owner chooses separately; logical next = formal kickoff PRODUCT-04-LAUNCH-ARCHITECTURE-01)

**Forbidden to re-decide in Launch Architecture:** what Launch is · Package BOM · when Package is approved · Content/Visual/Publication ownership · where Launch ends · Domain MVP vs Commercial MVP E2E.

---

## 0. One question

> **What is Launch in Marketsynth?**

Meaning, deliverable, ownership, boundaries, handoff spine, MVP cut — **not** how Launch runs, which screens exist, or which tables persist.

---

## 1. Definition

### 1.1 What Launch is

**Launch** is the **project-stage commercial capability** (`project.launch`) that turns an **Approved Strategy** into an **Approved Launch Package** (requirements-first commercial plan) and **issues requests / starts** downstream Content, Visuals, and Publication capability runs — without performing their work and without executing external channel actions.

Canonical inheritance (Execution Model OD-EM-01):

> Launch is one project-stage capability with its own repeatable CapabilityRun (`LaunchRun`).  
> A LaunchRun accepts a Strategy-pinned input, produces versioned Launch Package candidates, and orchestrates downstream Content / Visuals / Publication runs.  
> **Approved Launch Package** is the versioned result artifact of a LaunchRun — not the run itself.

### 1.2 Why Launch exists

After Strategy answers *whom / what / why / fences / direction*, the customer needs a **governed execution plan**: offer, campaign context, budget posture, content/visual **asks**, and publication **intent** — version-pinned and owner-approved.

Launch sells **managed execution of approved commercial decisions** — not “AI posted something,” not Strategy rewrite, not a content factory alone.

### 1.3 Why Launch is a Project capability — not a product

Lives inside Project spine (PRODUCT-02) · customers buy Project-path outcomes · repeatable LaunchRuns · Registry = availability only, **not** authorization.

Launch is **not:** separate product · autonomous agent · “publish” button · mandatory external send · Analytics · CRM/HR/Finance.

---

## 2. Commercial deliverable

### 2.1 Single primary deliverable

**Approved Launch Package** = the **only** primary commercial deliverable of Launch.

| Is | Is not |
|----|--------|
| Versioned, owner-approved **requirements-first** commercial SKU | LaunchRun status |
| Immutable after `launch_package_approval` | Mutable binder of asset IDs |
| May exist **without** created assets or external publication | PublicationPackage |
| Customer-readable + machine-readable execution **plan** | ContentAsset / VisualAsset |
| Head pointer for downstream **requests** | BusinessCampaign product · DeliveryEvidence · OutcomeRecord |

`LaunchCandidate` = draft / unapproved Package version.  
`LaunchRun` = CapabilityRun that produces candidates — **not** the SKU.

### 2.2 Paid value (what the client gets)

1. Strategy-pinned executable plan a team can run manually or via Marketsynth.  
2. CampaignFrame(s) + Offer Artifact(s) with selected offer for asks/plan.  
3. Budget state (known/unknown), envelope/constraints, paid-execution posture.  
4. ContentRequest (+ optional VisualRequest with explicit `visual_required`).  
5. Publication **Plan** (intent — not publish-ready payload).  
6. Measurement criteria, assumptions, limitations, approvals, next action.

**Not included:** published posts, DeliveryEvidence, analytics dashboards, rewritten Strategy, concrete creatives.

### 2.3 Bad Package (verifiable)

A Package is **not** commercially acceptable if it lacks any of: Strategy pin · ≥1 CampaignFrame · ≥1 Offer Artifact · Content requirements · Publication Plan · budget state · assumptions/limitations · approval path.

Also bad: invents assets · implies external send · duplicates Strategy as Offer Artifact · hides unknowns.

### 2.4 Three contracts (inherited — not redefined)

| Contract | Meaning | Launch Domain role |
|----------|---------|-------------------|
| **A** Launch Package completion | `ApprovedLaunchPackage` + `launch_package_approval` | **Launch Domain completion** |
| **B** Publication execution | Job + DeliveryEvidence (+ external id when available) | Downstream / Publication |
| **C** Commercial MVP E2E | Product can complete ≥1 real publish path | Product DoD — **not** Launch Domain completion |

A LaunchRun **may** stop at **A** without **B**. Product first-payment proof still requires path to **B** (CWF.1 / FINISH-01). Domain Model does **not** weaken product E2E DoD.

---

## 3. Package BOM (OD-LDM-01)

Semantics only — **no** field schemas. BOM classes are domain semantics, not an Artifact Flow pack.

### 3.1 Required

| Element | Meaning |
|---------|---------|
| Approved Strategy version pin | Immutable reference authorizing this Package |
| ≥1 CampaignFrame | Execution context(s) inside Launch |
| ≥1 Offer Artifact | Executable offer(s); ≠ Strategy Offer Structure; ≠ ContentAsset |
| Budget state / envelope / constraints | known\|unknown + range if known + spend constraints + `paid_execution_allowed` posture |
| ContentRequest | Required ask for MVP Launch path |
| Publication Plan | Launch-owned publish **intent** (may be none/deferred) |
| Measurement criteria | Inherited/adapted — honesty bar, not Analytics |
| Assumptions / limitations | Honest gaps |
| Approvals / approval refs | At least Package approval path |
| Next action | Explicit next step after this Package |

### 3.2 Conditional

| Element | When |
|---------|------|
| VisualRequest | When `visual_required = yes` (channel/format needs visual) |
| Multiple CampaignFrames | Separate segments / channels / hypotheses |
| Multiple Offer Artifacts | Variants under a frame; one **selected** offer for ContentRequest / Publication Plan |
| `budget_acknowledgement` | Before **paid** external execution when budget unknown / limited |

### 3.3 Forbidden inside Package

| Forbidden | Owner instead |
|-----------|---------------|
| ContentAsset | Content |
| VisualAsset | Visuals |
| PublicationPackage | Publication |
| PublicationJob | Publication |
| DeliveryEvidence | Publication / evidence |
| OutcomeRecord | Outcome Capture |

**No** approved asset IDs may be added to a Package after approval. Downstream artifacts may cite Package version (lineage); Package does **not** mutate to list asset IDs.

### 3.4 Immutability

After `launch_package_approval`, Package is **immutable**. Any requirement change → **new Package version** (new approval).

---

## 4. Canonical order (OD-LDM-02)

```
Approved Strategy
  → Launch Candidate
  → Approved Launch Package          ← Launch Domain completion (A)
  → Content / Visual execution       ← downstream
  → Publication Package              ← Publication-owned
  → external execution               ← contract B
  → Outcome                          ← project-level
```

Package is approved **before** Content/Visual assets exist.  
After assets appear, Package is **not** rewritten and **not** back-filled with asset IDs.

---

## 5. Content / Visual (OD-LDM-03)

| Rule | |
|------|--|
| ContentRequest | **Required** for MVP Launch path |
| VisualRequest | **Conditional** |
| Package must state | `visual_required` = yes/no · business/channel reason · whether Content-only path is allowed · what blocks Publication handoff |

If Package allows Content-only publication, Visual failure/absence **does not** block that path (Fabric optional-join).

---

## 6. Domain boundaries & ownership

| Domain | Owns / may | Must not |
|--------|------------|----------|
| **Strategy** | Whom/what/why; Offer **Structure**; fences; criteria | Budget ops; creatives; publish jobs |
| **Launch** | Package; CampaignFrame; Offer Artifact; budget envelope; Content/Visual **requests**; Publication **Plan**; Strategy interpretation for execution | Create assets; create PublicationPackage; send; own OutcomeRecord |
| **Content** | ContentAsset | Choose Strategy objective; auto-publish |
| **Visuals** | VisualAsset | Define messaging; mandatory every MVP Package |
| **Publication** | PublicationPackage · PublicationJob · DeliveryEvidence; **owner-guided** selection of concrete approved assets under Package pins | Rewrite Strategy; set Project `published=true` as sole model |
| **Outcome Capture** | OutcomeRecord (evidence-linked) | Launch executor; full Analytics |

### 6.1 Ownership tree

```
project.launch
├── CampaignFrame (1..N)
├── Offer Artifact (1..N per frame; selected offer for asks/plan)
├── Budget envelope / state
├── ContentRequest (required MVP)
├── VisualRequest (conditional)
├── Publication Plan
└── Approved Launch Package
```

Downstream (not Launch-owned): ContentAsset · VisualAsset · PublicationPackage · PublicationJob · DeliveryEvidence · OutcomeRecord.

**No overlaps** between Launch Package contents and downstream owned payloads.

---

## 7. Publication Plan vs Publication Package (OD-LDM-04)

| | **Publication Plan** (Launch) | **Publication Package** (Publication) |
|--|------------------------------|----------------------------------------|
| Owner | Launch | Publication |
| Contains | Channels · sequence · timing window · asset **requirements** · constraints · approval conditions · measurement criteria | Concrete approved ContentAsset(s) · concrete approved VisualAsset(s) · channel/destination config · publish-ready payload · version · publication approval |
| Created by | Launch (inside/with Package) | Publication capability |
| Launch may | Author Plan | **Must not** create PublicationPackage |

Publication (**owner-guided**) selects concrete assets **within** Approved Launch Package requirements. Launch does not assemble publish-ready payload.

---

## 8. Multiplicity

### 8.1 CampaignFrame (OD-LDM-05)

`1 LaunchRun → 1..N CampaignFrame`

MVP default may be **one** frame. Model must **not** freeze “exactly one.” Extra frames for segment / channel / hypothesis.

CampaignFrame is **not** a separate product. BusinessCampaign = reuse candidate only (EM deferred).

### 8.2 Offer Artifact (OD-LDM-07)

`1 CampaignFrame → 1..N OfferArtifact`

MVP: ≥1 **canonical** offer; variants optional; **selected** offer linked to ContentRequest and/or Publication Plan.

Offer Artifact ≠ ContentAsset ≠ Strategy Offer Structure ≠ Publication payload.

---

## 9. Budget (OD-LDM-06)

Package approval does **not** require an exact monetary amount.

**Required budget semantics on Package:**

- known / unknown  
- envelope/range if available  
- spend constraints  
- `paid_execution_allowed` / blocked posture  
- unresolved assumptions  

**Unknown budget:** does **not** block Package approval.  
**Does** block **paid** external execution until limit or typed `budget_acknowledgement`.

No Billing system in this model.

---

## 10. Handoff spine (semantic only)

```
Research → Strategy → Launch Package → Content ∥ Visual requests
  → approved assets → Publication Package → external execution → Outcome
```

| Step | Creates | Completes when |
|------|---------|----------------|
| Strategy | Approved Strategy Package | Strategy approval + launch eligibility |
| **Launch** | Candidate → **Approved Launch Package**; requests; Plan | **Package approval (A)** — not send |
| Content / Visuals | Assets | Asset approvals (Visual if required) |
| Publication | PublicationPackage · Job · DeliveryEvidence | External success when path pursued (**B**) |
| Outcome | OutcomeRecord | Evidence + observation (not Launch terminal) |

Domain Model does **not** define lifecycle states, retry, queues, or orchestration implementation — only ownership and boundaries (Fabric/Architecture elsewhere).

---

## 11. Where Launch ends

Launch ends at **Approved Launch Package** (contract **A**).

Launch does **not** include: channel send, paid provider mutation, DeliveryEvidence assertion, OutcomeRecord ownership.

Publication remains a **separate** contract (**B**). Package approval **never** implies external send.

---

## 12. MVP contracts (OD-LDM-08)

| Layer | Completes at | Includes | Excludes |
|-------|--------------|----------|----------|
| **Launch Domain MVP** | Approved Launch Package (**A**) | BOM §3 required (+ conditional as applicable) | Assets · PublicationPackage · Job · DeliveryEvidence · OutcomeRecord · external send |
| **Downstream execution** | Assets + PublicationPackage/Job as pursued | ContentAsset · optional VisualAsset · PublicationPackage · Job · DeliveryEvidence | Redefining Launch completion |
| **Commercial MVP E2E** | ≥1 real path to **B** | Strategy → Package → Content → optional Visual → Publication → external evidence | Claiming every LaunchRun must publish |

CWF.1 / FINISH-01 product publish DoD remains in force for **product** E2E. Transitional CWF Launch Pack / Offer paths are **adapters**, not canonical Launch Domain (§8.3 honesty retained).

---

## 13. Explicit non-goals

Lifecycle · state machine · Capability Catalog · Artifact Flow pack · Owner Journey · Runtime · queues · brokers · orchestration engines · schedulers · API · events · UI · JSON schemas · DB models · Billing · reopen EM A/B/C · Fabric rewrite · P02/P03 freeze edits · Launch Architecture seven-doc pack · new general foundation.

---

## 14. Owner decisions applied (OD-LDM-01…08)

| ID | Decision | Status |
|----|----------|--------|
| OD-LDM-01 | Requirements-first Package; no assets inside | **OWNER-APPROVED A** |
| OD-LDM-02 | Approve Package before assets; no back-fill of asset IDs | **OWNER-APPROVED** |
| OD-LDM-03 | ContentRequest required; Visual conditional + `visual_required` | **OWNER-APPROVED** |
| OD-LDM-04 | Plan ≠ Package; Publication selects assets | **OWNER-APPROVED** |
| OD-LDM-05 | CampaignFrame 1..N; MVP default one OK | **OWNER-APPROVED** |
| OD-LDM-06 | Exact sum not required; unknown blocks paid exec only | **OWNER-APPROVED** |
| OD-LDM-07 | Offer 1..N per frame; selected offer for asks/plan | **OWNER-APPROVED** |
| OD-LDM-08 | Domain MVP = A; E2E = C; send not in Domain completion | **OWNER-APPROVED** |

---

## 15. Finding closure

| ID | Status |
|----|--------|
| P0-LDM-01 | **CLOSED** — no asset refs on Package; PublicationPackage binds assets |
| P1-LDM-01 | **CLOSED** — completion = Package approval only (no “handoff-ready” asset gate) |
| P1-LDM-02 | **CLOSED** — Publication selects concrete assets under Package pins |
| P1-LDM-03 | **CLOSED** — ContentRequest required; Visual conditional |
| P1-LDM-04 | **CLOSED** — Domain MVP ≠ Commercial MVP E2E triad explicit |
| P2-LDM-01 | **CLOSED** — BOM = semantic classes only |
| P2-LDM-02 | **CLOSED** — “issues requests / starts” wording |
| P2-LDM-03 | Deferred hygiene (catalog/Journey naming) — not Domain freeze blocker |

---

## 16. Freeze record (applied)

| Field | Value |
|-------|-------|
| Patch task | PRODUCT-04-LAUNCH-DOMAIN-MODEL-PATCH-01 = **docs_verified** |
| Launch Domain Model | **OWNER-FROZEN** (2026-08-02) |
| **`owner_freeze`** | **OWNER-FROZEN** |
| Launch Architecture | **NOT STARTED** |
| Next priority | **NOT SET** |

### Owner freeze checklist

1. ☑ OD-LDM-01…08 accepted  
2. ☑ P0-LDM-01 closed  
3. ☑ Freeze-blocking P1 closed  
4. ☑ Package requirements-only + immutable  
5. ☑ Publication Plan ≠ Publication Package  
6. ☑ Multiplicities explicit  
7. ☑ MVP contracts separated  
8. ☑ Owner message: Domain Model = **OWNER-FROZEN** (2026-08-02)  
9. ☐ PRODUCT-04-LAUNCH-ARCHITECTURE-01 — only after separate kickoff; next priority currently **NOT SET**  

---

## Appendix A — Normative sources

PRODUCT-02 / 03 / 04-EM / 04-Fabric OWNER-FROZEN · CWF.1 / FINISH-01 (contract **C** product DoD) · Capability Registry (availability only)

## Appendix B — Hard boundary after freeze

After Domain Model **OWNER-FROZEN**: the only permitted next architecture program is applied `PRODUCT-04-LAUNCH-ARCHITECTURE-01` (owner kickoff required; next priority currently **NOT SET**).  
No new foundation or domain-prelude without proven P0.  
Lifecycle · Capability Catalog · Artifact Flow · Owner Journey · MVP implementation sequence belong to Launch Architecture.  
Re-opening Domain Model invariants 1–40, EM, Fabric, or contracts A/B/C is **forbidden**.
