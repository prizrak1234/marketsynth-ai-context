# SKILL-01.3 — Registry Read Models

**Phase:** SKILL-01.3  
**Status:** Complete (2026-07-23)  
**Depends on:** SKILL-01.1 (contracts), SKILL-01.2 (validator)

---

## Purpose

Read-only domain models and deterministic query behavior for the Marketsynth Skill Registry. Consumes validated package metadata and produces immutable registry snapshots.

**Registry record ≠ approval. Validation report ≠ active runtime binding.**

---

## Architecture

```
SkillPackageValidationReport
  → registry_projection.project_validation_report()
  → SkillRegistryVersionRecord
  → build_registry_snapshot()
  → SkillRegistrySnapshot
  → registry_queries (pure reads)
```

| Module | Role |
|--------|------|
| `registry_contracts.py` | Immutable read models, serialization, snapshot hash |
| `registry_projection.py` | Validation → version record; aggregation; conflicts |
| `registry_queries.py` | Pure queries, tenant visibility, eligibility derivation |
| `registry_errors.py` | Safe not-found errors (no cross-tenant leakage) |

No persistence, no mutation methods (`add`, `approve`, `activate`, `save`, `delete`).

---

## Read-model boundaries

- Represents **declared and validated state** only
- Does not promote lifecycle status
- Does not execute Skills
- Does not install packages

---

## Version semantics

| Concept | Meaning |
|---------|---------|
| `skill_id` | Logical Skill identity |
| `version` | Immutable package semver |
| `package_hash` | Exact content identity |
| `latest_known_version` | Highest validated non-rejected semver in snapshot |

No automatic version promotion. No numeric-highest → active inference.

---

## Validation projection

Outcomes: `projected`, `rejected`, `conflict`, `incomplete`.

- Invalid reports → `rejected` (no eligible record)
- Valid candidate → `projected`, status unchanged
- Package hash and normalized manifest preserved

---

## Snapshot model

`SkillRegistrySnapshot` includes deterministic indexes:

- `capability_index`
- `tenant_scope_index`
- `lifecycle_status_index`

Snapshot hash: SHA-256 over canonical JSON (distinct from package hash).

---

## Tenant visibility

| Case | Normal view |
|------|-------------|
| Global platform-native | Visible to all tenants |
| Tenant-private | Owner tenant only |
| Quarantined | Hidden from normal selection |
| Rejected | Audit view only |
| External import | Internal research view only |

Cross-tenant invisible records return the **same not-found error** as missing records.

---

## Eligibility view

Derived read-only `SkillEligibilityView`:

- `candidate` → not production eligible, not selectable
- `active` + valid + visible → selectable
- `suspended` / `archived` / `rejected` → not selectable for new work

Does not infer approval from validation.

---

## Query semantics

Exact match only. Deterministic ordering by `skill_id`. No fuzzy/vector search.

Methods: `get_skill`, `get_skill_version`, `list_skills`, `find_by_capability`, `find_visible_for_tenant`, `find_by_status`, `find_by_package_hash`, `query_registry`.

---

## Conflict detection

Pure detection only — no auto-resolution:

- Same `skill_id` + `version`, different hash → error
- Duplicate hash under different identities → warning
- Invalid tenant scope + source combination → error

---

## Frozen package projection

```
skill_id: ms.skill.market_validation
version: 0.1.0
status: candidate
validation_status: valid
production_eligible: false
selectable_for_new_work: false
lineage_resolvable: true
package_hash: 6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133
```

---

## Limitations

- In-memory only (no DB/API)
- `quarantine_import` visibility rules partial until SKILL-01.4
- No runtime selection or activation

---

## Future SKILL-01.4 integration

Quarantine Import Adapter will produce validation reports → projection → snapshot append flow (still read-only until persistence phase).

---

## Non-goals

Persistence, API, UI, lifecycle mutation, execution, discovery, MCP, CWF.1 migration.
