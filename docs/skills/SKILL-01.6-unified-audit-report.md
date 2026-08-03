# SKILL-01.6 — Unified Audit Report Schema

**Phase:** SKILL-01.6  
**Status:** Complete (2026-07-23)  
**Depends on:** SKILL-01.2–01.5 (validator, registry, quarantine, connector gateway)

---

## Purpose

Provide **one canonical, immutable, deterministic audit-report contract** that normalizes findings from:

- Skill package validation (SKILL-01.2)
- Quarantine import (SKILL-01.4)
- Registry projection / conflicts (SKILL-01.3)
- Connector Gateway policy evaluation (SKILL-01.5)

```
Package Validator ──┐
Quarantine Import ──┼→ Source Adapters → UnifiedAuditReport → Aggregation
Registry Conflicts ─┤
Connector Policy ───┘
```

**Not in this phase:** persistence, API, UI, lifecycle mutation, automatic approve/reject/activate.

---

## Architecture boundary

| Layer | Location | Role |
|-------|----------|------|
| Unified audit | `app/audit/` | **New** — canonical report + adapters + aggregation |
| Tool execution audit | `app/tools/audit_contracts.py` | **Preserved** — unrelated scope |
| Source systems | `app/skills/`, `app/connectors/` | **Unchanged** — adapters read-only |

Module decision: `app/tools/audit_contracts.py` covers tool execution logs only; no competing governing audit layer existed for Skills/Connectors.

---

## Module layout

```
app/audit/
├── __init__.py
├── contracts.py       # UnifiedAuditReport, AuditFinding, targets, provenance
├── classifications.py # Centralized severity + blocking rules
├── adapters.py        # Pure adapters from source result types
├── aggregator.py      # aggregate_audit_reports()
├── readiness.py       # Decision readiness derivation (diagnostic only)
├── serialization.py   # Canonical JSON + deterministic report hash
├── redaction.py       # Secret/path redaction helpers
├── fixtures.py        # Synthetic test fixtures
└── errors.py          # Safe domain errors
```

---

## Audit target model

Finite `AuditTargetType` values: `skill_package`, `skill_import`, `skill_registry_record`, `skill_registry_snapshot`, `connector`, `connector_tool`, `connector_request`, `connector_policy_decision`.

`AuditTargetReference` holds optional identity fields (`target_id`, `target_version`, `package_hash`, `tenant_id`, `import_id`, `connector_id`, `tool_id`, …). Fields are omitted when not applicable — no fabricated identifiers.

---

## Finding contract

`AuditFinding` preserves source provenance:

| Field | Purpose |
|-------|---------|
| `source_system` | Origin adapter (validator, quarantine, registry, connector) |
| `source_code` | Original structured code (never lost in normalization) |
| `category` | Finite enum (structure, schema, security, conflict, connector_policy, …) |
| `severity` | info / warning / error / critical |
| `blocking` | Blocks audit progression |
| `execution_blocking` | Blocks execution layer (distinct from audit blocking) |
| `source_payload_hash` | Deterministic hash of source fragment |

**Rule:** approval-required is `execution_blocking=true`, `blocking=false` — not a security defect.

---

## Source adapters

| Adapter | Source type |
|---------|-------------|
| `adapt_package_validation_report` | `SkillPackageValidationReport` |
| `adapt_quarantine_import_result` | `QuarantineImportResult` |
| `adapt_registry_conflict` | `SkillRegistryConflict` |
| `adapt_registry_projection_result` | `SkillRegistryProjectionResult` |
| `adapt_connector_policy_decision` | `ConnectorPolicyDecision` |
| `adapt_connector_evidence_descriptor` | `ConnectorEvidenceDescriptor` |
| `adapt_connector_execution_result_schema_support` | `ConnectorExecutionResult` (schema only) |

Each adapter: preserves `source_code`, maps severity via centralized table, redacts secrets/paths, does not mutate source objects.

---

## Severity normalization

Centralized in `app/audit/classifications.py`:

| Source | Mapping |
|--------|---------|
| Package validator | info→info, warning→warning, error→error; security codes → critical |
| Quarantine static | malicious codes (symlink, secret) → critical |
| Registry conflict | uses conflict severity field |
| Connector policy | deny/security → error/critical; approval → info; defer → warning |

Unknown severity does not downgrade to allow.

---

## Blocking rules

Mandatory blocking codes include: secrets, path traversal, symlink escape, invalid manifest/schema, identity/hash conflicts, cross-tenant exposure, connector policy deny, tool not allowed, billing without budget.

Approval-required alone is **not** audit-blocking.

---

## Decision readiness

Diagnostic status only — **does not approve, activate, or mutate lifecycle**.

| Value | Meaning |
|-------|---------|
| `not_ready` | Candidate / incomplete |
| `ready_for_audit` | Valid package, no blockers |
| `ready_for_human_review` | Successful quarantine import |
| `ready_for_approval_review` | Connector requires approval |
| `blocked` | Blocking findings or deny/conflict |
| `insufficient_information` | Defer / incomplete inputs |

There is **no** `ready_for_activation`. Readiness never triggers lifecycle transitions.

---

## Aggregation

`aggregate_audit_reports(target, source_reports) -> UnifiedAuditReport`:

- Deterministic finding order
- Deduplication by `(source_system, source_code, location, target_id, source_payload_hash)`
- Preserves all source references
- Derives overall severity (highest unresolved wins)
- Computes composite `report_hash`
- No source or lifecycle mutation

---

## Report hashing

SHA-256 over canonical JSON. Excluded from semantic hash:

- `audit_id`
- `generated_at`
- finding `created_at`
- source reference `generated_at`

Included: findings, severities, blockers, target identity, source codes, evidence references.

---

## Provenance

`AuditProvenance` records: `generated_by`, `generation_mode` (automated_static / automated_policy / composite), `source_systems`, `correlation_id`, `human_review_required`, `owner_decision_required`.

Automated reports are never marked human-reviewed.

---

## Evidence mapping

`AuditEvidenceReference` maps `ConnectorEvidenceDescriptor` into audit reports:

- `evidence_id`, input/output/provider hashes, lineage parent IDs

No parallel Evidence database model. Future SKILL-01.7 will wire lineage to existing Evidence contracts.

---

## Redaction

Canonical reports must not contain secrets, tokens, API keys, absolute paths, or cross-tenant hidden identifiers.

`redact_payload`, `redact_text`, `sanitize_location` redact values while preserving finding existence.

---

## Limitations

- No audit persistence or repositories
- No API endpoints or UI
- No owner approval workflow
- No lifecycle transitions
- No real connector execution

---

## Non-goals

- Automated legal/security approval
- Registry DB persistence
- CWF.1 / CWF.1a changes
- RFC-SKILL-004 changes

---

## Future SKILL-01.7 lineage integration

SKILL-01.7 will chain:

```
Skill package version
  → Validation report
  → Quarantine import
  → Registry projection
  → Connector request/result
  → Audit report
  → Existing Evidence lineage
```

Without migrations or live runtime changes.

---

## Verification

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
  -q

uv run ruff check app/audit tests/test_skill_01_6_unified_audit_report.py
```

**Result (2026-07-23):** 251 passed, 3 skipped; ruff clean on audit modules.

---

## Related documents

- [SKILL-01.2 — Manifest Package Validator](SKILL-01.2-manifest-package-validator.md)
- [SKILL-01.3 — Registry Read Models](SKILL-01.3-registry-read-models.md)
- [SKILL-01.4 — Quarantine Import Adapter](SKILL-01.4-quarantine-import-adapter.md)
- [SKILL-01.5 — Connector Gateway Interfaces](SKILL-01.5-connector-gateway-interfaces.md)
- [SKILL-01 Foundation Plan](../rfc/SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)
