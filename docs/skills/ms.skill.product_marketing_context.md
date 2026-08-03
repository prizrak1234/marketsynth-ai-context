# ms.skill.product_marketing_context

**Status:** candidate · non-executable · frozen 0.1.0 (SKILL-02.1) + 0.2.0 (SKILL-02.2.1)  
**Architecture:** [SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md](../rfc/SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md)

---

## Purpose

Transform fragmented user and business information into a structured, evidence-aware **Product Marketing Context** that downstream native Skills consume consistently.

This Skill **does not** research the market, validate viability, position the product, build offers, or execute external tools.

---

## Package identity

### v0.1.0 (frozen — no manifest `output_contract_type`)

| Field | Value |
|-------|-------|
| skill_id | `ms.skill.product_marketing_context` |
| version | `0.1.0` |
| owner | Marketsynth Platform |
| source_type | platform_native |
| tenant_scope | global |
| status | candidate |
| executable | false |
| output_contract_type | legacy mapping → `context` |
| package_hash | `5e3dfc1bfc48c56d33951006c3adcf80b4d53ad246e96669d1d32014934cc230` |
| path | `packages/skills/ms.skill.product_marketing_context/` |

### v0.2.0 (taxonomy — manifest declares `output_contract_type: context`)

| Field | Value |
|-------|-------|
| version | `0.2.0` |
| output_contract_type | `context` |
| package_hash | `08bf9d55a261da52a8659f5aa6f06c3f9a63f13f06a21aea5b2416b10a381eaa` |
| path | `packages/skills/ms.skill.product_marketing_context/0.2.0/` |

New downstream Skills (from SKILL-02.3) should depend on **0.2.x**.

---

## Role in native Skill family

Foundational **required dependency** (methodology/data) for:

- `ms.skill.market_research`
- `ms.skill.competitor_analysis`
- `ms.skill.icp_segmentation`
- `ms.skill.market_validation` (future 0.2.0+ migration)
- `ms.skill.positioning`
- `ms.skill.offer_builder`

Product Marketing Context has **no upstream Skill dependency**.

---

## Input contract

Schema: `schemas/input.schema.json`

Minimum: `raw_task`. Supports progressive/incomplete input.

Scalar fields (`product_name`, `business_model`, etc.) use claim-value objects with:

- `value`, `source_type`, `verification_status`, `confidence`, `notes`

Array fields use the shared claim model (`schemas/claim.schema.json`).

---

## Claim model

Schema: `schemas/claim.schema.json`

| Field | Purpose |
|-------|---------|
| claim_id | Stable identifier within output |
| domain | product_identity, pricing, competitor, … |
| statement | Normalized claim text |
| source_type | user_statement, document, external_source, prior_skill_output, system_inference, unknown |
| verification_status | unverified → verified (requires source_reference) |
| assumption / inference | Explicit flags — not promoted to evidence |
| conflict_group_id | Links contradictory claims |

Rules:

- Verified without `source_reference` → schema rejection
- `system_inference` + `inference: true` → cannot be verified
- Assumptions remain in `assumptions` output array

---

## Output contract

Schema: `schemas/output.schema.json`

Emits normalized domain arrays, `evidence_inventory`, `assumptions`, `unknowns`, `conflicts`, `clarification_questions`, and **readiness** (not viability verdict).

Readiness values: `ready`, `partially_ready`, `insufficient_context`, `conflicted`.

Required lineage: `skill_id`, `skill_version`, `input_hash`, `output_hash`, `provenance`.

---

## Readiness rules

Deterministic (no numeric confidence thresholds):

| Readiness | Condition |
|-----------|-----------|
| ready | Product identity, business model, customer claim, problem claim, geography/global scope, objective, provenance; no material conflicts |
| partially_ready | Usable for clarification/research with known gaps |
| insufficient_context | Core identity missing |
| conflicted | Material contradictory claims |

---

## Evidence discipline

Uses shared native evidence classes per SKILL-02.0. Verified claims require source references. Assumptions and inferences are never upgraded to verified facts.

---

## Dependencies

**Required:** none  
**Downstream consumers:** listed above (declared_future_dependency in manifest — not runtime triggers)

---

## Limitations

- Non-executable candidate skeleton — no runtime loader
- Does not replace CWF.1 Business Idea Validation
- Frozen `ms.skill.market_validation` v0.1.0 unchanged in SKILL-02.1
- No connector, tool, network, or script permissions

---

## Non-executable status

`activation_conditions.executable: false` · `allowed_tools: []` · `network_policy.default: deny` · `script_policy.enabled: false`

Registry projection: candidate · production_eligible: false

---

## Test coverage

Backend: `tests/test_skill_02_1_product_marketing_context.py` (39 cases)  
Fixtures: 8 input + 5 output under `tests/fixtures/`

---

## Future migration path

- SKILL-02.2+ downstream packages declare `required_dependency` on PMC 0.1.0 with version constraint
- Market Validation 0.2.0 may promote PMC from optional to required dependency (separate accepted phase)
- Runtime execution remains blocked until explicit SKILL-03+ authorization
