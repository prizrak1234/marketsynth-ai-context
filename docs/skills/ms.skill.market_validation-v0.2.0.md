# ms.skill.market_validation v0.2.0

**Status:** candidate · non-executable · frozen 0.2.0 (SKILL-02.6B)  
**Design:** [SKILL-02.6A Migration Design](../rfc/SKILL-02.6-MARKET-VALIDATION-0.2-MIGRATION-DESIGN.md)

---

## Purpose

Aggregate **PMC 0.2.x + MR 0.1.x + CA 0.1.x + CIM 0.1.x** into one evidence-backed commercial viability decision.

Only this Skill issues a viability **verdict** in the native golden path. CIM does not issue verdict.

---

## Package identity

| Field | Value |
|-------|-------|
| skill_id | `ms.skill.market_validation` |
| version | `0.2.0` |
| output_contract_type | `decision` |
| status | candidate |
| executable | false |
| package_hash | `ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a` |
| path | `packages/skills/ms.skill.market_validation/0.2.0/` |

Legacy 0.1.0 remains at package root — unchanged (`6c53b5b9…8133`).

---

## Dependencies (required)

| Upstream | Constraint |
|----------|------------|
| `ms.skill.product_marketing_context` | `>=0.2.0,<1.0.0` |
| `ms.skill.market_research` | `>=0.1.0,<1.0.0` |
| `ms.skill.competitor_analysis` | `>=0.1.0,<1.0.0` |
| CIM (via `ms.skill.icp_segmentation`) | schema `>=0.1.0,<1.0.0` |

Canonical CIM URI: `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/customer-intelligence.schema.json`

---

## Verdict contract

Finite values: `proceed`, `proceed_with_conditions`, `revise`, `defer`, `stop`, `insufficient_evidence`

**Verdict ≠ approval ≠ execution authorization.** `human_approval_required: true` for execution stages.

---

## Schemas

| Schema | Purpose |
|--------|---------|
| `input.schema.json` | Four upstream refs + validation objectives |
| `output.schema.json` | Full decision output |
| `decision_readiness.schema.json` | Pre-verdict readiness gate |
| `decision_dimension.schema.json` | 15 assessment dimensions |
| `hard_blocker.schema.json` | HB-001…HB-011 blockers |
| `validation_condition.schema.json` | Structured conditions |
| `validation_risk.schema.json` | Critical/noncritical risks |

Cross-field semantic validation: `tests/support/market_validation_v020_validation.py`

---

## Forbidden output

`positioning`, `final_offer`, `campaign`, `execution_status`, `publication`, `connector_result`

---

## Downstream consumers

| Consumer | May consume |
|----------|-------------|
| Positioning (02.7) | Verdict, conditions, segment refs, risks |
| Offer Builder (02.8) | Permitted downstream state only |
| Launch Strategy | Verdict guidance only |

---

## CWF.1 mapping (documentation only)

| BIV | MV 0.2.0 | Notes |
|-----|----------|-------|
| `proceed` | `proceed` | Direct |
| `reject` | `stop` | Adapter required |
| `defer` | `defer` | No BIV equivalent |

Fixtures: `tests/fixtures/cwf_mapping_*.json`

---

## Test coverage

`tests/test_skill_02_6_market_validation_v020.py` — 69 cases

```bash
uv run pytest tests/test_skill_02_6_market_validation_v020.py -q
```

---

## Non-goals

No runtime execution, CWF.1 migration, Positioning, Offer Builder, connectors, persistence, API, UI.
