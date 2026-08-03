# PRODUCT-05 — Content MVP Cut

> **Task:** PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01  
> **Owns:** First paying Content cut vs post-MVP  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-CT-03, 04, 08 **OWNER-ACCEPTED = A**  
> **Inherits:** Capability Pattern · Launch MVP triad · CWF.1 / FINISH-01 DoD

---

## Triad (do not conflate)

| Layer | Completes at |
|-------|----------------|
| **Content Domain / Architecture MVP** | ≥1 **approved ContentAsset** under pinned ContentRequest |
| **Downstream** | PublicationPackage / PackageJob as pursued |
| **Commercial MVP E2E** | Real Telegram publish + DeliveryEvidence (product DoD) |

---

## Content Architecture MVP (minimum)

| Item | Required |
|------|----------|
| Approved Launch Package pin | Yes |
| Versioned ContentRequest | Yes |
| ContentRun + ContentInputSnapshot | Yes |
| 1..N candidates → owner review/edit (UI default 1–3) | Yes (OD-CT-04) |
| One approved ContentAsset (typed; not JSON blob) | Yes |
| MVP type focus: Request-driven; CWF = telegram_post | Yes (OD-CT-03) |
| `content_approval` on asset version | Yes |
| Lineage to Request/Package/Offer/Strategy | Yes |
| Attribution on manual edits; regenerate ≠ overwrite approved | Yes (OD-CT-05) |
| Publication handoff eligibility (approved asset) | Yes |
| Persist restore of Content heads | Yes |

**Not required for Content Architecture MVP:** Visual · real send · A/B testing · SEO · brand-voice · multi-channel orchestration · H2.7 merge · Scenario Wizard as primary path · owner_preview as product UI · full ContentAssetType enum as product catalog.

---

## Commercial MVP E2E (product — preserved)

```
… → Approved Launch Package
  → ContentRequest
  → approved ContentAsset
  → optional Visual
  → PublicationPackage
  → external_execution_approval
  → PackageJob success
  → DeliveryEvidence
  → OutcomeRecord
```

CWF.1 / FINISH-01 Telegram DoD **not weakened**.

---

## Post-MVP (explicitly out)

A/B experimentation · SEO · brand voice studio · multi-channel calendars · H2.7 merge without later OD · universal Asset Framework · Content deciding Strategy/Launch · Instagram/LinkedIn providers · Factory as Architecture-canonical generator.

---

## Runtime order (OD-CT-08 = A — OWNER-ACCEPTED)

After Architecture **OWNER-FROZEN** (not started now):

1. ContentRequest + Package pin  
2. ContentRun + ContentInputSnapshot  
3. Adapter generation (Factory/AssetService under Request — OD-CT-01)  
4. Approval + restore  
5. Handoff read model for Publication  

**Not first:** Full E2E Content+Publish monolith · Factory UI first.
