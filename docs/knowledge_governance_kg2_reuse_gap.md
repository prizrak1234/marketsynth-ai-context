# KG.2 — Reuse / Gap Matrix

| Asset | Decision | Notes |
|-------|----------|-------|
| `knowledge_items` (H2.3) | REUSE as foundation body / catalog link | New governance tables do not duplicate body as competing SoT; versions hold content for governance lineage |
| `knowledge_snapshots` | REUSE + EXTEND refs for governance version/chunk ids | Execution SoT remains snapshots |
| KG.1 contracts | EXTEND | Persist via new tables mapping to contracts |
| `knowledge_foundation/*` | EXTEND admission + retrieval filter + snapshot | No second Runtime |
| Operator UI `/workspace/knowledge/manage` | EXTEND | Add governance sections |
| `/knowledge-foundation/*` APIs | REUSE | Add `/knowledge-governance/*` for operator lifecycle |
| Tenant | REUSE `owner_id` as tenant boundary | Field named `owner_id` / `tenant_owner_id` in governance tables |
| VectorDB / Graph / mass index | OUT OF SCOPE | Explicit non-goal |

Alembic: `20260719_0049` → `20260719_0050_knowledge_governance_ops`.
