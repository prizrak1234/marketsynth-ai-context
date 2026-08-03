# SKILL-01 — Foundation Freeze Manifest

**Status:** Frozen (CONDITIONALLY READY — owner sign-off pending)  
**Date:** 2026-07-23

---

## Frozen modules

| Module | Phase | Role |
|--------|-------|------|
| `packages/skills/ms.skill.market_validation/` | 01.0 | Driver skeleton package |
| `app/schemas/contracts.py` (SKILL-01.1 section) | 01.1 | Domain contracts |
| `app/skills/` | 01.2–01.4 | Validator, registry, quarantine |
| `app/connectors/` | 01.5 | Connector gateway interfaces |
| `app/audit/` | 01.6 | Unified audit report |
| `app/lineage/` | 01.7 | Lineage preparation |
| `app/foundation/` | 01.8 | Freeze contour fixture |

**Explicitly not frozen as runtime:** `app/mcp/` (legacy CMVP layer, unchanged).

---

## Frozen contracts

- `SkillManifest`, `SkillPackageDescriptor`, lifecycle transitions
- `SkillPackageValidationReport`, validator enums
- `SkillRegistryVersionRecord`, `SkillRegistrySnapshot`, eligibility views
- `QuarantineImportResult`, provenance records
- `ConnectorExecutionRequest`, `ConnectorPolicyDecision`, tool definitions
- `UnifiedAuditReport`, `AuditFinding`
- `LineageGraph`, `LineageNodeReference`, execution descriptors

---

## Frozen package

| Field | Value |
|-------|-------|
| Package | `ms.skill.market_validation` |
| Version | `0.1.0` |
| Status | `candidate` |
| Package hash | `6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133` |
| `allowed_tools` | `[]` |
| Network | deny-by-default |
| Scripts | disabled |

---

## Schema versions

| Layer | Version |
|-------|---------|
| Validator | `0.1.0` |
| Registry | `0.1.0` |
| Audit | `0.1.0` |
| Lineage | `0.1.0` |

---

## Integrated contour hashes (in-process, `FIXED_TIME`)

Built via `build_foundation_freeze_contour()` — stable within process:

| Artifact | Example hash (2026-07-23 run) |
|----------|-------------------------------|
| Package | `6c53b5b9…4b8133` |
| Registry snapshot | process-stable |
| Composite audit report | process-stable |
| Lineage graph | process-stable |

Recompute: `uv run python -c "from app.foundation.freeze_fixture import build_foundation_freeze_contour; print(build_foundation_freeze_contour())"`

---

## Test counts

| Suite | Count |
|-------|-------|
| SKILL-01.0 | 2 files |
| SKILL-01.1–01.7 | 7 files |
| SKILL-01.8 invariants | 61 tests |
| **Total SKILL-01** | **361 passed**, 3 skipped |

---

## Accepted RFC versions

| RFC | Status |
|-----|--------|
| ARCHITECTURAL-INVARIANTS | Accepted |
| RFC-SKILL-001 | Accepted |
| RFC-SKILL-002 | Accepted |
| RFC-SKILL-003 | Accepted |
| RFC-CONN-001 | Accepted |
| RFC-SKILL-004 | **Draft** (does not block Foundation) |

---

## Known limitations

- No persistence, API, UI, runtime loader
- No real external Connector execution
- Evidence mapping uses locator fallback
- Quarantine import generates volatile `import_id` (cached in freeze fixture)
- CWF.1 / CWF.1a parallel tracks exist outside Foundation boundary

---

## Explicit non-goals (frozen out)

Skill execution engine, Connector runtime, MCP installation, lifecycle activation, approval workflow implementation, marketplace, Discovery Engine, Draft Generator, CWF.1 migration, tenant upload UI.
