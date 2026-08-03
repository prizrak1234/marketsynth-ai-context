# SKILL-01.4 — Quarantine Import Adapter

**Phase:** SKILL-01.4  
**Status:** Complete (2026-07-23)  
**Depends on:** SKILL-01.2 (validator), SKILL-01.3 (registry read models)

---

## Purpose

Safe read-only import of **local external** Skill package candidates into isolated quarantine. No installation, activation, execution, or tenant visibility.

```
External package → ingest → fingerprint → static inspection
  → production validator (quarantine_import) → quarantine record → audit required
```

**Not:** `External package → registry → active`

---

## Trust boundary

| Rule | Enforcement |
|------|-------------|
| External source untrusted | Provenance separates declared vs verified |
| Quarantine mandatory | `effective_status = quarantined` on success |
| Validation ≠ approval | `production_eligible = false` always |
| No network import | Local paths only; URLs rejected |
| No execution | Static copy + validation only |

---

## Supported sources

| Type | SKILL-01.4 |
|------|------------|
| `local_directory` | ✅ |
| `external_candidate_fixture` | ✅ |
| `platform_research_candidate` | ✅ |
| `local_archive` | Deferred (rejected) |
| Remote URL / git / marketplace | ❌ Forbidden |

---

## Import pipeline

1. Validate `QuarantineImportRequest`
2. Resolve local source path
3. Static inspect source tree
4. Calculate source fingerprint (SHA-256)
5. Create isolated quarantine workspace
6. Materialize safe file copy
7. Calculate materialized hash
8. Run `validate_skill_package(..., mode=quarantine_import)`
9. Apply quarantine lifecycle overlay in registry projection
10. Record provenance + metadata
11. Return immutable `QuarantineImportResult`

---

## Quarantine workspace

```
<quarantine_base>/<import_id>/
├── normalized/     # materialized package copy
├── reports/        # metadata.json
└── (source/ reserved for future snapshots)
```

Temporary base dir in tests/CLI; no repo commits of imported packages.

---

## Static inspection

Rejects: symlinks, executables, binaries, `.env`, secret-like filenames, nested archives, oversize files, excessive depth/count.

Runs **before** production validator.

---

## Provenance

`QuarantineProvenanceRecord` stores:

- `source_claims` — untrusted manifest declarations (status, tools, network, etc.)
- `unresolved_claims` — claims not verified (e.g. declared `active`)
- `verified_*` — always `None` in SKILL-01.4

No absolute paths in normalized reports (validation `package_path` redacted to `import_id`).

---

## Validation mode: `quarantine_import`

Implemented in `package_validator.py`:

- Source `active`/`approved` → warning (claim ignored)
- Non-empty `allowed_tools` → error
- Network allow → error
- Scripts enabled → error
- Does **not** apply candidate-only lifecycle errors for declared active status

---

## Effective lifecycle overlay

Source manifest stored unchanged. Registry projection forces:

- `lifecycle_status = quarantined`
- `source_type = external_import`
- `production_eligible = false`
- `tenant_visible = false`

---

## Conflict detection

In-memory `QuarantineImportState` detects:

- Duplicate source fingerprint
- Same skill_id+version, different hash
- Platform-native ID collision (`ms.skill.market_validation`)
- Expected skill_id/version mismatch

No auto-merge, no overwrite.

---

## Limits (defaults)

| Limit | Default |
|-------|---------|
| Total bytes | 10 MiB |
| Single file | 512 KiB |
| File count | 256 |
| Directory depth | 12 |

Injectable via `QuarantineImportLimits` in tests.

---

## Registry projection

Uses SKILL-01.3 read models only — in-memory, not persisted.

- Normal tenant queries: **cannot see** imported record
- Audit view: can inspect metadata

---

## CLI

```bash
uv run python -m app.skills.quarantine_import tests/fixtures/skills/quarantine/valid_external
```

Exit 0 = quarantined; non-zero otherwise. Uses temporary quarantine workspace.

---

## Limitations

- Directory-only import (no archives)
- No persistence beyond temp workspace
- No audit report schema (SKILL-01.6)
- No Connector Gateway (SKILL-01.5)

---

## Future SKILL-01.6 integration

Quarantine import results will feed structured audit reports before any promotion beyond `quarantined`.

---

## Non-goals

Remote git, marketplace, installation, activation, runtime loader, MCP, CWF.1 migration.
