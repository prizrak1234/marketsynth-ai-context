# PRODUCT-04 — Launch Capability Catalog

> **Task:** PRODUCT-04-LAUNCH-ARCHITECTURE-PATCH-01  
> **Owns:** Applied Launch composition units (not separate products/routes)  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-LA-02…05, 07–08 **OWNER-ACCEPTED**  
> **Inherits:** Domain Model · EM · Fabric OWNER-FROZEN

Units are **sections of one Launch capability**, not micro-products. Registry availability remains separate.

---

## LC-01 Launch Input Interpretation

| Field | Value |
|-------|-------|
| Purpose | Bind Approved Strategy into LaunchInputSnapshot |
| Customer value | Correct Strategy pin; no silent “latest” |
| Entry | `launch_eligible` / Strategy package approval |
| Consumed | ApprovedStrategyPackage |
| Produced | LaunchInputSnapshot |
| Blocking | Missing Strategy pin; cross-project; eligibility revoked (any override must be server-attested, tenant/project-scoped, audited — define before Runtime) |
| Exit | Snapshot immutable for this LaunchRun |
| Approval | Upstream Strategy / eligibility sufficient to start |
| Multiplicity | 1 per LaunchRun |
| Invalidation | Strategy revoke/supersede → new snapshot/run |
| Recoverability | Persist snapshot; restore from it |
| MVP | **Required** |
| Acceptance | Snapshot contains Strategy version id; dynamic latest denied |
| Out of scope | Strategy rewrite |

---

## LC-02 CampaignFrame Definition

| Field | Value |
|-------|-------|
| Purpose | Define execution context(s) inside Launch |
| Customer value | Clear segment/objective without ops CRM |
| Entry | LaunchRun with snapshot |
| Consumed | Snapshot · Strategy fences |
| Produced | CampaignFrame (1..N) |
| Blocking | Empty objective/segment |
| Exit | Frame(s) included in Package |
| Approval | Via **single** `launch_package_approval` (OD-LA-03) — no per-frame approval |
| Multiplicity | **1..N** per LaunchRun; MVP UI **default one** (OD-LA-05 = A) |
| Invalidation | Frame edit → new Package version |
| MVP | **Required (≥1)** |
| Acceptance | ≥1 frame; **≠ BusinessCampaign**; no 1:1 mapping (OD-LA-02) |
| Out of scope | Full media plan · Analytics entity · BusinessCampaign product |

**Fields (semantic):** objective · target segment · Strategy/Offer refs · channel direction · budget constraints · measurement criteria · assumptions · limitations · scope.

**BusinessCampaign (OD-LA-02 = B):** partial adapter reuse only after compatibility proof; never CampaignFrame identity.

---

## LC-03 Offer Artifact Definition

| Field | Value |
|-------|-------|
| Purpose | Executable offer under frame |
| Customer value | Sellable offer wording/CTA without writing final posts |
| Consumed | Strategy Offer Structure · frame |
| Produced | OfferArtifact (1..N per frame) |
| Blocking | No selected offer for ContentRequest/Plan |
| Approval | Via package (no per-offer approval in MVP) |
| Multiplicity | 1..N; ≥1 canonical MVP |
| MVP | **Required** |
| Acceptance | ≠ Structure · ≠ ContentAsset · selected offer linked |
| Out of scope | Pricing engine |

**Semantic content:** canonical/variant · CTA · channel adaptation · timing/conditions · frame binding · assumptions · constraints.

**Reuse:** Offer Builder → **adapter** (pin to Strategy + Package version).

---

## LC-04 Budget Envelope (OD-LA-04 = A)

| Field | Value |
|-------|-------|
| Purpose | Honesty about spend posture |
| Produced | **Budget section on Package** (not separate BudgetArtifact in MVP) |
| Semantics | known \| unknown · envelope/range · constraints · `paid_execution_allowed` · acknowledgement state · assumptions |
| Blocking for Package | None for unknown |
| Blocking for paid exec | Unknown without limit/ack |
| MVP | **Required semantics as Package section** |
| Acceptance | Section versioned with Package; no standalone BudgetArtifact |
| Out of scope | Billing · payment rails · actual spend (Execution) |

**Post-MVP trigger for separate BudgetArtifact (only if proven need):** independent lifecycle · multiple envelopes · separate approval chains · Finance/Billing integration · cross-campaign allocation.

---

## LC-05 Content Request Definition

| Field | Value |
|-------|-------|
| Purpose | Tell Content what to produce |
| Produced | ContentRequest (no final text) |
| Consumed | Package pins · frame · selected offer |
| Blocking | Missing ContentRequest on MVP Package |
| Multiplicity | 1..N |
| Approval | Covered by package approval for requirements; asset uses `content_approval` |
| Cancellation | OD-LA-07: cancel request version **without** mutating Package if requirements unchanged |
| Revision | New request version; if BOM/requirements change → Package revision first |
| MVP | **Required** |
| Acceptance | Pinned to Package version; audience, messaging constraints, channel, format, objective, CTA, variants, approval expectations, publication requirements, assumptions |
| Out of scope | ContentAsset authorship |

---

## LC-06 Visual Request Definition

| Field | Value |
|-------|-------|
| Purpose | Conditional visual ask |
| Produced | VisualRequest |
| Fields | visual_required · reason · format · dimensions · creative constraints · brand/context · offer/content context · approval expectations · Content-only fallback |
| Cancellation | Same OD-LA-07 rules as Content |
| MVP | **Conditional** |
| Acceptance | If visual_required=no, Content-only path explicit |
| Out of scope | VisualAsset authorship |

---

## LC-07 Publication Plan

| Field | Value |
|-------|-------|
| Purpose | Launch-owned publish **intent** |
| Produced | PublicationPlan (in/with Package) |
| Fields | channels · timing window · sequence · asset requirements · destination expectations · approvals required · measurement · constraints · assumptions |
| MVP | **Required** (value may be none/deferred) |
| Acceptance | ≠ PublicationPackage; covered by package approval |
| Out of scope | Job execution · DeliveryEvidence |

**Handoff target (OD-LA-08):** Publication builds `PublicationPackage → PackageJob → DeliveryEvidence`. Legacy `PublicationJob` not authored here.

---

## LC-08 Launch Package Assembly

| Field | Value |
|-------|-------|
| Purpose | Assemble LaunchCandidate BOM |
| Produced | LaunchCandidate |
| MVP | **Required** |
| Acceptance | BOM matches Domain Model; no assets inside; budget as **section** |
| Out of scope | UI layout |

---

## LC-09 Launch Package Review

| Field | Value |
|-------|-------|
| Purpose | Owner review / approve / reject / revise |
| Produced | ApprovalRecord · new versions |
| MVP | **Required** |
| Acceptance | Single typed `launch_package_approval` covering whole Package (OD-LA-03); actor server-attested |
| Out of scope | External send · per-section approvals |

---

## LC-10 Launch Handoff

| Field | Value |
|-------|-------|
| Purpose | Start Content/Visual runs; expose Plan to Publication |
| Produced | Executor run refs · handoff markers |
| Blocking | stale_blocking Package · missing required requests |
| MVP | **Required** for E2E path; optional stop-at-Package |
| Acceptance | Does not create PublicationPackage; Publication uses **PackageJob** path (OD-LA-08) |
| Out of scope | PackageJob / PublicationJob lifecycle ownership · dual-send |
