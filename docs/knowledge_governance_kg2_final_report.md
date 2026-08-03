# KG.2 — Operational Knowledge Governance final report

**Date:** 2026-07-19  
**Phase:** Knowledge Governance Persistence + Operator + Runtime Enforcement  
**Non-goals honored:** no VectorDB, no Graph DB, no mass `/docs` index, no auto-publish, no parallel Runtime, no remote Git.

## Status matrix

| Track | Status | Notes |
|-------|--------|-------|
| Architecture (KG.1) | **complete** | Contracts, ADR/Volume/RFC, policy helpers |
| Persistence | **complete** | `kg_*` tables + `knowledge_snapshots.governance_meta`; migration `20260719_0050`; immutable versions |
| Operator | **complete** | Service + `/knowledge-governance/*` + UI tabs on `/workspace/knowledge/manage` |
| Runtime enforcement | **complete** | Industrial domains → governed Snapshot only; block `insufficient_governed_knowledge`; citation gate on governed drafts |
| Benchmark | **complete (pack + runner)** | `drilling_operations` ≥30 cases; runner without external LLM |
| Owner acceptance | **pending** | Owner must run acceptance scenario on real DB + smoke publish/expire |

## Acceptance scenario (owner)

1. Migrate: `uv run alembic upgrade head`
2. Create candidate via API or Operator UI
3. Assign owner/reviewer → validate → publish
4. Submit `content.telegram_post` about буровая безопасность
5. Confirm UserRequest has `knowledge_snapshot_id` with `governance_meta`
6. Expire version (`next_review_at` in the past) → re-run → blocked
7. Supersede → validate → publish new version → execution passes

## Regression

```bash
uv run pytest tests/test_architecture_knowledge_governance.py tests/test_phase_kg2_knowledge_governance_ops.py -q
```
