# Commercial MVP P1 — Alembic Migration Audit (0029–0034)

## Chain (append-only, linear)

| Revision | File | down_revision | Tables |
|----------|------|---------------|--------|
| `20260614_0029` | `…_project_briefs_…` | `20260603_0028` | `project_briefs` |
| `20260614_0030` | `…_investigations_…` | `20260614_0029` | `investigations` |
| `20260614_0031` | `…_sources_…` | `20260614_0030` | `sources`, `investigation_source_links` |
| `20260614_0032` | `…_evidence_…` | `20260614_0031` | `investigation_evidence`, `evidence_source_links` |
| `20260614_0033` | `…_business_verdict_…` | `20260614_0032` | verdicts, snapshots, links |
| `20260614_0034` | `…_marketing_strategy_…` | `20260614_0033` | `marketing_strategies` |

## Checks

| Check | Result |
|-------|--------|
| Duplicate revision IDs | None in 0029–0034 |
| Historical edits | None in this review |
| Destructive ops | Create-table oriented; downgrades drop in reverse order per file |
| ORM parity | Tables match P0 models |
| Code head | `20260614_0034` |
| Local Postgres | **Drift** — `alembic current` fails on missing `20260608_0033` (unrelated; not repaired) |
| Fresh SQLite pytest | `create_all` — OK |
| Static chain test | `test_alembic_commercial_mvp_revision_chain` |

## Policy

Do not use drifted local PostgreSQL as sole validation. Fresh isolated upgrade/downgrade against Postgres remains a P2 ops task when DB tooling available.
