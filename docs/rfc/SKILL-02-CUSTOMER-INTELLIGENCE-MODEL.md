# SKILL-02 — Customer Intelligence Model (CIM)

| Field | Value |
|-------|-------|
| **RFC ID** | SKILL-02-CIM |
| **Status** | **Accepted (architecture)** — **shared schema frozen v0.1.0 (SKILL-02.5)** |
| **Owner sign-off** | 2026-07-23 (post SKILL-02.3) |
| **Blocks** | SKILL-02.4 package implementation (spec must exist first) |
| **Frozen in** | SKILL-02.5 — `packages/knowledge/customer_intelligence/0.1.0/` |

---

## Problem

Without a shared customer model, each downstream capability reinvents its own structures:

```
ICP → segments list
Positioning → pains, objections, JTBD (again)
Offer Builder → triggers, barriers (again)
Copywriting / Ads / CRM / SEO → 15 divergent “customer” shapes
```

That duplicates logic, breaks lineage, and makes Positioning a second ICP.

---

## Decision

Introduce **Customer Intelligence Model (CIM)** — one canonical, evidence-aware format for describing **who the customer is, what they need, and how they buy**.

CIM is a **shared knowledge contract**, not a Skill package. Skills **produce** or **consume** CIM documents; they do not define parallel customer schemas.

**Rejected alias:** “Customer Knowledge Model (CKM)” — owner chose **CIM** for clarity with downstream “intelligence” consumption (Positioning, Offer, GTM).

---

## Role in the stack

```
Knowledge (PMC, Research, Competitors, …)
        ↓
Skills (normalize → structured artifacts)
        ↓
Customer Intelligence (CIM)     ← unified customer truth
        ↓
Decision (Market Validation)
        ↓
Execution (Offer, Copy, Ads, …)
        ↓
Evidence + Learning
```

ICP & Segmentation (`ms.skill.icp_segmentation`) is the **primary producer** of CIM in the commercial golden path. Positioning **must consume** CIM — not re-derive JTBD, pains, objections, or segment ranks.

---

## CIM document structure (logical)

Top-level: `CustomerIntelligenceDocument`

| Section | Purpose |
|---------|---------|
| `document_id` | Stable artifact id |
| `skill_id` / `skill_version` | Producer lineage |
| `source_references` | Upstream PMC, Research, Competitor Analysis hashes |
| `segments` | Ranked list of `CustomerSegmentIntelligence` |
| `icp_recommendation` | Optional primary ICP pointer + rationale (not a verdict) |
| `cross_segment_patterns` | Shared pains, triggers, barriers across segments |
| `evidence_gaps` | What is missing for confident GTM |
| `assumptions` / `unknowns` / `conflicts` | Governed uncertainty |
| `research_status` / `evidence_quality` / `coverage` | Same research taxonomy as Market Research / Competitor Analysis |
| `input_hash` / `output_hash` | Lineage |

### CustomerSegmentIntelligence (per segment)

Each segment is a **full intelligence record**, not a label:

| Field group | Fields |
|-------------|--------|
| Identity | `segment_id`, `name`, `rank`, `priority_score`, `fit_rationale` |
| Jobs & outcomes | `jobs_to_be_done[]`, `pain_points[]`, `desired_outcomes[]` |
| Buying motion | `buying_triggers[]`, `buying_barriers[]`, `objections[]`, `decision_makers[]` |
| Economics & urgency | `budget_sensitivity`, `urgency`, `awareness_stage`, `market_sophistication` |
| Trust & channels | `trust_drivers[]`, `channel_preferences[]`, `language` |
| Evidence discipline | `evidence[]`, `assumptions[]`, `unknowns[]`, `conflicts[]` |

Every substantive claim follows **source → observation → inference → confidence** (same discipline as research findings). Verified claims require `source_reference`.

### What CIM is not

- Not a commercial viability **verdict** (`proceed` / `stop`)
- Not **positioning** or **offer** copy
- Not a CRM contact record or ad audience export
- Not a free-text persona paragraph without provenance

---

## Producer / consumer matrix

| Capability | Relationship to CIM |
|------------|---------------------|
| PMC | Supplies product/market claims; may seed audience hints — does not produce CIM |
| Market Research | Supplies demand/customer signals — CIM inputs |
| Competitor Analysis | Supplies competitive pressure context — CIM inputs |
| **ICP & Segmentation** | **Primary CIM producer** (SKILL-02.4) |
| **CIM Freeze** | Shared JSON Schema + enums frozen (SKILL-02.5) |
| Market Validation 0.2 | May consume CIM as evidence input — decision layer |
| Positioning | **Consumer only** — selects/channels CIM, does not recompute JTBD |
| Offer Builder | Consumer — maps offer to CIM triggers/barriers |
| Copywriting / Ads / SEO / CRM | Future consumers — same CIM shape |

---

## Output contract (SKILL-02.4 → 02.5)

**SKILL-02.4 (implemented ✅):**

- `ms.skill.icp_segmentation` v0.1.0 output embeds `customer_intelligence` conforming to CIM draft schema.
- Draft schema location: `packages/skills/ms.skill.icp_segmentation/schemas/customer_intelligence.schema.json`
- Schema `$id`: `ms.skill.icp_segmentation/customer_intelligence/0.1.0-draft`
- Manifest `output_contract_type`: **`research`**
- Package hash: `075a4f1989a9050614babec004dda54a420d7f7bd717d9ac7e8a34b41e8ae71a`
- Freeze audit: [SKILL-02.4-icp-segmentation-freeze-audit.md](SKILL-02.4-icp-segmentation-freeze-audit.md)

**SKILL-02.5 (frozen ✅):**

- Canonical bundle: `packages/knowledge/customer_intelligence/0.1.0/`
- Canonical URI: `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/`
- Bundle hash: `b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea`
- ICP 0.1.0 preserved unchanged; `normalize_icp_local_cim()` for shared validation
- Freeze audit: [SKILL-02.5-CIM-SHARED-SCHEMA-FREEZE.md](SKILL-02.5-CIM-SHARED-SCHEMA-FREEZE.md)

**SKILL-02.6 (next):**

- Extract `schemas/customer_intelligence.schema.json` to shared location (TBD: `packages/knowledge/` or `app/schemas/cim/` — decided at freeze, not before 02.4 draft).
- Freeze segment enums, evidence rules, and cross-skill `$ref` strategy.
- Regression: ICP fixtures + downstream consumer fixture tests (Positioning stub).

---

## Implementation status

| Step | Status |
|------|--------|
| CIM architecture RFC | ✅ Accepted |
| SKILL-02.4 ICP package with draft CIM schema | ✅ Frozen candidate |
| SKILL-02.5 shared schema promotion | ✅ Frozen v0.1.0 |
| SKILL-02.6 Market Validation 0.2.0 | Planned |

---

## Related

- [SKILL-02-MARKET-KNOWLEDGE-GRAPH.md](SKILL-02-MARKET-KNOWLEDGE-GRAPH.md) — logical aggregation of CIM with other entities
- [SKILL-02-KNOWLEDGE-CORE-VISION.md](SKILL-02-KNOWLEDGE-CORE-VISION.md) — post–SKILL-02 program direction
- [SKILL-02-OUTPUT-CONTRACT-TAXONOMY.md](SKILL-02-OUTPUT-CONTRACT-TAXONOMY.md)
