# Skill packages (MSP)

Platform-native and adapted **Marketsynth Skill Packages** live under this directory.

**Canonical layout (RFC-SKILL-002):**

```
packages/skills/<skill_id>/
├── SKILL.md
├── manifest.yaml
├── resources/
├── templates/
├── schemas/
└── tests/
```

**SKILL-01.0 driver:** `ms.skill.market_validation/` — non-executable skeleton; status `candidate`.

**SKILL-02.3:** `ms.skill.competitor_analysis/` — research output contract; status `candidate`.

**Version layout (transitional):** See [docs/rfc/SKILL-02-transitional-version-layout.md](../../docs/rfc/SKILL-02-transitional-version-layout.md). Legacy frozen semver may live at package root; newer versions in nested `<semver>/` directories. **Root is never “latest”.**

Packages are validated by pytest (`tests/test_skill_01_0_market_validation_package.py`). No runtime loader in SKILL-01.0.

Audit reference IDs (e.g. MS-SKILL-005) are research labels only — production identity is `skill_id` in manifest.
