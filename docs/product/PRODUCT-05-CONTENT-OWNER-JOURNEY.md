# PRODUCT-05 — Owner Content Journey

> **Task:** PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01  
> **Owns:** Owner flow placement — no UI layout  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD-CT-07 = A:** owner_preview Content Factory = **legacy/dev only**; commercial path = Command Center Content  
> **Honesty:** Do not present owner_preview / recovery-preview as the product Content path

---

## Container

Project Command Center → Content (after Approved Launch Package + ContentRequest).

---

## Steps

### A. Launch Package approved with ContentRequest

| | |
|--|--|
| User | “Can I create content?” |
| System | Eligibility: Package approved · Request present · not stale_blocking |
| CTA | Start Content |
| Block | Missing Request · Strategy/Package issues |

### B. Start ContentRun

| | |
|--|--|
| Persist | ContentRun + ContentInputSnapshot |
| Restore | Same run id |

### C. Candidates generated (1..N; UI default 1–3)

| | |
|--|--|
| Persist | ContentCandidate drafts under Request |
| CTA | Review · Regenerate · Edit |
| Note | Variants ≠ A/B test platform (OD-CT-04) |

### D. Review / edit

| | |
|--|--|
| Persist | New version; actor attribution |
| Constraints | Tone/language/length/channel from Request — not reinvented |

### E. Reject / regenerate

| | |
|--|--|
| Persist | rejected or **new candidate** (OD-CT-05); approved intact if already approved |
| Forbidden | Overwrite approved |

### F. Approve ContentAsset

| | |
|--|--|
| Persist | `content_approval` · current_approved |
| CTA | Handoff to Publication · Stop |
| Note | Does **not** publish |

### G. Publication handoff

| | |
|--|--|
| System | Publication reads Plan + selects approved assets |
| Persist | PublicationPackage (Publication-owned) |
| Block | stale_blocking · missing approval |

### H. Stale / Package superseded

| | |
|--|--|
| Persist | derived stale_*; in-flight may complete (OD-LA-06) |
| CTA | New Request under v2 · Discard/accept legacy explicitly |

### I. Cancel Request / abandon

| | |
|--|--|
| Persist | Cancel child (OD-LA-07); Package unchanged |
| History | Kept |

### J. Restore after refresh

Same persisted heads; assets labeled with Request + Package version.

---

## Forbidden owner-facing behaviors

- Presenting owner_preview Content Factory as the commercial Content path (OD-CT-07).  
- Letting Content “improve” Offer/ICP/budget.  
- JSON-only product UI for customer deliverable.  
- Blind regenerate / in-place replace of approved text (OD-CT-05).  
- Treating H2.7 drafts as ContentAsset without a future adapter OD (OD-CT-02).
