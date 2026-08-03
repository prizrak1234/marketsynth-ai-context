# SKILL-01.2 — Manifest and Package Validator

**Phase:** SKILL-01.2  
**Status:** Complete (2026-07-23)  
**Depends on:** SKILL-01.0 (frozen), SKILL-01.1 (contracts)

---

## Purpose

Production-grade **read-only** validator for Marketsynth Skill packages (MSP). Parses `manifest.yaml`, validates through canonical `SkillManifest` domain contracts, inspects package structure, validates referenced JSON Schemas, enforces security invariants, and returns a deterministic validation report.

**Validation ≠ execution.** A passing report does not imply approved, active, production-eligible, or runtime-compatible status.

---

## Architecture

```
app/skills/
├── __init__.py              # Public exports
├── errors.py                # Domain errors (safe messages)
├── validation_contracts.py  # Report + mode contracts
├── manifest_parser.py       # Safe YAML → dict → SkillManifest
├── hashing.py               # Deterministic SHA-256 package hash
├── package_validator.py     # Orchestrator (16 stages)
└── validate_package.py      # CLI entrypoint
```

### Domain vs package validation

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Domain | `app/schemas/contracts.py` | `SkillManifest` semantics, lifecycle enums |
| Parse | `manifest_parser.py` | Safe YAML, duplicate keys, coercion guards |
| Package | `package_validator.py` | File existence, paths, schemas, hash, security |

Domain rules are **not duplicated** — package validator calls `SkillManifest.model_validate`.

---

## Parser choice

| Decision | Choice |
|----------|--------|
| Library | **PyYAML** `SafeLoader` (explicit production dependency) |
| Loader | `StrictManifestLoader` — duplicate-key rejection, alias/tag rejection |
| Coercion guard | String enum fields (`status`, `id`, etc.) must remain strings after parse |
| Forbidden | `yaml.load` unsafe loader, custom general parser, object constructors |

---

## Dependency decision

Added to `pyproject.toml` as **direct production dependencies**:

- `pyyaml>=6.0.2` — manifest parsing (required; was not previously direct)
- `jsonschema>=4.23.0` — Draft 2020-12 schema validation (required; was not previously direct)

Transitive `uv.lock` entries are **not** relied upon.

---

## Validation stages

1. Resolve package root  
2. Enforce package-root boundary  
3. Inspect required structure (`manifest.yaml`, `SKILL.md`)  
4. Read manifest as bytes  
5. Parse YAML safely  
6. Reject unsupported YAML constructs  
7. Validate through `SkillManifest`  
8. Normalize domain representation  
9. Validate lifecycle restrictions (candidate mode)  
10. Validate path references  
11. Validate input/output JSON Schemas  
12. Validate declared test suite paths  
13. Enforce scripts policy (globally disabled in 01.2)  
14. Scan forbidden secret-like manifest keys (raw dict, pre-Pydantic)  
15. Calculate deterministic package hash  
16. Return structured validation report  

---

## Validation modes

| Mode | SKILL-01.2 behavior |
|------|---------------------|
| `candidate` | **Fully implemented** |
| `quarantine_import` | Enum only — emits warning |
| `registry_readiness` | Enum only — emits warning |

---

## Security checks

- `allowed_tools: []` for candidate skeleton  
- `network_policy.default: deny`  
- `script_policy.enabled: false`  
- No symlinks inside package  
- No path traversal in references  
- No executable/script files while scripts disabled  
- Forbidden manifest keys: `api_key`, `secret`, `token`, `password`, `credential`, etc.  
- SKILL.md must not contain permission configuration blocks  

---

## JSON Schema validation

- Draft 2020-12 required (`$schema`)  
- `jsonschema.Draft202012Validator.check_schema`  
- No remote `$ref` (`http://`, `https://`)  
- Local `$ref` must resolve inside package root  
- Output schema must require `skill_id`, `skill_version`, `verdict`  
- Verdict enum must match `SkillValidationVerdict`  

---

## Hashing algorithm

Matches SKILL-01.0 freeze audit:

- Algorithm: **SHA-256**  
- Ordering: lexicographic sort of relative POSIX paths  
- Content: UTF-8 path bytes + raw file bytes per file  
- Excludes: directories, symlinks (rejected)  
- No timestamps or filesystem metadata  

**Frozen package hash:** `6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133`

---

## Report contract

See `SkillPackageValidationReport` in `app/skills/validation_contracts.py`.

Key fields: `valid`, `validation_mode`, `package_hash`, `normalized_manifest`, `errors`, `warnings`, `checks`, `schema_results`, `security_findings`, `validator_version`.

Each issue includes: `code`, `severity`, `message`, `location`, `rule_reference`, `remediation_hint`.

---

## Public API

```python
from pathlib import Path
from app.skills import validate_skill_package, parse_skill_manifest, calculate_skill_package_hash
from app.skills.validation_contracts import SkillValidationMode

report = validate_skill_package(
    Path("packages/skills/ms.skill.market_validation"),
    mode=SkillValidationMode.CANDIDATE,
)
```

---

## CLI usage

```bash
uv run python -m app.skills.validate_package packages/skills/ms.skill.market_validation
uv run python -m app.skills.validate_package packages/skills/ms.skill.market_validation --json
```

Exit code: `0` = valid, non-zero = invalid.

---

## Migration from test helper

| Component | Status |
|-----------|--------|
| `tests/support/skill_package_validation.py` | **Deprecated** for validation; retained for SKILL-01.0 I/O fixture tests |
| `app/skills/package_validator.py` | **Authoritative** for package validation |
| Freeze audit hash | Uses `app.skills.hashing.calculate_skill_package_hash` |

---

## Limitations (SKILL-01.2)

- No registry persistence (SKILL-01.3)  
- No quarantine import flow (SKILL-01.4)  
- No Skill execution or dynamic loading  
- `quarantine_import` / `registry_readiness` modes not fully implemented  
- Remote JSON Schema resolution intentionally disabled  

---

## Non-goals

Execution engine, API, DB, MCP, external Skill install, CWF.1 migration, discovery, generation.

---

## Future SKILL-01.3 integration

Registry read models will consume `SkillPackageValidationReport` + `SkillPackageDescriptor` from successful candidate validation before any promotion beyond `quarantined`.
