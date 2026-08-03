# PRODUCT-05 — Content Lifecycle

> **Task:** PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01  
> **Owns:** ContentRun / Candidate / Asset / Approval lifecycles (not Project enum; not PublicationJob)  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-CT-04, 05, 06 **OWNER-ACCEPTED = A**  
> **Inherits:** Fabric · Launch Lifecycle (OD-LA-06/07) · Capability Pattern

---

## 0. Separation

| Layer | Object |
|-------|--------|
| A. ContentRun | Fabric CapabilityRun statuses |
| B. ContentCandidate / ContentAsset | ArtifactVersionState-aligned |
| C. content_approval | ApprovalRecord on asset version |
| D. Derived UI | drafting · awaiting_review · approved · stale_* · execution_* |

---

## A. ContentRun

`queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted`

Interrupted = terminal. Retry = attempt. Rerun = new run. Resume only with safe checkpoint.

---

## B. Candidate / Asset

| State | Meaning |
|-------|---------|
| draft | Generating / editable candidate |
| ready_for_review | Submitted for owner |
| approved | `content_approval` on this version |
| rejected | Decision retained |
| superseded | Newer approved head |
| invalidated | Explicit event |
| archived | Soft retention |

**Immutability:** approved body does not change. Edits → new version or revision lineage.  
**Regenerate (OD-CT-05 = A):** new draft/candidate only — never clobbers approved.

### Status mapping (OD-CT-06 = A — OWNER-ACCEPTED)

Semantic Pattern / ArtifactVersionState remains normative.  
Current code `ContentAssetStatus` (`draft→review→approved→archived`) is an **adapter mapping** implemented at Runtime — Architecture does **not** mandate rewriting the live enum now.

| Code (approx.) | Semantic |
|----------------|----------|
| draft | draft / generating |
| review | ready_for_review |
| approved | approved (+ content_approval) |
| archived | archived |

`rejected` / `superseded` / `invalidated` may be represented via metadata, lineage, or future adapter fields — Runtime detail.

---

## C. Approval

`pending` (derived) · `approved` · `rejected` · `expired` · `invalidated`  
Pinned to ContentAsset version. Expired blocks **new** Publication use of that approval; does not delete asset history.

---

## D. Derived customer states

| Label | Typical derivation |
|-------|--------------------|
| drafting | Run running / candidate draft |
| awaiting_review | ready_for_review + pending content_approval |
| approved | current_approved asset version for Request |
| stale_viewable | Upstream Package/Request/Offer changed |
| stale_blocking | Blocks new Publication handoff |
| execution_requires_attention | Failed run · ambiguous (N/A for Content send) · blocked Request |

---

## Scenarios

| # | Scenario | Outcome |
|---|----------|---------|
| 1 | Package approved → ContentRequest ready | ContentRun may start |
| 2 | Candidates generated (1..N) | Drafts under Request |
| 3 | Owner edits draft | New version; attribution |
| 4 | Owner rejects | rejected retained; regenerate or revise |
| 5 | content_approval | current_approved head |
| 6 | Regenerate after approve | New candidate; approved intact |
| 7 | Package v2 while Content running | OD-LA-06: complete+stale; new Request for v2 |
| 8 | Cancel Request | OD-LA-07: Package unchanged; stop child |
| 9 | Request revised (requirements) | Needs Package revision first if BOM changes |
| 10 | Handoff to Publication | Only approved non-blocking assets |
| 11 | Multiple Requests | N ContentRuns / asset lineages |
| 12 | Rollback | New draft from prior version snapshot (history kept) |

---

## Variants (OD-CT-04 = A — not A/B platform)

**Model:** 1..N candidates under one ContentRequest.  
**UI default:** 1–3 (product choice).  
**Forbidden:** exactly-one forever; traffic-split A/B experimentation platform in Content MVP.  
Selection is owner decision before/at approval.
