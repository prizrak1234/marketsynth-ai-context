# SKILL-02 — Output Contract Taxonomy

| Field | Value |
|-------|-------|
| **Status** | Accepted (2026-07-23) |
| **Patch** | SKILL-02.1.1 — freezes validator extension from ad-hoc skill_id checks |
| **Governs** | All native Skill packages (SKILL-02+) |

---

## 1. Purpose

Package output schemas are validated by **`output_contract_type`** declared in `manifest.yaml`, not by hard-coded `skill_id` exceptions. This prevents the production validator from accumulating per-Skill `if` branches.

Architecture parent: [SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md](SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md).

Implementation: `app/skills/output_contract_rules.py` · `app/skills/package_validator.py`.

---

## 2. Contract classes

| output_contract_type | Role | Required discriminator(s) | Forbidden fields |
|---------------------|------|---------------------------|------------------|
| `context` | Normalize business/product context | `readiness` | `verdict`, `research_status`, `evidence_quality`, `coverage`, `execution_status` |
| `research` | Structure market evidence and gaps | `research_status`, `evidence_quality`, `coverage`, `evidence_gaps` | `verdict`, `readiness`, `execution_status` |
| `decision` | Commercial viability verdict | `verdict` | `readiness`, `research_status`, `evidence_quality`, `coverage`, `execution_status` |
| `execution` | Future execution Skills (not SKILL-02) | `execution_status` | `verdict`, `readiness`, `research_status`, `evidence_quality`, `coverage` |

All output contracts require lineage fields: `skill_id`, `skill_version`.

---

## 3. Discriminator enums

### context → readiness

`ready` · `partially_ready` · `insufficient_context` · `conflicted`

### research → research_status

`complete` · `partially_complete` · `insufficient_sources` · `conflicted` · `out_of_scope`

**Not allowed:** `proceed`, `stop`, `viable`, `unviable` — those belong to Market Validation (`decision`).

### research → evidence_quality

`comprehensive` · `partial` · `insufficient` · `conflicted` · `unknown`

### research → coverage

`full` · `partial` · `minimal` · `unknown`

### decision → verdict

`proceed` · `proceed_with_conditions` · `revise` · `defer` · `stop` · `insufficient_evidence`

### execution → execution_status (reserved)

`pending` · `in_progress` · `completed` · `failed` · `blocked`

---

## 4. Package mapping (SKILL-02)

| skill_id | output_contract_type | version |
|----------|---------------------|---------|
| `ms.skill.product_marketing_context` | context | 0.1.0 (patched manifest) |
| `ms.skill.market_research` | research | 0.1.0 |
| `ms.skill.market_validation` | decision | 0.1.0 (patched manifest) |

---

## 5. Validation rules

1. `manifest.yaml` **must** declare `output_contract_type`.
2. Output JSON Schema **must** require the contract's discriminator fields.
3. Output JSON Schema **must not** declare forbidden discriminator properties.
4. Enum values on discriminators **must** match domain enums in `app/schemas/contracts.py`.
5. Non-decision contracts **must not** declare commercial verdict enums.

---

## 6. Non-goals

- No runtime loader or Skill execution.
- No automatic inference of contract type from schema alone (manifest is source of truth).
- No `skill_id`-specific validator branches.

---

## 7. Migration note (SKILL-02.1.1)

Packages frozen before this patch lacked `output_contract_type`. PMC and Market Validation 0.1.0 manifests were updated with explicit contract types; package hashes changed accordingly. Schemas unchanged.
