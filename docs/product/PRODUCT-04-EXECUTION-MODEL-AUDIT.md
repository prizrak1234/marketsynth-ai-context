# PRODUCT-04-EXECUTION-MODEL-AUDIT

> **Task:** PRODUCT-04-EXECUTION-MODEL-CONSISTENCY-AUDIT-01  
> **Title:** Commercial Execution Model Cross-Document and Runtime Consistency Audit  
> **Type:** Read-only architecture audit  
> **Date:** 2026-08-02  
> **Audited:** `docs/product/PRODUCT-04-EXECUTION-MODEL.md`  
> **EM status:** **OWNER-FROZEN** (2026-08-02)  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Code / Runtime / P02 / P03 / EM freeze act:** docs status only — no code

---

## 1. Executive verdict

| Field | Value |
|-------|-------|
| **Audit completeness** | **PASS** (docs + CWF/Golden Path + code inventory covered) |
| **EM internal coherence** | **Strong thesis**; **incomplete operational definitions** (CapabilityRun, terminal states, package contents, Campaign/Offer order) |
| **PRODUCT-02 compatibility** | **Mostly compatible** (Command Center, Launch subtree, ApprovalRecord, multi-instance publication, Outcome Project-level) |
| **PRODUCT-03 compatibility** | **Compatible** on Strategy≠Launch / Offer Structure≠Offer Artifact / Channel Direction≠media |
| **CWF.1 / Golden Path** | **Material commercial contradiction** on first-paying DoD (publish+`message_id`+Delivery Evidence vs Package-as-stop) — **resolvable** by splitting three contracts (see §6) |
| **Code compatibility** | **Foundations reusable via adapters**; vocabulary and uniqueness constraints **do not match** EM; no unified ApprovalRecord / LaunchPackage / DeliveryEvidence / OutcomeCapture |
| **Freeze recommendation** | **B. FREEZE AFTER PATCHES** |
| **Not A** | OD-EM unresolved; CWF DoD split not written into EM; definition gaps freeze-blocking |
| **Not C** | Core thesis sound; surgical OD + EM patches sufficient — not a rewrite |

**Composite audit PASS** = completeness of this audit. **Not** owner freeze of Execution Model.

---

## 2. Freeze recommendation

### **B. FREEZE AFTER PATCHES**

Minimum before owner may set Execution Model `OWNER-FROZEN`:

1. Resolve **OD-EM-01…10** (this audit’s refined matrix §18) in writing.  
2. Apply **PRODUCT-04-EXECUTION-MODEL-PATCH-01** (exact list §19).  
3. Explicitly encode the **three-contract split** (Launch Package completion ≠ Publication execution ≠ Commercial MVP E2E).  
4. Do **not** start PRODUCT-04-LAUNCH-ARCHITECTURE-01, Runtime, or Research from freeze alone.

---

## 3. Pack completeness

| Item | Status |
|------|--------|
| Single EM document exists | Yes |
| Sections 1–14 present | Yes |
| Declares docs_verified / freeze NOT SET | Yes |
| Declares Launch Architecture not started | Yes |
| Operational definitions (run, terminal, package BOM) | **Incomplete** — see P0-EM-01 |
| OD list aligned with freeze needs | Draft OD list **must be remapped** (§18) |
| Consistency audit (this file) | Created |

---

## 4. Core definition

### 4.1 Claim under audit

> Launch = project-stage capability, orchestrating execution of Approved Strategy.

### 4.2 Answers (evidence-based)

| Question | EM today | Audit finding |
|----------|----------|---------------|
| Launch — one capability or orchestration boundary? | States **both** (capability whose behavior is orchestration) | **Acceptable if clarified:** one Registry capability `project.launch` **and** an orchestration **boundary** (subtree). Mixing without stating “capability = boundary owner” is freeze-blocking ambiguity → **P0-EM-01** |
| Own CapabilityRun? | **Not stated** | Must be **yes** for realizability with PRODUCT-02 four-layer model. Recommend: Launch CapabilityRun hosts orchestration; Content/Visual/Publication have **child** runs under Launch |
| Launch Package = artifact or aggregate? | Called artifact / package interchangeably | Treat as **versioned aggregate artifact** (`LaunchPackage`) containing Offer + campaign frame + checklist + pins + executor request refs — must be patched |
| Content/Visual/Publication runs belong to? | “Under Launch” | Recommend: **owned by Launch CapabilityRun** (tenant/project/launch_run binding); not free-floating Project siblings |
| Multiple Launch runs per Project? | Implied by versioning; not explicit | **Must be yes** (align ARTIFACT-FLOW multi Launch versions) |
| One Strategy → many Launch runs? | Softly implied | **Must be yes**; pin each Launch to one Strategy version |
| Launch using different Strategy versions? | Mid-Launch stale rules exist; multi-head unclear | **One Launch run pins one Strategy version**; new Strategy head → new Launch version / rebuild — not silent re-pin |
| Terminal state of Launch? | “Stop without publish” described; no state enum | **Missing** → P0-EM-01. Recommend semantic terminals: `package_approved` · `executing` · `partially_executed` · `completed_with_publication` · `abandoned` · `invalidated` (derived labels OK; not ProjectLifecycleState) |

### 4.3 Verdict

Thesis **directionally correct**. Freeze **blocked** until capability vs aggregate vs run vs terminal are non-ambiguous.

---

## 5. Deliverable

### 5.1 Primary SKU claim

**Approved Launch Package** as primary commercial deliverable after Strategy — **commercially coherent** and aligns with PRODUCT-02 Launch `commercialDeliverable` = “thin launch plan (offer/channels/budget/checklist)” (`CAPABILITY-CATALOG.md` §4.4).

### 5.2 Gaps in EM

| Topic | Gap |
|-------|-----|
| Package BOM (what’s in / out) | Listed vaguely; no normative contents table |
| vs “Launch Plan” | CWF uses “launch plan”; EM does not map synonym |
| vs Publication Package | Stated optional; relationship (contains refs vs separate) under-specified |
| Ready when? | “Package approval” — no checklist of required children for MVP |
| Approver | Owner via ApprovalRecord — OK but type name not fixed |
| Pinned to Strategy? | Via LaunchInputSnapshot — yes in spirit; assertable contract missing |
| Immutable after approval? | Inherited from P02 — should restate as Launch invariant |
| Multiple versions? | Yes by inheritance — must be explicit |
| Value without execution? | Claimed — need concrete risk-reduction bullets (patch) |

### 5.3 Paid value without publication (recommended wording for patch)

Client receives: locked Offer Artifact, campaign frame/checklist, Strategy-pinned constraints, executor-ready briefs, explicit next gates.  
That is **handoff-ready execution control** — not an AI essay.  
**Does not** replace CWF first-paying E2E proof (see §6).

---

## 6. CWF / publication consistency

### 6.1 Contradiction (evidence)

| Source | First-paying / Launch Pack DoD |
|--------|--------------------------------|
| CWF.1 directive | Real Publication → Delivery Evidence; Launch Pack includes **one real Telegram publish** |
| PRODUCT-FINISH-01 | publish → `message_id` + Evidence |
| PRODUCT-02 Telegram GP | Publish → message_id → Evidence |
| Journey J8.3 | Published proof / message_id / Delivery evidence |
| DEC-003 | Owner browser golden path + real Telegram send |
| PRODUCT-04 EM | Approved Launch Package alone = valid stop; OD-EM-06 open |
| PRODUCT-02 catalog `launch.publication` | commercialDeliverable = **One real channel publish (MVP)** |

### 6.2 Three contracts (normative recommendation for owner)

| Contract | Meaning | Completion signal |
|----------|---------|-------------------|
| **1. Launch Package completion** | Launch capability commercial gate | `ApprovedLaunchPackage` + `launch_package_approval` |
| **2. Publication execution completion** | External send path | `PublicationPackage` approved + `external_execution_approval` + `PublicationJob` terminal + `DeliveryEvidence` / `message_id` |
| **3. Commercial MVP end-to-end completion** | First paying customer product DoD | At least one **scenario** that achieves (1) **and** (2) on the sellable path (Telegram MVP), **plus** upstream Research/Strategy (target) or transitional CWF until Strategy live |

**Compatibility rule:**

```
Launch instance MAY terminate at (1) without (2).
Commercial MVP DoD STILL REQUIRES that the product can demonstrate (3)
  = at least one governed path that reaches (2).
```

These are **not** the same sentence. EM currently collapses (1) into “commercial outcome” language and collides with CWF (3).

### 6.3 Owner decision

See **OD-EM-06** (§18). Freeze blocker **YES** until written into EM.

---

## 7. Offer / Campaign semantics

| Topic | Finding |
|-------|---------|
| Offer Structure in Strategy | PRODUCT-03 SC-03 — **exists**; Launch must not re-decide |
| Launch Offer Artifact | Named; mapping to live Offer Builder (CWF, unique per Launch Pack) = **adapter / transitional** |
| Campaign | EM “Campaign frame” **undefined type** (artifact vs aggregate vs context) |
| Offer vs Campaign order | Chain says “Offer / Campaign” parallel slash — **ambiguous** |
| Campaign without Publication | Should be **yes** |
| One Offer → many Campaigns | Not stated |
| One Campaign → many PublicationPackages | Implied by P02 multi-instance; not stated for Campaign frame |
| vs BusinessCampaign | Code AI.146 `/business-campaigns` — **legacy parallel vocabulary**; OD-EM-04 freeze blocker |

**Corrected variant (recommendation only):**

1. Strategy Offer Structure → Launch **Offer Artifact** (one head per Launch Package version).  
2. **ExecutionPlanFrame** (rename candidate) inside Launch Package = sequence/budget/checklist — **not** `BusinessCampaign`.  
3. Optional later: multiple frames per Launch (post-MVP) without renaming BOS Campaign until migration plan exists.

---

## 8. Budget

### 8.1 Recommended split (for OD-EM-03)

| Layer | Owns | Does not own |
|-------|------|--------------|
| **Strategy** | Pricing **assumptions**; spend_band guidance; channel direction; fences | Ops allocation; provider invoices |
| **Launch** | Budget **envelope** + allocation **proposal** + campaign spend limits inside Package | Payment/billing system; auto-authorize provider spend |
| **Execution** | Actual spend / provider costs recorded on jobs/evidence | Changing Strategy pricing assumptions |

### 8.2 Open questions (freeze-relevant)

| Question | Audit stance |
|----------|--------------|
| Separate budget artifact? | MVP: **fields inside LaunchPackage** + ApprovalRecord type; post-MVP may split |
| BudgetApprovalRecord? | Prefer typed ApprovalRecord `budget_acknowledgement` bound to Package version — not boolean |
| Package without budget? | **Allowed** if Strategy spend_band absent **and** no paid external action; **hard block** before paid provider / paid ads |
| Unknown budget | Assumption-constrained Package + honest limitation; block external paid gates |
| Hard block | External paid execution without acknowledgement; contradiction with Strategy fence |

Code: budget **fragments** (StrategyBudgetPolicy, connector BudgetPolicy, brief `budget_range`) — **no** Launch budget gate on CWF Launch Pack. **Missing** vs model.

---

## 9. Approvals

### 9.1 Minimal MVP graph (recommendation)

| Approval | MVP required? | Binds |
|----------|---------------|-------|
| Strategy package (upstream) | Yes | StrategyPackage |
| `launch_handoff` / start | Yes (entry) | LaunchInputSnapshot creation |
| `launch_package_approval` | **Yes — primary** | LaunchPackage |
| `budget_acknowledgement` | **Conditional** (if spend/paid path or Strategy spend_band present) | Package version |
| `content_approval` | Yes **if** Publication path pursued | ContentPackage/assets |
| `visual_approval` | Yes **if** checklist requires visuals | VisualPackage/assets |
| `publication_package_approval` | Yes **if** Publication path | PublicationPackage |
| `external_execution_approval` | Yes **if** real send | Job / package binding |

### 9.2 Anti-patterns (EM mostly OK)

| Anti-pattern | Status |
|--------------|--------|
| Approval explosion | Risk if every SC / every asset needs unique gate — keep package-level primary |
| Boolean approvals | Forbidden by P02; code still uses status fields — **adapter debt** |
| Approval without artifact version | Forbidden |
| External execution without explicit approval | EM forbids — keep |
| Approval surviving invalidation | Must bind version; invalidate with package |

Draft EM lists gates but does not mark **conditional vs mandatory** clearly → patch.

---

## 10. Capability boundaries

| Boundary | EM | Audit |
|----------|-----|-------|
| Strategy whom/what/why/direction | Clear | **PASS** vs P03 |
| Launch executable plan | Clear intent | Needs BOM + run model |
| Content = text assets | Clear | **PASS** |
| Visuals = visual assets | Clear | **PASS** |
| Publication = delivery + external | Clear | **PASS** |
| Outcome = evidence consumer | Corrected in EM (Project-level) | **PASS** vs catalog |
| Launch generates Content? | Says “requesting executors” | Must forbid direct generation in Launch Architecture |
| Umbrella creep | Warned | Keep P05–P07 separate |

Overlaps with CWF transitional Offer/Launch Pack are **documented honesty**, not architecture endorsement.

---

## 11. Multiplicity

| Rule | EM | Code / P02 | Finding |
|------|-----|------------|---------|
| One Strategy → many Launch | Implicit | P02 versions; CWF **one LP per verdict** | **Hidden 1:1 in live CWF** — contradicts target |
| One Launch → many Campaign frames | Unclear | BusinessCampaign many/project | Needs OD-EM-04 + OD-EM-08 |
| Content ∥ Visuals | Explicit | P02 OD-04 | **PASS** |
| Many PublicationPackages / Jobs | Explicit | Jobs many; package unique `(asset, channel)` | **Partial conflict** |
| Retry ≠ new Launch | Not stated | Delivery logs have attempts | Must state |
| Partial completion | Soft | — | Must state |
| Abandoned keeps artifacts | Soft via P02 | — | Must restate |

**Hidden one-to-one contracts to break in target model (not in this audit’s code edits):**  
`uq_lpr_owner_verdict`, `uq_offer_launch_pack`, `uq_publication_packages_asset_channel`.

---

## 12. Artifact graph

| Artifact | Producer | Consumer | Multiplicity | Version | Approval | Immutable when approved | MVP? | Role clarity |
|----------|----------|----------|--------------|---------|----------|-------------------------|------|--------------|
| ApprovedStrategyPackage | Strategy | Launch | 1 head / many versions | Yes | strategy_package | Yes | Yes | Clear |
| LaunchInputSnapshot | Launch entry | LaunchPackage | 1 per Launch version | Pin | handoff | Snapshot | Yes | Clear (P03 pin; not in P02 catalog) |
| LaunchCandidate | Launch | Owner | Many versions | Yes | — | No | Yes | Clear |
| ApprovedLaunchPackage | Launch | Executors / owner | 1 head | Yes | launch_package | Yes | Yes | Clear as SKU; BOM weak |
| OfferArtifact | Launch Offer unit | Package / Content | 1 head / Launch version (rec.) | Yes | via package or typed | Yes when approved | Yes | Clear conceptually; live = CWF offer |
| CampaignFrame | Launch | Content/Pub | **TBD** | TBD | via package | TBD | Minimal | **Unclear** — P0 |
| ContentRequest / VisualRequest | Launch | Executors | Many | Soft | — | — | Yes | Named weakly in EM |
| ContentAsset / ContentPackage | Content | Publication | Many | Yes | content | Yes | Yes | Package vs Asset naming drift |
| VisualAsset / VisualPackage | Visuals | Publication | Many | Yes | visual | Yes | Optional | Same |
| PublicationPackage | Publication | Jobs | Many | Yes | pub package | Yes | MVP path | Clear |
| ExecutionApproval | Owner | Jobs | Per external act | — | external_execution | — | MVP path | Should be ApprovalRecord type |
| PublicationJob | Publication | Evidence | Many | Status machine | — | Terminal records kept | MVP path | Clear in code |
| ExecutionEvidence / DeliveryEvidence | Job | Outcome | Many | Attempts | — | Append-only | MVP path | Alias unresolved |
| OutcomeRecord | Outcome Capture | Owner / Opt later | Many | Yes | — | — | When evidence exists | Clear |

Artifacts without clear role until OD: **CampaignFrame**, dual **ExecutionEvidence** name, **ContentRequest** schema.

---

## 13. Lifecycle realizability

EM **can** be realized via:

`ProjectLifecycleState` + `Launch CapabilityRunState` + `ArtifactVersionState` + `ApprovalRecord` + `PublicationJobStatus`

**without** collapsing spine into ProjectLifecycleState (P02 invariant).

| Scenario | Realizable? | Notes |
|----------|-------------|-------|
| 1 Strategy stale before Launch approval | Yes | Block / revalidate; no approve |
| 2 Strategy stale after Launch approval | Yes | Mid-Launch owner choice (P02/P03) |
| 3 Content approved, Visual rejected | Yes | Parallel; Publication waits on required set |
| 4 Budget changed | Yes | New Package version + new acknowledgement |
| 5 Pub package approved, execution rejected | Yes | No job / no fake evidence |
| 6 Provider failure | Yes | DeliveryEvidence failure honesty |
| 7 Retry | Yes | New job/attempt; **not** new Launch |
| 8 Partial execution | Yes | Terminal `partially_executed` |
| 9 Abandoned | Yes | Keep artifacts; lose head |
| 10 Reopened | Yes | New run/version |
| 11 Multiple campaigns | **Blocked on OD-EM-04** | |
| 12 Outcome after Project paused | Yes | Outcome Capture independent; ProjectLifecycle ≠ spine |

Missing explicit Launch CapabilityRunState in EM → patch (labels only; no lifecycle doc).

---

## 14. Commercial value

| Question | Concrete answer |
|----------|-----------------|
| Pays for (Launch stage) | Approved Launch Package = governed execution plan pinned to Strategy |
| Without publication | Offer + frame + checklist + briefs + explicit gates — handoff to team or later send |
| With publication | Same + PublicationPackage + job + DeliveryEvidence (`message_id`) |
| ≠ AI plan | Versioned, approved, invalidatable, Strategy-pinned, approval-bound; not chat transcript |
| Risk reduction | Prevents Strategy drift into posts; prevents publish without package; prevents fake “published” |
| Team handoff | Export/approved package fields (OD-EM-10) |
| Manual execute | Owner can execute outside Marketsynth using Package — still valuable |
| Launch failure | Cannot produce eligible approved package; or dishonest publish claims; or violates Strategy fences |
| First paying minimum | **Contract (3)** in §6: product must prove one real Telegram (or MVP channel) path; **instances** may stop at Package |

Vague “managed execution” alone is **insufficient** without §6 split — noted as commercial P0 until patched.

---

## 15. MVP cut

### 15.1 Minimum assertable MVP (target spine)

- Approved Strategy input (or transitional waiver documented)  
- ≥1 Launch Candidate → ≥1 Approved Launch Package  
- ≥1 Offer Artifact  
- Limited Content  
- Optional Visual  
- Publication **capability in band** + ability to run **one** channel job with external approval  
- Execution Evidence  
- Outcome Record **when** evidence exists  

### 15.2 Exclude from MVP

Full Campaign management · multi-channel · complex budgets · scheduling calendar · full Analytics · Optimization · CRM · team workflows · per-asset approval explosion · asset variant matrices · BusinessCampaign Control Center as Launch SKU.

### 15.3 Tension

EM §9 lists Publication path “optional but modeled” and stop-without-publish; P02 band includes one Publication channel commercially. **Resolved only by §6 three-contract split.**

---

## 16. Code compatibility

| Subsystem | Status | Rewrite? | Notes |
|-----------|--------|----------|-------|
| BusinessCampaign | **legacy** naming | No rewrite now | Keep; map via OD-EM-04; do not equate to CampaignFrame |
| Offer Builder | **adapter** | Low | Remap upstream from Verdict/LP → Strategy/Launch later |
| CWF Launch Pack | **adapter / transitional** | Medium later | Retire per OD-EM-07; not permanent EM Launch |
| Content Factory / assets | **legacy / adapter** | Medium | Toward ContentPackage under Launch |
| Visual generation | **legacy / missing under Launch** | Low–medium | Optional MVP |
| PublicationPackage / Jobs | **adapter** | Low | Reuse; watch unique `(asset,channel)` |
| PublicationDeliveryLog | **adapter** for DeliveryEvidence | Low | Prefer alias (OD evidence) |
| Telegram provider | **reusable_as_is** foundation | No | Gated real send |
| ApprovalRecord unified | **missing** | Medium when Runtime | Per-domain approvals today |
| OutcomeCapture | **missing** | Low MVP | CampaignMetrics ≠ Outcome |
| Capability Registry | **aligns** (planned) | No | Not authz |

**Do not** recommend rewrite of Telegram/publication foundations. Prefer adapters + uniqueness policy changes when Launch Runtime starts.

---

## 17. Findings

### P0 (freeze blockers)

| ID | Problem | Docs | Code | Evidence | Commercial | Architecture | Corrected variant | OD required | Freeze blocker |
|----|---------|------|------|----------|------------|--------------|-------------------|-------------|----------------|
| **P0-EM-01** | Launch mixes capability / orchestrator / package without CapabilityRun, terminal states, package BOM | EM §1,§5,§6 | — | §4 this audit | Ambiguous what is sold/complete | Launch Architecture would invent silently | Patch definition + terminals + BOM | OD-EM-01,02 | **YES** |
| **P0-EM-02** | CWF.1 / FINISH-01 / catalog Publication DoD vs EM stop-without-publish / primary SKU | EM §5,§9,§11, OD-EM-06; CWF directive; FINISH-01; CAPABILITY-CATALOG §4.7 | TG publish path | §6 | Wrong first-payment definition risk | Spine vs CWF | Encode three contracts | **OD-EM-06** | **YES** |
| **P0-EM-03** | CampaignFrame semantic undefined; collision with BusinessCampaign | EM §3,§6.3 | `business_campaigns`, CampaignTable | §7 | Duplicate SKU risk | Parallel Campaign products | Rename or map; forbid BOS=Frame | **OD-EM-04** | **YES** |
| **P0-EM-04** | Budget boundary incomplete (artifact? approval? hard blocks?) | EM OD-EM-03 | budget fragments only | §8 | Paid action without gate | Spend authz creep | Split Strategy/Launch/Execution budget | **OD-EM-03** | **YES** |

### P1

| ID | Problem | Docs | Code | Consequence | Corrected variant | OD | Freeze blocker |
|----|---------|------|------|-------------|-------------------|----|----------------|
| **P1-EM-01** | Offer Artifact boundary vs Strategy Offer Structure under-specified; live Offer tied to Launch Pack 1:1 | EM §4–5; P03 SC-03 | `uq_offer_launch_pack` | Rewrite / wrong pin | Define Offer Artifact fields + 1 head per Launch version | OD-EM-05 | Soft YES for Architecture |
| **P1-EM-02** | Approval graph not marked mandatory vs conditional; code lacks ApprovalRecord | EM §7 | offer/package status fields | Approval explosion or boolean debt | Minimal MVP table §9 | OD-EM-07 | Soft YES |
| **P1-EM-03** | Multiplicity not normative; CWF 1 LP per verdict; package unique asset+channel | EM weak; ARTIFACT-FLOW strong | uq_* constraints | Hidden 1:1 | Explicit multiplicity + adapter plan | OD-EM-08 | Soft YES |
| **P1-EM-04** | Outcome Capture scope vs Analytics; N/A without evidence under-documented in spine diagram | EM §6.2 | CampaignMetrics | Fake empty Outcome | Outcome only with evidence; Project-level | OD-EM-09 | No if patched |
| **P1-EM-05** | Export/handoff of Approved Launch Package unspecified | EM commercial value | — | Weak paid artifact | Export contract for approved only | OD-EM-10 | Soft YES |
| **P1-EM-06** | ExecutionEvidence vs DeliveryEvidence dual naming | EM §8 | PublicationDeliveryLog | Duplicate types | One MVP name = DeliveryEvidence | (fold into OD-EM-10 or evidence note) | No |
| **P1-EM-07** | Transitional CWF retirement sequencing | EM OD-EM-07 old | launch_pack_* | Two spines forever | Sequence gate after Strategy Runtime | (see remapped OD list) | No for EM freeze if dated |

### P2

| ID | Problem | Notes |
|----|---------|-------|
| **P2-EM-01** | Draft OD-EM-05…10 numbering ≠ freeze-critical questions | Remap in §18 |
| **P2-EM-02** | `00_INDEX` may still say PRODUCT-03 next | Out of this task’s SoT allow-list |
| **P2-EM-03** | ContentPackage vs ContentAsset naming | Align in Launch Architecture |
| **P2-EM-04** | Visual optional already matches P02 catalog | Confirm OD-EM (visual) as non-blocker |

---

## 18. Owner decisions (refined OD-EM-01…10)

> Draft EM OD list is **superseded for decision-taking** by this matrix. Patch must rewrite §13 of EM to match.

### OD-EM-01 — Launch definition

| Field | Content |
|-------|---------|
| **Question** | Is Launch a project-stage capability whose job is orchestration (subtree boundary)? |
| **A** | Yes — `project.launch` capability + orchestration boundary; child executor runs | 
| **B** | Launch is only a workflow label without CapabilityRun |
| **C** | Launch is a separate product app |
| **Recommendation** | **A** |
| **Commercial** | One SKU stage after Strategy |
| **Architecture** | Matches P02 Launch subtree |
| **Runtime** | Launch CapabilityRun required |
| **MVP** | Thin orchestrator |
| **Freeze blocker** | **YES** |

### OD-EM-02 — Primary deliverable

| Field | Content |
|-------|---------|
| **Question** | Is **Approved Launch Package** the primary commercial deliverable after Strategy? |
| **A** | Yes — Package primary; publication secondary |
| **B** | Primary = Publication / DeliveryEvidence |
| **C** | Primary = Campaign |
| **Recommendation** | **A** |
| **Commercial** | Aligns thin launch plan catalog |
| **Architecture** | Aggregate artifact |
| **Runtime** | Package approval gate |
| **MVP** | Package required; publish path modeled |
| **Freeze blocker** | **YES** |

### OD-EM-03 — Budget boundary

| Field | Content |
|-------|---------|
| **Question** | How are Strategy assumptions vs Launch envelope vs execution spend split? |
| **A** | Dual: Strategy spend_band assumptions + Launch envelope fields + conditional `budget_acknowledgement`; hard block paid external without ack |
| **B** | Budget only at Strategy |
| **C** | Budget only at Launch; Strategy silent |
| **Recommendation** | **A** |
| **Commercial** | Honest paid gates |
| **Architecture** | No billing system |
| **Runtime** | ApprovalRecord typed |
| **MVP** | Fields in Package; no billing |
| **Freeze blocker** | **YES** |

### OD-EM-04 — Campaign semantic

| Field | Content |
|-------|---------|
| **Question** | What is “Campaign” in the execution chain? |
| **A** | Launch-internal **ExecutionPlanFrame** (rename); **not** BusinessCampaign |
| **B** | Reuse BusinessCampaign as Launch CampaignFrame |
| **C** | Drop Campaign term; only Offer+Checklist inside Package |
| **Recommendation** | **A** or **C** for MVP (prefer **C** if rename cost high); **forbid B** without migration RFC |
| **Commercial** | Avoid second Campaign SKU |
| **Architecture** | Prevent AI.146 collision |
| **Runtime** | No new Campaign product |
| **MVP** | Minimal frame fields inside Package |
| **Freeze blocker** | **YES** |

### OD-EM-05 — Offer Artifact boundary

| Field | Content |
|-------|---------|
| **Question** | Exact boundary Strategy Offer Structure vs Launch Offer Artifact? |
| **A** | Structure = decisions; Artifact = sellable packaging/copy/terms for execution; Artifact pinned to Structure version |
| **B** | Launch may revise Structure without Strategy version |
| **Recommendation** | **A** (P03 invariant) |
| **Commercial** | Clear upgrade from CWF Offer |
| **Architecture** | Honor Offer Structure ≠ Offer Artifact |
| **Runtime** | Adapter from Offer Builder |
| **MVP** | One Offer Artifact head / Launch Package version |
| **Freeze blocker** | Soft **YES** |

### OD-EM-06 — Publication optionality vs MVP

| Field | Content |
|-------|---------|
| **Question** | How do Package completion, Publication completion, and Commercial MVP E2E relate? |
| **A** | Adopt §6 three contracts: instance may stop at Package; MVP E2E still requires product can complete one real publication scenario |
| **B** | Every Launch instance must publish to be “complete” |
| **C** | Drop real publication from Commercial MVP DoD |
| **Recommendation** | **A** |
| **Commercial** | Reconciles CWF.1 without making Launch a publish button |
| **Architecture** | Publication stays in MVP band |
| **Runtime** | External gate retained |
| **MVP** | Model includes one-channel publish capability |
| **Freeze blocker** | **YES** |

### OD-EM-07 — Approval granularity

| Field | Content |
|-------|---------|
| **Question** | Minimal MVP approval set? |
| **A** | §9 table: handoff + package (+ conditional budget) + executor approvals when publishing + publication package + external |
| **B** | Only package approval ever |
| **C** | Per-field / per-SC approvals |
| **Recommendation** | **A** |
| **Freeze blocker** | Soft **YES** |

### OD-EM-08 — Launch multiplicity

| Field | Content |
|-------|---------|
| **Question** | Many Launch runs per Project / per Strategy version? |
| **A** | Yes — many Launch runs; each pins one Strategy version; retry≠new Launch |
| **B** | Exactly one Launch per Project |
| **C** | Exactly one Launch per Strategy head |
| **Recommendation** | **A** |
| **Commercial** | Re-launch without deleting history |
| **Architecture** | Matches ARTIFACT-FLOW |
| **Runtime** | Break CWF 1:1 when migrating |
| **MVP** | Allow ≥1; UI may start with one |
| **Freeze blocker** | Soft **YES** |

### OD-EM-09 — Outcome Capture scope

| Field | Content |
|-------|---------|
| **Question** | Outcome Capture vs Analytics vs N/A without publish? |
| **A** | Project-level; only when DeliveryEvidence/jobs exist; not full Analytics; N/A if stop at Package |
| **B** | Always create Outcome on Package approve |
| **C** | Fold Outcome into Launch executor |
| **Recommendation** | **A** |
| **Freeze blocker** | No if patched |

### OD-EM-10 — Export / handoff deliverable

| Field | Content |
|-------|---------|
| **Question** | What is exported / handed off as paid Launch artifact? |
| **A** | Approved Launch Package only (customer-readable + machine JSON); DeliveryEvidence separate when exists |
| **B** | Export drafts freely |
| **C** | Export equals PublicationPackage always |
| **Recommendation** | **A** (mirrors Strategy export discipline) |
| **Freeze blocker** | Soft **YES** |

---

## 19. Exact patch list (for PRODUCT-04-EXECUTION-MODEL-PATCH-01)

Do **not** apply in this audit. Future patch only:

1. **§1 / §6** — Clarify Launch = capability + orchestration boundary; require Launch CapabilityRun; child executor runs.  
2. **§5** — Package BOM (in/out); immutable; pin; versions; vs Launch Plan synonym; vs PublicationPackage.  
3. **§3 / §11 / §9** — Insert **three-contract split** (§6 of this audit); rewrite OD-EM-06 language.  
4. **§6.3 / chain** — Resolve Campaign term per OD-EM-04 (rename or fold into Package).  
5. **§7** — Mandatory vs conditional approvals table.  
6. **§8** — Add OfferArtifact, CampaignFrame/ExecutionPlanFrame, ContentRequest/VisualRequest rows; pick DeliveryEvidence name.  
7. **New short §** — Launch terminal labels + multiplicity rules + retry≠new Launch.  
8. **§8 / budget** — Strategy vs Launch vs Execution budget split + hard blocks.  
9. **§11 / commercial** — Concrete value with/without publication; reference contract (3).  
10. **§13** — Replace OD list with audit §18 matrix (post owner answers).  
11. **Honesty** — Keep CWF transitional; do not edit P02/P03 freeze text; ticket amends remain separate.  
12. **Out of patch** — No Launch Architecture pack; no code; no Registry/Journey edits.

---

## 20. Next step

```text
Owner resolves OD-EM-01…10 (this matrix)
  → PRODUCT-04-EXECUTION-MODEL-PATCH-01
  → owner freeze Execution Model (separate message)
  → PRODUCT-04-LAUNCH-ARCHITECTURE-01
```

**Not now:** Launch Architecture · Runtime · Research · code · auto-freeze.

---

## 23. PATCH-01 validation (PRODUCT-04-EXECUTION-MODEL-PATCH-01)

> **Date:** 2026-08-02  
> **OD-EM-01…10:** **OWNER-APPROVED** (applied in EM)  
> **EM status:** **OWNER-FROZEN** (2026-08-02)  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Code / P02 / P03 / Registry:** unchanged

### 23.1 P0 / freeze-blocking P1 closure

| ID | Status | Evidence in patched EM |
|----|--------|------------------------|
| P0-EM-01 | **CLOSED** | §1, §5 LaunchRun vs Package + BOM |
| P0-EM-02 | **CLOSED** | §3 three contracts A/B/C |
| P0-EM-03 | **CLOSED** | §7 CampaignFrame; BusinessCampaign = reuse candidate |
| P0-EM-04 | **CLOSED** | §9 budget split + unknown + ack |
| P1-EM-01 | **CLOSED** | §8 Offer Structure ≠ Artifact; 1→N |
| P1-EM-02 | **CLOSED** | §10 approval table mandatory/conditional |
| P1-EM-03 | **CLOSED** | §11 multiplicity + retry |
| P1-EM-04 | **CLOSED** | §13 Outcome Capture scoped |
| P1-EM-05 | **CLOSED** | §14 export ACL + approved-only |
| P1-EM-06 | **CLOSED** | DeliveryEvidence canonical |
| P1-EM-07 | Deferred | CWF retire — not EM freeze blocker |

### 23.2 Consistency matrix (post-patch)

| Axis | Status |
|------|--------|
| PRODUCT-02 Command Center / Launch subtree | **PASS** |
| PRODUCT-02 Publication in MVP band | **PASS** via contract C (product E2E) |
| PRODUCT-02 ApprovalRecord / no published=true | **PASS** (docs) |
| PRODUCT-03 Strategy≠Launch / Offer / Channel | **PASS** |
| PRODUCT-03 launch_eligible / pins | **PASS** |
| CWF.1 / FINISH-01 publish DoD | **PASS** — binds to contract **C**, not every LaunchRun |
| LaunchRun vs ApprovedLaunchPackage | **PASS** |
| CampaignFrame semantics | **PASS** |
| Budget boundary | **PASS** |
| Offer boundary | **PASS** |
| Approvals minimal + version-pinned | **PASS** |
| Multiplicity 1→N | **PASS** (target); live CWF uq_* = adapter debt for Architecture |
| Outcome Capture | **PASS** |
| MVP cut | **PASS** |
| Registry / code | Unchanged; reuse map honest |

### 23.3 Exact next owner action

```text
Next priority: NOT SET
Logical next (when owner chooses): formal kickoff PRODUCT-04-LAUNCH-ARCHITECTURE-01 (docs-only)
NOT: re-open Execution Model · auto-start Runtime · treat BusinessCampaign as canonical without audit
```

### 23.4 PATCH-01 reviewer composite

| Reviewer | Verdict |
|----------|---------|
| Architecture | **PASS** |
| Product | **PASS** |
| Runtime | **PASS** |
| Security | **PASS** |
| Test | **PASS** |

**Composite:** **PASS**

**Residual (non-blocking; deferred after freeze):** LaunchRun state model · BusinessCampaign compatibility · dual publication stack audit · CWF retirement · catalog wording cleanup

### 23.5 Freeze confirmation

```
PRODUCT-04-EXECUTION-MODEL = OWNER-FROZEN
owner_freeze = OWNER-FROZEN
frozen_at = 2026-08-02
invariants = EM Freeze record §1–26
```


---

## Appendix — Consistency matrix (summary — pre-patch historical)

| Axis | Status |
|------|--------|
| P02 Command Center / Launch subtree | Align |
| P02 MVP spine includes Publication band | Align **if** §6 contracts adopted |
| P02 ApprovalRecord / no published=true | Align (docs); code adapter |
| P03 Strategy≠Launch / Offer / Channel | Align |
| P03 launch_eligible / pins | Align (semantic) |
| CWF.1 publish DoD | **Conflict** until OD-EM-06 **A** — **resolved in PATCH-01 §23.2** |
| Registry planned Launch/* | Align |
| Live CWF 1:1 uniqueness | **Conflicts** target multiplicity |
| BusinessCampaign vs Campaign frame | **Conflict** until OD-EM-04 — **resolved as reuse candidate** |
| Budget unified | **Missing** — **resolved as Launch envelope (docs)** |

---

## Appendix — Reviewer composite (consistency audit)

| Reviewer | Verdict |
|----------|---------|
| Architecture | **PASS** |
| Product | **PASS** |
| Runtime | **PASS** |
| Security | **PASS** |
| Test | **PASS** |

**Composite:** **PASS** (audit completeness — not Execution Model owner freeze)

