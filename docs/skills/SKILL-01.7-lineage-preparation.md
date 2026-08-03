# SKILL-01.7 — Lineage Preparation

**Phase:** SKILL-01.7  
**Status:** Complete (2026-07-23)  
**Depends on:** SKILL-01.2–01.6 (validator, registry, quarantine, connector gateway, unified audit)

---

## Purpose

Prepare **canonical immutable lineage contracts** and **pure lineage-construction helpers** that connect:

```
Skill Package Version
  → Package Validation
  → Quarantine Import (optional)
  → Registry Projection / Snapshot
  → Connector Request / Policy / Result / Evidence
  → Unified Audit Report
  → Existing Evidence references
```

This phase defines lineage **semantics only**. It does not persist graphs, migrate databases, modify live runtime behavior, execute Skills, or invoke real Connectors.

---

## Module location decision

| Layer | Location | Role |
|-------|----------|------|
| Lineage preparation | `app/lineage/` | **New** — contracts, builders, validators, mappings |
| Unified audit | `app/audit/` | **Unchanged** — source reports for audit lineage nodes |
| Existing Evidence | `app/schemas/contracts.py` (`KnowledgeEvidenceRef`) | **Authoritative** — mapping boundary only |
| Tool execution audit | `app/tools/audit_contracts.py` | **Preserved** — unrelated scope |
| CWF.1 snapshot/evidence | existing contracts | **Unchanged** — no migration |

No competing lineage package existed in Python. Commercial MVP lineage docs under `docs/commercial_mvp_p1_*` are product notes, not a governing runtime layer. `app/lineage/` is a **preparation boundary** compatible with existing Evidence — not a replacement.

---

## Module layout

```
app/lineage/
├── __init__.py
├── contracts.py       # LineageGraph, nodes, edges, descriptors, findings
├── identity.py        # Deterministic node ID rules
├── builders.py        # Pure graph builders + combine_lineage_graphs()
├── validators.py      # Continuity validation + tenant filter
├── serialization.py   # Canonical JSON + deterministic graph hash
├── mappings.py        # Evidence-compatible reference mapping
├── fixtures.py        # Synthetic test fixtures
└── errors.py          # Safe domain errors
```

---

## Lineage node model

Finite `LineageNodeType` values:

`skill_package`, `skill_version`, `package_validation`, `quarantine_import`, `registry_projection`, `registry_snapshot`, `connector_request`, `connector_policy_decision`, `connector_result`, `connector_evidence`, `unified_audit_report`, `existing_evidence`, `approval_reference`, `project_snapshot`, `execution_record`.

`LineageNodeReference` holds optional identity fields (`node_id`, `tenant_id`, `project_id`, `skill_id`, `skill_version`, `connector_id`, `package_hash`, `report_hash`, `evidence_id`, `snapshot_id`, `snapshot_hash`, …). Fields are omitted when not applicable — **no fabricated IDs**.

---

## Edge model

Finite `LineageEdgeType` values:

`derived_from`, `validated_by`, `imported_as`, `projected_to`, `included_in`, `requested_by`, `authorized_by`, `denied_by`, `executed_as`, `produced`, `evidenced_by`, `audited_by`, `supersedes`, `version_of`, `belongs_to`, `references`, `resolved_by`.

Causal meaning is explicit per edge type — generic string labels are rejected.

---

## Canonical chains

### A. Platform-native Skill package

```
skill_package → package_validation → registry_projection → unified_audit_report
```

### B. External candidate

```
external source metadata → quarantine_import → package_validation → registry_projection → unified_audit_report
```

### C. Skill-backed connector request (future runtime)

```
skill_version → connector_request → connector_policy_decision → connector_result → connector_evidence → unified_audit_report
```

### D. Existing Evidence linkage

```
unified_audit_report → existing_evidence
```

### E. Approval linkage

```
connector_request → approval_reference → connector_result
```

**Important:** `approval_reference` is a **reference only**. Audit readiness and approval references do **not** imply lifecycle approval or execution authorization.

---

## Identity rules

Deterministic node IDs (examples):

| Node | Pattern |
|------|---------|
| Skill package | `skill:{skill_id}:{skill_version}:{package_hash}` |
| Package validation | `validation:{validator_version}:{package_hash}:{report_hash}` |
| Quarantine import | `quarantine:{import_id}:{materialized_hash}` |
| Registry projection | `registry:{skill_id}:{skill_version}:{package_hash}` |
| Registry snapshot | `registry-snapshot:{snapshot_id}` |
| Connector request | `connector-request:{request_id}` |
| Connector result | `connector-result:{request_id}:{result_status}:{output_hash}` |
| Audit report | `audit:{report_hash}` |
| Evidence | `evidence:{evidence_id}` |

No secrets or mutable display names in IDs.

---

## Builders

Pure builders (no source mutation):

- `build_package_validation_lineage(...)`
- `build_quarantine_lineage(...)`
- `build_registry_projection_lineage(...)`
- `build_connector_request_lineage(...)`
- `build_connector_result_lineage(...)`
- `build_audit_lineage(...)`
- `combine_lineage_graphs(...)`

Builders preserve source hashes, tenant/project context, skill identity, and deterministic ordering. Cross-tenant merges and identity conflicts are rejected.

---

## Continuity validation

`validate_lineage_continuity(graph)` checks edge/node integrity, hash consistency, tenant boundaries, connector request/result/evidence linkage, audit source presence, quarantine effective status, archived/deprecated resolvability, acyclic required subgraphs, and lifecycle semantics (audit readiness ≠ approval).

Findings use finite codes (`missing_parent`, `hash_mismatch`, `tenant_mismatch`, `evidence_missing`, …) with severities `info` / `warning` / `error` / `critical`. Cross-tenant mismatch is **critical/blocking**.

`filter_graph_for_tenant(graph, tenant_id)` hides tenant-private nodes from other tenants without leaking existence counts in errors.

---

## Execution descriptors (contracts only)

### SkillExecutionLineageDescriptor

For future runtime attribution: `execution_id`, `skill_id`, `skill_version`, `package_hash`, registry snapshot id/hash, tenant/project, input/output hashes, parent evidence, approval reference, connector request ids, audit report ids, timestamps, status.

### ConnectorExecutionLineageDescriptor

`request_id`, connector/tool identity, skill attribution, credential **binding reference** (never credential material), hashes, result status, evidence id, parent lineage ids.

### AuditLineageDescriptor

`audit_id`, `report_hash`, target/source report ids, evidence ids, generation metadata, `owner_decision_required`. Human review is **not** marked complete without an explicit human decision reference.

---

## Evidence mapping

Pure helpers in `app/lineage/mappings.py`:

- Connector evidence descriptor → `EvidenceLineageReference` → `KnowledgeEvidenceRef`
- Audit evidence reference → lineage reference
- Package validation report hash → Evidence-compatible source reference
- Quarantine provenance → Evidence-compatible provenance reference

**No new Evidence persistence layer.**

### Unresolved compatibility gaps (SKILL-01.8+)

- `KnowledgeEvidenceRef.source_uri` expects durable URIs; connector descriptors provide hashes only — locator fallback used.
- Quarantine provenance has no first-class KG Evidence id yet.
- Package validation report hash is a locator, not a persisted Evidence row.
- CWF.1 snapshot/evidence lineage integration deferred to SKILL-02+ runtime wiring.

---

## Snapshot lineage

- `snapshot_id` and `snapshot_hash` are distinct fields.
- Projected Skill versions link to the snapshot containing them via `included_in` edges.
- Execution descriptors may reference exact registry snapshot id/hash.
- Later snapshots do not rewrite historical execution lineage.
- Archived/deprecated versions remain addressable by exact identity/hash.

---

## Serialization and graph hash

- Canonical UTF-8 JSON with stable node/edge ordering.
- `compute_graph_hash()` — SHA-256 over semantic graph body.
- Excludes: `graph_hash`, node `created_at`, source reference timestamps.
- Audit source references use `report_hash` as `source_id` (not volatile `audit_id`).
- `sanitize_for_serialization()` redacts absolute paths and secret-like fragments.

---

## Graph merge rules

`combine_lineage_graphs()`:

- Preserves identical nodes and merges identical edges.
- Rejects same node ID with different semantic payload (`metadata_hash` conflict).
- Rejects cross-tenant graphs.
- Does not auto-resolve conflicts.

---

## Limitations

- No persistence, API, UI, or live runtime wiring.
- No Skill execution, dynamic loading, lifecycle mutation, or real Connector calls.
- No MCP, provider SDKs, network calls, or background jobs.
- CWF.1 / CWF.1a unchanged.

---

## Non-goals

Lineage persistence, graph database, SQL tables, migrations, approval workflow implementation, billing, external network, CWF.1 migration.

---

## Freeze-audit readiness

SKILL-01.7 completes the **semantic chain** from package through audit to Evidence references. SKILL-01.8 Foundation Freeze Audit verifies the full contour end-to-end.

**Regression:** `uv run pytest tests/test_skill_01_7_lineage_preparation.py -q` (49 cases).

**Full Foundation regression:**

```bash
uv run pytest \
  tests/test_skill_01_0_market_validation_package.py \
  tests/test_skill_01_0_freeze_audit.py \
  tests/test_skill_01_1_contracts.py \
  tests/test_skill_01_2_package_validator.py \
  tests/test_skill_01_3_registry_read_models.py \
  tests/test_skill_01_4_quarantine_import_adapter.py \
  tests/test_skill_01_5_connector_gateway_interfaces.py \
  tests/test_skill_01_6_unified_audit_report.py \
  tests/test_skill_01_7_lineage_preparation.py \
  -q
```
