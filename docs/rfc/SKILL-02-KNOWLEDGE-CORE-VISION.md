# SKILL-02 — Knowledge Core Vision (post–native Skills)

| Field | Value |
|-------|-------|
| **Status** | Directional — owner alignment 2026-07-23 |
| **Timing** | After SKILL-02.9 freeze; **before** executable Skill runtime |
| **Does not authorize** | Implementation in current SKILL-02 packages |

---

## Thesis

Most AI marketing tools stack:

```
Prompt → LLM → Answer
```

Marketsynth is forming an **agency operating system**:

```
Knowledge → Skills → Decision → Execution → Evidence → Learning
```

**Skills are one layer**, not the product. Shared **Knowledge Core** (CIM, MKG, Evidence registry) is what prevents duplication when HR, Legal, Sales, Finance, and GTM modules arrive.

---

## Layers

| Layer | Role | SKILL-02 status |
|-------|------|-----------------|
| **Knowledge** | Immutable artifacts, schemas, lineage (PMC, Research, CIM, …) | In progress via native packages |
| **Skills** | Methodology operators over knowledge (non-executable in 02.x) | 02.0–02.3 ✅ |
| **Decision** | Verdicts with evidence snapshots (Market Validation) | MV 0.1.0 frozen; 0.2.0 → 02.6 |
| **Execution** | Offer, copy, ads, publish (future + connectors) | Blocked until SKILL-03+ |
| **Evidence** | Source → claim → confidence chain | Embedded in every artifact |
| **Learning** | Gap detection, re-research triggers (future) | Not SKILL-02 |

---

## Why before runtime

Once Skills execute and persist outputs, retro-fitting a unified customer model requires migration, dual schemas, and broken lineage. **CIM freeze (02.5) and MKG logical model now** keep the architecture holdable while packages are still non-executable contracts.

---

## Recommended program sequence (owner-aligned)

```
SKILL-02.4  ICP & Segmentation          → produces CIM-shaped output
SKILL-02.5  CIM Freeze                  → shared schema, no duplicate customer models
SKILL-02.6  Market Validation 0.2       → consumes CIM + golden path deps
SKILL-02.7  Positioning                 → consumer-only of CIM
SKILL-02.8  Offer Builder
SKILL-02.9  Native Skills Freeze
     ↓
Knowledge Core RFC (MKG persistence, cross-domain entities)
     ↓
SKILL-03    Connector Runtime
```

**Skill Discovery** (RFC-SKILL-004) remains a **parallel read-only track** — not renumbered into 02.5; see [SKILL-ROADMAP.md](SKILL-ROADMAP.md).

**KB-SKILL-01** (2026-07-23) adds external artifact schemas, quarantined workflow catalog metadata, and five candidate engineering/content Skills — see [KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md](KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md). Future persistence: KB-02–KB-06 in [SKILL-ROADMAP.md](SKILL-ROADMAP.md).

**KB-WPL-01.5** (2026-07-23) adds `ms.skill.knowledge_linking` — non-executable metadata linking layer over Skills, Patterns, Practices, RFCs, and indexes. See [KB-WPL-01.5-KNOWLEDGE-LINKING-SKILL.md](KB-WPL-01.5-KNOWLEDGE-LINKING-SKILL.md).

**KB-WPL-01.8** (2026-07-24) adds deterministic read-only discovery read models over the frozen Profession/Capability/Skill/Pattern hierarchy — see [KB-WPL-01.8-KNOWLEDGE-DISCOVERY-READ-MODELS.md](KB-WPL-01.8-KNOWLEDGE-DISCOVERY-READ-MODELS.md). No persistence, vector search, or Skill Generator in this phase.

**KB-WPL-01.9** (2026-07-24) closes the KB-WPL-01 program with integrated freeze audit — see [KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md](KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md). Program status: `frozen_read_only_knowledge_program`.

---

## Related

- [SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md](SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md)
- [SKILL-02-MARKET-KNOWLEDGE-GRAPH.md](SKILL-02-MARKET-KNOWLEDGE-GRAPH.md)
- [PROJECT_VISION.md](../PROJECT_VISION.md)
