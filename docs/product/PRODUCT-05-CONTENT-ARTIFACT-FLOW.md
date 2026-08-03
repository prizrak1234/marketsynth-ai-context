# PRODUCT-05 — Content Artifact Flow

> **Task:** PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01  
> **Owns:** Artifact graph, stale rules, Publication handoff, code reuse audit  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-CT-01, 02, 07 **OWNER-ACCEPTED = A**  
> **Inherits:** Launch Artifact Flow · Fabric pointers/stale · Capability Pattern

---

## 1. Graph

```
ApprovedStrategyPackage
  → ApprovedLaunchPackage
  → ContentRequest (Launch-owned, versioned)
  → ContentInputSnapshot
  → ContentRun
  → ContentCandidate (1..N)
  → ContentAsset (approved version)
  → PublicationPackage (Publication selects)
  → PackageJob → DeliveryEvidence → OutcomeRecord
```

| Artifact | Producer | Consumer | Mult. | Approval | MVP |
|----------|----------|----------|-------|----------|-----|
| ContentRequest | Launch | Content | N | via Package | Yes |
| ContentInputSnapshot | Content entry | ContentRun | 1/run | eligibility | Yes |
| ContentCandidate | ContentRun | Owner | N | — | Yes |
| ContentAsset | Content | Publication | N | content_approval | Yes |
| PublicationPackage | Publication | Jobs | N | pub package | Path |

Pointers: `latest_created` · `current_candidate` · `current_approved` per asset lineage.

---

## 2. Lineage (required on ContentAsset)

Must retain references (semantic):

- ContentRequest version id  
- Launch Package version id  
- OfferArtifact / CampaignFrame refs from Request  
- Strategy version pin (read-through)  
- ContentRun id  
- channel / format / language / length constraints applied  
- generation vs manual_edit attribution  

Tone, language, length, channel constraints are **consumed from ContentRequest / Package**, not invented by Content.

---

## 3. Stale / invalidation

| Upstream | Effect on Content |
|----------|-------------------|
| Launch Package superseded | Assets under old Request → stale vs Package v2; new Request required for v2 path |
| ContentRequest revised | Prior assets may stale_viewable |
| Offer / CampaignFrame change via new Package | Same as Package supersession |
| Explicit invalidate | History kept; no cascade delete |

No rewrite of DeliveryEvidence. No silent attach of stale asset to new Package without owner decision (Launch OD-LA-06).

---

## 4. Publication handoff

Eligibility: `content_approval` on asset version · asset not stale_blocking for this Package · channel matches PublicationPlan expectations · tenant/project match.

Publication owns concrete selection into PublicationPackage. Canonical send remains PackageJob (Launch OD-LA-08). Content does not call Telegram.

---

## 5. Code reuse audit (read-only)

| Element | Class | Note |
|---------|-------|------|
| ContentAssetTable + versions + diff + rollback | **A As-is** | Mature; adapter to Pattern states |
| ContentAssetService lifecycle/approve | **A/B As-is→adapter** | Map draft/review/approved ↔ Pattern |
| ContentFactoryGenerationService | **B Adapter only (OD-CT-01 = A)** | **Never Architecture-canonical**; must accept ContentRequest pin; today brief-driven |
| Copywriter specialist conversion | **B Adapter** | Producer into ContentAsset |
| Scenario Wizard content conversion | **C/D Partial/legacy** | Not Launch ContentRequest path |
| H2.7 content_draft_service | **E Incompatible · isolated (OD-CT-02 = A)** | Separate persistence/status; **no merge now**; adapter only later with proven need |
| PublicationPackage from approved asset | **A As-is** | Canonical handoff seed |
| PackageJob / Telegram (B) | **A As-is** | Publication-owned |
| PublicationJob (A) | **D Legacy** | Not Content Architecture target |
| Owner_preview Content Factory UI | **D Legacy/dev only (OD-CT-07 = A)** | **Not** commercial Command Center path |
| ContentRequest entity | **F Missing** | Required Architecture object |
| ContentRun / ContentInputSnapshot | **F Missing** | Required |
| Unified typed content_approval (Fabric ApprovalRecord) | **F Missing / partial** | Metadata blob today; map via OD-CT-06 adapter |
| Project content hydration contract | **C Partial** | List endpoints only |
| CWF Launch Pack → Content | **F Missing** | Integration = Runtime after Architecture (OD-CT-08) |

**Commercial value of current ContentAsset stack:** high for versioning/review/Telegram package path.  
**Cost of change:** moderate — adapter + Request pin, not rewrite.  
**Regression risk:** controlled — H2.7 stays isolated; Factory stays non-canonical.

---

## 6. Scenario oracles (sample)

1. ContentRun pinned to ContentRequest + Package versions.  
2. Approved asset immutable; regenerate does not overwrite.  
3. Assets not written into Launch Package.  
4. Stale after Package v2; no silent v2 attach.  
5. Cross-project handoff denied.  
6. PublicationPackage only from approved asset.  
7. Content does not set ICP/Offer/budget.
