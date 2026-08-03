# PRODUCT-04 — Marketsynth Execution Fabric

> **Task:** PRODUCT-04-EXECUTION-FABRIC-01 · **Patch:** PRODUCT-04-EXECUTION-FABRIC-PATCH-01  
> **Title:** Marketsynth Execution Fabric  
> **Type:** Docs-only architecture  
> **Status:** **OWNER-FROZEN**  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Frozen at:** 2026-08-02  
> **OD-EF-01…10:** **OWNER-APPROVED** (2026-08-02)  
> **Basis:** OD-EF-01…10 applied · P0-EF-01 closed · freeze-blocking P1 closed · consistency matrix PASS · reviewers 5/5 PASS · code/runtime/research unchanged  
> **Audit:** `PRODUCT-04-EXECUTION-FABRIC-AUDIT.md` · PATCH validation §25 · freeze §26  
> **Inherits:** PRODUCT-02 OWNER-FROZEN · PRODUCT-03 OWNER-FROZEN · PRODUCT-04 Execution Model OWNER-FROZEN  
> **Does not:** auto-start Launch Architecture · Launch Runtime · code · queues · brokers · DB schema · DSL · workflow engine · new foundation · rewrite P02/P03/EM freeze text

---

## Freeze record

```
owner_freeze: OWNER-FROZEN
owner_freeze_status: frozen
frozen_at: 2026-08-02
frozen_by: owner
program: PRODUCT-04 Execution Fabric
basis: OD-EF-01…10 applied; P0-EF-01 closed; freeze-blocking P1 closed; consistency matrix PASS; reviewers 5/5 PASS; code/runtime/research unchanged
```

### Frozen invariants (normative)

1. Execution Fabric — semantic contract, not a separate product.  
2. Fabric is not a workflow engine, scheduler, broker, DSL, or event-sourcing platform.  
3. Capability Registry manages availability and UX exposure.  
4. Fabric describes capability execution semantics.  
5. Backend authorization remains a separate boundary.  
6. Common CapabilityRun lifecycle: `queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted`.  
7. Approval, stale, partial, and published are **not** CapabilityRun states.  
8. Retry creates a new execution attempt of the **same** CapabilityRun.  
9. Rerun creates a **new** CapabilityRun and a new lineage entry.  
10. Revision creates a new artifact version.  
11. Interrupted run is terminal by default.  
12. Resume is allowed only with a proven safe checkpoint.  
13. InputSnapshot is immutable and pinned to specific artifact versions.  
14. A capability does not dynamically read “latest project state.”  
15. Artifact payload remains domain-specific.  
16. Approved artifact is immutable.  
17. Owner edit creates a new version.  
18. Approval is pinned to an artifact version.  
19. Approval does not transfer to a new version.  
20. Stale is a derived state.  
21. Invalidation is an explicit event/decision.  
22. History is not deleted and not rewritten.  
23. Optional branch join is defined by the domain capability.  
24. Fabric does not create a global enum of child-state combinations.  
25. External critical action requires explicit approval.  
26. For external action the following are mandatory: `external_action_fingerprint`; `execution_idempotency_key`; execution ledger; attempt history; provider reference when available; reconciliation before retry.  
27. Result classification: `confirmed_success` · `confirmed_failure` · `not_started` · `ambiguous`.  
28. Blind retry on an ambiguous result is forbidden.  
29. Ambiguous external result requires reconciliation or human resolution.  
30. Reload/restart does not automatically repeat an external action.  
31. OutcomeRecord is linked to ExecutionEvidence.  
32. OutcomeRecord is project-level and is not full Analytics.  
33. Restore is based on persisted domain state, not browser storage.  
34. Cross-project and cross-tenant handoff are forbidden by default.  
35. HandoffSnapshot is a logical boundary, not a mandatory separate table.  
36. Fabric MVP is limited to the minimum needed for the first runtime.  
37. Generic DAG, scheduler, backend CapabilityDefinition table, and workflow DSL are post-MVP.  
38. After Fabric freeze, new general foundation layers are forbidden without a proven P0.  
39. The next architecture is applied Launch Architecture only.  
40. Freezing Fabric does **not** automatically start Launch Runtime.

### What freeze does / does not

| Freeze does | Freeze does **not** |
|-------------|---------------------|
| Accept Execution Fabric as OWNER-FROZEN | Start Launch Architecture pack automatically |
| Lock invariants 1–40 for Launch Architecture | Start Launch Runtime / Strategy Runtime / Research |
| Authorize planning against Fabric semantics | Rewrite PRODUCT-02/03/EM · edit Registry · change code |
| Close the last general foundation before applied Launch | Treat dual publication stack as auto-canonical |

**Deferred:** dual publication stack audit · BusinessCampaign compatibility · runtime authorization enforcement · stale domain defaults · physical HandoffSnapshot decision  

**Next priority:** **NOT SET** (owner chooses separately; logical next = formal kickoff PRODUCT-04-LAUNCH-ARCHITECTURE-01)

---

## 1. Executive definition

**Execution Fabric** is the **shared semantic contract** for how Marketsynth capabilities execute and hand off — not a product, not a screen, not a capability, not a runtime framework.

> How does an approved capability start, pin inputs, run, produce artifacts, get approval, hand off, retry safely, go stale, restore, record evidence, and export — **the same way** for Launch, Content, Visuals, Publication, and peers?

Users never buy “Fabric.” After this document is owner-frozen, **no new general foundation** before Launch Architecture without a proven P0 that cannot be closed inside Launch Architecture.

---

## 2. Scope and non-goals

### In scope

CapabilityDefinition (semantic) · CapabilityRun · InputSnapshot · ArtifactVersion + pointers · ApprovalRecord · orchestration patterns · parallelism · retry/rerun/resume · stale/invalidation · restore · DeliveryEvidence · OutcomeRecord · external-action ledger · security · observability · export · reuse map · MVP cut · test oracles

### Out of scope / forbidden

| Forbidden | Why |
|-----------|-----|
| Revisit EM invariants 1–26 | OWNER-FROZEN |
| Launch BOM / CampaignFrame / Offer fields | Launch Architecture |
| Content / Visual / Publication Architecture | Later programs |
| Celery, Redis, Kafka, Temporal, queues, brokers | Not Fabric |
| Physical tables, SDK, DSL, low-code / DAG engine | Overdesign |
| Mandatory backend CapabilityDefinition table | OD-EF-10 |
| Capability Registry edits | Exposure SoT |
| Auto-start Launch Architecture / Runtime | Owner gate |

**Fabric is not:** product · UI · capability · Launch Runtime · task queue · event bus · agent framework · authorization layer.

---

## 3. Relationship to frozen architecture

| Layer | Fabric role |
|-------|-------------|
| PRODUCT-02 | Shared grammar of four layers |
| PRODUCT-03 | Does not redefine Strategy; enables handoff |
| PRODUCT-04 EM | Must not contradict; LaunchRun = CapabilityRun specialization; A/B/C preserved |
| Registry | Availability only — not authz |
| CWF.1 / FINISH-01 | Contract C via external-action evidence — not redefined |

**EM contracts remain normative:** A Package · B Publication execution · C Commercial MVP E2E.

---

## 4. Current foundation audit (honesty)

| Area | Tag |
|------|-----|
| BIV durable run / interrupt→FAILED / startup recovery | **adapter** |
| AgentRun | **legacy** — do not unify |
| PublicationJob (attempts, weak outbound idempotency) | **adapter + debt** |
| PublicationPackageJob (create fingerprint) | **adapter + dual-stack debt** |
| DeliveryLog | **adapter** → DeliveryEvidence |
| Offer versioning | **adapter** |
| Unified ApprovalRecord / OutcomeRecord | **missing** |
| Capability Registry | **aligns** (availability) |

Dual publication stacks: **compatibility audit in Launch Architecture** — neither stack auto-canonical (see §21).

---

## 5. Core Fabric model

```
CapabilityDefinition (semantic)
  → CapabilityRun
  → InputSnapshot
  → ArtifactVersion (candidate → approved)
  → ApprovalRecord
  → Handoff (logical → next InputSnapshot; optional persisted HandoffSnapshot)
  → Next CapabilityRun(s)
  → DeliveryEvidence / execution ledger   (if external)
  → OutcomeRecord                         (when evidence / provenance)
```

| Object | Role |
|--------|------|
| CapabilityDefinition | Docs/semantic card — **not** mandatory backend table |
| CapabilityRun | Identity = `run_id` + InputSnapshot; hosts **attempts** |
| InputSnapshot | Immutable pinned inputs |
| ArtifactVersion | Domain payload; pointers §9 |
| ApprovalRecord | Version-pinned decision |
| Handoff | Logical transition; physical form = Runtime design choice |
| DeliveryEvidence | External action proof |
| OutcomeRecord | Project-level post-execution facts |

---

## 6. CapabilityDefinition (OD-EF-10)

Semantic contract aligned with catalog ids where possible.

**Does not require:** backend CapabilityDefinition table · duplication of Capability Registry · authz.

| Layer | Owns |
|-------|------|
| **Capability Registry** | Availability / public exposure / route |
| **Fabric CapabilityDefinition** | Execution semantics |
| **Backend authorization** | Who may invoke |

---

## 7. CapabilityRun (OD-EF-01)

### Canonical statuses (only)

`queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted`

**Not in common enum:** `waiting_for_approval` · `partial` · `stale` · `approved` · `published` · `blocked`

| Rule | |
|------|--|
| Run terminal ≠ artifact result | Failed/interrupted may leave **partial** artifact (`result_kind=partial`) |
| `succeeded` ≠ partial primary output | Primary artifact for a `succeeded` run must be non-partial; partial-only result maps to `failed`/`interrupted`, never `succeeded` |
| Succeeded may leave **unapproved** candidate | Approval is separate |
| Waiting for approval | **Derived:** terminal run + candidate + pending ApprovalRecord |
| Partial | Artifact/result — **not** run status |

### Fields (semantic)

`tenant_id` · `project_id` · `capability_id` · `run_id` · `input_snapshot_id` · `parent_run_id` (conditional) · `correlation_id` · **request** `idempotency_key` · `rerun_of_run_id` (if rerun) · `status` · timestamps · `safe_error` · attempt refs · produced artifact refs

**LaunchRun** = CapabilityRun with `capability_id = project.launch`.

**After interrupted + successful attempt:** parent may become terminal `succeeded`/`failed` **without** reopening `running` (default).

---

## 8. InputSnapshot and Handoff (OD-EF-10)

### InputSnapshot — **required** semantic boundary

Immutable · version-pinned · tenant/project-bound · no dynamic “latest project” reads · cross-project handoff forbidden by default · cross-tenant forbidden.

### HandoffSnapshot — **conditional**

- Logically describes transition (source run, approved pins, constraints, approvals, target capability).  
- **May** be a separate persisted object **or** simply the next run’s InputSnapshot.  
- Must not duplicate full upstream payload.  
- Physical form decided in first Runtime / Launch Architecture audit — **not** a universal mandatory table.

---

## 9. Artifact model and pointers (P1-EF-05 closed)

Inherits PRODUCT-02 ArtifactVersionState. Payload remains domain-specific.

### Three distinct pointers (never one ambiguous “current”)

| Pointer | Meaning |
|---------|---------|
| `latest_created_version` | Newest created version id |
| `current_candidate_version` | Editable / in-review head (domain) |
| `current_approved_version` | Canonical approved head for handoff |

Many historical approved versions may exist. **One** canonical `current_approved` per lineage/context. Changing a pointer does **not** rewrite history.

**ApprovedArtifact** = ArtifactVersion with binding ApprovalRecord — **not** a separate universal type.

---

## 10. Approval model (OD-EF-04)

PRODUCT-02 ApprovalRecord.

| Rule | |
|------|--|
| Version-pinned; server-attested actor | |
| Does not transfer to new version | |
| New version always needs new approval | |
| Rejection / invalidation retained | |
| External action = separate approval type | |
| Expiry | Domain-configurable; **not** required for all types |
| Expired | History kept; **blocks new** external action; does **not** undo completed action |
| Expired ≠ invalidated ≠ rejected ≠ superseded artifact | Different causes |

---

## 11. Orchestration and handoff

Patterns (not a DAG engine): sequential · parallel fork · join · optional branch · reject/rework · repeated run · stop without next · abandon/reopen · post-execution outcome.

Illustrative only: Strategy→Launch→Content∥Visuals→Publication→Outcome. Mandatory branches = domain (Launch Architecture).

---

## 12. Parallelism and optional join (OD-EF-07)

- Independent child CapabilityRuns  
- Fabric supports: **required** branch · **optional** branch · **minimum completion set** · **accepted partial completion**  
- Join rules = **domain capability** (e.g. Content required, Visual optional)  
- Parent orchestration result = derived from domain completion contract — **never** auto “all children succeeded”  
- **No** global enum of child-state combinations  
- Failed child does not auto-complete/abandon Project  

---

## 13. Retry / rerun / resume / revision (OD-EF-02, OD-EF-03)

| Term | Definition |
|------|------------|
| **Retry** | New **execution attempt** of the **same** CapabilityRun — same `run_id`, same `input_snapshot_id`, same logical intent; attempt lineage persisted. Valid only while the run is not yet terminal (`queued`/`running`), **except** the interrupted carve-out below |
| **Rerun** | **New** CapabilityRun — new `run_id`, new request idempotency boundary, explicit `rerun_of_run_id`, new or re-pinned InputSnapshot. Required after terminal `failed`/`cancelled` (and after `interrupted` when resume is not proven) |
| **Revision** | New **artifact version** — not automatically a new run |
| **Resume** | Continue after `interrupted` **only** with proven safe checkpoint (below) |

### Resume policy (OD-EF-03 A)

**Default:** `interrupted` is **terminal**.

Resume allowed **only if** capability blueprint proves:

- persisted checkpoint  
- safe repeatability of next step  
- **no** unresolved ambiguous external side effect  
- deterministic continuation boundary  
- unchanged pinned inputs  

**Forbidden** generic resume for publish / paid action / message send / external mutation **without** reconciliation.

If resume contract not proven → **Rerun** or manual recovery — never blind continue.

Successful attempt after interrupt may set parent terminal `succeeded`/`failed` without reopening `running`.

---

## 14. External action deduplication (OD-EF-08 A — closes P0-EF-01)

**Freeze invariant:** blind retry of critical external actions is **forbidden**.

### Mandatory for each critical external action

- `external_action_fingerprint`  
- `execution_idempotency_key` (distinct from run-create key)  
- Persisted **execution ledger**  
- Provider request/reference id when available  
- Attempt history  
- **Reconciliation / probe before retry**  
- Result classification  

### Result classification

| Class | Meaning |
|-------|---------|
| `confirmed_success` | Do **not** retry |
| `confirmed_failure` | May retry/rerun per policy |
| `not_started` | May retry if safe |
| `ambiguous` | **No** automatic retry |

### Ambiguous rules

1. Do not repeat the action automatically.  
2. Customer-safe status: **«Результат внешнего действия требует проверки»**.  
3. Provider lookup / reconciliation.  
4. If impossible → **human resolution**.  

Also: reload/restart must not re-fire action; duplicate paid/publish effect forbidden; confirmed_success never retried.

**Not** provider-specific implementation design — semantic contract only.

---

## 15. Stale (OD-EF-05)

Stale is **derived** from pinned dependencies (not a manual universal ArtifactVersionState).

| Label | Effect |
|-------|--------|
| `stale_viewable` | Readable; not “current” without warning |
| `stale_blocking` | Blocks new handoff **and** external execution; needs revalidation / new version |

Domain blueprints define dependency rules.

---

## 16. Invalidation (OD-EF-06 A)

**No cascade deletion. No automatic rewrite of downstream artifacts.**

Upstream change:

- Preserves history  
- Computes **derived stale** on dependents  
- Blocks new handoff/execution only per **domain** critical-dependency rules  
- Does **not** undo completed external actions  
- Requires owner/domain decision to rebuild  

**Explicit `invalidated`:** separate event/decision (actor, reason, timestamp) — not auto for entire chain. Blocks further handoff; invalidates related approvals for handoff; does not delete artifact.

---

## 17. Restore / recovery

UI derived from persisted domain state — not sessionStorage/localStorage SoT.

```
Project hydration
  → active/recent CapabilityRuns
  → latest_created / current_candidate / current_approved pointers
  → pending ApprovalRecords
  → interrupted/failed runs
  → stale (derived)
  → external jobs / ledger
  → next actions (derived)
```

No universal project aggregate required beyond composing existing persisted objects.

---

## 18. Evidence and Outcome (OD-EF-09)

| Object | Role |
|--------|------|
| Evidence | Decision support (e.g. Research) |
| DeliveryEvidence / ExecutionEvidence | Proof of external action |
| OutcomeRecord | Project-level observed result |

### OutcomeRecord

- Tenant/project-bound; **project-level**  
- Links: capability run · external job/action · ExecutionEvidence · campaign/publication context · observation window  
- **Not** a LaunchRun child artifact · **not** Analytics  
- May appear after Launch terminal / even after Project pause  
- **Forbidden** without ExecutionEvidence **except** explicit manual observation with actor attribution + provenance  

---

## 19. Security

Tenant/project/run/artifact/snapshot ownership · server-attested approval actors · external action authz · export ACL · no cross-tenant · cross-project handoff deny-by-default · secrets excluded · Registry ≠ authz · frontend ≠ authz · knowledge reuse only via sanitized contract.

---

## 20. Observability and export

**Observability:** correlation_id · lineage · parent/child · terminals · safe errors · retry/rerun · artifacts · approvals · external ledger · outcomes.

**Export:** approved versions only · tenant/project ACL · no secrets · domain payload · export ≠ new approval.

---

## 21. Code reuse and dual publication stack

| Subsystem | Status |
|-----------|--------|
| BIV runs / recovery | adapter |
| PublicationJob / PackageJob / Delivery | adapter; **dual-stack debt** |
| Approval adapters | → ApprovalRecord |
| Launch Pack / BusinessCampaign | transitional / reuse candidate |

### Freeze follow-up (Launch Architecture — not this task)

Compatibility audit **required** before declaring any publish path canonical:

PublicationJob · Delivery · legacy/direct publish · CWF publication · ExecutionApproval · duplicate-execution risk.

Until then: **no** stack is auto-canonical. Any real send path must still honor §14 fingerprint / ledger / no-blind-retry.

---

## 22. Fabric MVP cut (OD-EF-10 A)

### Required

CapabilityRun · InputSnapshot · ArtifactVersion semantics + three pointers · ApprovalRecord · execution attempts · request idempotency · external execution idempotency + ledger · restore · stale/invalidation · DeliveryEvidence · tenant/project isolation

### Conditional

HandoffSnapshot as separate persisted object · `parent_run_id` · orchestration relation · OutcomeRecord (with first external path)

### Post-MVP

Generic DAG · scheduler platform · broker abstraction · backend CapabilityDefinition registry · workflow DSL · cross-project orchestration · event-sourcing platform

Fabric is **not** a commitment to build a full execution platform before first Runtime.

---

## 23. Testability matrix (strengthened)

| # | Oracle |
|---|--------|
| 1 | Retry keeps same `run_id` + InputSnapshot |
| 2 | Rerun creates new `run_id` + `rerun_of_run_id` |
| 3 | Interrupted run does not resume without proven safe checkpoint |
| 4 | Ambiguous external response does **not** trigger blind retry |
| 5 | Fingerprint / execution_idempotency_key blocks duplicate external action |
| 6 | Reconciliation/probe before retry when outcome unknown |
| 7 | Approval expiry blocks new execution; history retained |
| 8 | Upstream change makes downstream `stale_*` (derived) |
| 9 | Explicit invalidation keeps history; blocks handoff |
| 10 | Optional branch does not block domain-approved path |
| 11 | Outcome requires ExecutionEvidence or attributed manual provenance |
| 12 | latest_created / current_candidate / current_approved distinguishable |
| 13 | Cross-project handoff denied by default |
| 14 | Restore independent of browser storage |
| 15 | Succeeded run may still have unapproved candidate |
| 16 | Waiting-for-approval is derived, not a run status |
| 17 | Reload does not auto-fire external action |
| 18 | Export only approved version + ACL |
| 19 | Successful attempt after `interrupted` may set parent terminal `succeeded`/`failed` without reopening `running` |
| 20 | `succeeded` primary artifact `result_kind` ≠ `partial` |

Each future test: setup · action · persisted result · observable evidence.

---

## 24. Risks

| ID | Mitigation |
|----|------------|
| R1 Workflow-engine creep | Hard non-goals + MVP cut |
| R2 Re-open EM | Forbidden |
| R3 Unify AgentRun | Legacy ban |
| R4 Globalize one-active-run | Domain-only |
| R5 Dual publish stacks | Launch Architecture audit |
| R6 Registry as authz | Three-layer split |
| R7 Another foundation before Launch | Forbidden without proven P0 |

---

## 25. Owner decisions applied (OD-EF-01…10)

| ID | Decision | Status |
|----|----------|--------|
| OD-EF-01 | Minimal run states; no waiting/partial/stale/approved/published on run | **OWNER-APPROVED** |
| OD-EF-02 | Retry = attempt same run; Rerun = new run | **OWNER-APPROVED A** |
| OD-EF-03 | Interrupted terminal; resume only with safe checkpoint; no blind external resume | **OWNER-APPROVED A** |
| OD-EF-04 | Expiry supported, domain-configurable; history kept | **OWNER-APPROVED** |
| OD-EF-05 | stale_viewable / stale_blocking derived | **OWNER-APPROVED** |
| OD-EF-06 | No cascade delete; explicit invalidation; derived stale | **OWNER-APPROVED A** |
| OD-EF-07 | Optional join = domain; Fabric semantics only | **OWNER-APPROVED** |
| OD-EF-08 | No blind retry; fingerprint + ledger + classification + reconciliation | **OWNER-APPROVED A** |
| OD-EF-09 | Outcome project-level; evidence-linked | **OWNER-APPROVED** |
| OD-EF-10 | Minimal first Runtime; no DAG/CapabilityDefinition table | **OWNER-APPROVED A** |

---

## 26. Finding closure

| ID | Status |
|----|--------|
| P0-EF-01 | **CLOSED** — §14 ambiguous/no blind retry |
| P1-EF-01 | **CLOSED** — CapabilityDefinition semantic/docs |
| P1-EF-02 | **CLOSED** — interrupt + attempt terminal rule |
| P1-EF-03 | **CLOSED** for Fabric freeze — dual-stack follow-up ticketed to Launch Architecture |
| P1-EF-04 | **CLOSED** — Handoff conditional |
| P1-EF-05 | **CLOSED** — three pointers |
| P1-EF-06 | **CLOSED** — Outcome conditional / evidence-linked |
| P2-EF-01 | **CLOSED** — parent join domain-derived |

---

## 27. Freeze record (applied)

| Field | Value |
|-------|-------|
| Patch task | PRODUCT-04-EXECUTION-FABRIC-PATCH-01 = **docs_verified** |
| Execution Fabric | **OWNER-FROZEN** (2026-08-02) |
| **`owner_freeze`** | **OWNER-FROZEN** |
| Launch Architecture | **NOT STARTED** |
| Next priority | **NOT SET** |

### Owner freeze checklist

1. ☑ OD-EF-01…10 accepted  
2. ☑ P0-EF-01 closed  
3. ☑ Freeze-blocking P1 closed  
4. ☑ No blind external retry  
5. ☑ Run/attempt identity explicit  
6. ☑ Resume restricted  
7. ☑ Pointers explicit  
8. ☑ HandoffSnapshot not mandatory infra  
9. ☑ Fabric MVP minimal  
10. ☑ Owner message: Fabric = **OWNER-FROZEN** (2026-08-02)  
11. ☐ PRODUCT-04-LAUNCH-ARCHITECTURE-01 — only after separate kickoff; next priority currently **NOT SET**  

---

## Appendix A — Normative sources

PRODUCT-02 / 03 / 04-EM OWNER-FROZEN · Capability Registry (availability) · CWF.1 (contract C)

## Appendix B — Hard boundary after freeze

After Fabric **OWNER-FROZEN**: the only permitted next architecture program is applied `PRODUCT-04-LAUNCH-ARCHITECTURE-01` (owner kickoff required; next priority currently **NOT SET**).  
New general foundation before Launch **forbidden** unless proven P0 cannot be closed inside Launch Architecture.  
Re-opening Fabric, EM Launch model, or the three completion contracts A/B/C is **forbidden**.
