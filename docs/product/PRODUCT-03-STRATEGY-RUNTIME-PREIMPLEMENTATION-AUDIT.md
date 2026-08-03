# PRODUCT-03 — Strategy Runtime Preimplementation Audit

> **Task:** PRODUCT-03-STRATEGY-RUNTIME-01-PREIMPLEMENTATION-AUDIT  
> **Title:** Strategy Runtime Readiness and Reuse Audit  
> **Type:** Read-only technical audit  
> **Priority:** **P0** — sole active priority (2026-08-02)  
> **Status:** **docs_verified** · audit complete · **implementation NOT STARTED**  
> **Code / migrations / UI:** **unchanged**  
> **Research real smoke / Evidence Hardening:** **PAUSED** until **2026-08-18**  
> **Visual / Publication Architecture:** **NOT STARTED** (deferred while this P0 is active)

---

## 1. Verdict

| Field | Value |
|-------|-------|
| **Verdict** | **READY TO PLAN** Strategy Runtime against frozen PRODUCT-03 — **not** ready to declare P0.6 `MarketingStrategy` canonical |
| **Safe path before 2026-08-18** | Implement Strategy Runtime on **pinned Research/Verdict fixtures** (harness + persisted historical artifacts) · **no new real Research run** · **no** fixture binding in commercial customer path |
| **Primary reuse** | BusinessVerdict eligibility · evidence snapshot hashes · P0.6 version/supersede/review UX patterns · FE eligibility adapters · Fabric CapabilityRun / InputSnapshot / ApprovalRecord **semantics** |
| **Primary gap** | PRODUCT-03 entities (`StrategyInputSnapshot`, `StrategyRun`, SC-01…07 package, typed `strategy_package_approval`, research pin, stale labels, export) are **mostly missing** |
| **Do not start yet** | Launch Runtime · Visual/Publication Architecture · Research Hardening · Registry/Journey cutover without ticket · declaring MarketingStrategy = StrategyPackage |

**One-line thesis:** Build a **new Pattern-compliant Strategy Runtime** that **adapts** (does not canonize) P0.6 MarketingStrategy and **pins** today’s Research/Verdict artifacts as interim research identity until Evidence Hardening lands.

---

## 2. Current implementation inventory

### 2.1 Live Strategy-related stack (P0.6)

| Layer | Path | What exists |
|-------|------|-------------|
| DB | `app/db/models/marketing_strategy.py` → `MarketingStrategyTable` | Single table `marketing_strategies`: verdict + evidence pins, integer `version`, lifecycle, section JSON blobs, in-row `approved_*`, `metadata.review_events` |
| Repo | `app/db/repositories/marketing_strategies.py` | `get_by_id_for_owner`, `next_version`, `list_for_project`, `latest_approved`, `latest_any` |
| Domain | `app/domain/marketing_strategy_engine.py` | Verdict gate, positioning/offers/channel validation, readiness |
| Domain | `app/domain/business_verdict_engine.py` → `compute_strategy_eligibility` | GO / CONDITIONAL_GO eligibility |
| Service | `app/services/marketing_strategy_service.py` | `create`, `build_deterministic_draft` (**no LLM**), `update_draft`, submit/approve/reject/return/archive/supersede |
| API | `app/api/routes/marketing_strategies.py` | CRUD + lifecycle under `/projects/{id}/marketing-strategies` |
| Contracts | `app/schemas/contracts.py` (~3883+) | `MarketingStrategy*` models + nested Strategy* section types |
| Migration | `alembic/versions/20260614_0034_marketing_strategy_commercial_mvp_p0_6.py` | Creates `marketing_strategies` |
| Tests | `tests/test_commercial_mvp_p0_6_marketing_strategy.py` | Draft firewall, NOGO block, approve creates no plan/agent/LLM |

### 2.2 Research / verdict inputs (interim “ResearchArtifact”)

| Artifact in code | Path | Role vs PRODUCT-03 “Research” |
|------------------|------|-------------------------------|
| `CommercialResearchRunTable` | `app/db/models/commercial_research_run.py` | Research run lifecycle (BIV/CWF) |
| `BusinessVerdictTable` | `app/db/models/business_verdict.py` | Owner decision / verdict gate used by P0.6 |
| `BusinessVerdictEvidenceSnapshotTable` | same | Evidence pin (`id` + `hash`) copied onto MarketingStrategy |
| No type named `ResearchArtifact` | — | Blueprint name; map via adapter identity (see §5) |

### 2.3 Parallel / non-canonical “strategy” vocabularies

| Path | Role | Note |
|------|------|------|
| `app/marketing/strategy_contracts.py` | Markdown ContentAsset quality for Strategist specialist | **Not** Strategy Package |
| Marketing department Strategist agents / ContentAssets | Conveyor drafts | **Not** PRODUCT-03 Runtime |
| `web/src/lib/strategy/*` (mock, localStorage Alpha) | Product Alpha local strategy | Legacy UI support |
| CWF Launch Pack / Offer Builder | Live commercial path | **Bypasses** Strategy (transitional — Blueprint §0) |

### 2.4 Downstream consumers

| Consumer | Strategy coupling |
|----------|-------------------|
| `ImplementationPlan` | Pins `marketing_strategy_id` + version (P0.6) |
| Offer Builder (`app/product/offer_builder/`) | **None** — BIV verdict only |
| Launch Pack (`launch_pack_service.py`) | **None** — BIV + Offer |
| Commercial workflow | Research → decision → Launch Pack / Offer |

### 2.5 Frontend

| Surface | Path | Note |
|---------|------|------|
| Strategy page | `web/.../projects/[projectId]/strategy/page.tsx` | Behind `LegacyProjectPipelineGuard` |
| Workspace view | `strategy-workspace-view.tsx` | Calls P0.6 build-draft / approve |
| Adapters | `strategy-adapter.ts`, `strategy-eligibility.ts`, `marketing-strategy-api-adapter.ts`, index adapters | Integration glue to P0.6 |
| Registry | `project.strategy` planned/reserved | Must **not** claim live Strategy until Runtime DoD |

### 2.6 LLM

P0.6 generation = **deterministic template only**. Origin enum reserves `FUTURE_LLM_ASSISTED`. No provider calls on MarketingStrategy create/approve. Optional real LLM over **fixture inputs** is allowed in test harness only (see §10).

---

## 3. Frozen contracts inherited

| Source | Status | What Strategy Runtime must honor |
|--------|--------|----------------------------------|
| PRODUCT-03 Strategy Blueprint | **OWNER-FROZEN** | Invariants 1–18 · SC-01…07 · Partial wall · package approval · pin · stale · export · freeze ≠ Runtime |
| PRODUCT-02 lifecycle / artifacts / approvals | **OWNER-FROZEN** | ApprovalRecord semantics · versioning · tenant/project · no boolean “approved” as SoT |
| PRODUCT-04 Execution Model | **OWNER-FROZEN** | Strategy ≠ Launch · Offer Structure ≠ Offer Artifact · A/B/C · 1 Strategy → N LaunchRuns |
| PRODUCT-04 Execution Fabric | **OWNER-FROZEN** | CapabilityRun states · InputSnapshot immutability · retry≠rerun · ApprovalRecord not run state · restore |
| PRODUCT-04 Capability Pattern | **OWNER-FROZEN** | Form for capability Runtime; no new foundation; no parallel run model |
| Launch / Content Architecture | **OWNER-FROZEN** | Do **not** implement Launch/Content Runtime in this program |
| Transitional honesty | PRODUCT-03 §0 / MVP Cut §4 | CWF Launch/Offer remains live until Strategy Runtime + Journey/IA cutover |

**Deferred tickets (not this audit):** `PRODUCT-03-JOURNEY-IA-DRIFT-01` · `PRODUCT-02-ARTIFACT-CATALOG-AMEND-STRATEGY-PINS`

---

## 4. Reuse map (A–F)

| Element | Class | Evidence / rule |
|---------|-------|-----------------|
| `BusinessVerdict` eligibility (GO / CONDITIONAL_GO) | **A** | Keep as gate component inside StrategyInputSnapshot builder |
| Evidence snapshot id/hash persistence pattern | **A** | Reuse pin fields; extend to full research pin set |
| Tenant/project ownership checks on strategy routes | **A** | Preserve isolation patterns |
| P0.6 lifecycle transitions (draft → review → approve) | **B** | Map to Candidate + `strategy_package_approval`; do not treat row boolean as ApprovalRecord |
| P0.6 version + supersede | **B** | Map to StrategyPackageVersion lineage |
| P0.6 section JSON (segments, positioning, offers, channels, metrics) | **B** | Adapter → SC-01…03, SC-05, SC-07; fill SC-04 Messaging + SC-06 fences |
| `marketing_strategy_engine` validators | **B** | Keep as section validators under SC units |
| FE eligibility / API adapters | **B** | Retarget to new contracts; drop Alpha mock as product path |
| ImplementationPlan strategy pin | **C** | Remap when package ids change |
| Strategist ContentAsset / `strategy_contracts.py` | **D** | Isolated; not Strategy Package |
| Legacy Strategy UI + localStorage Alpha | **D** | Not Command Center product path |
| Deterministic-only draft as customer “AI Strategy” | **D** | Honest as draft assist; not paid package alone |
| Offer Builder / Launch Pack without Strategy | **E** (target spine) | Transitional live; cutover via Journey ticket — **do not** rewrite Launch Runtime here |
| Declaring `MarketingStrategyTable` = ApprovedStrategyPackage | **E** | Single-row approve ≠ Fabric ApprovalRecord + SC package |
| `StrategyInputSnapshot` | **F** | Missing |
| `StrategyRun` (CapabilityRun) | **F** | Missing |
| Typed `StrategyCandidate` / package version entity | **F** / **C** | Semantic only on P0.6 row |
| `StrategyApprovalRecord` / `strategy_package_approval` | **F** | Missing (row fields only) |
| `partial_strategy_override` | **F** | Missing |
| Named `strategy_approved_head` / `strategy_candidate_head` | **F** / soft **C** | Soft via `latest_approved` |
| Derived stale labels | **F** | Missing |
| SC-04 Messaging as first-class section | **F** | Absent in P0.6 |
| Export approved package (customer + JSON) | **F** | Missing |
| LLM-assisted candidate generation | **F** | Reserved origin only |
| Unified Fabric ApprovalRecord store | **F** | Project-wide gap; Strategy may introduce typed strategy approvals first without universal store rewrite |

---

## 5. Missing runtime contracts (logical minimum)

Do **not** invent a second Fabric. Bind PRODUCT-03 names to Fabric Pattern:

| Logical entity | Fabric / Pattern role | MVP requirement |
|----------------|----------------------|-----------------|
| **StrategyInputSnapshot** | InputSnapshot | Immutable pin: Research/Verdict version ids · evidence refs · owner decision · optional `partial_strategy_override` · gaps/assumptions |
| **StrategyRun** | CapabilityRun (`capability_id = project.strategy`) | One run may fill whole package (OD-P03-02) |
| **StrategyCandidate** | ArtifactVersion draft / ready_for_review | SC-01…SC-07 + summary/risks/assumptions/limitations |
| **StrategyPackageVersion** | Versioned StrategyPackage | Edit/regen → **new** version; approved immutable |
| **StrategyApprovalRecord** | ApprovalRecord | Primary: `strategy_package_approval`; extras: override, budget ack, launch_handoff (handoff may defer) |
| **research_pin** | Pin fields on snapshot/package | Concrete Research identity (see interim mapping below) |
| **strategy_candidate_head** | Pointer | Current draft/review |
| **strategy_approved_head** | Pointer | Current approved |
| **stale / invalidation** | Derived labels | `stale_viewable` · `stale_launch_blocking` · `revalidated` + P02 superseded/invalidated |

### Interim research identity (until Evidence Hardening)

Blueprint says “ResearchArtifact version.” Code has no `ResearchArtifact` type. **Runtime must pin a stable composite** without waiting for rename:

```text
research_pin (interim) =
  commercial_research_run_id + status/version markers (if present)
  + business_verdict_id + business_verdict_version
  + evidence_snapshot_id + evidence_snapshot_hash
```

After 2026-08-18 Evidence Hardening: **adapter mapping** from hardened Research artifact → same StrategyInputSnapshot fields — **no Strategy rewrite** if pin is versioned and opaque to generators.

---

## 6. Persistence / migration needs

| Boundary | Need migration? | Notes |
|----------|-----------------|-------|
| StrategyInputSnapshot store | **Yes** (new table or immutable JSON blob with id) | Required for pin/restore |
| StrategyRun + attempts | **Yes** | Fabric CapabilityRun semantics |
| Strategy package versions (SC payload) | **Yes** (new or evolved) | Prefer **new** package tables + **B adapter** from P0.6 rather than overloading `marketing_strategies` as canonical |
| Approval records for strategy types | **Yes** | At least strategy-scoped ApprovalRecord table or typed rows; do not fake via `approved_at` alone |
| Pointers (candidate/approved heads) | **Yes** (columns or pointer table) | Soft `latest_*` insufficient for cold restore honesty |
| Stale labels | **No** dedicated enum table | Derived at read time |
| P0.6 `marketing_strategies` | **Keep** during transition | **D legacy** read/adapter; no silent dual-write as two product truths |
| Offer/Launch tables | **No** in Strategy Runtime MVP | Cutover later |
| Universal Fabric ApprovalRecord for all capabilities | **Not required** for Strategy MVP | Avoid foundation creep |

**Physical schema not designed here** — only boundaries that will need Alembic when implementation starts.

---

## 7. Backend scope (when implementation starts)

**In scope for Strategy Runtime MVP**

1. Contracts-first: snapshot, run, candidate/package version, approval types, eligibility labels.  
2. Persistence + repository isolation (tenant/project).  
3. Eligibility: Full Research/Verdict · Partial + override · Partial without override → **block**.  
4. Generate whole candidate (deterministic first; optional LLM later behind origin flag).  
5. Manual section edit → new version + attribution.  
6. Regenerate section / whole → new candidate/version (never mutate approved).  
7. Reject / return / approve (package-level).  
8. Research superseded before/during run → block or stale rules (OD-P03-09).  
9. Cold restore composition (heads + pins + pending approval).  
10. Export approved only (customer-readable + JSON).  
11. Honest provider failure surfaces (if LLM enabled).

**Out of backend MVP**

- Launch Package generation · Content/Visual generation · Pricing engine · ROI · multi-market · CRM · Analytics · dual-stack Publication · Registry edits · Journey/IA cutover (separate ticket).

---

## 8. Frontend scope (when implementation starts)

| In | Out |
|----|-----|
| Command Center **Strategy** panel (post Journey/IA ticket or gated preview) | Claiming Strategy live in Registry before DoD |
| Review SC-01…07 · evidence vs assumption · Partial limitations | Legacy Alpha localStorage as SoT |
| Approve / edit / regenerate / export | Launch Pack redesign |
| Restore after refresh from server heads | owner_preview as product path |
| Honest blocked Partial without override | Mock success Strategy |

**Transitional:** Keep CWF Launch/Offer until cutover; UI must not imply Strategy is approved spine while Runtime incomplete.

---

## 9. Security

| Rule | Status for Runtime |
|------|-------------------|
| Tenant + project mandatory on all Strategy entities | Required |
| Cross-project Strategy handoff | **Denied** |
| Cross-tenant | **Denied** |
| Sanitize inbound section text | `sanitize_payload` / `sanitize_text` |
| Server-attested actor on approvals | Required |
| No secrets in export | Required |
| Registry ≠ authorization | Preserve |
| Fixture Research in commercial path | **Forbidden** |
| Fake Strategy success / silent mock | **Forbidden** |

---

## 10. Testing strategy before 2026-08-18

### Allowed

| Mode | Use |
|------|-----|
| Deterministic fixtures in **test harness** | Full / Partial / superseded Research+Verdict packages |
| Persisted **historical** Research/Verdict rows in local/dev DB | Replay pins |
| Sanitized fixture Research packages (tests only) | E2E oracle inputs |
| Real LLM over **approved fixture inputs** | Optional provider smoke — **separate** from DoD |
| Provider smoke | Isolated; not `owner_accepted` |

### Forbidden

| Mode | Why |
|------|-----|
| Fixture binding in commercial Runtime | Customer false confidence |
| Fake Strategy result on customer path | Commercial safety |
| `owner_accepted` via deterministic E2E alone | Honesty |
| `real_pipeline_verified` without real Research integration | After Hardening only |
| New real Research run for this program | PAUSED until 2026-08-18 |

### Mandatory future E2E oracles (1–14)

1. Full Research/Verdict → Strategy candidate  
2. Partial without override → **blocked**  
3. Partial with override → constrained candidate  
4. Refresh / supersede during generation → honest terminal / stale  
5. Cold restore candidate  
6. Edit → new version  
7. Regenerate section → new version  
8. Approval → immutable package  
9. Research superseded → Strategy stale  
10. Cross-project denial  
11. Cross-tenant denial  
12. No duplicate generation after reload (idempotency)  
13. Provider failure visible honestly  
14. Export matches approved version  

---

## 11. Input scenarios (A–G)

| ID | Scenario | Expected Runtime behavior |
|----|----------|---------------------------|
| **A** | Full approved Research/Verdict | SIS pin → StrategyRun → SC-01…07 candidate → review → approve |
| **B** | Partial + explicit `partial_strategy_override` | Constrained candidate; limitations visible; critical SC gaps may block handoff |
| **C** | Partial **without** override | **Blocked** — no candidate |
| **D** | Research superseded **before** Strategy start | Cannot create SIS from stale head; must pin new acceptance or stop |
| **E** | Research superseded **during** generation | Run fails or completes+stale per Fabric/OD-P03-09; no silent attach to new research |
| **F** | Existing approved Strategy reopened | Edit/regen → **new** version; prior approved intact until new approval |
| **G** | Manual create/import **without** Research pin | **Out of MVP** under frozen Blueprint (start = Research acceptance or Partial override). P0.6 `MANUAL` create = **legacy**; do not promote |

---

## 12. Strategy operations matrix

| Operation | MVP | Rule |
|-----------|-----|------|
| Generate whole candidate | Yes | One StrategyRun OK |
| Regenerate section | Yes | New version/candidate; approved intact |
| Manual edit section | Yes | Attribution + new version |
| Reject | Yes | Candidate terminal; history kept |
| Request revision | Yes | Return to draft / new version loop |
| Approve | Yes | `strategy_package_approval` · package immutable |
| Rollback | Soft | Point heads to prior **approved** version; no mutate history |
| Export | Yes | Approved only |
| Restore | Yes | Server heads + pins |
| Stale / revalidate | Yes | Derived labels; revalidate must not invent evidence |

---

## 13. MVP cut

### Required

- Pinned StrategyInputSnapshot  
- ≥1 StrategyRun  
- SC-01…SC-07 candidate  
- Evidence vs assumption distinction  
- Owner review  
- Edit → new version  
- Regenerate → new candidate/version  
- Package-level approval  
- Immutable approved package  
- Cold restore  
- Tenant/project isolation  
- JSON + customer-readable export  

### Out of MVP

Pricing engine · predictive ROI · multi-market · advanced funnel · brand voice · CRM · Launch generation · Content generation · full Analytics · Journey/IA Registry cutover (ticket) · Launch Runtime · Visual/Publication Architecture.

---

## 14. Risks

| Risk | Mitigation |
|------|------------|
| Treating P0.6 as PRODUCT-03 SoT | Explicit **D/E** classification; adapter only |
| Dual commercial paths forever | Journey/IA drift ticket after Runtime DoD |
| Building Strategy on weak Research | Fixtures until 18 Aug; Hardening before `real_pipeline_verified` |
| New foundation (universal Asset/Approval framework) | Strategy-scoped approvals first; Fabric semantics only |
| LLM essay without pins | Snapshot-first; evidence/assumption tags mandatory |
| Scope creep into Launch/Offer rewrite | Forbidden in this program |
| Continuing architecture docs instead of Runtime | This audit is last doc before contracts/impl slices |

---

## 15. Exact implementation slices (recommended order)

| Slice | Task ID (proposed) | Deliverable | Depends |
|-------|-------------------|-------------|---------|
| **S0** | `PRODUCT-03-STRATEGY-RUNTIME-02-CONTRACTS-01` | Add logical contracts to `contracts.py` (Snapshot, Run, Candidate/Package, Approvals, pins, labels) — **no migration yet** | This audit |
| **S1** | `PRODUCT-03-STRATEGY-RUNTIME-03-PERSISTENCE-01` | Alembic + repos for Snapshot/Run/Package/Approval; P0.6 remains legacy | S0 + owner OD-SR-01 if needed |
| **S2** | `PRODUCT-03-STRATEGY-RUNTIME-04-ELIGIBILITY-01` | Full/Partial/override wall; scenario A–C oracles | S1 |
| **S3** | `PRODUCT-03-STRATEGY-RUNTIME-05-GENERATE-01` | Deterministic candidate SC-01…07 from SIS; optional LLM flag off by default | S2 |
| **S4** | `PRODUCT-03-STRATEGY-RUNTIME-06-VERSION-APPROVE-01` | Edit/regen/approve/export/restore/stale | S3 |
| **S5** | `PRODUCT-03-STRATEGY-RUNTIME-07-UI-01` | Command Center Strategy review surface (honest states) | S4 · may parallel Journey ticket |
| **S6** | `PRODUCT-03-STRATEGY-RUNTIME-08-RESEARCH-ADAPTER-01` | Map Evidence-Hardened Research → SIS (**≥2026-08-18**) | S4 + Research Hardening |

**Stop rule:** Each slice = one PR; contracts before DB; no Launch Runtime; no Visual/Publication Architecture.

---

## 16. Acceptance criteria (program-level, later)

1. Strategy starts only from pinned Research/Verdict acceptance or Partial override.  
2. Partial without override never produces customer candidate.  
3. Approved package immutable; edit/regen creates new version.  
4. Approvals are typed records pinned to package version + research pin + actor.  
5. Cold restore returns same heads without browser SoT.  
6. Export matches approved version only.  
7. Oracles 1–14 green in harness (fixtures OK before 18 Aug).  
8. No fixture Research in commercial Runtime.  
9. P0.6 not advertised as PRODUCT-03 Strategy Package.  
10. `real_pipeline_verified` only after Hardening + real Research integration (post-18 Aug).  

---

## 17. Owner decisions (only if blocking)

| ID | Question | Why it may block | Suggested default |
|----|----------|------------------|-------------------|
| **OD-SR-01** | Persist Strategy Package as **new tables + P0.6 adapter** vs **evolve `marketing_strategies` in place**? | Migration shape / dual-write risk | **A — new tables + adapter**; keep P0.6 read-only legacy |
| **OD-SR-02** | Confirm **manual/import without Research pin** stays **out of MVP**? | P0.6 allows `MANUAL` create | **A — out of MVP** (Blueprint start rules) |

No other OD required to begin **S0 contracts**. Launch/Offer cutover timing stays on `PRODUCT-03-JOURNEY-IA-DRIFT-01`.

---

## 18. Recommended first implementation task

```text
PRODUCT-03-STRATEGY-RUNTIME-02-CONTRACTS-01
```

**Type:** contracts-first (then tests for contract shapes) · **no** UI · **no** Research run · **no** Launch Runtime.  
**Goal:** Encode StrategyInputSnapshot · StrategyRun · StrategyCandidate/PackageVersion · StrategyApprovalRecord · research_pin · heads · stale labels in `app/schemas/contracts.py` aligned to PRODUCT-03 + Fabric — without declaring P0.6 canonical.

---

## 19. How real Research plugs in later (no rewrite)

```text
Evidence Hardening (≥2026-08-18)
  → stable Research artifact version API
  → Adapter fills StrategyInputSnapshot.research_pin
  → Existing StrategyRun / Package / Approval unchanged
  → E2E oracle set gains real_pipeline path
  → Only then claim real_pipeline_verified for Strategy
```

Generators consume **Snapshot fields**, not “call latest Research.” That is the non-rewrite contract.

---

## 20. Explicit non-goals of this audit

- Code / migrations / UI changes  
- Starting Strategy Runtime implementation  
- Research Hardening / real smoke  
- Visual or Publication Architecture  
- Launch Runtime  
- New Execution Model / Fabric / Asset Framework  
- Journey/IA/Registry edits  
- Owner freeze of Runtime (Runtime not started)

---

## 21. Stop

Audit complete. **Implementation NOT STARTED.** Await owner approval of **OD-SR-01/02** (if contested) then **PRODUCT-03-STRATEGY-RUNTIME-02-CONTRACTS-01**.
