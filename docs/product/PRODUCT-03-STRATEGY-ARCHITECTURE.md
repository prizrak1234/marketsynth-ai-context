# PRODUCT-03 — Strategy Architecture and Commercial Blueprint

> **Program ID:** **PRODUCT-03** = Strategy Architecture (canonical)  
> **Task:** PRODUCT-03-STRATEGY-BLUEPRINT-01 · **Patch:** PRODUCT-03-STRATEGY-BLUEPRINT-PATCH-01  
> **Type:** Docs-only product architecture  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **OD-P03-01…10:** **OWNER-APPROVED** (variant A + clarifications, 2026-08-02)  
> **Basis:** OD applied · P0-01…07 closed · freeze-blocking P1 closed · consistency PASS · reviewers 5/5 PASS · no code/runtime/research  
> **Inherits:** PRODUCT-02 OWNER-FROZEN invariants (`OWNER-FREEZE.md`) — pack text not casually rewritten  
> **Does not:** start Strategy Runtime, change IA/Registry/Journey runtime, or modify code

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-03 Strategy Architecture
basis: OD-P03-01…10 applied; P0-01…07 closed; freeze-blocking P1 closed; consistency matrix PASS; reviewers 5/5 PASS; code/runtime/research unchanged
```

### Frozen invariants (normative)

1. Strategy — one project-stage capability and one commercial SKU.  
2. SC-01…SC-07 — internal Strategy units, not separate products.  
3. Strategy Package — single versioned artifact.  
4. Approved Strategy is immutable.  
5. Any edit/regenerate creates a new version.  
6. Package-level approval — primary MVP contract.  
7. Partial Research requires explicit owner override.  
8. Override may be revoked; dependents invalidated without deleting history.  
9. Strategy is pinned to a concrete Research version.  
10. Stale — derived state (eligibility labels; not ArtifactVersionState enum).  
11. Strategy and Launch are separated: Strategy = whom / what / why / channel direction; Launch = concrete execution.  
12. Offer Structure ≠ Launch Offer Artifact.  
13. Channel Direction ≠ media execution.  
14. MVP Strategy includes SC-01…SC-07, package approval, handoff, and export.  
15. Pricing engine, advanced funnel, predictive ROI, CRM strategy, optimization — post-MVP.  
16. Only approved version is exported.  
17. Capability Registry is not authorization.  
18. Freeze does **not** auto-start Strategy Runtime.

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Accept PRODUCT-03 Strategy Blueprint as OWNER-FROZEN | Start Strategy Runtime |
| Authorize planning against these invariants | Auto-start Research Hardening |
| Enable deferred Journey/IA/Registry ticket after freeze | Edit Capability Registry / Journey / IA in this act |
| | Start Skills Stage 2 automatically |

**Deferred:** `PRODUCT-03-JOURNEY-IA-DRIFT-01` · `PRODUCT-02-ARTIFACT-CATALOG-AMEND-STRATEGY-PINS`  
**Next priority:** **NOT SET** (owner chooses separately)

---

## 0. Paths: current vs target (P0-07 closed as documentation)

| Path | Sequence | Status |
|------|----------|--------|
| **Current implemented (transitional)** | Research → owner decision → **Launch Pack / Offer (CWF)** | Live customer path until Strategy Runtime |
| **Target frozen spine** | Research → owner decision → **Strategy** → thin Launch → … | This blueprint; **not** implemented |

Until Strategy Runtime ships: product UI must **not** claim Strategy is live. Registry `project.strategy` remains planned/reserved.  
**Follow-up (after PRODUCT-03 freeze, before Strategy Runtime):** Journey/IA/Registry patch — Continue → Strategy; amend Active slice A→B→C→E; J3.1 next action. Ticket placeholder: `PRODUCT-03-JOURNEY-IA-DRIFT-01` (not this task).

Historical Visual golden path uses **superseded program label** — see §17. Filename retained.

---

## 1. What Strategy is (normative)

**Strategy** is the **system of owner-approved commercial decisions** that converts a **pinned Research artifact set** into an **approved direction of action** for Launch.

| Question | Strategy responsibility |
|----------|-------------------------|
| Whom? | SC-01 Segment / ICP |
| How we win / what we promise? | SC-02 Positioning + Value Proposition |
| What we sell (structure)? | SC-03 Offer Structure (+ pricing **assumptions**) |
| What we say? | SC-04 Messaging |
| Where first (direction)? | SC-05 Channel Direction |
| What Launch must not violate? | SC-06 Launch Constraints (**fence**, not SKU) |
| How we know it worked? | SC-07 Measurement Criteria (**honesty bar**, not SKU / not Analytics) |

Strategy is **not:** AI essay · Research rewrite · Content plan · Launch plan · auto-continue after Partial Research.

**Paid deliverable:** **Approved Strategy Package** (customer-readable + machine JSON) — one commercial SKU for Strategy, not seven micro-products.

---

## 2. Commercial value

| Question | Answer |
|----------|--------|
| Pays for | Locked decisions in one approved package |
| vs prompt | Pins, ApprovalRecords, versioning, revoke, export, Launch gate |
| Failure | Unlinked claims, hidden Partial confidence, Launch without approval, generic advice |
| Export | Customer-readable + JSON of **approved** version only (§16) |

---

## 3. Research / Strategy / Launch boundary

| Layer | Owns | Does not own |
|-------|------|--------------|
| **Research** | Evidence, findings, risks, gaps, verdict/partial | Positioning/offer locks |
| **Strategy** | Whom, positioning/VP, offer **structure**, messaging, channel **direction**, constraints, success criteria | Budget ops, schedules, media plan, posts, publish jobs |
| **Launch** | Sequence, budget ops, Offer **Artifact**, assets, schedule, publication package | Re-deciding Strategy without revision |
| **Content / Visuals / Publication** | Concrete assets / external execution | Strategy pillars rewrite |

**Offer split:** Strategy = Offer Structure Decision · Launch = Offer Artifact (today’s Offer Builder maps here **after** Strategy in target spine).  
**Channel split:** Strategy = preferred channels + why + risks/assumptions · Launch = budget, sequence, schedule, execution.

---

## 4. Input contract (pinned)

Strategy consumes **StrategyInputSnapshot** (semantic pin — see §12), never “latest blob.”

**Mandatory (full path):** accepted Research (`research_acceptance`) · Research version ids · evidence refs · findings/risks/limitations · geography · product context · owner decision.  

**Partial path:** + unresolved gaps · confidence limits · explicit assumptions · `partial_strategy_override` · fixed list of accepted risks.

**Forbidden:** unpinned data · sibling-project artifacts · MarketingPlan as silent Strategy source.

---

## 5. Strategy Package (OD-P03-02)

**One** `StrategyPackage`. MVP may use **one Strategy capability run** producing the whole package. SC units are **sections**, not mandatory separate CapabilityRun pipelines.

| Section | Role |
|---------|------|
| `summary` | Strategy Summary |
| SC-01…SC-07 | Composition units |
| `risks` | Risks |
| `open_assumptions` | Open assumptions |
| `limitations` | Limitations |
| `next_action` | Recommended next action (usually Launch handoff) |

Section lineage is **semantic** (traceable within package versions). Separate orchestration per SC is **not** MVP.

---

## 6. Decomposition (OD-P03-01 · OWNER-APPROVED)

```text
project.strategy  (one Project stage · one nav/panel)
├── SC-01 Segment / ICP
├── SC-02 Positioning + Value Proposition
├── SC-03 Offer Structure
├── SC-04 Messaging
├── SC-05 Channel Direction
├── SC-06 Launch Constraints      ← boundary/honesty (not SKU)
└── SC-07 Measurement Criteria    ← boundary/honesty (not SKU)
```

**Forbidden:** seven commercial modules, seven sidebar entries, seven required CapabilityRuns for MVP.

---

## 7. Partial Research (OD-P03-04 · OWNER-APPROVED)

1. Partial **never** auto-opens Strategy.  
2. Explicit `partial_strategy_override` + visible limitations.  
3. `assumption_constrained=true`; inherited gaps/limitations; lower confidence; fixed accepted-risks list.  
4. May block incomplete SC fields and Launch handoff (critical gaps: SC-01 primary segment, SC-03 offer structure, SC-05 primary channel without evidence **or** assumption).  
5. `launch_handoff_approval` requires `accepted_gap_ids[]` + `residual_gap_ids[]` when constrained.  
6. **Cannot** clear `assumption_constrained` via handoff or revalidation alone.

### 7.1 Override revoke (closes P0-05)

Owner may **revoke** `partial_strategy_override` (ApprovalRecord → `invalidated` / `expired` via PRODUCT-02 fields).

**On revoke:**

| Effect | Rule |
|--------|------|
| StrategyInputSnapshot created under that override | **Invalidated / unusable** — no new Candidate from it |
| Strategy candidate | ArtifactVersionState `invalidated`; eligibility blocked |
| Approved Strategy bytes | **Not deleted**; Launch eligibility blocked (`stale_launch_blocking`) |
| Launch handoff | **Blocked** |
| Already handed-off Launch | Mid-Launch owner decision required (continue / rebuild / cancel / partial) — same pattern as §10.4 |
| History | **Preserved** |
| Resume | New Research acceptance **or** new override (+ new SIS) |

Attribution on edits: `edited_by` is server-attested — never client-writable (same rule as `decided_by`).

---

## 8. Approvals (OD-P03-03 · OWNER-APPROVED)

No boolean. **Primary MVP:** `strategy_package_approval`.

| Type | Role |
|------|------|
| `strategy_package_approval` | **Primary** — locks package |
| `partial_strategy_override` | Partial → Strategy |
| `budget_assumptions_acknowledgement` | When any spend_band field present (see Cards SC-03) |
| `research_revalidation` | Discouraged Launch-continue without new Strategy version |
| `launch_handoff_approval` | Enter LaunchInputSnapshot |
| `strategy_candidate_review` | Optional soft clarification (not Launch unlock) |
| `strategy_rollback` | Restore prior approved head |

**Not required:** per-SC approvals.

**Always pinned:** tenant · project · Strategy artifact id/version · Research version · actor (server-attested) · timestamp · decision · reason/comment.  
Registry ≠ authorization. Who-may inherits platform ACL (owner/manager class) — Strategy pack does not invent a second authz system.

---

## 9. Edit / regenerate / versioning (OD-P03-07/08 · closes P0-04)

**Any** of the following creates a **new** StrategyPackage version (no in-place mutation of an existing version record):

- section edit (manual);  
- section regenerate;  
- full candidate regenerate;  
- cascade must-refresh after dependency change.

**Approved package:** immutable. Edits require new version + **new** `strategy_package_approval`.

### Manual owner edit rules

| Rule | Normative |
|------|-----------|
| New version | Always |
| Attribution | `edited_by` + timestamp (server-attested) |
| Prior AI/version | Preserved (immutable history; `supersedes` / previous_version_id) |
| Assertion without evidence | Becomes **owner assumption** |
| Broken evidence link | Explicit `evidence_link_status=broken` (blocks ready_for_review until fixed or assumption-tagged on constrained path) |
| Re-approval | Required before Launch |

**Rollback:** point current approved pointer to prior approved version; record `strategy_rollback`; do not mutate prior bytes.

---

## 10. Stale / pointers / mid-Launch (OD-P03-09 · closes P0-01 locally)

### 10.1 PRODUCT-02 vs PRODUCT-03 vocabulary (no silent P02 rewrite)

| Layer | Meaning |
|-------|---------|
| PRODUCT-02 ArtifactVersionState | `draft` / `ready_for_review` / `approved` / `rejected` / `superseded` / `invalidated` / `archived` — **no** `stale` enum |
| PRODUCT-02 UI “stale” (frozen) | Derived: status ∈ {superseded, invalidated} **or** version ≠ type head |
| PRODUCT-03 **eligibility labels** (this pack) | Derived overlays for Strategy Launch gating — **not** new ArtifactVersionState values |

### 10.2 Current pointer contract

| Pointer | Meaning |
|---------|---------|
| `strategy_approved_head` | Current approved Strategy version (if any) |
| `strategy_candidate_head` | Current draft / in-review candidate |
| `research_pin` | Research version(s) on StrategyInputSnapshot / package |
| `research_head` | Latest Research terminal version for project |

### 10.3 Derived Strategy eligibility labels

| Label | When | Launch |
|-------|------|--------|
| `stale_viewable` | Package readable in history / not Launch pin | N/A |
| `stale_launch_blocking` | Trigger list below — **not** emitted for pin-mismatch when `revalidated` applies | **Blocked** |
| `revalidated` | Active `research_revalidation` for `(strategy_approved_head, research_head)` | May Launch if other gates pass |

P02 `superseded` / `invalidated` remain **ArtifactVersionState** values (not eligibility overlays).

**Precedence:** `revalidated` (pin-mismatch only) > `stale_launch_blocking` > `stale_viewable`.

**`stale_launch_blocking` triggers** (evaluated on Launch pin = `strategy_approved_head`):

1. `research_pin ≠ research_head` **AND** no active `research_revalidation` for `(strategy_approved_head, research_head)`; **or**  
2. Enabling `partial_strategy_override` revoked/expired/invalidated; **or**  
3. Owner explicitly blocked Launch eligibility on this approved head.

**Does not trigger:** changes on unapproved `strategy_candidate_head`. Approved head stays Launch-eligible during mid-revise until triggers 1–3 fire or a **new** approved head replaces it.

**`launch_eligible`:**

```text
launch_eligible =
  strategy_approved_head.status == approved
  AND package == strategy_approved_head
  AND NOT stale_launch_blocking
  AND launch_handoff_approval satisfied
  AND partial critical-gap rules satisfied
```

(Pin match **or** active revalidation is already encoded inside trigger 1 / `revalidated`.)  
**Default:** revise on new Research. **`research_revalidation`:** discouraged; MUST NOT strip `assumption_constrained`, invent evidence, or upgrade confidence.

### 10.4 Mid-Launch (P1-04 closed)

If Launch already consumes approved Strategy version **V**:

- New Strategy candidate **must not** rewrite Launch in place.  
- System creates new Strategy candidate / version.  
- Owner chooses: continue current Launch · rebuild Launch · cancel Launch · partially update dependents.  
- Existing Launch artifacts retained until owner decision.

---

## 11. UI topology (placement only)

Project Command Center → Strategy **panel/stage** (not Workspace app, not flat nav).  
IA/Journey/Registry edits = follow-up `PRODUCT-03-JOURNEY-IA-DRIFT-01` after freeze.

---

## 12. Semantic artifact model (closes P0-02 without editing OWNER-FROZEN P02)

| Semantic name | Role | PRODUCT-02 relation |
|---------------|------|---------------------|
| `StrategyInputSnapshot` | Immutable pin of Research versions + owner decision / override | Logical pin / `created_from` — **follow-up** to add to P02 catalog only via owner-signed P02 amendment |
| `StrategyCandidate` | StrategyPackage in draft / ready_for_review | Package + ArtifactVersionState |
| `ApprovedStrategyPackage` | StrategyPackage + `strategy_package_approval` | StrategyPackage approved |
| `LaunchInputSnapshot` | Pin of approved Strategy (+ Research) for Launch | Logical pin into LaunchPackage — P02 catalog follow-up |

**This patch does not edit** `docs/product/ARTIFACT-FLOW.md` (OWNER-FROZEN). Follow-up ticket: `PRODUCT-02-ARTIFACT-CATALOG-AMEND-STRATEGY-PINS` (owner-gated).

---

## 13. KPIs / Launch readiness

| ID | Item |
|----|------|
| LR-01 | MVP sections + package fields complete |
| LR-02 | `strategy_package_approval` on approved head |
| LR-03 | `launch_eligible` (§10.3) |
| LR-04 | SC-05 primary channel |
| LR-05 | SC-06 constraints non-empty |
| LR-06 | SC-07 ≥1 criterion |
| LR-07 | If constrained: gap acks on handoff |
| LR-08 | If any of `spend_band_min`, `spend_band_max`, `spend_band_currency` set: each has provenance + `budget_assumptions_acknowledgement` |

KPIs: evidence-linked ratio · assumption count · approval/revision count · time to approve · invalidation counts · acceptance rate · LR completeness %. No ROI promises.

---

## 14. Code reuse map

Unchanged thesis: Offer Builder → Launch after Strategy; skill schemas reusable; MarketingStrategy legacy vocabulary; Launch Pack gate UX reusable; no ApprovalRecord in app yet; Registry planned ≠ authz.

---

## 15. Owner decisions — **OWNER-APPROVED**

| ID | Decision | Status |
|----|----------|--------|
| OD-P03-01 | One stage; SC-01…07 internal; SC-06/07 not SKUs | **OWNER-APPROVED A** |
| OD-P03-02 | One StrategyPackage; one run OK for MVP | **OWNER-APPROVED A** |
| OD-P03-03 | Package-level primary; typed extras only | **OWNER-APPROVED A** |
| OD-P03-04 | Strict Partial wall + revoke | **OWNER-APPROVED A** |
| OD-P03-05 | Pricing assumptions only + provenance | **OWNER-APPROVED A** |
| OD-P03-06 | Channel direction only | **OWNER-APPROVED A** |
| OD-P03-07 | Edit/regen section or full → new version | **OWNER-APPROVED A** |
| OD-P03-08 | Manual edits with attribution + re-approval | **OWNER-APPROVED A** |
| OD-P03-09 | Derived eligibility labels + mid-Launch owner choice | **OWNER-APPROVED A** |
| OD-P03-10 | Customer-readable + JSON approved export | **OWNER-APPROVED A** |

---

## 16. Export (OD-P03-10)

| Export | MVP |
|--------|-----|
| Customer-readable Strategy Package | Yes |
| Machine-readable JSON | Yes |
| PDF/DOCX/Slides | Post-MVP |

**Only approved version.** Contents: artifact id/version · Research version · SC-01…07 · evidence refs · assumptions · limitations · risks · approval metadata · generated/edited attribution · derived eligibility label at export time.  
**ACL:** tenant + project ownership required.

---

## 17. Program ID (closes P0-06 · option A)

| Label | Meaning |
|-------|---------|
| **PRODUCT-03** (unqualified) | **Strategy Architecture** — this pack |
| Historical Visual path | File `PRODUCT-03-VISUAL-ASSET-GOLDEN-PATH.md` retained; alias **LEGACY-PRODUCT-03-VISUAL-ASSET-GOLDEN-PATH** · `program_id_status: SUPERSEDED_ID` · canonical = PRODUCT-FINISH-01 Step J |

---

## 18. Companion docs

1. [PRODUCT-03-STRATEGY-ARTIFACT-FLOW.md](./PRODUCT-03-STRATEGY-ARTIFACT-FLOW.md)  
2. [PRODUCT-03-STRATEGY-CAPABILITY-CARDS.md](./PRODUCT-03-STRATEGY-CAPABILITY-CARDS.md)  
3. [PRODUCT-03-STRATEGY-OWNER-JOURNEY.md](./PRODUCT-03-STRATEGY-OWNER-JOURNEY.md)  
4. [PRODUCT-03-STRATEGY-MVP-CUT.md](./PRODUCT-03-STRATEGY-MVP-CUT.md)  
5. [PRODUCT-03-STRATEGY-BLUEPRINT-AUDIT.md](./PRODUCT-03-STRATEGY-BLUEPRINT-AUDIT.md) (§23 PATCH validation)

---

## 19. Patch pass status

| Criterion | Status |
|-----------|--------|
| OD-P03-01…10 applied | Yes |
| P0 closures | See audit §23 |
| Code unchanged | Yes |
| `owner_freeze` | **OWNER-FROZEN** (2026-08-02) |
