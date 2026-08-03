# Market Validation — Version Mapping

**Phase:** SKILL-02.6A  
**Status:** Design — pending owner review  
**Scope:** Documentation only; no package or runtime changes

---

## Identity rule

```
same skill_id + different version = distinct immutable package identity
```

| Version | Package path | Hash | Status |
|---------|--------------|------|--------|
| `0.1.0` | `packages/skills/ms.skill.market_validation/` | `6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133` | **Frozen legacy** |
| `0.2.0` | `packages/skills/ms.skill.market_validation/0.2.0/` | `ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a` | **Frozen (02.6B)** |

No in-place patch. MV 0.1.0 bytes remain immutable.

---

## 0.1.0 — frozen legacy

| Attribute | Value |
|-----------|-------|
| Input model | Standalone — `idea_description` + optional evidence |
| Dependencies | All **declared_future** or optional; no upstream hash refs |
| Output contract | Legacy-mapped to `decision` via `LEGACY_OUTPUT_CONTRACT_TYPES` |
| CIM consumption | **None** — predates golden path |
| Upstream chain | Not required |
| Producer role | Verdict-only skeleton (non-executable) |

**Lineage:** Historical outputs remain resolvable via `skill_id`, `skill_version`, `provenance`, frozen hash.

---

## 0.2.0 — new immutable package (02.6B)

| Attribute | Value |
|-----------|-------|
| Input model | Golden-path aggregation — PMC + MR + CA + CIM refs |
| Dependencies | Explicit required constraints (see below) |
| Output contract | Declared `output_contract_type: decision` in manifest |
| CIM consumption | **Required** — shared CIM v0.1.0 consumer |
| Upstream chain | PMC 0.2.x → MR 0.1.x → CA 0.1.x → ICP/CIM 0.1.x |
| Producer role | **Sole authorized viability verdict issuer** in native Skill set |

---

## Required dependency graph (0.2.0)

| Dependency | Constraint | Relationship |
|------------|------------|--------------|
| `ms.skill.product_marketing_context` | `>=0.2.0,<1.0.0` | required |
| `ms.skill.market_research` | `>=0.1.0,<1.0.0` | required |
| `ms.skill.competitor_analysis` | `>=0.1.0,<1.0.0` | required |
| CIM (via `ms.skill.icp_segmentation`) | schema `>=0.1.0,<1.0.0` | required |

ICP produces CIM; MV consumes the shared CIM contract, not a parallel customer model.

**Required dependency payload fields (02.6B schema enforcement):**

| Field | Purpose |
|-------|---------|
| `source_skill_id` | Upstream skill identity |
| `source_skill_version` | Semver of upstream package |
| `source_output_hash` | Lineage to frozen upstream output |
| `source_status` | Upstream readiness/research status |
| `source_evidence_references` | Traceable evidence IDs |
| `source_unknowns` | Preserved unknowns from upstream |
| `source_conflicts` | Preserved conflicts from upstream |
| `provenance` | Audit trail stub |

Missing identity or hash → **reject at package-schema validation** (02.6B).

---

## Verdict vocabulary

### MV Skill package (0.1.0 and 0.2.0)

Finite enum — **no synonyms, no hidden statuses:**

| Value | Meaning |
|-------|---------|
| `proceed` | Evidence supports moving to the next stage; no unresolved critical blocker |
| `proceed_with_conditions` | Progress reasonable only if explicit conditions are satisfied |
| `revise` | Core idea may be viable after material changes (segment, offer, model, pricing, geography, positioning assumption, execution approach) |
| `defer` | Decision should wait — timing, evidence, operational readiness, or external conditions insufficient |
| `stop` | Evidence indicates unacceptable risk or lack of commercial rationale within declared scope |
| `insufficient_evidence` | No responsible verdict can be issued |

### CWF.1 BIV runtime (`BusinessIdeaValidationVerdictKind`)

**File:** `app/schemas/contracts.py`

| Value | Present in BIV runtime |
|-------|------------------------|
| `proceed` | ✓ |
| `proceed_with_conditions` | ✓ |
| `revise` | ✓ |
| `reject` | ✓ (not `stop`) |
| `insufficient_evidence` | ✓ |
| `defer` | ✗ |
| `stop` | ✗ |

---

## CWF.1 mapping table

**Rule:** Document only — **do not modify CWF.1 runtime in 02.6A.**

| Legacy BIV / CWF.1 value | MV 0.2.0 value | Compatibility | Migration risk |
|--------------------------|----------------|---------------|----------------|
| `proceed` | `proceed` | Direct | Low — same semantics |
| `proceed_with_conditions` | `proceed_with_conditions` | Direct | Low |
| `revise` | `revise` | Direct | Low |
| `reject` | `stop` | **Requires adapter** | Medium — Skill uses `stop`; BIV uses `reject`. Documented in MV 0.1.0 SKILL.md §6 |
| `insufficient_evidence` | `insufficient_evidence` | Direct | Low |
| — | `defer` | **MV-only** | **Unknown** — no BIV equivalent; future CWF adapter must define mapping or new branch |
| BIV `VerdictKind.no_go` | MV `stop` | **Requires adapter** | Medium — business layer mapping via `verdict_mapper.py` |
| BIV `VerdictKind.conditional_go` | MV `proceed` / `proceed_with_conditions` / `revise` | **Requires adapter** | Medium — three MV values map to one business verdict |
| BIV `VerdictKind.insufficient_data` | MV `insufficient_evidence` | Direct | Low |
| CWF `CommercialNextStepAction.stop_project` | MV `stop` | **Requires adapter** | Medium — UI action, not verdict enum |

**Do not invent equivalence** where none exists. `defer` is marked **Unknown** for CWF.1 until a future migration RFC defines it.

### BIV → Business verdict (`verdict_mapper.py`)

| BIV verdict | `VerdictKind` |
|-------------|---------------|
| `proceed` | `conditional_go` |
| `proceed_with_conditions` | `conditional_go` |
| `revise` | `conditional_go` |
| `reject` | `no_go` |
| `insufficient_evidence` | `insufficient_data` |

---

## Legacy output contract compatibility

| Mapping | 0.1.0 → 0.2.0 | Status |
|---------|---------------|--------|
| Input: standalone `idea_description` | Input: upstream hash refs + CIM ref | **incompatible** |
| Output: verdict enum (6 values) | Output: same enum + expanded structure | **conditionally_compatible** |
| Output: no upstream refs | Output: required source refs | **incompatible** |
| Output: `evidence_gaps[]` | Output: `decision_dimensions` + structured gaps | **requires_adapter** |
| Output: flat risk arrays | Output: structured `critical_risks` / `noncritical_risks` | **requires_adapter** |
| Verdict semantics | Same 6 values preserved | **compatible** |
| Historical 0.1.0 outputs readable | Yes — lineage-resolvable | **compatible** |
| Automatic migration | Not promised | — |

**Policy:** 0.2.0 has the right to be incompatible with 0.1.0 input model if honestly documented. Historical 0.1.0 outputs remain lineage-resolvable; no silent migration.

---

## Output contract taxonomy

| Version | `output_contract_type` | Discriminator |
|---------|------------------------|---------------|
| 0.1.0 | Legacy-mapped → `decision` | `verdict` |
| 0.2.0 | Declared → `decision` | `verdict` |

CIM is **not** an `output_contract_type`. ICP remains `research`; CIM is embedded shared artifact ([SKILL-02.5](../rfc/SKILL-02.5-CIM-SHARED-SCHEMA-FREEZE.md)).

---

## Frozen hash registry

MV 0.1.0 hash must remain in `FROZEN_PACKAGE_HASHES` until 0.2.0 is separately frozen. When 0.2.0 publishes, add new entry — do not replace 0.1.0.

```python
("ms.skill.market_validation", "0.1.0"): "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
```

---

## Related documents

- [SKILL-02.6 Migration Design](../rfc/SKILL-02.6-MARKET-VALIDATION-0.2-MIGRATION-DESIGN.md)
- [Decision Matrix](market-validation-decision-matrix.md)
- [Consumer Contracts](market-validation-consumer-contracts.md)
- [ms.skill.market_validation.md](ms.skill.market_validation.md)
