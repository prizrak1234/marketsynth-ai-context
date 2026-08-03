# PRODUCT-04 — Launch MVP Cut

> **Task:** PRODUCT-04-LAUNCH-ARCHITECTURE-PATCH-01  
> **Owns:** First paying Launch cut vs post-MVP  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-LA-04, 05, 08–10 **OWNER-ACCEPTED**  
> **Inherits:** Domain Model OD-LDM-08 · EM contracts A/B/C · CWF.1 product DoD

---

## Triad (do not conflate)

| Layer | Completes at | Owner of DoD |
|-------|--------------|--------------|
| **Launch Architecture / Domain MVP** | Approved Launch Package (**A**) | This pack + Domain Model |
| **Downstream execution** | Assets + PublicationPackage / **PackageJob** as pursued | Content/Visual/Publication |
| **Commercial MVP E2E** | ≥1 real path to DeliveryEvidence (**B**), product (**C**) | CWF.1 / FINISH-01 |

---

## Launch Architecture MVP (minimum)

| Item | Required |
|------|----------|
| One Approved Strategy version pin | Yes |
| One LaunchRun | Yes |
| One LaunchCandidate → Approved Launch Package | Yes |
| CampaignFrame (≥1; UI default one; model **1..N**) | Yes |
| One canonical OfferArtifact | Yes |
| Budget **section** (known/unknown OK; no BudgetArtifact) | Yes |
| ≥1 ContentRequest | Yes |
| VisualRequest | Optional / conditional |
| PublicationPlan (may be deferred value) | Yes |
| Single `launch_package_approval` | Yes |
| Export: Markdown + JSON of approved Package version | Yes |
| Persist restore of Package/run heads | Yes |

**Not required for Launch Domain/Architecture MVP:** ContentAsset · VisualAsset · PublicationPackage · PackageJob · DeliveryEvidence · OutcomeRecord · multi-channel · scheduler · BudgetArtifact · BusinessCampaign product.

---

## Commercial MVP E2E (product — must remain possible)

Minimum path the **product** must prove (not every LaunchRun):

```
Strategy (or documented CWF transitional upstream)
  → Approved Launch Package
  → ContentAsset (approved)
  → optional VisualAsset
  → PublicationPackage (approved)
  → external_execution_approval
  → successful PackageJob          ← canonical (OD-LA-08)
  → DeliveryEvidence (+ message_id when available)
  → basic OutcomeRecord
```

Legacy PublicationJob must not be a second canonical E2E proof path.  
CWF.1 / FINISH-01 Telegram publish DoD **not weakened**.

---

## Post-MVP (explicitly out)

Multi-channel orchestration · advanced budget allocation · separate BudgetArtifact (until triggers in Catalog LC-04) · scheduling calendar · asset experimentation · complex branching · Optimization · portfolio Analytics · CRM · team workflows · advanced campaign management · Billing · BusinessCampaign as CampaignFrame · indefinite dual canonical publish stacks · PDF/DOCX/Slides export.

---

## Runtime implementation order (OD-LA-10 = A — OWNER-ACCEPTED)

After Architecture **OWNER-FROZEN** (not started now). **No** full E2E monolith as first slice. **No** Offer-only standalone product.

| Slice | Scope |
|-------|--------|
| **R1** | LaunchRun + LaunchInputSnapshot + Candidate + Package + `launch_package_approval` |
| **R2** | ContentRequest → existing Content adapter |
| **R3** | Conditional VisualRequest → Visual adapter |
| **R4** | PublicationPlan → PublicationPackage → **PackageJob** |
| **R5** | External execution approval + DeliveryEvidence |
| **R6** | Basic OutcomeRecord |

**Runtime freeze precondition (OD-LA-08):** dual-stack migration + deduplication tests pass before Launch Runtime owner-freeze.

Stop-at-Package remains Domain MVP (A). Monetizing Package-only as a commercial SKU still needs explicit owner commercial framing before pricing claims. E2E publish remains product gate (C).
