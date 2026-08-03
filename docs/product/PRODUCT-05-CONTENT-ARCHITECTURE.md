# PRODUCT-05 — Content Architecture

> **Task:** PRODUCT-05-CONTENT-ARCHITECTURE-FREEZE-01 (base: PATCH-01 · ARCHITECTURE-01)  
> **Title:** Marketsynth Content Capability Architecture  
> **Type:** Docs-only capability architecture (Pattern-compliant)  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **OD-CT-01…08:** **OWNER-APPROVED** (all **A**, 2026-08-02)  
> **Basis:** PATCH-01 completed · OD-CT all A · composite 5/5 PASS · no open freeze blockers · code/Runtime unchanged · FREEZE-01  
> **Inherits (OWNER-FROZEN — do not reopen):** PRODUCT-02 · PRODUCT-03 · EM · Fabric · Launch Domain Model · Launch Architecture · Capability Pattern  
> **Pack:** Lifecycle · Artifact Flow · Owner Journey · MVP Cut · Audit/Freeze  
> **Does not:** Content Runtime · code · UI/API/migrations · new foundation · Asset Framework · Strategy/Launch reopen · Publication Architecture · Visual Architecture · real publish · PRODUCT-06 auto-start

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-05 Content Architecture
basis: PATCH-01 docs_verified; OD-CT-01…08 OWNER-APPROVED all A; soft blockers closed; composite 5/5 PASS; code/Runtime unchanged; FREEZE-01
```

### Frozen invariants (normative — Content Architecture pack)

1. Content = `project.content` capability (Project Command Center — not a Workspace micro-product).  
2. Flow: Approved Launch Package → ContentRequest → ContentRun → Candidate(s) → approved ContentAsset → Publication handoff.  
3. Content does **not** decide ICP · Offer · Campaign objective · budget · channel execution · Strategy pillars.  
4. ContentRequest is **Launch-owned** input; Content must not mutate Package/Request requirements.  
5. ContentAsset is **Content-owned** domain deliverable; typed; versioned.  
6. Content Factory = **adapter-only** under ContentRequest — **never** Architecture-canonical (OD-CT-01).  
7. H2.7 content drafts remain **isolated**; no merge without later proven adapter OD (OD-CT-02).  
8. MVP types = Request-driven; commercial CWF path focuses on **`telegram_post`** (OD-CT-03).  
9. Candidates **1..N** under one Request; UI may default 1–3; variants ≠ A/B platform (OD-CT-04).  
10. Approved ContentAsset body is **immutable**; regenerate = **new candidate** only (OD-CT-05).  
11. Code status enum maps to Pattern via **Runtime adapter** — no Architecture rewrite of enum now (OD-CT-06).  
12. `owner_preview` / recovery-preview = **legacy/dev only**; commercial path = Command Center Content (OD-CT-07).  
13. First Runtime slice (after this freeze, not started): ContentRequest + Package pin → Snapshot/Run → adapter generation → approval → Publication handoff read model (OD-CT-08).  
14. Content does **not** publish; PackageJob remains Publication-owned canonical send.  
15. Content Architecture does **not** produce DeliveryEvidence.  
16. ContentInputSnapshot pins Request/Package versions — no dynamic “latest Strategy.”  
17. Cross-tenant forbidden; cross-project Content handoff **denied**.  
18. Registry ≠ authorization.  
19. No queues / DSL / universal Asset Framework from this pack.  
20. Freezing Content Architecture does **not** auto-start Content Runtime or PRODUCT-06 Visual Architecture.

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Lock Content Architecture pack as OWNER-FROZEN | Start Content Runtime |
| Lock OD-CT-01…08 + invariants 1–20 | Start PRODUCT-06 Visual Architecture automatically |
| Close applied Content architecture before Visual | Rewrite P02/P03/EM/Fabric/Launch/Pattern · edit Registry · change code |
| Record Factory as adapter-only; H2.7 isolated | Merge H2.7 · declare Factory Architecture-canonical |

**Next priority:** **NOT SET**.

---

## Pre-implementation check

| # | Result |
|---|--------|
| 1. Inventory | ContentAsset as-is; Content Factory **adapter-only (OD-CT-01)**; H2.7 **isolated (OD-CT-02)**; ContentRequest missing; CWF↔Content missing; PublicationPackage as-is; owner_preview **legacy/dev only (OD-CT-07)** |
| 2. Frozen contracts | Pattern 1–12 · Launch Architecture 1–26 / OD-LA · Fabric 1–40 · EM A/B/C |
| 3. Contradictions (honest) | Factory still brief-driven in code until Runtime pin; dual draft stacks kept isolated; owner_preview not commercial |
| 4. Reuse | Adapter Factory + ContentAssetService; PackageJob handoff retained |
| 5. Legacy risks | H2.7 isolated; Scenario Wizard; PublicationJob (A); owner_preview |
| 6. Owner decisions | OD-CT-01…08 **all A accepted** |
| 7. Deliverables | Exactly **six** docs |
| 8. In scope | Applied Content capability architecture |
| 9. Out of scope | Runtime · A/B · SEO · multi-channel catalog · Visual/Publication Architecture |
| 10. Freeze blockers | **Closed** · FREEZE-01 **applied** |

---

## 1. Purpose and customer value

**Capability id:** `project.content` (Project Command Center — not a Workspace micro-product).

**One question this pack answers:**  
How Marketsynth takes an **approved, versioned ContentRequest** (from Launch), runs Content, produces reviewable **ContentCandidate(s)**, yields **approved ContentAsset(s)**, and hands them to Publication — **without** re-deciding Strategy or Launch.

| Customer pays for | Content does **not** decide |
|-------------------|-----------------------------|
| Concrete, editable, versioned channel text aligned to approved Offer/Request | ICP · Offer · Campaign objective · budget · channel execution · Strategy pillars rewrite |
| Honest review/edit/approve before publish | Silent regenerate of approved versions |
| Lineage to Strategy/Offer/Request | Universal JSON blob “content engine” |

---

## 2. Inputs

| Input | Rule |
|-------|------|
| Tenant / project | Mandatory; cross-tenant forbidden; cross-project Content handoff **denied** (absolute) |
| Upstream | **Approved Launch Package** version + **ContentRequest** version (Launch-owned) |
| ContentInputSnapshot | Immutable pin: Package version · ContentRequest version · selected OfferArtifact · CampaignFrame · channel/format constraints · messaging constraints · CTA · Strategy refs (read-only) · assumptions |
| Eligibility | Package `current_approved` present; ContentRequest not cancelled; Package not `stale_blocking` for new Content handoff |
| Registry | Availability only — not authz |

**Forbidden inputs as decision authority:** “latest Strategy”, free-form brief that bypasses ContentRequest, BusinessCampaign as ContentRequest substitute.

---

## 3. Outputs

| Class | Owner | Object |
|-------|-------|--------|
| Domain deliverable | Content | **Approved ContentAsset** (versioned) |
| Intermediate | Content | ContentCandidate (draft / ready_for_review) |
| Evidence | Publication / Execution | DeliveryEvidence (not Content-owned) |
| Outcome | Project | OutcomeRecord (not Content-owned) |

Content does **not** own PublicationPackage, PackageJob, or Launch Package.

---

## 4. CapabilityRun — ContentRun

`ContentRun` = Fabric CapabilityRun with `capability_id = project.content`.

Statuses (only): `queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted`.

| Rule | |
|------|--|
| Interrupted | Terminal; no silent reopen as `running` |
| Retry | New attempt, same `run_id` + ContentInputSnapshot (Fabric: pre-terminal or interrupted carve-out) |
| Rerun | New ContentRun + `rerun_of_run_id` |
| Regenerate | Domain term for producing a **new candidate version** under same Request — **never** overwrites approved asset body (OD-CT-05). Fabric retry vs new ContentRun binding = first Runtime TZ (not Architecture) |
| Succeeded | May leave unapproved candidates |
| Pending `content_approval` | Derived — not a run status |

---

## 5. Snapshots

**ContentInputSnapshot** (required): pins Package + ContentRequest (+ Offer/Frame/constraints). Immutable for the run.  
**HandoffSnapshot** to Publication: logical — approved ContentAsset version ids + Package/Request pins; physical form = Runtime.

---

## 6. Artifact ownership

| Artifact | Owner | Notes |
|----------|-------|-------|
| ContentRequest | **Launch** | Input only; Content must not mutate Package/Request requirements |
| ContentCandidate | Content | Pre-approval draft(s) for a Request |
| ContentAsset | Content | Domain deliverable; typed; versioned |
| PublicationPackage | Publication | Created from approved assets + PublicationPlan |

### ContentAsset types (OD-CT-03 = A)

Channel text artifacts with explicit type (not a free JSON blob).  
**MVP:** Request-driven types; commercial CWF path focuses on **`telegram_post`**.  
Code enum values (`landing_page`, `ad_copy`, …) remain **post-MVP reuse candidates** — not Architecture license to expand MVP. Not “telegram_post only forever.”

### Versioning (OD-CT-05 = A)

- Append-only versions; approved version immutable.  
- Owner edit of approved → **new version** or **revision asset** (adapter-compatible with current revision-as-new-row).  
- **Regenerate** → new candidate only; **approved intact**.  
- **Forbidden:** in-place overwrite of approved body; Option B “replace approved in place” = architecture FAIL.

---

## 7. Approval points

| Approval | Scope |
|----------|-------|
| `content_approval` | Pins to **ContentAsset version** (path-dependent; required before Publication uses asset) |
| Not Content’s job | `launch_package_approval` · `publication_package_approval` · `external_execution_approval` |

No per-sentence approval. Manual owner edits before approval require **attribution** (actor, timestamp) on the version/revision metadata.

---

## 8. Restore

```
Project open
  → ContentRuns (active/recent)
  → ContentRequests (pinned Package version) + status
  → candidates / current_approved ContentAsset versions
  → derived stale vs Package/Request
  → pending content_approval
  → Publication handoff state (read)
  → next actions
```

Browser storage not SoT. Each child/asset labeled with **pinned ContentRequest + Package version**.

---

## 9. Retry / rerun / resume / revision / regenerate

| Term | Meaning |
|------|---------|
| Retry | Same ContentRun attempt (Fabric) |
| Rerun | New ContentRun |
| Resume | Only safe checkpoint; else rerun |
| Revision | New artifact version / revision lineage — not automatic new run |
| Regenerate | New candidate under same Request; **does not** mutate approved (OD-CT-05 = A) |

Align with Launch OD-LA-06/07: Package supersession → in-flight may complete; asset stale vs new Package; new Request for v2; cancel request ≠ mutate Package.

---

## 10. Handoff to Publication

```
Approved ContentAsset version(s)
  + Launch PublicationPlan
  + owner-guided selection
  → Publication creates PublicationPackage
  → PackageJob path (canonical)
```

Content **lists eligible approved assets**; Publication **selects and packages**. Content does not send Telegram.

**Stale:** ContentRequest / Offer / CampaignFrame / Package change → dependent ContentAsset may be `stale_viewable`; new Publication handoff may be `stale_blocking` until revalidation or new asset under new Request.

---

## 11. Evidence and Outcome

Content Architecture **does not** produce DeliveryEvidence. External send remains Publication + Fabric ledger. OutcomeRecord remains project-level.

---

## 12. Export

Optional for MVP Domain Content: customer-readable text of **approved** ContentAsset version + machine JSON (asset id, version, Request/Package pins, type, channel, attribution). ACL tenant/project; no secrets.

---

## 13. UI placement

Project Command Center → Content panel (after Launch Package approved + ContentRequest).  
**Not** Workspace Content Factory micro-product.  
**Not** owner_preview / recovery-preview as commercial path (**OD-CT-07 = A**: legacy/dev only; Command Center is the product target).  
No layout design in this pack.

---

## 14. MVP boundary

See `PRODUCT-05-CONTENT-MVP-CUT.md`. Domain MVP = approved ContentAsset under pinned Request. Candidates **1..N** (OD-CT-04); UI may default 1–3. Commercial E2E still requires Publication path (unchanged CWF DoD).

---

## 15. Runtime boundary (OD-CT-08 = A)

Architecture ≠ Runtime. **First Runtime slice after Architecture freeze** (not started now):

1. **ContentRequest + Package pin**  
2. ContentRun + ContentInputSnapshot  
3. **Adapter:** Content Factory / ContentAssetService generation **under ContentRequest** (OD-CT-01 — never canonical Architecture)  
4. content_approval + restore heads  
5. Handoff read model for Publication  

**Forbidden as first slice:** full E2E Content+Publish monolith · Factory UI-first without Request pin.

No queues/DSL/Asset Framework. H2.7 remains **isolated** (OD-CT-02); merge only via later proven adapter OD.

---

## 16. Explicit non-goals

Strategy/Launch reopen · universal Asset Framework · A/B testing · SEO · brand-voice product · multi-channel orchestration · Visual Architecture · Publication Architecture rewrite · declaring Content Factory **canonical** · merging H2.7 now · owner_preview as product entry · code/UI/API.

---

## Appendix — Pattern checklist map

Appendix A items 1–17 of Capability Pattern are addressed across this pack (Architecture · Lifecycle · Artifact Flow · Journey · MVP · Audit oracles). Domain-only Content rules do not copy Launch Package BOM into Content.

---

## Freeze applied (PRODUCT-05-CONTENT-ARCHITECTURE-FREEZE-01)

| Field | Value |
|-------|-------|
| Content Architecture | **OWNER-FROZEN** (2026-08-02) |
| **`owner_freeze`** | **OWNER-FROZEN** |
| **`frozen_at`** | 2026-08-02 |
| Invariants | Freeze record **1–20** |
| OD-CT-01…08 | **OWNER-APPROVED** (all A) |
| Content Runtime | **NOT STARTED** |
| PRODUCT-06 Visual Architecture | **NOT STARTED** |
| **Next priority** | **NOT SET** |

Freeze does **not** authorize Content Runtime, Visual Architecture, Publication Architecture, Research, or code without a separate owner priority.
