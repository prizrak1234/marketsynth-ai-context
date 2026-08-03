# ms.skill.market_validation

**Skill ID:** `ms.skill.market_validation`  
**Version:** `0.1.0` (frozen legacy at root) · **`0.2.0` frozen** ([SKILL-02.6B](../rfc/SKILL-02.6B-market-validation-v0.2.0-freeze-audit.md))  
**Status:** `candidate` (non-executable skeleton)  
**Phase:** SKILL-01.0 (0.1.0) · SKILL-02.6A (design) · **SKILL-02.6B (0.2.0 package)**  
**Audit reference:** MS-SKILL-005 (SKILL-R0.1) — research label only; not production identity

---

## Purpose

Platform-native Skill package skeleton for **Market Validation**: evaluate whether a business or product idea has sufficient evidence and commercial rationale to proceed, revise, defer, or stop.

This package defines future contracts for the golden-path CWF.1 step **Idea → Research → Verdict**. It does **not** execute and does **not** replace the existing Business Idea Validation (BIV) runtime.

---

## Package structure

```
packages/skills/ms.skill.market_validation/
├── SKILL.md
├── manifest.yaml
├── resources/README.md
├── templates/verdict_summary.md.jinja2
├── schemas/
│   ├── input.schema.json
│   └── output.schema.json
└── tests/
    ├── eval_manifest.yaml
    └── fixtures/
```

No `scripts/` directory. Scripts disabled in manifest.

---

## Manifest summary

| Field | Value |
|-------|-------|
| id | `ms.skill.market_validation` |
| version | `0.1.0` |
| source | `platform_native` |
| status | `candidate` |
| tenant_scope | `global` |
| owner | Marketsynth Platform |
| allowed_tools | `[]` (empty) |
| script_policy | disabled |

---

## Input contract

Schema: `schemas/input.schema.json`

Required: `idea_description`

Optional (progressive clarification): product/service, target market, geography, intended customer, business model, pricing/budget/timeline, founder constraints, known competitors, available evidence, user risk tolerance.

Field states distinguish: provided, optional_missing, unknown, user_assumption, externally_verified.

**Rule:** assumptions are not evidence.

---

## Output contract

Schema: `schemas/output.schema.json`

Required lineage: `skill_id`, `skill_version`

Allowed verdicts: `proceed`, `proceed_with_conditions`, `revise`, `defer`, `stop`, `insufficient_evidence`

Legacy BIV mapping: runtime `reject` → package `stop` (migration note).

---

## Evidence rules

Evidence classes: user_statement, market_source, competitor_source, demand_signal, pricing_signal, audience_signal, assumption, inference.

- Every material conclusion must trace to evidence, assumption, or inference.
- Inferences must not be presented as verified facts.
- High-confidence verdict thresholds: **open implementation question** (not frozen in skeleton).

---

## Approval rules (declarative metadata only)

| Action | Approval |
|--------|----------|
| Analysis preparation | Not required |
| Verdict presentation | Not required |
| Launch / execution transition | **Required** |
| Paid or write actions | **Required** |
| Publication | Native publication flow — no Skill bypass |

---

## Dependencies

Declared future dependencies (non-executable):

- `ms.skill.product_marketing_context` — optional
- `ms.skill.market_research` — declared_future_dependency
- `ms.skill.competitor_analysis` — declared_future_dependency
- `ms.skill.icp_segmentation` — declared_future_dependency

---

## Limitations

- Non-executable skeleton — no runtime loader in SKILL-01.0.
- No connector or tool permissions.
- Does not guarantee profitability or fabricate demand.
- Does not replace `app/business_idea_validation/` CWF.1 workflow.

---

## Current non-executable status

| Check | State |
|-------|-------|
| Runtime loader | None |
| Registry promotion | Not performed |
| MCP / tools | None granted |
| CWF.1 BIV | Unchanged — live path remains Python operator |

---

## Future migration path

**SKILL-02.6B (frozen):** [ms.skill.market_validation-v0.2.0.md](ms.skill.market_validation-v0.2.0.md) · [Freeze audit](../rfc/SKILL-02.6B-market-validation-v0.2.0-freeze-audit.md)

**SKILL-02.6A (design):**

- [Migration Design](../rfc/SKILL-02.6-MARKET-VALIDATION-0.2-MIGRATION-DESIGN.md)
- [Version Mapping](market-validation-version-mapping.md)
- [Decision Matrix](market-validation-decision-matrix.md)
- [Consumer Contracts](market-validation-consumer-contracts.md)

**SKILL-02.6B (next):** Implemented at `packages/skills/ms.skill.market_validation/0.2.0/` — **frozen**.

1. SKILL-01.1+ — contracts in `app/schemas/contracts.py` derived from this package.
2. SKILL-01.2 — manifest validator CLI.
3. SKILL-02 — optional lineage fields on BIV runs (`skill_id`, `skill_version`) without behavior change.
4. SKILL-02 — governed execution when owner accepts freeze.

---

## Test coverage

Backend tests: `tests/test_skill_01_0_market_validation_package.py` (24 cases)

Fixtures: `packages/skills/ms.skill.market_validation/tests/fixtures/`

Run:

```bash
uv run pytest tests/test_skill_01_0_market_validation_package.py -q
```

---

## Explicit non-goals (SKILL-01.0)

- Skill execution engine
- External Skill installation
- MCP installation
- Tenant upload UI
- Automatic activation
- Changes to CWF.1 / CWF.1a behavior

---

## Related documents

- [SKILL-01 Foundation Plan](../rfc/SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)
- [RFC-SKILL-002](../rfc/RFC-SKILL-002-skill-package-format.md)
- [Audit card MS-SKILL-005](../research/skills/candidates/05-market-validation.md)
