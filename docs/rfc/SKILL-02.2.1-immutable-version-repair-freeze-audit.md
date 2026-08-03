# SKILL-02.2.1 — Immutable Version Repair (Freeze Audit)

**Status:** Frozen  
**Date:** 2026-07-23  
**Scope:** Restore frozen 0.1.0 lineage; publish PMC 0.2.0 with `output_contract_type`; legacy MV mapping.

---

## Problem

SKILL-02.1.1 added `output_contract_type` **in-place** to frozen packages, violating semver immutability:

| Package | Version | Frozen hash (restored) | Broken hash (reverted) |
|---------|---------|------------------------|------------------------|
| `ms.skill.product_marketing_context` | 0.1.0 | `5e3dfc1bfc48c56d33951006c3adcf80b4d53ad246e96669d1d32014934cc230` | `7fcecc47…bf88` |
| `ms.skill.market_validation` | 0.1.0 | `6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133` | `7106b6cd…adba` |

**Invariant (blocking):** same `skill_id + version` → same `package_hash`.

---

## Repair actions

### Product Marketing Context

| Version | Path | `output_contract_type` | Hash |
|---------|------|------------------------|------|
| 0.1.0 | `packages/skills/ms.skill.product_marketing_context/` | legacy → `context` | `5e3dfc1b…cc230` |
| 0.2.0 | `packages/skills/ms.skill.product_marketing_context/0.2.0/` | `context` (manifest) | `08bf9d55…81eaa` |

Nested `0.2.0/` is excluded from parent 0.1.0 hash via semver directory exclusion in `app/skills/hashing.py`.

### Market Validation 0.1.0

- Manifest restored without `output_contract_type`.
- Compatibility mapping in `app/skills/legacy_output_contract.py`:

```python
("ms.skill.market_validation", "0.1.0") → decision
```

No MV 0.2.0 in this phase — deferred to SKILL-02.6.

### Validator

- `output_contract_type` optional on `SkillManifest`; required for new packages unless legacy-mapped.
- `immutable_version_hash_conflict` error when frozen hash mismatches.
- Registry `duplicate_skill_version_hash` conflict unchanged.

---

## Regression

```bash
uv run pytest (Get-ChildItem tests -Filter "test_skill_0*.py").FullName -q
```

Dedicated: `tests/test_skill_02_2_1_immutable_version_repair.py`

---

## Queue (unchanged)

```
02.2.1 Immutable Version Repair  ✅
02.3   Competitor Analysis        ← next (blocked until owner accepts 02.2.1)
```

**Downstream dependency for 02.3:** Product Marketing Context **0.2.x** + Market Research 0.1.x.
