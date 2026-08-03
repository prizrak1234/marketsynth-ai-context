# Commercial MVP P1 — Architecture Review

**Mode:** Audit-first · minimal patches only  
**Date:** 2026-07-14  
**Branch:** `master` (local only)

## 1. Baseline and checkpoint

| Item | Value |
|------|-------|
| Checkpoint I7 | `1341c29` |
| Checkpoint P0.1 | `9c6b408` |
| Checkpoint P0.2–P0.5 | `4c3de96` |
| Checkpoint P0.6 | `8dbcc03` — `chore: checkpoint commercial MVP phase P0.6` |
| Code migration head | `20260614_0034` |
| Local Postgres `alembic current` | **drift** — missing `20260608_0033` (documented; not repaired in this review) |
| Pytest DB | Fresh SQLite via `create_all` — green |

No remote Git operations.

## 2. Domain inventory (summary)

| Domain | ORM | API | FE adapter | Tests |
|--------|-----|-----|------------|-------|
| Project | existing | `/projects` | project-sync | I1–I7 |
| ProjectBrief | `project_briefs` | `/projects/{id}/briefs` | project-brief-* | P0.1 |
| Investigation | `investigations` | `/projects/{id}/investigations` | investigation-* | P0.2 |
| Source + links | `sources`, `investigation_source_links` | `/projects/{id}/sources` | source-* | P0.3 |
| Evidence + links | `investigation_evidence`, `evidence_source_links` | nested under investigation | evidence-* | P0.4 |
| BusinessVerdict + snapshot | `business_verdicts`, snapshots, links | `/business-verdicts` + inv create | business-verdict-* | P0.5 |
| MarketingStrategy | `marketing_strategies` | `/marketing-strategies` | marketing-strategy-* | P0.6 |

Full matrices: sibling `commercial_mvp_p1_*.md` docs.

## 3. Canonical lineage

See [commercial_mvp_p1_lineage_model.md](commercial_mvp_p1_lineage_model.md).

**Enforced answers:**

| Question | Answer | Enforcement |
|----------|--------|-------------|
| Investigation only on submitted Brief? | **Yes** | `brief_not_submitted` |
| Evidence only Sources in same Project? | **Yes** | `cross_project_source` |
| Verdict snapshots exact Evidence versions? | **Yes** | snapshot links + `stale_version` |
| Strategy only approved eligible Verdict? | **Yes** | `verdict_not_approved` / `verdict_type_not_eligible` |
| Later Evidence mutates approved Verdict basis? | **No** | pinned snapshot hash/versions; accepted Evidence content immutable |
| Later Verdict mutates approved Strategy? | **No** | Strategy pins verdict id+version; approved Strategy immutable |

## 4–10. Matrices

- SoT: [commercial_mvp_p1_source_of_truth_matrix.md](commercial_mvp_p1_source_of_truth_matrix.md)
- Versioning: [commercial_mvp_p1_versioning_matrix.md](commercial_mvp_p1_versioning_matrix.md)
- Lifecycle: [commercial_mvp_p1_lifecycle_matrix.md](commercial_mvp_p1_lifecycle_matrix.md)
- API: [commercial_mvp_p1_api_consistency_audit.md](commercial_mvp_p1_api_consistency_audit.md)
- Migrations: [commercial_mvp_p1_migration_audit.md](commercial_mvp_p1_migration_audit.md)
- Coverage: [commercial_mvp_p1_test_coverage_matrix.md](commercial_mvp_p1_test_coverage_matrix.md)

## 11. Semantic invariants — held

Project ≠ Brief · Investigation ≠ AgentRun · Source ≠ Evidence · Evidence ≠ Finding · Evidence ≠ Verdict · Readiness ≠ Verdict · Verdict ≠ Verdict Approval ≠ Execution Approval · Strategy ≠ MarketingPlan · Strategy approve ≠ Plan approve ≠ execution approve · No CoT · No LLM→Evidence · No supervisor→Evidence.

## 12–14. Frontend / Alpha freeze

Backend mode for verdicts/strategies does not silent-mock. Hybrid labels local preview separately. Product Alpha A1–A6 UX freeze intact (routes, branding, vocabulary). A7 remains paused.

## 15. Migration audit

Linear `20260614_0029` → `0034`. Static chain test added. Local Postgres drift out of scope.

## 16–18. Tests / E2E / errors

Added `tests/test_commercial_mvp_p1_lineage_e2e.py`: full chain, immutability, draft-brief gate, cross-project Source, no MarketingPlan/Campaign/AgentRun/LLM, alembic chain.

## 19–20. Security / performance

No secrets in domain JSON; URLs treated as data (no fetch on Source register). N+1 / large history = P1 observation only (not patched).

## 21–26. Decisions

- Gaps: [commercial_mvp_p1_gap_register.md](commercial_mvp_p1_gap_register.md)
- ImplementationPlan: **Option A** — own durable domain (P1.1) — [decision](commercial_mvp_p1_implementation_plan_decision.md)
- MarketingPlan handoff: criteria mostly **unmet/partial** — [criteria](commercial_mvp_p1_marketingplan_handoff_criteria.md)
- V2.2: still **blocked/partial** — [review](commercial_mvp_p1_v2_2_entry_review.md)
- AI.592: paused, follows V2.2 — [review](commercial_mvp_p1_ai_592_review.md)
- A7: redesign later over Impl→Plan→V2.2 — [decision](commercial_mvp_p1_a7_decision.md)

## 27. Minimal patches applied

| Patch | Type |
|-------|------|
| P0.6 checkpoint commit `8dbcc03` | baseline |
| `tests/test_commercial_mvp_p1_lineage_e2e.py` | critical invariant + E2E |
| `web/.../marketing-strategy-p0-6.selfcheck.ts` | adapter selfcheck |
| P1 architecture docs + DEVELOPMENT.md | freeze |

**No new product domain.** No MarketingPlan/Campaign/Agent Run/LLM/execution/provider actions.

## 28. Recommended next phase

**Commercial MVP P1.1 — durable ImplementationPlan Domain**, then P1.2 controlled MarketingPlan draft handoff, then V2.2 Verified Execution (owner-gated).
