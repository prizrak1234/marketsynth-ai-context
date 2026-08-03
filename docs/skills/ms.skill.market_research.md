# ms.skill.market_research

**Status:** candidate · non-executable · frozen 0.1.0 (SKILL-02.2)  
**Output contract:** `research`  
**Architecture:** [SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md](../rfc/SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md)

---

## Purpose

Consume normalized **Product Marketing Context**, define research questions, structure available market evidence, detect gaps, and prepare an evidence-aware research output for downstream Skills.

Does **not** issue commercial verdicts, autonomously search the web, or invoke connectors.

---

## Package identity

| Field | Value |
|-------|-------|
| skill_id | `ms.skill.market_research` |
| version | `0.1.0` |
| output_contract_type | `research` |
| status | candidate |
| package_hash | `6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e` |

---

## Dependency

**Required:** `ms.skill.product_marketing_context` (methodology/data)  
**Downstream:** `ms.skill.competitor_analysis`

---

## Research finding model

Source → Observation → Inference → Confidence

Schema: `schemas/research_finding.schema.json`

Each finding includes: `claim`, `observation`, `source_reference`, `source_type`, `verification_status`, `confidence`, `inference`, `limitations`.

---

## Output discriminators

| Field | Values |
|-------|--------|
| research_status | complete, partially_complete, insufficient_sources, conflicted, out_of_scope |
| evidence_quality | comprehensive, partial, insufficient, conflicted, unknown |
| coverage | full, partial, minimal, unknown |
| evidence_gaps | array of gap descriptions |

**Forbidden:** `verdict`, `readiness`, proceed/stop/viable/unviable

---

## Non-executable status

No tools · network deny · scripts disabled · production_eligible: false

---

## Tests

`tests/test_skill_02_2_market_research.py` — 28 cases
