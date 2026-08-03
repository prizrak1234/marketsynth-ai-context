# PRODUCT-04 — Owner Launch Journey

> **Task:** PRODUCT-04-LAUNCH-ARCHITECTURE-PATCH-01  
> **Owns:** Owner flow placement only — no UI layout / IA edits  
> **Status:** **docs_verified** · **ready_for_owner_freeze** · `owner_freeze` **NOT SET**  
> **OD applied:** OD-LA-01…10 **OWNER-ACCEPTED**  
> **Honesty:** Until Strategy Runtime live, CWF Launch Pack path remains **transitional adapter**

---

## Container

Project Command Center → Launch panel (after Strategy readiness). Not a Workspace Launch app.

---

## Journey steps

### A. Strategy approved

| | |
|--|--|
| User | “Can I start Launch?” |
| System | Check launch_eligible + Strategy pin |
| Persist | — |
| CTA | Start Launch |
| Block | Missing Strategy approval / eligibility |
| Next | B |

### B. Start Launch

| | |
|--|--|
| System | Create LaunchRun + LaunchInputSnapshot |
| Persist | Run queued/running |
| CTA | Wait / view progress |
| Restore | Same run id |
| Note | Interrupt → terminal (OD-LA-01); recovery ≠ silent return to running |

### C. Launch candidate generated

| | |
|--|--|
| System | LaunchCandidate with BOM |
| Persist | Candidate draft/ready_for_review |
| CTA | Review |
| Next | D–G |

### D. Review CampaignFrame / Offer / Budget

| | |
|--|--|
| User | Are frame, offer, budget section honest? |
| CTA | Edit · Clarify · Approve path · Reject |
| Persist | Edits → new candidate version |
| Note | UI may default **one** frame; model allows N (OD-LA-05) |

### E. Request clarification

| | |
|--|--|
| Persist | Notes / assumptions updated → new version |
| CTA | Resume review |
| Block | Empty critical fields |

### F. Reject candidate

| | |
|--|--|
| Persist | rejected + reason |
| CTA | Revise · Abandon |
| Next | G or T |

### G. Revise package

| | |
|--|--|
| Persist | New candidate / Package version |
| Rule | Never mutate approved Package |
| When | BOM / offer / channel / request requirements change (OD-LA-07 B) |

### H. Approve package

| | |
|--|--|
| Persist | Single `launch_package_approval` · current_approved |
| Covers | Frames · offers · budget section · ContentRequests · conditional VisualRequests · PublicationPlan · assumptions/limitations |
| CTA | Stop here (Domain MVP) · Start Content · Export Markdown+JSON |
| Block | Incomplete BOM |
| Note | **Does not** publish |

### I. Content generation

| | |
|--|--|
| System | Start Content capability from ContentRequest |
| Persist | Content run + ContentAsset drafts |
| CTA | Review assets · Cancel this request (OD-LA-07 A — Package unchanged) |
| Restore | Child run status + pinned Package version |

### J. Optional Visual generation

| | |
|--|--|
| System | If visual_required |
| Persist | VisualRequest run + assets |
| Fail | Content-only if Package allows |
| Cancel | Same as Content (request cancel ≠ Package mutate) |

### K. Review assets

| | |
|--|--|
| Persist | content_approval / visual_approval |
| CTA | Continue to Publication · Revise request · Regenerate under current Package |
| Stale | If Package superseded mid-flight → see step S / OD-LA-06 |

### L. Publication handoff

| | |
|--|--|
| System | Publication reads Plan + selects approved assets (owner-guided) |
| Persist | PublicationPackage draft → **PackageJob** path (OD-LA-08) |
| Block | stale_blocking Package · missing assets · Plan none · legacy dual-send attempt |

### M. Approve PublicationPackage

| | |
|--|--|
| Persist | publication_package_approval |
| CTA | Approve external execution |

### N. Approve external execution

| | |
|--|--|
| Persist | external_execution_approval · budget_ack if needed |
| Block | Unknown budget without ack · missing Fabric fingerprint/ledger readiness (Runtime) |
| Path | PackageJob only as canonical; legacy PublicationJob not offered as second send |

### O. Publication success

| | |
|--|--|
| Persist | PackageJob succeeded · DeliveryEvidence · external id |
| CTA | View evidence · Outcome |

### P. Publication ambiguous

| | |
|--|--|
| Persist | Result class `ambiguous` |
| CTA | Reconcile · Human resolution |
| Forbidden | Blind retry |

### Q. Publication failed

| | |
|--|--|
| Persist | confirmed_failure |
| CTA | Retry attempt (same job policy) · Revise package/assets |

### R. Outcome captured

| | |
|--|--|
| Persist | OutcomeRecord (project) linked to evidence |
| Note | Not Launch completion |

### S. Strategy / Package becomes stale (incl. in-flight OD-LA-06)

| | |
|--|--|
| Persist | derived stale_*; child may complete; assets stale vs new Package |
| CTA | New Package version · New requests for v2 · Accept/discard stale asset explicitly · Safe cancel if no external side effect |
| Forbidden | Silent attach of v1 asset to v2 · auto-cancel all · rewrite evidence |
| Block | New external on stale_blocking |

### T. Abandon / reopen Launch

| | |
|--|--|
| Persist | Run cancelled **or** new LaunchRun (rerun) |
| Forbidden | Silent resurrect of terminal interrupted run |
| History | Kept |

---

## Honesty: transitional CWF

Current product may show Verdict → Launch Pack → Offer → Content → Telegram. That path is an **adapter**, not Approved Launch Package. Target journey is A→H (Domain MVP) then I→O (E2E via PackageJob). Do not present CWF Pack as Domain Model Package.
