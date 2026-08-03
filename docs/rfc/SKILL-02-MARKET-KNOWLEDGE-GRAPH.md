# SKILL-02 — Market Knowledge Graph (logical model)

| Field | Value |
|-------|-------|
| **RFC ID** | SKILL-02-MKG |
| **Status** | **Accepted (architecture sketch)** — not a database, not SKILL-02 implementation |
| **Owner sign-off** | 2026-07-23 |
| **Implementation** | Post–SKILL-02 Knowledge Core program; no graph DB in native Skill phase |

---

## Problem

Native Skills already produce structured artifacts (PMC, research findings, competitors, soon CIM). Without a **logical** aggregation model, each new module (HR, Legal, Sales, Finance) will invent its own entity graph.

---

## Decision

Define **Market Knowledge Graph (MKG)** as a **logical domain model** — how marketing knowledge entities relate — not Neo4j, not a runtime graph query engine in SKILL-02.

MKG answers: *what entity types exist, what references what, and how lineage flows*.

---

## Entity types (initial)

| Entity | Typical source Skill / layer | Notes |
|--------|------------------------------|-------|
| `Product` | PMC | What we sell |
| `Market` | Market Research | Scope, structure, signals |
| `Segment` | ICP → **CIM** | Ranked customer intelligence |
| `Competitor` | Competitor Analysis | Typed competitor records |
| `Channel` | Research, Competitor, ICP | Distribution / preference |
| `Offer` | Offer Builder (future) | Packaging, not copy |
| `Claim` | All layers | Atomic evidenced statement |
| `Evidence` | All layers | Source-linked support |
| `ResearchArtifact` | Research, Competitor, ICP | Versioned Skill outputs |
| `Audience` | CIM segment alias | Same as Segment in v1 |
| `PricingSignal` | Research, Competitor | Observed price points |
| `PositioningHypothesis` | Positioning (future) | **Consumes CIM** — does not recreate segment model |
| `DifferentiationGap` | Competitor Analysis | Input to Positioning via CIM + gaps |

Future extensions (explicitly out of SKILL-02): `Campaign`, `Asset`, `LegalConstraint`, `HiringProfile`, `FinancialScenario`.

---

## Relationship patterns (logical)

```
Product ──operates_in──▶ Market
Market ──has_signal──▶ Claim ──supported_by──▶ Evidence
Competitor ──competes_in──▶ Market
Competitor ──targets──▶ Segment
Segment ──defined_by──▶ CustomerIntelligence (CIM)
ResearchArtifact ──feeds──▶ Segment
DifferentiationGap ──informs──▶ PositioningHypothesis
PositioningHypothesis ──constrains──▶ Offer
```

References are **by identity + hash**, not mutable pointers:

- `entity_id`
- `source_skill_id` / `source_skill_version`
- `source_output_hash`
- `evidence_references[]`

Immutable Skill outputs remain SoT; MKG is a **view** over frozen artifacts.

---

## MKG vs CIM

| | CIM | MKG |
|---|-----|-----|
| Scope | Customer / buyer intelligence only | Full marketing knowledge ontology |
| Freeze | SKILL-02.5 | Knowledge Core program (post 02.9) |
| Format | JSON Schema document | Logical model + future registry |
| SKILL-02 work | ICP produces CIM ✅ (02.4) | Document only — no persistence |

**SKILL-02.4 entity mappings** (documented in [ms.skill.icp_segmentation.md](../skills/ms.skill.icp_segmentation.md#mkg-mapping-logical-only--no-persistence)): `CustomerIntelligenceDocument → customer_intelligence`, `CustomerSegment → segment`, `JobToBeDone → job`, `PainPoint → pain`, relations `segment HAS_JOB job`, `segment HAS_PAIN pain`, `claim SUPPORTED_BY evidence`.

---

## Non-goals (SKILL-02)

- Graph database or vector store
- Runtime graph traversal API
- Automatic entity merge/dedup across tenants
- UI graph visualization

---

## Path to Knowledge Core

After **SKILL-02.9 Native Skills Freeze**, the next major program is **Knowledge Core** design: MKG + CIM + Evidence registry as the shared foundation before executable runtime. See [SKILL-02-KNOWLEDGE-CORE-VISION.md](SKILL-02-KNOWLEDGE-CORE-VISION.md).

---

## Related

- [SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md](SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md)
- [SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md](SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md)
