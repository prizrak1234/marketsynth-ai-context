# Integration I7 — Backend gap register

Priority: **P0** blocks honest commercial MVP · **P1** first production workflow · **P2** execution automation · **P3** enhancement

| ID | Gap | Pri | Workaround | Risk | Minimum solution | Migration | UI dep | Tests |
|----|-----|-----|------------|------|------------------|-----------|--------|-------|
| G1 | Durable ProjectBrief / Intake | P0 | local draft + Project name/desc | Lost commercial intake; reopen loses fidelity | Persist brief entity or Project structured fields | medium | Intake | create/update/owner |
| G2 | Durable Investigation | P0 | projections + local | No audit trail of research | Investigation aggregate + stages | high | Investigation | CRUD + owner |
| G3 | Source | P0 | skill-run candidates | LLM/run treated as source | Source records with provenance | high | Investigation | provenance |
| G4 | Evidence | P0 | supervisor as signals | Fake evidence authority | Evidence linked to Source | high | Verdict | citation required |
| G5 | BusinessVerdict | P0 | local deterministic | Decisions not real SoT | Verdict + readiness + human review | medium | Verdict/Strategy gates | eligibility |
| G6 | MarketingStrategy | P0 | local strategy | GTM not durable | Strategy domain ≠ MarketingPlan | medium | Strategy | no dual-write to plan |
| G7 | Safe MarketingPlan draft handoff API | P1 | read-only preview | Cannot materialize specialist spine from ImplPlan | Explicit draft create from mapped fields | low–med | Impl handoff | draft-only invariants |
| G8 | ImplementationPlan domain | P1–P2 | local A6 | Ops vs PM split fragile | Optional dedicated domain (I6 Option C long-term) | medium | Impl | versioning |
| G9 | ApprovalRequest abstraction | P1 | scattered approve endpoints | Collapsed “approved” UX risk | Category-discriminated approval resources | medium | all gates | boundary tests |
| G10 | Verified Execution (V2.2) | P2 | MarketingPlan execution-runs + flags | Unsafe automation | Intent/ready/approve/verify/evidence | high | post-Alpha | flags |
| G11 | Outcome + Knowledge Candidate | P2–P3 | campaign learnings partial | Weak institutional memory | Outcome → evidence → knowledge | med–high | later | AI.60x suite |
| G12 | Project timeline / workforce overlay | P3 | CC timeline / workforce read-model | Chrome only | keep read-only overlays | low | Workspace | freeze |

## Recommended sequencing (owner preference)

**Commercial MVP first:** G1→G6 (P0), then G7/G9 (P1), **then** G10 Verified Execution.
