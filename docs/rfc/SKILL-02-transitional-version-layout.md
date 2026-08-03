# SKILL-02 — Transitional Version Layout

**Status:** Accepted (SKILL-02.2.1)  
**Scope:** Filesystem layout for immutable Skill package versions during native Skill set rollout.

---

## Problem

The first frozen native packages (`ms.skill.product_marketing_context` 0.1.0, `ms.skill.market_validation` 0.1.0) were published at the **package root** before `output_contract_type` and nested versioning existed. Repair (SKILL-02.2.1) introduced **nested semver directories** for new versions without rewriting frozen bytes.

Without explicit rules, developers may assume:

- the root directory is the **latest** version;
- nested folders are optional convenience;
- hashing includes all files under the skill_id folder.

All three assumptions are **wrong**.

---

## Transitional layout rule

| Location | Meaning |
|----------|---------|
| `packages/skills/<skill_id>/` (root) | **Legacy frozen version** when that semver was first published at root (e.g. PMC 0.1.0). Immutable — do not edit in place. |
| `packages/skills/<skill_id>/<semver>/` | **New immutable version** published after repair (e.g. PMC 0.2.0). Package root for validation and hashing is the nested directory. |
| Future greenfield packages | May use root for first version **or** nested `<semver>/` from day one — registry identity is always `skill_id + version + package_hash`, not path shape. |

### Hashing

- Hash for version **V** is computed over the **package root for V** only.
- When legacy version lives at root, **nested semver sibling directories are excluded** from the root hash (`app/skills/hashing.py`).
- Nested version `0.2.0/` is hashed independently as its own root.

### Registry semantics

- **Identity:** `skill_id` + `version` + `package_hash` (immutable triple).
- **`latest_known_version`:** derived from registry read models / semver ordering — **never** from “newest folder on disk” or “root = latest”.
- **Validation entry point:** pass the directory that contains `manifest.yaml` for the target version (root for legacy 0.1.0, nested path for 0.2.0+).

### Do not

- Treat root as “current” or “head”.
- Edit frozen root packages to add taxonomy fields — publish new semver instead.
- Mix version contents in one directory without nested isolation.

---

## Examples

```
packages/skills/ms.skill.product_marketing_context/
├── manifest.yaml          # frozen 0.1.0
├── SKILL.md
├── schemas/
└── 0.2.0/                 # excluded from 0.1.0 hash
    ├── manifest.yaml      # 0.2.0 with output_contract_type
    └── ...

packages/skills/ms.skill.competitor_analysis/   # greenfield 0.1.0 at root
├── manifest.yaml
└── ...
```

---

## Related

- [SKILL-02.2.1 immutable version repair](SKILL-02.2.1-immutable-version-repair-freeze-audit.md)
- [RFC-SKILL-002 § Transitional versioning](RFC-SKILL-002-skill-package-format.md)
- [packages/skills/README.md](../../packages/skills/README.md)
