# Skill contract field mapping (SKILL-01.1)

**Purpose:** Single reference for manifest.yaml ↔ Python domain contracts ↔ JSON Schema I/O.  
**Driver package:** `ms.skill.market_validation` v0.1.0 (frozen)

---

## Source of truth hierarchy

| Layer | Role | Location |
|-------|------|----------|
| **Python contracts** | Domain types for registry, validator, lineage | `app/schemas/contracts.py` |
| **manifest.yaml** | Package declaration → parsed into `SkillManifest` | `packages/skills/<skill_id>/manifest.yaml` |
| **JSON Schema** | Package input/output I/O only | `packages/skills/<skill_id>/schemas/*.schema.json` |
| **Registry policy** | Final eligibility + permissions at runtime | Future SKILL-01.3+ |

Python contracts are canonical for **manifest semantics**. JSON Schema is canonical for **I/O payloads** only.

---

## Manifest → SkillManifest mapping

| manifest.yaml field | Python contract | Notes |
|-------------------|-----------------|-------|
| `id` | `SkillManifest.id` | Pattern `ms.skill.*` |
| `name` | `SkillManifest.name` | |
| `version` | `SkillManifest.version` | Semver |
| `description` | `SkillManifest.description` | |
| `owner` | `SkillManifest.owner` | |
| `source` | `SkillManifest.source` | `SkillSourceType` |
| `license` | `SkillManifest.license` | |
| `status` | `SkillManifest.status` | `SkillLifecycleStatus` |
| `capabilities` | `SkillManifest.capabilities` | `list[str]` |
| `activation_conditions` | `SkillActivationConditions` | |
| `required_inputs.schema_ref` | `SkillInputSchemaReference` | |
| `output_schema.schema_ref` | `SkillOutputSchemaReference` | |
| `required_evidence` | `SkillEvidencePolicy` | |
| `dependencies` | `SkillDependencies` | |
| `allowed_tools` | `SkillManifest.allowed_tools` | Must be `[]` for skeleton |
| `approval_policy` | `SkillApprovalPolicy` | Declarative only |
| `tenant_scope` | `SkillTenantScope` | |
| `quality_threshold` | `SkillQualityThreshold` | |
| `known_limitations` | `SkillManifest.known_limitations` | |
| `test_suite` | `SkillTestSuiteRef` | |
| `provenance` | `SkillProvenance` | |
| `provenance.audit_research_id` | `SkillProvenance.audit_research_id` | Research only (MS-SKILL-005) |
| `runtime_compatibility` | `SkillManifest.runtime_compatibility` | |
| `knowledge_scopes` | `SkillManifest.knowledge_scopes` | |
| `network_policy` | `SkillNetworkPolicy` | |
| `script_policy` | `SkillScriptPolicy` | |
| `resource_limits` | `SkillResourceLimits` | Optional |

---

## I/O schema ↔ runtime (future)

| JSON Schema | Python (future execution) | Current CWF.1 |
|-------------|---------------------------|---------------|
| `input.schema.json` | Skill activation input | `BusinessIdeaValidationInput` (partial overlap) |
| `output.schema.json` | Skill activation output | `BusinessIdeaValidationOutput` + package lineage fields |

Package output adds `skill_id`, `skill_version`, extended evidence trace — not yet wired to BIV.

---

## Identity mapping (research vs production)

| Label | Type | Example |
|-------|------|---------|
| Production `skill_id` | Registry identity | `ms.skill.market_validation` |
| Audit card ID | Research reference only | `MS-SKILL-005` |
| Owner commercial ID | Roadmap label only | `MS-SKILL-001` (Market Validation driver) |

---

## Round-trip test

```
tests/fixtures/skill_manifests/ms.skill.market_validation.v0.1.0.json
  → SkillManifest.model_validate
  → normalized_registry_snapshot()
  → SkillManifest.model_validate (again)
  → assert stable
```

Run: `uv run pytest tests/test_skill_01_1_contracts.py -q`

---

## Frozen package hash

SHA-256 (sorted paths + bytes): `6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133`

See [SKILL-01-0-freeze-audit.md](../rfc/SKILL-01-0-freeze-audit.md).
