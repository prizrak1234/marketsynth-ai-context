# Commercial MVP P1 — Test Coverage Matrix

| Capability | Unit/Domain | Service/API | Integration E2E | FE adapter selfcheck | Missing / next |
|------------|-------------|-------------|-----------------|----------------------|----------------|
| Brief versioning | P0.1 | P0.1 | P1 e2e | project-brief.selfcheck | — |
| Investigation linkage | P0.2 | P0.2 | P1 e2e (draft blocked) | investigation-p0-2 | — |
| Source immutability | P0.3 | P0.3 | partial | source-p0-3 | deeper supersede cycle |
| Source reuse | P0.3 | P0.3 | — | — | optional |
| Evidence traceability | P0.4 | P0.4 | P1 e2e | evidence-p0-4 | — |
| Evidence review | P0.4 | P0.4 | P1 e2e | evidence-p0-4 | — |
| Evidence snapshot | P0.5 | P0.5 | P1 e2e | verdict.selfcheck | — |
| Verdict rules | P0.5 | P0.5 | P1 e2e | verdict.selfcheck | — |
| Verdict approval boundary | P0.5 | P0.5 | P1 e2e + firewall | — | — |
| Strategy eligibility | P0.6 | P0.6 | P1 e2e | marketing-strategy-p0-6 | — |
| Strategy approval boundary | P0.6 | P0.6 | P1 e2e | marketing-strategy-p0-6 | — |
| Cross-owner isolation | partial (auth fixtures) | existing require_owner | — | — | dedicated dual-user P1+ |
| Cross-project isolation | P0.5/P0.6 | P0.5 + P1 source test | P1 | — | verdict/strategy cross-id extras optional |
| No downstream side effects | P0.2–P0.6 flags | P0.6 + P1 | P1 count tables | strategy-plan.selfcheck | — |
| No mock fallback (backend) | — | — | — | source + strategy origin | strategy-adapter comment stale (docs only) |
| Migration chain | static P1 | — | — | — | live Postgres upgrade when available |

## Commands

```bash
uv run pytest tests/test_commercial_mvp_p0_1_project_brief.py \
  tests/test_commercial_mvp_p0_2_investigation.py \
  tests/test_commercial_mvp_p0_3_source.py \
  tests/test_commercial_mvp_p0_4_evidence.py \
  tests/test_commercial_mvp_p0_5_business_verdict.py \
  tests/test_commercial_mvp_p0_6_marketing_strategy.py \
  tests/test_commercial_mvp_p1_lineage_e2e.py -q
```
