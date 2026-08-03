# PRODUCT-04 — Launch Artifact Flow

> **Task:** PRODUCT-04-LAUNCH-ARCHITECTURE-PATCH-01  
> **Owns:** Artifact graph, BOM confirmation, stale/approvals, pointers, reuse audits  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-LA-02…09 **OWNER-ACCEPTED**  
> **Inherits:** Domain Model BOM · EM handoff · Fabric pointers/stale

---

## 1. Confirmed Package BOM

### Required

Approved Strategy version reference · LaunchInputSnapshot reference · 1..N CampaignFrame · 1..N OfferArtifact · **budget section** (known/unknown · envelope/range · constraints · paid_execution_allowed · ack state · assumptions) · 1..N ContentRequest · PublicationPlan · measurement criteria · assumptions · limitations · approvals · next action

### Conditional

VisualRequest · budget_acknowledgement · multiple frames · offer variants · branch constraints · `visual_required` metadata

### Forbidden in Package

ContentAsset · VisualAsset · PublicationPackage · PublicationJob · PackageJob · DeliveryEvidence · OutcomeRecord · BudgetArtifact (MVP) · post-approval asset ID back-fill · BusinessCampaign identity

**After approval:** immutable. Requirement change → new version. Child request cancel ≠ Package mutation (OD-LA-07).

---

## 2. Artifact graph

```
ApprovedStrategyPackage
  → LaunchInputSnapshot
  → LaunchCandidate
  → ApprovedLaunchPackage
  → CampaignFrame / OfferArtifact / budget section
  → ContentRequest  ∥  VisualRequest
  → ContentAsset / VisualAsset          (executors)
  → PublicationPlan                     (Launch-owned; in Package)
  → PublicationPackage                  (Publication selects assets)
  → PackageJob                          (canonical send — OD-LA-08)
  → Delivery / DeliveryEvidence
  → OutcomeRecord                       (project Outcome Capture)

Legacy (temporary migration source, not canonical):
  PublicationJob (code-stack A) — isolated; no dual canonical send
```

| Artifact | Producer | Consumer | Mult. | Version | Approval | Immutable when approved | MVP |
|----------|----------|----------|-------|---------|----------|-------------------------|-----|
| ApprovedStrategyPackage | Strategy | Launch | 1 head | Yes | strategy | Yes | Yes |
| LaunchInputSnapshot | Launch entry | LaunchRun | 1/run | Pin | eligibility | Snapshot | Yes |
| LaunchCandidate | LaunchRun | Owner | N | Yes | — | No | Yes |
| ApprovedLaunchPackage | LaunchRun | Executors | 1 head | Yes | launch_package | Yes | Yes |
| CampaignFrame | Launch | Requests | N/run | Via pkg | via pkg | With pkg | Yes |
| OfferArtifact | Launch | Requests | N/frame | Yes | via pkg | When approved | Yes |
| Budget section | Launch | Exec / ack | 1/pkg | Via pkg | via pkg + conditional ack | With pkg | Yes |
| ContentRequest | Launch | Content | N | Yes | — | Soft | Yes |
| VisualRequest | Launch | Visuals | N | Yes | — | Soft | Cond. |
| ContentAsset | Content | Publication | N | Yes | content | Yes | Path |
| VisualAsset | Visuals | Publication | N | Yes | visual | Yes | Opt |
| PublicationPlan | Launch | Publication | 1+/pkg | Via pkg | via pkg | With pkg | Yes |
| PublicationPackage | Publication | PackageJob | N | Yes | pub package | Yes | Path |
| PackageJob | Publication | Evidence | N | Status | external | Terminal kept | Path |
| PublicationJob (A) | Legacy | — | N | Status | — | Terminal kept | **Legacy** |
| DeliveryEvidence | Job | Outcome | N | Append | — | Append-only | Path |
| OutcomeRecord | Outcome Capture | Owner | N | Yes | — | — | When evidence |

**Pointers (per lineage):** `latest_created_version` · `current_candidate_version` · `current_approved_version`.

---

## 3. Approval graph (MVP) — OD-LA-03 = A

**Mandatory package gate:** single `launch_package_approval` covering frames · offers · budget section · ContentRequests · conditional VisualRequests · PublicationPlan · assumptions/limitations.

**Mandatory (path-dependent):** `content_approval` · `publication_package_approval` · `external_execution_approval`.

**Conditional:** `visual_approval` · `budget_acknowledgement` · revalidation approval.

**Not in MVP:** per-section approvals for CampaignFrame / Offer / Request.

Each pinned to artifact version · expiry/invalidation/supersession per Fabric · owner edit → new version.

---

## 4. Stale / invalidation rules (Launch)

| Upstream | Downstream | Default |
|----------|------------|---------|
| Strategy superseded | Package | stale_blocking for new handoff |
| Frame/Offer/budget-req change | Requests | new Package version; old requests stale |
| ContentRequest change | ContentAsset | stale_viewable; may need new asset |
| Package v2 while child on v1 | Asset from v1 | derived stale vs v2; no silent attach (OD-LA-06) |
| PublicationPlan change | PublicationPackage | stale_blocking for new jobs |
| Budget ack expired | Paid external | blocked |
| Explicit invalidate Package | Approvals for handoff | invalidated; history kept |

No cascade deletion. External history preserved.

---

## 5. Scenario oracles

| # | Scenario | Assert |
|---|----------|--------|
| 1 | Strategy superseded before Package approval | Candidate invalidated/stale; no approve on dead pin |
| 2 | Strategy superseded after Package approval | Package stale_*; new Package for new Strategy |
| 3 | Package revised before Content | New Package version; new ContentRequest |
| 4 | Package superseded while Content running | OD-LA-06: complete+stale; no auto-cancel; new request for v2 |
| 5 | ContentRequest revised after asset | Asset may stale; history kept |
| 6 | Visual optional abandoned | Content-only if allowed |
| 7 | PublicationPlan changed | New Package version; PubPackage stale |
| 8 | PubPackage approved then Package stale | PubPackage not deleted; new handoff blocked until revalidation |
| 9 | External already happened then invalidation | Evidence retained; no undo |
| 10 | Rollback to prior approved Package | Pointer change; history intact |
| 11 | Multiple CampaignFrame | Supported (UI default one) |
| 12 | Multiple PublicationPackage | Supported |
| 13 | Cross-project handoff | Denied by default |
| 14 | Cross-tenant handoff | Denied by default |
| 15 | Cancel request without Package change | Package immutable; request cancelled (OD-LA-07) |
| 16 | Duplicate semantic send A+B paths | **Forbidden** (OD-LA-08) |

---

## 6. CampaignFrame vs BusinessCampaign (OD-LA-02 = B — OWNER-ACCEPTED)

| | CampaignFrame | BusinessCampaign (code) |
|--|---------------|-------------------------|
| Role | Launch execution context inside Package | BOS ops container (plans, dashboard) |
| Product? | No | Appears as campaign product surface |
| In Package BOM? | Yes | **No** |
| Canonical for Launch? | Yes (domain object) | **No** |
| Decision | — | **Partial reuse via adapter** with hard constraints |

### Reusable candidates (only after compatibility proof)

- project binding  
- objective  
- audience references  
- selected operational metrics  
- publication relationships **where valid** as **data hints only** (never satisfy `publication_package_approval` / `external_execution_approval`)

### Not reusable automatically

- lifecycle  
- status model  
- ownership  
- CampaignFrame identity  
- Strategy / Package pinning  
- approvals  
- artifact lineage  

Incompatible lifecycle/ownership remain **legacy**.  
**No 1:1 migration assumption.** Final migration plan = separate **Launch Runtime** task.

---

## 7. Dual publication stack (OD-LA-08 = A — OWNER-ACCEPTED)

| Path | Role | Status |
|------|------|--------|
| **PublicationPackage → PackageJob → Delivery → DeliveryEvidence** | Canonical target for Launch Runtime | **Canonical target** (code-stack B) |
| PublicationJob asset-direct (code-stack A) | Temporary migration source | **Legacy** — retained; not deleted by this docs task; **not** canonical |
| DeliveryLog | Evidence seed | Adapter → DeliveryEvidence |
| ExecutionApproval typed | Missing | Missing foundation |

### Rules

1. Launch Runtime builds around **PackageJob** path.  
2. Legacy PublicationJob: retain until proven migration plan; **do not** run as second canonical send path.  
3. One semantic external publication action → **one** fingerprint / idempotency boundary.  
4. Migration must preserve successful DeliveryEvidence history.  
5. Replay/retry must not duplicate publication.  
6. Direct/legacy send paths isolated before Runtime acceptance.

### Runtime freeze blocker (Architecture pack records; Runtime not started)

**Launch Runtime cannot be owner-frozen** until dual-stack migration + deduplication tests pass.

Architecture `owner_freeze` remains a separate gate (this pack → ready_for_owner_freeze).

---

## 8. Code reuse map (honest)

| Element | Class | Note |
|---------|-------|------|
| BusinessCampaign | **B Partial adapter** (OD-LA-02) | Not canonical; not CampaignFrame |
| LaunchPackRequest | B Adapter | Decision gate ≠ Package |
| Offer Builder | B Adapter | Pin Strategy + Package |
| Content Factory | B Adapter | After Package; via ContentRequest |
| Visual assets | B Adapter | Optional |
| PublicationPackage | B Adapter | Publication-owned |
| PackageJob (B) | **A/B Canonical target** | OD-LA-08 |
| PublicationJob (A) | D Legacy / migration source | No dual canonical |
| DeliveryLog | B Adapter | → DeliveryEvidence |
| ExecutionApproval | F Missing | Typed approvals |
| Telegram (B) | B Adapter | Real send for E2E on PackageJob path |
| Hydration | A Pattern reuse | Extend for Launch heads |
| Operational metrics | C Partial | Not OutcomeRecord |

---

## 9. Export shape (OD-LA-09 = A)

| Format | Contents |
|--------|----------|
| Markdown | Customer-readable structured Approved Package |
| JSON | Machine: version metadata · Strategy pin · frames · offers · budget section · requests · PublicationPlan · assumptions/limitations · approval metadata |

Version-pinned · tenant/project ACL · no secrets. PDF/DOCX/Slides = post-MVP.
