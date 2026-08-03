# COMMERCIAL-SPINE

> **Program:** PRODUCT-02  
> **Owns:** Orchestration graph + MVP / post-MVP / reserved boundary  
> **Patch:** PRODUCT-02-BLUEPRINT-PATCH-01 · OD-04 · OD-05 · OD-06 · OD-07 · OD-08  
> **Status:** OWNER-APPROVED · `owner_freeze` NOT SET

---

## 1. Spine is a graph, not a linear state machine

The commercial path is an **orchestration graph**: owner gates, revision loops, parallel branches, multi-instance publication, and (post-MVP) optimization cycles.

**Forbidden freeze:** treating the spine as one irreversible conveyor enum that collapses Content, Visuals, and Publication into a single project state.

---

## 2. MVP commercial spine (OD-05 · OWNER-APPROVED)

```
Intake
  → Research
  → owner decision (accept / override-with-assumptions / pause / abandon)
  → Strategy
  → thin Launch
  → limited Content  ⎤ may proceed in parallel
  → optional Visual  ⎦
  → one Publication channel (multi-job capable model; MVP uses one channel)
  → basic Outcome Capture
```

### Not in first commercial DoD

- Full Analytics platform  
- Optimization engine  
- Multi-channel orchestration  
- CRM, HR, Legal, Finance, Programmer  
- Workspace Portfolio Analytics  

These remain catalogued / reserved / post-MVP — they do **not** block first payment readiness.

---

## 3. Orchestration graph (full picture)

```
                    ┌── pause / abandon / reopen ──┐
                    ▼                              │
Intake ──► Research ──► [owner gate] ──► Strategy ◄─┘
                          │                 │
                          │ reject/rework   │ revision loop
                          ▼                 ▼
                     (stay / abandon)   thin Launch
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                       Content         Visuals      Offer/Budget/…
                     (parallel)      (parallel)
                          │               │
                          └───────┬───────┘
                                  ▼
                         Approval package(s)
                                  │
                                  ▼
                    PublicationJob(s)  ← multi-instance (OD-07)
                                  │
                                  ▼
                        basic Outcome Capture
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
              (MVP stop)            Optimization candidate (post-MVP)
                                              │
                                              ▼
                                   owner approval → new Strategy /
                                   Launch / Content versions
```

---

## 4. Owner gate after Research

| Outcome | Next |
|---------|------|
| Research accepted (sufficient) | Strategy may start |
| Partial Research | **Blocked** unless explicit override (OD-08) |
| Reject / rework | New Research run or abandon |
| Pause / abandon | ProjectLifecycleState change |

Override path marks Strategy as **assumption-constrained** and inherits gaps / limitations / confidence / assumptions.

---

## 5. Parallel Content & Visuals (OD-04)

Under Launch:

```
Launch
├── Content   → own runs, versions, ApprovalRecords
└── Visuals   → own runs, versions, ApprovalRecords
```

Publication requires an **approved set of necessary artifacts**, not a shared Content+Visuals enum.

---

## 6. Publication multi-instance (OD-07)

One Launch may have:

- multiple content assets  
- multiple visual assets  
- multiple publication packages  
- multiple PublicationJobs  
- retries, schedules, channels, execution evidence  

**Forbidden model:** `published=true` as the only publication truth.

MVP **uses** one channel commercially; the **model** remains multi-instance.

---

## 7. Optimization (OD-06 · post-MVP)

```
Outcome Capture
  → Optimization Candidate
  → owner approval
  → new versioned Strategy / Launch / Content
```

Does **not** rewrite history. Creates new versioned candidates; prior approved artifacts become superseded/stale as lineage requires.

---

## 8. Boundary table

| Band | Includes |
|------|----------|
| **MVP** | Intake, Research, owner decision, Strategy, thin Launch, limited Content, optional Visual, one Publication channel, basic Outcome Capture |
| **Post-MVP** | Multi-channel, full Project Analytics, Optimization loop, Portfolio Analytics, CRM (when journey exists), extended support |
| **Reserved** | HR, Legal, Finance, Programmer, Billing expansion, Team workflows (until journeys) |

---

## 9. Relation to ProjectLifecycleState

Spine progress ≠ ProjectLifecycleState. See [PROJECT-LIFECYCLE.md](./PROJECT-LIFECYCLE.md).

---

## 10. Implementation note

Semantic orchestration only. No runtime, no migrations.
