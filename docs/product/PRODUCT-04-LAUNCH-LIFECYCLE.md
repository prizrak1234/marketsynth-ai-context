# PRODUCT-04 — Launch Lifecycle

> **Task:** PRODUCT-04-LAUNCH-ARCHITECTURE-PATCH-01  
> **Owns:** Applied Launch lifecycles (not global Project enum)  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-LA-01, 06, 07 **OWNER-ACCEPTED**  
> **Inherits:** Domain Model · EM · Fabric OWNER-FROZEN

---

## 0. Separation rule

**Forbidden:** collapsing LaunchRun states with PublicationJob / PackageJob states or Project lifecycle enums.

Four layers:

| Layer | What |
|-------|------|
| **A. LaunchRun** | Fabric CapabilityRun statuses |
| **B. Package / Candidate** | ArtifactVersionState-aligned |
| **C. Approval** | ApprovalRecord decisions |
| **D. Derived customer UI** | Computed labels — not persisted SoT |

---

## A. LaunchRun lifecycle (OD-LA-01 = A)

`queued` · `running` · `succeeded` · `failed` · `cancelled` · `interrupted`

| Rule | |
|------|--|
| **Interrupted** | **Terminal** |
| After interrupt + recovery | Run does **not** return to `running` |
| Retry | New **attempt**, same `run_id` — Fabric carve-out only (pre-terminal or `interrupted`); does **not** reopen other terminals as `running` |
| Rerun | New LaunchRun (`rerun_of_run_id`) — new owner intent |
| Manual recovery | Explicit owner decision |
| Resume | Only with proven safe checkpoint; else retry / rerun / manual recovery |
| Succeeded | May hold **unapproved** candidate |
| Failed / interrupted | May preserve **partial** artifact (`result_kind=partial`) |
| Pending approval | **Derived** from artifact + missing decided ApprovalRecord — **not** a run status |
| Not run statuses | waiting_for_approval · partial · stale · approved · published |

**Forbidden:** silently resurrecting a terminal run into `running`.

---

## B. LaunchCandidate / Package lifecycle

`draft` · `ready_for_review` · `approved` · `rejected` · `superseded` · `invalidated` · `archived`

| Transition | Meaning |
|------------|---------|
| draft → ready_for_review | Candidate assembled for owner |
| → approved | Single `launch_package_approval` on this version (OD-LA-03) |
| → rejected | Decision retained; history kept |
| approved → superseded | Newer approved head; prior immutable |
| → invalidated | Explicit event (actor/reason/time) |
| Any → archived | Soft retention |

**Immutability:** once `approved`, body does not change. Edits → **new version**.  
**Cancellation of child requests does not mutate** an approved Package (OD-LA-07).

---

## C. Approval lifecycle

`pending` · `approved` · `rejected` · `expired` · `invalidated`

**Clarification:** `pending` is **derived** (triggering artifact version exists without a decided ApprovalRecord) — not necessarily a persisted `decision` enum value.

Pinned to artifact version. Expired ≠ invalidated ≠ rejected ≠ superseded artifact. Expired blocks **new** external action; does not undo completed send.

---

## D. Derived customer states

| Label | Typical derivation |
|-------|--------------------|
| drafting | Candidate draft / running |
| awaiting_review | Candidate ready_for_review + pending package approval |
| approved | current_approved Package exists |
| stale_viewable | Upstream change; readable with warning |
| stale_blocking | Blocks new handoff / external |
| execution_in_progress | Child Content/Visual/Publication runs active |
| execution_requires_attention | Ambiguous external · failed child · blocked handoff |

---

## Scenario matrix

| # | Scenario | Persisted outcome |
|---|----------|-------------------|
| 1 | Strategy approved → Launch start | LaunchRun + LaunchInputSnapshot |
| 2 | Candidate generated | LaunchCandidate draft/ready |
| 3 | Owner requests changes | New candidate version |
| 4 | Candidate rejected | rejected retained |
| 5 | Package approved | current_approved; Domain MVP (A) |
| 6 | Package superseded | New approved head; old immutable |
| 7 | Strategy stale | Package stale_*; handoff rules |
| 8 | Budget changes | New Package version if requirements change |
| 9 | ContentRequest revised | New request version; assets may stale |
| 10 | Visual optional fails | Content-only if Package allows |
| 11 | Publication handoff blocked | stale_blocking / missing assets / approvals |
| 12 | Launch abandoned | Run cancelled/failed; history kept |
| 13 | Launch reopened | New LaunchRun (rerun) — not silent resume of terminal |
| 14 | Multiple Launch runs | N runs under Project |
| 15 | In-flight after Package supersession | § In-flight policy (OD-LA-06 **accepted**) |

---

## In-flight supersession policy (OD-LA-06 = A — OWNER-ACCEPTED)

**Scenario:** Package v1 approved → ContentRequest v1 dispatched → Package v2 approved.

| Rule | Behavior |
|------|----------|
| Auto-cancel | **No** |
| Child run | **May complete** |
| Result | Remains bound to **request v1**; history preserved |
| Stale | Asset/result **derived stale against Package v2** (Content-derived overlay preferred; Launch does not own ContentAsset mutation) |
| Reuse of v1 asset for v2 | Only via **explicit owner decision** (accept for legacy/manual use · discard for v2 · regenerate under v2) |
| v2 path | **New** ContentRequest / VisualRequest under v2 required |
| DeliveryEvidence / history | **Never rewritten** |
| Hard cancel | Only separate **safe** command if external side effect **not yet started** |

**Forbidden:**

- mutate v1 request / Package body  
- attach v1 asset to v2 **silently**  
- rewrite DeliveryEvidence  
- cascade delete  
- universal hard cancel of all children  

Publication handoff for **v2** uses only assets satisfying **v2** requests (or explicit owner revalidation).

Restore lists each child run/request with its **pinned Package version**.

---

## Request cancellation vs Package revision (OD-LA-07 = C — OWNER-ACCEPTED)

| Mode | When | Effect |
|------|------|--------|
| **A. Request cancellation** | Requirements of Package still valid; stop a specific request/run | Cancels that request version / child run; **Approved Package unchanged**; audit history kept |
| **B. Package revision** | BOM / branch obligation / offer / channel / requirements change | **New Package version** + new request lineage |

Cancellation of a child **must not** automatically alter Approved Package.

---

## Restore / recovery

```
Project open
  → active/recent LaunchRun(s)
  → current_candidate / current_approved / latest_created Package
  → derived stale
  → pending ApprovalRecords (derived)
  → child Content/Visual runs (each labeled with pinned Package version)
  → PublicationPlan + PublicationPackage / PackageJob (+ legacy Job if present)
  → external ledger / ambiguous flags
  → derived next actions
```

| Case | Expectation |
|------|-------------|
| Browser refresh / new session | Same persisted heads |
| Backend restart | Interrupted run stays terminal; recovery via retry attempt / rerun / manual — not silent `running` |
| Failed Content child | Package remains approved; next = retry/rerun Content or cancel request |
| Visual optional failure | Continue if Content-only allowed |
| Pending package approval | awaiting_review (derived) |
| Pending external approval | Block send |
| Ambiguous publication | No blind retry; human/reconciliation (Fabric) |
| Superseded Package | Head = new approved; old readable; in-flight children attributed to pinned version |

Browser storage is **not** SoT.
