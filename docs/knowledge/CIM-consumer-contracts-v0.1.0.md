# CIM Consumer Contracts v0.1.0

**Canonical CIM:** `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/customer-intelligence.schema.json`

Downstream Skills **consume** CIM — they do not redefine customer intelligence fields.

Fixtures: `packages/knowledge/customer_intelligence/0.1.0/consumers/`

---

## Required consumer reference

Every consumer must declare:

| Field | Purpose |
|-------|---------|
| `cim_schema_uri` | Canonical shared schema URI |
| `cim_version` | Supported CIM version (`0.1.0`) |
| `cim_document_hash` | Lineage to producer output |
| `source_skill_id` | Primary producer (`ms.skill.icp_segmentation`) |
| `selected_segment_ids` | Explicit segment scope |

Optional but recommended: `evidence_references`, `unknowns`, `conflicts`.

---

## Positioning (`ms.skill.positioning`) — **0.1.0 frozen (SKILL-02.7)**

**May derive:** positioning hypotheses, territories, value framing, differentiation framing, message hierarchy, downstream offer inputs.

**Must not recompute:** segment boundaries, JTBD, pains, objections, decision roles, buying triggers, trust drivers, awareness stage, market sophistication.

**Must preserve:** MV verdict (`market_validation_verdict_consumed`), inherited blockers and conditions.

**Must not emit:** `verdict`, `final_offer`, `campaign`, `execution_status`, `approval_granted`.

Package: `packages/skills/ms.skill.positioning/` · Regression: `tests/test_skill_02_7_positioning.py`

---

## Offer Builder (`ms.skill.offer_builder`)

**May consume:** segment priorities, pains, outcomes, objections, triggers, barriers, budget sensitivity, proof requirements, decision roles, trust drivers.

**Must not redefine** customer model fields.

---

## Content Strategy / Copywriting

**May consume:** selected segment IDs, awareness stage, sophistication, pains, outcomes, objections, trust drivers, channel/content preferences.

**Must not** silently broaden audience beyond declared CIM segments.

---

## CRM handoff (future)

**May map** segments to qualification fields, decision roles, objections, urgency, budget sensitivity, buying stage.

**Must not** add personal customer records to shared CIM. CIM describes segment intelligence, not individual leads.

---

## Advertising planning (future)

**May consume:** channel preferences, awareness stage, pains, budget sensitivity for audience planning within declared segments.

---

## Market Validation 0.2.0 (`ms.skill.market_validation`)

**May consume:** primary ICP candidates, priority assessment, demand signals, evidence quality, reachability, budget fit, competitive pressure, switching difficulty, blockers, unknowns, conflicts.

**Retains** viability verdict responsibility — CIM does not issue `verdict`, `viable`, or `unviable`.

---

## Invariant

> Positioning is a CIM consumer, not a segmentation engine.
