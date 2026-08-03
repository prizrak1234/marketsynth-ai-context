# ms.skill.positioning

**Version:** 0.1.0  
**Status:** Frozen candidate (SKILL-02.7)  
**output_contract_type:** `research`

## Purpose

Consume **Customer Intelligence Model 0.1.x**, **Competitor Analysis 0.1.x**, and
**Market Validation 0.2.x** to produce evidence-backed positioning hypotheses,
territories, differentiation framing, value framing, and message hierarchy
recommendations.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Positioning hypotheses with ranking | Customer segmentation / JTBD recompute |
| Territories and differentiation framing | Viability verdict override |
| Message hierarchy (strategic) | Final Offer, pricing, campaigns |
| Downstream Offer Builder inputs | Launch execution or publication |

## Dependencies

| Dependency | Constraint |
|------------|------------|
| CIM (via ICP) | >=0.1.0,<1.0.0 |
| ms.skill.competitor_analysis | >=0.1.0,<1.0.0 |
| ms.skill.market_validation | >=0.2.0,<1.0.0 |
| ms.skill.product_marketing_context | optional >=0.2.0,<1.0.0 |

## Market Validation boundary

MV verdict is authoritative. `stop` → no launch-ready recommendation.
`ready_for_offer_design` ≠ human approval ≠ execution authorization.

## Package location

`packages/skills/ms.skill.positioning/`

## Regression

```bash
uv run pytest tests/test_skill_02_7_positioning.py -q
```

## Freeze audit

[SKILL-02.7-positioning-freeze-audit.md](../rfc/SKILL-02.7-positioning-freeze-audit.md)
