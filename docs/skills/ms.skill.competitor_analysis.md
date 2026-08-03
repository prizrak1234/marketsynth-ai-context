# ms.skill.competitor_analysis

**Status:** candidate · non-executable · frozen 0.1.0 (SKILL-02.3)  
**Architecture:** [SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md](../rfc/SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md)

---

## Purpose

Transform **Product Marketing Context 0.2.x** and **Market Research 0.1.x** outputs into an evidence-aware **competitive landscape**: competitor types, comparisons, differentiation gaps, and research status — without commercial verdicts, positioning, offers, or web research.

Not a SWOT generator. Primary contract is structured competitive landscape with sources, contradictions, and gaps.

---

## Package identity

| Field | Value |
|-------|-------|
| skill_id | `ms.skill.competitor_analysis` |
| version | `0.1.0` |
| output_contract_type | `research` |
| status | candidate |
| executable | false |
| package_hash | `14903c8744b57c472bf09875a41d4b825f175c5cb8ae55eecfdce1829a48cde0` |
| path | `packages/skills/ms.skill.competitor_analysis/` |

---

## Dependencies

| Upstream | Constraint | Relationship |
|----------|------------|--------------|
| `ms.skill.product_marketing_context` | `>=0.2.0,<1.0.0` | required (0.1.0 **not** compatible) |
| `ms.skill.market_research` | `>=0.1.0,<1.0.0` | required |

Methodology/data only — no runtime orchestration. Upstream hashes, evidence refs, unknowns, and conflicts preserved.

---

## Input contract

Requires `product_marketing_context` and `market_research_output` dependency references with `source_skill_id`, `source_skill_version`, `source_output_hash`.

Optional: competitor candidates, known direct/indirect/substitute/alternative lists, price/offer/channel data, comparison dimensions, scope, geography, constraints.

---

## Competitor model

Finite types: `direct`, `indirect`, `substitute`, `alternative`, `emerging`, `potential`, `unknown`.

Verified strengths/weaknesses require `source_reference`. "No competitors" cannot be verified without explicit evidence.

---

## Comparison model

Structured dimensions across finite categories (product, pricing, offer, channel, proof, etc.) with subject vs competitor values and explicit gaps.

---

## Output contract

`output_contract_type: research` — required discriminators: `research_status`, `evidence_quality`, `coverage`, `evidence_gaps`.

Forbidden: `verdict`, `readiness`, `execution_status`.

Evidence quality uses architecture enums (`comprehensive`, `partial`, `insufficient`, `conflicted`, `unknown`) — aligned with Market Research.

---

## Differentiation gaps

Structured gaps with `positioning_candidate_reference` as downstream hint only — **not** final positioning.

---

## Downstream consumers

- `ms.skill.icp_segmentation` (planned 02.4) → **✅ frozen 0.1.0 (02.4)**
- `ms.skill.market_validation` 0.2.0+ (planned 02.6)
- `ms.skill.positioning` (planned 02.7)

---

## Limitations

- Non-executable skeleton — no runtime loader.
- No autonomous web research or connectors.
- No commercial viability verdict.

---

## Test coverage

`tests/test_skill_02_3_competitor_analysis.py` — 50 cases including schema, fixtures, registry, audit, lineage, frozen hash regression.
