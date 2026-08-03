# PRODUCT-04 — Marketsynth Commercial Execution Model

> **Task:** PRODUCT-04-EXECUTION-MODEL-01 · **Patch:** PRODUCT-04-EXECUTION-MODEL-PATCH-01  
> **Title:** Marketsynth Commercial Execution Model  
> **Type:** Docs-only architecture  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **OD-EM-01…10:** **OWNER-APPROVED** (2026-08-02)  
> **Basis:** OD applied · P0-EM-01…04 closed · freeze-blocking P1 closed · consistency PASS · reviewers 5/5 PASS · no code/runtime/research  
> **Audit:** `PRODUCT-04-EXECUTION-MODEL-AUDIT.md` · PATCH validation §23 · freeze §23.5  
> **Inherits:** PRODUCT-02 OWNER-FROZEN · PRODUCT-03 OWNER-FROZEN  
> **Does not:** auto-start Launch Architecture · Runtime · code · UI · Registry edits · rewrite P02/P03 freeze text

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-04 Commercial Execution Model
basis: OD-EM-01…10 applied; P0-EM-01…04 closed; freeze-blocking P1 closed; consistency matrix PASS; reviewers 5/5 PASS; code/runtime/research unchanged
```

### Frozen invariants (normative)

1. Launch — one project-stage capability.  
2. Launch has a repeatable LaunchRun.  
3. Approved Launch Package — versioned artifact, not a LaunchRun status.  
4. One Project may have multiple LaunchRuns.  
5. One Strategy version may spawn multiple LaunchRuns.  
6. Primary commercial deliverable — Approved Launch Package.  
7. Launch Package may exist without external publication.  
8. Publication execution — separate contract.  
9. Commercial MVP E2E must prove ≥1 real publication path.  
10. CampaignFrame — execution context inside Launch, not a separate product.  
11. BusinessCampaign — reuse candidate only until a separate compatibility audit.  
12. Strategy Offer Structure ≠ Launch Offer Artifact.  
13. Budget premises belong to Strategy.  
14. Budget envelope and allocation proposal belong to Launch.  
15. Actual spend and transaction evidence belong to Execution.  
16. Unknown budget does not block Launch Package.  
17. Paid external execution requires budget acknowledgement or an allowed limit.  
18. Content, Visuals, and Publication — downstream Launch executors.  
19. Content and Visuals may run in parallel.  
20. Publication — multi-instance.  
21. Retry does not create a new LaunchRun.  
22. Outcome Capture — project-level consumer of ExecutionEvidence / DeliveryEvidence.  
23. Outcome Capture is not full Analytics.  
24. Approvals are typed and pinned to artifact version.  
25. Registry is not authorization.  
26. Freezing the Execution Model does **not** auto-start Launch Architecture or Runtime.

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Accept Execution Model as OWNER-FROZEN | Start Launch Architecture pack automatically |
| Lock invariants 1–26 for Launch Architecture | Start Launch Runtime / Strategy Runtime / Research |
| Authorize planning against three contracts A/B/C | Rewrite PRODUCT-02/03 · edit Registry · change code |
| | Treat BusinessCampaign as canonical without compatibility audit |

**Deferred:** LaunchRun state model · BusinessCampaign compatibility · dual publication stack audit · CWF retirement · catalog wording cleanup  
**Next priority:** **NOT SET** (owner chooses separately; logical next = formal kickoff PRODUCT-04-LAUNCH-ARCHITECTURE-01)

---

## 1. Executive definition

**Marketsynth sells managed execution of owner-approved commercial decisions** — not a content generator, not an auto-publisher, not seven micro-products.

| Layer | Role |
|-------|------|
| **Strategy** | Whom / what / why / channel **direction** / fences / success criteria |
| **Launch** | One **project-stage capability** with repeatable **Launch CapabilityRun** (`LaunchRun`) that orchestrates execution of an Approved Strategy |
| **Content / Visuals / Publication** | **Executors** under Launch — own capability runs; Launch does **not** perform their work |
| **Outcome Capture** | Project-level **consumer** of DeliveryEvidence — not a Launch executor; not full Analytics |

**Canonical Launch definition (OD-EM-01 A):**

> Launch is one project-stage capability (`project.launch`) with its own repeatable CapabilityRun.  
> A **LaunchRun** accepts a Strategy-pinned input, produces versioned Launch Package candidates, and **orchestrates** downstream Content / Visuals / Publication runs.  
> **Approved Launch Package** is the versioned **result artifact** of a LaunchRun — not the run itself.

```
Project
└── Launch (capability)
    ├── LaunchRun #1  → ApprovedLaunchPackage v…
    ├── LaunchRun #2  → …
    └── LaunchRun #N
```

Launch is **not:** autonomous agent · separate product · “publish” button · mandatory external send.

---

## 2. Commercial execution problem

PRODUCT-01–03 answered look, Project, and Strategy. This model answers: **what the customer buys after Strategy** and how execution completes without collapsing into “AI posted something.”

---

## 3. Three completion contracts (OD-EM-06 — closes P0-EM-02)

These are **different** and must not be conflated:

| Contract | Meaning | Completion signal |
|----------|---------|-------------------|
| **A. Launch Package completion** | LaunchRun commercial gate | `ApprovedLaunchPackage` + `launch_package_approval` |
| **B. Publication execution completion** | External send path | Terminal successful `PublicationJob` + `DeliveryEvidence` + external id / `message_id` when available |
| **C. Commercial MVP E2E completion** | Product first-paying proof | Marketsynth **can** complete ≥1 governed scenario through **B** (Telegram / MVP channel), with upstream Research→Strategy (target) or documented transitional CWF until Strategy live |

**Compatibility rule:**

```
A LaunchRun MAY terminate at (A) without (B).
Commercial MVP DoD STILL REQUIRES that the product can demonstrate (C) = path to (B).
CWF.1 / FINISH-01 publish + Delivery Evidence binds to (C), not to every LaunchRun terminal.
```

Publication always needs its own approvals. No auto-external execution after Launch Package approval alone.

---

## 4. Canonical execution model

### 4.1 Spine

```
Approved Strategy Package
        ↓
   LaunchRun (CapabilityRun)
        ↓
   LaunchCandidate → ApprovedLaunchPackage
        ↓
   CampaignFrame (1…N) + Offer Artifact(s)
        ↓
   Content ∥ Visuals   (executor runs; may be parallel)
        ↓
   PublicationPackage(s) → PublicationJob(s)   (optional per instance)
        ↓
   DeliveryEvidence
        ↓
   OutcomeRecord (when evidence exists)
```

Aligns PRODUCT-02 MVP spine and PRODUCT-03 Strategy≠Launch / Offer Structure≠Offer Artifact / Channel Direction≠media.

### 4.2 Forbidden reorderings

| Forbidden | Why |
|-----------|-----|
| Strategy → Offer Artifact → Launch | Offer Artifact is Launch-owned |
| Strategy → Content → Launch | Skips Package |
| Launch = only Publication | Collapses orchestrator into send |
| Auto Strategy → external publish | Violates approvals + contract (A)/(B) split |
| Equating BusinessCampaign = CampaignFrame without migration audit | OD-EM-04 |

### 4.3 Current vs target

| Path | Sequence | Status |
|------|----------|--------|
| **Target** | Research → Strategy → Launch → … | Blueprint; Registry planned/reserved |
| **Transitional** | Research → CWF Launch Pack / Offer | Live until Strategy Runtime + Journey/IA drift |

UI must not claim target spine is live.

---

## 5. LaunchRun vs Approved Launch Package (OD-EM-01 / OD-EM-02 — closes P0-EM-01)

| Concept | Is | Is not |
|---------|----|--------|
| **LaunchRun** | Repeatable CapabilityRun under `project.launch` | The commercial SKU file |
| **LaunchCandidate** | Draft / unapproved Package version produced by a run | Approved deliverable |
| **ApprovedLaunchPackage** | **Primary commercial deliverable** after Strategy | PublicationPackage · DeliveryEvidence · the LaunchRun status |

### 5.1 LaunchRun behavior

- Accepts `LaunchInputSnapshot` pinned to an **Approved Strategy version**  
- May create LaunchCandidate → after `launch_package_approval` → ApprovedLaunchPackage  
- Orchestrates downstream capability runs (requests; does not write final Content/Visual assets or execute Publication)  
- One Project → **N** LaunchRuns; one Strategy version → **N** LaunchRuns  
- **Commercial terminals** use contracts A/B/C (§3). Normative Launch CapabilityRunState enum = **Launch Architecture** (not required to freeze this model)  

### 5.2 Package BOM (minimum)

| Include | Notes |
|---------|-------|
| Strategy version reference | Pin |
| CampaignFrame collection | ≥1 in MVP |
| Offer Artifact references | ≥1 in MVP |
| Budget assumptions / envelope / unknowns | OD-EM-03 |
| Content requirements | |
| Optional Visual requirements | |
| Publication plan | May be “none / deferred” for stop-at-Package |
| Approvals | Bound records |
| Unresolved assumptions | Honest |
| Measurement criteria | From Strategy / frames |
| Next action | Explicit |

### 5.3 Package properties

Versioned · immutable after approval · customer-readable · machine-readable · executable manually or by Marketsynth · **may exist without external publication** · ≠ Publication Package.

---

## 6. Capability boundaries

| Capability | Owns | Must not |
|------------|------|----------|
| **Strategy** | Whom / what / why / direction; Offer **Structure**; Channel Direction; fences; measurement criteria | Budget ops allocation; schedules; creatives; publish jobs |
| **Launch** | LaunchRun; Package; CampaignFrame; Offer Artifact; orchestration; budget envelope | Write final Content/Visual assets; execute Publication; re-decide Strategy; pretend Registry authorizes spend; replace Analytics |
| **Content** | Concrete text assets | Choose Strategy objective; auto-publish |
| **Visuals** | Concrete visual assets | Define messaging; mandatory every MVP run |
| **Publication** | PublicationPackage · PublicationJob · DeliveryEvidence | Strategy rewrite; Project `published=true` |
| **Outcome Capture** | OutcomeRecord from evidence | Launch executor; full Analytics; Optimization |

---

## 7. CampaignFrame (OD-EM-04 — closes P0-EM-03)

**Campaign is an execution context inside Launch — not a separate product.**

Canonical semantic object: **CampaignFrame**

| Field (logical) | Role |
|-----------------|------|
| objective | What this frame tries to achieve |
| target segment | Audience slice |
| Offer reference | Binding to Offer Artifact |
| channel direction | Within Strategy fences |
| budget constraints | Within Launch envelope |
| measurement criteria | Honesty bar for this frame |
| scope / assumptions | Limits |

**Multiplicity:** 1 LaunchRun → **N** CampaignFrame.

**BusinessCampaign (AI.146):** reuse **candidate** only. **Not** automatically canonical. Compatibility / migration = Launch Architecture audit — not this freeze.

---

## 8. Offer boundary (OD-EM-05 — closes freeze-blocking P1-EM-01)

| Entity | Owner | Content |
|--------|-------|---------|
| **Strategy Offer Structure** | Strategy | Abstract commercial decision: value, structure, constraints |
| **Launch Offer Artifact** | Launch | Executable: wording, variant, CTA, channel adaptation, timing/conditions, CampaignFrame binding |

**1 Offer Structure → N Offer Artifact.**  
Offer Artifact ≠ Content asset.

---

## 9. Budget boundary (OD-EM-03 — closes P0-EM-04)

| Layer | Owns |
|-------|------|
| **Strategy** | Pricing assumptions; channel direction; constraints / spend_band guidance |
| **Launch** | Budget **envelope**; allocation proposal; spend limits; unknowns; execution constraints (fields in Package) |
| **Execution** | Actual spend; provider/channel cost; external transaction evidence on jobs/evidence |

**Unknown budget:** does **not** block creating / approving Launch Package.  
**Does** block **paid external execution** unless an allowed limit + typed `budget_acknowledgement` exists.

Typed ApprovalRecord: **`budget_acknowledgement`** (conditional).  
**No** Billing / payment system in this model.

---

## 10. Approval graph (OD-EM-07 — closes P1-EM-02)

All gates = **ApprovalRecord** semantics (PRODUCT-02) — not Project/Launch booleans.  
Each approval pinned to: tenant · project · artifact id/version · actor · decision · timestamp · invalidation condition.

| Approval | MVP | Notes |
|----------|-----|-------|
| `launch_package_approval` | **Required** | Primary Launch commercial gate |
| `content_approval` | **Required if** publishing path uses content | Version-pinned |
| `visual_approval` | **Required if** Visual used | |
| `publication_package_approval` | **Required if** Publication path | |
| `external_execution_approval` | **Required if** real send / paid provider | Never implied by Package approval |
| `budget_acknowledgement` | **Conditional** | Before paid external execution |
| Strategy handoff / `launch_eligible` | Upstream | **Sufficient** to create Launch candidate — **no** mandatory separate `launch_start_approval` |

**Forbidden:** approval explosion · boolean-only · approval without artifact version · external execution without explicit approval · approval surviving package invalidation.

---

## 11. Multiplicity (OD-EM-08 — closes P1-EM-03)

| Rule | Multiplicity |
|------|--------------|
| Strategy version → LaunchRun | **1 → N** |
| LaunchRun → CampaignFrame | **1 → N** |
| CampaignFrame → Content assets | **1 → N** |
| CampaignFrame → Visual assets | **1 → N** |
| LaunchRun → PublicationPackage | **1 → N** |
| PublicationPackage → PublicationJob | **1 → N** |

**Retry:** does **not** create a new LaunchRun; does **not** create a new PublicationPackage without package change; creates a new execution attempt/job per publication contract.  
**History** is never overwritten.  
New business hypothesis / campaign scale → new CampaignFrame and/or new LaunchRun.

Content ∥ Visuals may run in parallel under a LaunchRun.

---

## 12. Artifact handoff

Semantic graph (no DB schema). Aliases to PRODUCT-02 catalog where noted; pins may need future catalog amend tickets (no unsigned P02 rewrite here).

```
ApprovedStrategyPackage
  → LaunchInputSnapshot
  → LaunchCandidate
  → ApprovedLaunchPackage
  → CampaignFrame (N)
  → OfferArtifact (N)
  → ContentRequest / VisualRequest
  → ContentAsset / VisualAsset
  → PublicationPackage
  → PublicationJob
  → DeliveryEvidence   (= MVP evidence name; ExecutionEvidence alias retired)
  → OutcomeRecord
```

| Artifact | Producer | Consumer | Mult. | Version | Approval | Immutable when approved | Invalidation | Binding | MVP |
|----------|----------|----------|-------|---------|----------|-------------------------|--------------|---------|-----|
| ApprovedStrategyPackage | Strategy | Launch | 1 head | Yes | strategy_package | Yes | New Strategy head / stale rules | tenant/project | Yes |
| LaunchInputSnapshot | Launch entry | LaunchRun | 1/run | Pin | handoff/`launch_eligible` | Snapshot | Strategy revoke/stale | tenant/project/run | Yes |
| LaunchCandidate | LaunchRun | Owner | N versions | Yes | — | No | Strategy change / abandon | run | Yes |
| ApprovedLaunchPackage | LaunchRun | Executors / export | 1 head | Yes | launch_package | Yes | New version supersedes head | run | Yes |
| CampaignFrame | Launch | Content/Pub | N/run | Yes | via package | With package | Package supersede | run | Yes |
| OfferArtifact | Launch | Frame / Content | N | Yes | via package | When approved | Structure/Strategy change | run | Yes |
| ContentRequest / VisualRequest | Launch | Executors | N | Soft | — | — | Package change | run | Yes |
| ContentAsset | Content | Publication | N | Yes | content | Yes | Stale vs new Package | run/frame | Yes |
| VisualAsset | Visuals | Publication | N | Yes | visual if used | Yes | Same | run/frame | Optional |
| PublicationPackage | Publication | Jobs | N | Yes | pub package | Yes | Asset/channel change | run | Path |
| PublicationJob | Publication | Evidence | N | Status | external | Terminal kept | Retry = new attempt/job | package | Path |
| DeliveryEvidence | Job | Outcome | N | Append | — | Append-only | Never delete | job | Path |
| OutcomeRecord | Outcome Capture | Owner | N | Yes | — | — | — | project + refs | When evidence |

---

## 13. Outcome Capture (OD-EM-09 — closes P1-EM-04)

**Project-level** capability post-execution. Consumes **DeliveryEvidence**. Not Launch executor · not full Analytics · not Optimization.

If LaunchRun stops at Package with no jobs: Outcome Capture = **N/A** (no fake empty success).

**MVP OutcomeRecord (logical fields):** project_id · LaunchRun ref · CampaignFrame ref · PublicationJob ref · delivery status · external identifier · timestamp · available basic metrics · actual cost if available · observation window · source/provider.

---

## 14. Export / handoff (OD-EM-10 — closes P1-EM-05)

**Approved Launch Package** is a portable deliverable.

| Form | MVP |
|------|-----|
| Customer-readable representation | Yes |
| Machine-readable JSON | Yes |
| PDF / DOCX / slides | **Post-MVP** |

**Export only approved version.** Required contents: Strategy version · Launch Package version · CampaignFrame(s) · Offer Artifact(s) · budget assumptions · Content/Visual requirements · Publication plan · approvals · limitations · unresolved assumptions · measurement criteria · next action.

**ACL:** tenant/project ownership + platform who-may. **No** secrets/tokens/credentials in export payloads. DeliveryEvidence exported separately when present.

---

## 15. MVP cut

### 15.1 Include

- Approved Strategy input (target)  
- ≥1 LaunchRun  
- ≥1 CampaignFrame  
- 1 Approved Launch Package  
- ≥1 Offer Artifact  
- Limited Content  
- Optional Visual  
- One Publication **channel in model** + ability to run one successful PublicationJob with external approval + DeliveryEvidence (product contract **C**)  
- Basic OutcomeRecord when evidence exists  
- Customer-readable + JSON export  

MVP product must prove contract **C**; a given LaunchRun may stop at contract **A**.

### 15.2 Post-MVP / reserved

Multi-channel orchestration · advanced budget UI · calendar/scheduling · full Analytics · Optimization · CRM · Team workflows · complex approval chains · asset experimentation · predictive performance · Billing.

---

## 16. Commercial value

| Question | Answer |
|----------|--------|
| Pays for (Launch stage) | **Approved Launch Package** — Strategy-pinned, approval-bound execution plan |
| Without publication | Offer + CampaignFrame(s) + requirements + gates + export — handoff-ready |
| With publication | Same + PublicationPackage + job + DeliveryEvidence |
| ≠ AI plan | Versioned, immutable when approved, invalidatable, exportable, fence-bound |
| Failure | Cannot approve eligible Package; dishonest publish claims; fence violations |

---

## 17. Code reuse map (inventory only — no compatibility claimed without proof)

| Subsystem | Status |
|-----------|--------|
| BusinessCampaign | **Reuse candidate** — audit required in Launch Architecture; not auto-canonical CampaignFrame |
| Offer Builder | **Adapter** (today CWF Launch Pack) |
| CWF Launch Pack | **Transitional / adapter** — not permanent EM LaunchRun |
| Content Factory / assets | **Adapter / legacy** toward Content under Launch |
| Visual asset foundation | **Adapter / legacy** |
| PublicationPackage / PublicationJob | **Adapter** — reuse foundations |
| Delivery / PublicationDeliveryLog | **Adapter** for DeliveryEvidence |
| Execution / connector approvals | **Adapter** toward ApprovalRecord |
| Telegram publication | **Reusable foundation** (gated) |
| Operational / campaign metrics | **Legacy** ≠ OutcomeRecord |
| Capability Registry | **Aligns** (planned) — not authz |

Uniqueness debt (`uq_lpr_owner_verdict`, `uq_offer_launch_pack`, `uq_publication_packages_asset_channel`) conflicts target multiplicity — resolve in Launch Architecture / Runtime, not here.

---

## 18. Owner decisions applied (OD-EM-01…10)

| ID | Decision | Status |
|----|----------|--------|
| OD-EM-01 | Launch = project-stage capability + LaunchRun; Package = artifact | **OWNER-APPROVED A** |
| OD-EM-02 | Primary deliverable = Approved Launch Package | **OWNER-APPROVED** |
| OD-EM-03 | Budget: Strategy assumptions / Launch envelope / Execution actuals; unknown OK for Package; block paid external without ack | **OWNER-APPROVED** |
| OD-EM-04 | CampaignFrame inside Launch; BusinessCampaign = reuse candidate only | **OWNER-APPROVED** |
| OD-EM-05 | Offer Structure ≠ Offer Artifact; 1→N | **OWNER-APPROVED** |
| OD-EM-06 | Three contracts A/B/C | **OWNER-APPROVED** |
| OD-EM-07 | Minimal typed approvals; no mandatory separate launch_start if handoff OK | **OWNER-APPROVED** |
| OD-EM-08 | One-to-many multiplicity; retry ≠ new LaunchRun | **OWNER-APPROVED** |
| OD-EM-09 | Outcome Capture project-level evidence consumer | **OWNER-APPROVED** |
| OD-EM-10 | Approved-only export + ACL + no secrets; PDF post-MVP | **OWNER-APPROVED** |

---

## 19. Finding closure

| ID | Status |
|----|--------|
| P0-EM-01 | **CLOSED** — LaunchRun vs Package + BOM |
| P0-EM-02 | **CLOSED** — three contracts |
| P0-EM-03 | **CLOSED** — CampaignFrame |
| P0-EM-04 | **CLOSED** — budget split + ack |
| P1-EM-01…05 | **CLOSED** for freeze (Offer, approvals, multiplicity, Outcome, export) |
| P1-EM-06 | **CLOSED** — DeliveryEvidence canonical MVP name |
| P1-EM-07 | **Deferred** (CWF retire sequencing) — not EM freeze blocker |
| P2-* | Hygiene / Launch Architecture |

---

## 20. Freeze record (applied)

| Field | Value |
|-------|-------|
| Patch task | PRODUCT-04-EXECUTION-MODEL-PATCH-01 = **docs_verified** |
| Execution Model | **OWNER-FROZEN** (2026-08-02) |
| **`owner_freeze`** | **OWNER-FROZEN** |
| Launch Architecture | **NOT STARTED** |
| Next priority | **NOT SET** |

### Owner freeze checklist

1. ☑ OD-EM-01…10 accepted  
2. ☑ P0-EM-01…04 closed  
3. ☑ Three contracts explicit  
4. ☑ LaunchRun ≠ Package  
5. ☑ CampaignFrame unambiguous  
6. ☑ Budget / Offer / approvals / multiplicity / Outcome / export explicit  
7. ☑ PRODUCT-02/03 invariants preserved  
8. ☑ CWF.1 maps to contract **C**  
9. ☑ Owner message: Execution Model = **OWNER-FROZEN** (2026-08-02)  
10. ☐ PRODUCT-04-LAUNCH-ARCHITECTURE-01 — only after separate kickoff; next priority currently **NOT SET**  

---

## Appendix A — Normative sources

PRODUCT-02 OWNER-FROZEN pack · PRODUCT-03 Strategy pack · CWF.1 / PRODUCT-FINISH-01 (E2E = contract C) · Capability Registry (availability only)

## Appendix B — Non-starts

No Launch Architecture pack · no Runtime · no code · no Registry/Journey/IA edits · no P02/P03 freeze text rewrite · no Billing.
