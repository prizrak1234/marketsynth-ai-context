# PROJECT-LIFECYCLE

> **Program:** PRODUCT-02  
> **Owns:** Four-layer lifecycle semantics (not a DB schema)  
> **Patch:** PRODUCT-02-BLUEPRINT-PATCH-01 · OD-01 · OD-08 · OD-10  
> **Status:** OWNER-APPROVED (semantics) · `owner_freeze` NOT SET

---

## 0. Layer split (OD-01 · OWNER-APPROVED)

| Layer | Name | What it answers |
|-------|------|-----------------|
| A | **ProjectLifecycleState** | Is this commercial idea still in play? |
| B | **CapabilityRunState** | Did this attempt of a capability succeed? |
| C | **ArtifactVersionState** | Is this version draft / approved / superseded / invalidated? |
| D | **ApprovalRecord** | Who decided what, when, with what status? |

**Forbidden:** one global enum mixing `research_running`, `strategy_approved`, `publishing`, `analytics_ready` into Project state.

UI timelines and CTAs are **derived** from these layers — not separate persistent project enums.

---

## A. ProjectLifecycleState (small & stable)

| State | Meaning |
|-------|---------|
| `draft` | Project created; intake incomplete or not yet advanced |
| `active` | Owner is progressing the commercial path |
| `paused` | Explicitly paused by owner |
| `completed` | Owner/business decision that the commercial unit is done |
| `abandoned` | Owner abandoned the idea |
| `archived` | Storage/visibility archival — **allowed** because existing product storage already uses archival patterns; not a conveyor stage |

### Rules

1. Project state does **not** encode which capability is running.  
2. A terminal **capability run** does **not** auto-complete the Project.  
3. `completed` / `abandoned` / `archived` are **owner/business** decisions (or explicit archival action).  
4. Pause/abandon/reopen are first-class (reopen → `active` from `paused`/`abandoned` with audit note — product policy later).

---

## B. CapabilityRunState (architectural semantics)

Example values (not a new runtime enum to implement now):

| State | Meaning |
|-------|---------|
| `queued` | Accepted, not started |
| `running` | In progress |
| `succeeded` | Run finished with usable output (may still need approval) |
| `failed` | Run failed; recoverable per capability policy |
| `cancelled` | Owner/system cancelled |
| `interrupted` | External interrupt / timeout / kill |

### Rules

1. Capability runs **may repeat** (new run_id, new versions).  
2. Some capabilities may run **in parallel** (Content ∥ Visuals under Launch).  
3. Failed/cancelled run does not by itself change ProjectLifecycleState.  
4. Partial Research success still requires **owner gate** before Strategy (OD-08).

---

## C. ArtifactVersionState (architectural semantics)

Example values:

| State | Meaning |
|-------|---------|
| `draft` | Editable working version |
| `ready_for_review` | Submitted for approval |
| `approved` | Bound by ApprovalRecord; **immutable snapshot** |
| `rejected` | Rejected; may spawn revision |
| `superseded` | Replaced by a newer version; retained for lineage |
| `invalidated` | Explicitly invalidated (e.g. parent Strategy change) |
| `archived` | Retention / soft-hide |

Approved artifacts are **never deleted** for convenience; they become `superseded` / `invalidated` / `archived`.

**“Stale” is not a separate enum value.** UI may say “stale for current Launch”; assertable truth is: version `status` ∈ {`superseded`,`invalidated`} and/or it is **not** the current head pointer for its type (see ARTIFACT-FLOW §2).

---

## D. ApprovalRecord lifecycle

| Status | Meaning |
|--------|---------|
| `pending` | Awaiting decision |
| `approved` | Accepted |
| `rejected` | Declined |
| `expired` | Past `expires_at` without decision |
| `invalidated` | Prior approval no longer valid |

Approval is **never** a bare boolean on the artifact. See [ARTIFACT-FLOW.md](./ARTIFACT-FLOW.md) § ApprovalRecord.

---

## 1. Capability progress vs Project state

Progress through Intake → Research → Strategy → Launch → … is tracked via:

- capability run history  
- artifact versions + lineage  
- ApprovalRecords  
- derived UI next-action  

**Not** via expanding ProjectLifecycleState.

---

## 2. Parallelism & loops

| Pattern | Allowed |
|---------|---------|
| Content ∥ Visuals under Launch | Yes (OD-04) |
| Multiple PublicationJobs | Yes (OD-07) |
| Strategy revision loop | Yes — new version; may invalidate dependent Launch candidates |
| Optimization loop | Post-MVP — new versioned candidates (OD-06) |
| Research rerun | Yes — new ResearchReport version |

---

## 3. Partial Research → Strategy (OD-08 · OWNER-APPROVED)

**Default:** Partial Research does **not** open Strategy automatically.

Allowed path:

```
partial Research result
  → owner reviews limitations
  → explicit override / continue decision (ApprovalRecord)
  → Strategy marked assumption-constrained
```

On override, Strategy **must inherit**: gaps, limitations, confidence, unresolved assumptions.

---

## 4. Derived UI (not project states)

Examples of derived labels (display only):

- “Research running”  
- “Strategy awaiting approval”  
- “Publication failed”  
- “Content ready · Visuals pending”

These must **not** be written into ProjectLifecycleState.

---

## 5. Implementation note

This document defines **semantic contracts** for future runtime. It does **not** authorize migrations, enums in code, or Strategy Runtime.
