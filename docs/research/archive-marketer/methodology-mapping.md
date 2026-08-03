# Methodology Mapping — Archive → Marketsynth Skills

**Program:** ARCHIVE-MKT-01.0

---

## Master mapping

| Archive section | Source file | Target Skill / artifact | Relationship |
|-----------------|-------------|-------------------------|--------------|
| Сбор информации о сегменте | File 1 | `ms.skill.customer_interview_design` | Produces interview guide; feeds CIM evidence |
| Soc-dem placeholders | File 1 | CIM segment context (existing) | Reference only — ICP/CIM owns segments |
| Pain / desire / transformation questions | File 1 | Interview question domains | ADAPT with bias/sensitivity tags |
| Fear taxonomy | File 1 | Meaning Extraction fear categories | Shared taxonomy |
| Распаковка смыслов — desires | File 2 | `ms.skill.customer_meaning_extraction` | `customer_meaning` (type: desire) |
| Satisfaction table | File 2 | `desire-to-benefit-map` | supported / partial / unsupported |
| Promise formulations | File 2 | `promise-candidate` (shared schema) | Not approved copy |
| Fear / objection table | File 2 | `fear-objection-map` | proof requirement linkage |
| Упаковка — 5 inputs | File 3 | Offer Builder models | offer_promise, mechanism, time_to_value |
| Thesis structure | File 3 | `offer_candidate.offer_promise` | Requires substantiation |
| Обоснование — segment + 3 desires | File 4 | Offer Builder | segment fit block |
| Step delivery (5 steps) | File 4 | `delivery_mechanism.process_steps` | intermediate outcomes |
| Why it works | File 4 | Claim Substantiation | mechanism + proof validation |
| Service block | File 4 | `service_advantages` | service_expectation linkage |
| Safety block | File 4 | `risk_reversal` + Claim Substantiation | **not** outcome proof |
| Price justification | File 4 | `price_justification` | evidence or assumption |
| Product decomposition | File 4 | `product_components` | benefit language |
| Upsell / cross-sell / bundle | File 4 | `bundle_candidates` etc. | exploratory candidates |

---

## Pipeline placement

```
ms.skill.product_marketing_context
        ↓
ms.skill.market_research
        ↓
ms.skill.competitor_analysis
        ↓
ms.skill.icp_segmentation → CIM 0.1.x
        ↓
ms.skill.customer_interview_design     ← File 1
        ↓ (interview evidence as user_statement)
ms.skill.customer_meaning_extraction ← File 2
        ↓
ms.skill.market_validation 0.2.x
        ↓
ms.skill.positioning 0.1.x             ← frozen
        ↓
ms.skill.claim_substantiation          ← Files 2–4 promise safety
        ↓
ms.skill.offer_builder                 ← Files 3–4
        ↓
Content / Copy / Launch (future)
```

---

## Shared contracts (01.1)

| Archive concept | Shared schema |
|-----------------|---------------|
| Marketing promise / claim | `marketing-claim.schema.json` |
| Promise from desire | `promise-candidate.schema.json` |
| Proof need | `proof-requirement.schema.json` |
| Evidence link | `claim-evidence-link.schema.json` |
| Risk reversal | `risk-reversal.schema.json` |
| Guarantee proposal | `guarantee-proposal.schema.json` |
| Price justification | `price-justification.schema.json` |
| Compliance finding | `claim-compliance-finding.schema.json` |

---

## CIM boundary

| Archive field | CIM owner | New Skill rule |
|---------------|-----------|----------------|
| Segment boundaries | ICP / CIM | Interview Design references only |
| Pain points | CIM | Meaning Extraction deepens language, no new pain IDs without evidence |
| JTBD | CIM | No recompute |
| Objections | CIM | Fear map references CIM objection IDs |
| Trust drivers | CIM | trust_requirement references CIM |

---

## Positioning boundary (frozen 0.1.0)

Positioning consumes CIM + CA + MV. Meaning Extraction **feeds** positioning inputs but does not replace Positioning. Claim Substantiation gates claims **after** positioning hypotheses exist.

---

## Offer boundary

Offer Builder consumes substantiated claims only. Archive «готовый оффер» examples are **structural templates**, not publishable copy.
