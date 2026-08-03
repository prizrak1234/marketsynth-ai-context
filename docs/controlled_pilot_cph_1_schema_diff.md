# CPH.1 — Schema diff report

Compare: local data DB `botfazer` vs disposable head `botfazer_cph1` (`20260614_0036`) vs SQLAlchemy commercial ORM expectations.

## Summary

| Aspect | `botfazer` (data) | `botfazer_cph1` (head) |
|--------|-------------------|-------------------------|
| Alembic | `20260608_0033` (orphan) | `20260614_0036` |
| Classification | `MISSING_FROM_TREE` | `CURRENT` |
| Commercial MVP chain tables | **Missing** | **Present** |
| AI.60x / workforce extras | Present | Absent (clean commercial bootstrap) |
| Suitable for Commercial MVP / pilot | **No** | **Yes** |

## Commercial MVP tables

| Table | Expected at head | `botfazer` | `botfazer_cph1` |
|-------|------------------|------------|-----------------|
| projects | yes | yes (3 rows) | yes |
| project_briefs | yes | **no** | yes |
| investigations | yes | **no** | yes |
| sources | yes | **no** | yes |
| investigation_source_links | yes | **no** | yes |
| investigation_evidence | yes | **no** | yes |
| evidence_source_links | yes | **no** | yes |
| business_verdicts | yes | **no** | yes |
| business_verdict_evidence_snapshots | yes | **no** | yes |
| business_verdict_evidence_links | yes | **no** | yes |
| marketing_strategies | yes | **no** | yes |
| implementation_plans | yes | **no** | yes |
| implementation_marketing_plan_handoffs | yes | **no** | yes |
| marketing_plans | yes | yes (1) | yes |

## Extra tables on `botfazer` (not on clean pilot)

Examples: `campaign_learnings`, `project_insights`, `project_decisions`, `project_goals`, `decision_outcome_evidence`, `execution_approvals`, `execution_approval_audit_events`, `workflow_execution_runs`, `campaign_client_report_snapshots`, `campaign_deliverables_pack_snapshots`, `campaign_intelligence_report_snapshots`.

**Diff class:** material divergence — not a behind-by-N commercial upgrade; parallel / WIP schema.

## ORM parity (head disposable)

- Migrated schema accepts ORM `User` + `Project` + `ProjectBrief` create without `SQLModel.metadata.create_all`.
- SQLite pytest `create_all` remains the default unit-test path; **not** proof of PostgreSQL migration safety.

## Indexes / FKs

On `botfazer_cph1`, commercial tables expose multiple FK constraints (≥5 counted in smoke). Full column-level dump omitted (noise); use:

```bash
uv run python scripts/cph1_db_tools.py schema-parity
uv run python scripts/cph1_schema_probe.py   # if present
```

## Conclusion

Schema mismatch is **material**. Reconciliation cannot be a stamp. Prefer new pilot DB; data DB rebuild only with owner approval.
