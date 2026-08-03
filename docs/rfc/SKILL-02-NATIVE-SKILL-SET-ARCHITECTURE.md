# SKILL-02 — Native Skill Set Architecture

| Field | Value |
|-------|-------|
| **Status** | Accepted (2026-07-23) |
| **Owner sign-off** | SKILL-01 Foundation CONDITIONALLY READY approved; SKILL-02.0 scope accepted |
| **Governs** | SKILL-02.1–02.9 native package phases |
| **Does not authorize** | Runtime execution, Discovery, Draft Generation (RFC-SKILL-004 Draft) |

---

## 1. Purpose

Define the coherent **platform-native Skill family** for the Marketsynth commercial workflow before creating additional packages. Native Skills are **methodology and contract artifacts** — not runtime operators in SKILL-02.

Foundation reference: [SKILL-01-FOUNDATION-FREEZE-AUDIT.md](SKILL-01-FOUNDATION-FREEZE-AUDIT.md) · [SKILL-01-FREEZE-MANIFEST.md](SKILL-01-FREEZE-MANIFEST.md).

---

## 2. Native Skill family (canonical IDs)

| skill_id | Name | Phase |
|----------|------|-------|
| `ms.skill.product_marketing_context` | Product Marketing Context | SKILL-02.1 |
| `ms.skill.market_research` | Market Research | SKILL-02.2 |
| `ms.skill.competitor_analysis` | Competitor Analysis | SKILL-02.3 |
| `ms.skill.icp_segmentation` | ICP & Segmentation | SKILL-02.4 |
| `ms.skill.market_validation` | Market Validation | Frozen 0.1.0 (SKILL-01.0); 0.2.0 → 02.6 |
| `ms.skill.positioning` | Positioning | SKILL-02.7 |
| `ms.skill.offer_builder` | Offer Builder | SKILL-02.8 |

**Optional later (not in SKILL-02.0 scope):** `ms.skill.pricing`, `ms.skill.launch_strategy`, `ms.skill.cro_audit`, `ms.skill.copywriting`, `ms.skill.seo_audit`, `ms.skill.content_strategy`.

---

## 3. Dependency graph

Methodology and **data dependencies** — not runtime execution order.

```
ms.skill.product_marketing_context
        ↓
ms.skill.market_research
        ↓
ms.skill.competitor_analysis
        ↓
ms.skill.icp_segmentation          → produces Customer Intelligence (CIM)
        ↓
[Customer Intelligence Model]      → SKILL-02.5 shared schema freeze
        ↓
ms.skill.market_validation (0.2+)
        ↓
ms.skill.positioning               → consumes CIM; no JTBD/pain recompute
        ↓
ms.skill.offer_builder
```

Logical aggregation over all artifacts: [Market Knowledge Graph (logical)](SKILL-02-MARKET-KNOWLEDGE-GRAPH.md) — not implemented in SKILL-02 packages.

### Relationship terms (RFC-SKILL-002)

| Term | Meaning |
|------|---------|
| `required_dependency` | Downstream Skill cannot produce valid output without accepted upstream output version |
| `optional_dependency` | Downstream may proceed with partial context; gaps must be explicit |
| `declared_future_dependency` | Planned link; unresolved in current package version |
| `unresolved_dependency` | Identity known; compatibility not yet verified |
| `compatibility_constraint` | Declared accepted upstream semver range on manifest |
| `version_constraint` | Exact or minimum upstream package version |

**Frozen note:** `ms.skill.market_validation` v0.1.0 lists `product_marketing_context` as `optional_dependency`. Migration to `required_dependency` + CIM consumption requires **Market Validation 0.2.0** (SKILL-02.6), not silent manifest edit.

---

## 3.1 Customer Intelligence Model (CIM)

Shared customer truth — **not** owned by any single Skill package.

| Rule | Detail |
|------|--------|
| Producer | `ms.skill.icp_segmentation` (primary) |
| Consumers | Positioning, Offer Builder, Copy, Ads, CRM, SEO — same schema |
| Freeze | SKILL-02.5 — extract + freeze JSON Schema |
| Spec | [SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md](SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md) |

Positioning **must not** re-derive pains, JTBD, objections, or segment ranks. It selects and channels existing Customer Intelligence.

---

## 4. Shared context contract — ProductMarketingContext

Conceptual aggregate consumed/produced across native Skills. **Not free-text only** — structured claims with provenance.

### Domains

| Domain | Description |
|--------|-------------|
| product identity | Name, type, description, stage |
| business model | Revenue model, pricing model claims |
| customer segments | Target customer claims (pre-ICP) |
| geography | Market scope |
| market category | Category/industry framing |
| problem statement | Problems addressed |
| value proposition assumptions | Value claims (not verified positioning) |
| pricing assumptions | Price/packaging claims |
| competitors | Named competitor claims |
| channels | Go-to-market channel claims |
| brand constraints | Voice, tone, taboo topics |
| business constraints | Budget, timeline, operational limits |
| available evidence | Inventory of cited material |
| unknowns | Explicit gaps |
| provenance | Source Skill / user / document lineage |

### Epistemic classification

Every claim MUST be classified as one of:

| Class | Description |
|-------|-------------|
| user-provided fact | Stated by user; unverified until sourced |
| user assumption | Explicitly labeled assumption |
| external evidence | Cited external source |
| inference | Derived; never default-verified |
| unknown | Deliberately unset |
| conflict | Contradictory claims coexisting |

---

## 5. Output compatibility rules

When Skill A output feeds Skill B input (contract-only in SKILL-02):

1. `skill_id` and `skill_version` of source preserved in provenance.
2. Source `output_hash` preserved in dependency reference metadata.
3. Evidence references preserved by ID — not dropped or rewritten.
4. Assumptions remain assumptions; inferences remain inferences.
5. Conflicts remain visible in output — not silently resolved.
6. Unknowns are not silently filled by downstream Skills.
7. Downstream Skill cannot upgrade inference to verified fact without new evidence.
8. Dependency output is **immutable** — consumers copy/reference, never mutate upstream artifact.
9. Each consuming Skill declares **accepted upstream versions** in manifest dependencies.

No runtime composition engine in SKILL-02.

---

## 6. Shared evidence discipline

### Evidence classes (manifest + schema)

Domain enum (SKILL-01.1): `user_statement`, `market_source`, `competitor_source`, `demand_signal`, `pricing_signal`, `audience_signal`, `assumption`, `inference`.

Package schemas additionally model **`unknown`** and **`conflict`** as first-class output states (readiness/claim groups) pending domain enum extension.

### Minimum evidence metadata

| Field | Required |
|-------|----------|
| evidence_type | yes |
| source_reference | yes for verified claims |
| claim | yes |
| verification_status | yes |
| confidence | yes |
| collected_at | when available |
| provenance | yes |
| tenant_id | when tenant-scoped |
| project_id | when project-scoped |

**Rule:** No Skill may mark evidence as verified without `source_reference`.

---

## 7. Shared verdict discipline

| Skill | Issues commercial verdict? |
|-------|---------------------------|
| Product Marketing Context | **No** — readiness only |
| Market Research | No — evidence summary + gaps |
| Competitor Analysis | No — pressure/differentiation report |
| ICP & Segmentation | No — segment ranking |
| Market Validation | **Yes** — viability verdict |
| Positioning | No — positioning options |
| Offer Builder | No — offer candidates |

No Skill may output unsupported profitability guarantees.

---

## 8. Shared package rules (SKILL-02)

Every native package:

| Rule | Value |
|------|-------|
| `source` | `platform_native` |
| `output_contract_type` | `context` \| `research` \| `decision` (see taxonomy) |
| `tenant_scope` | `global` |
| `status` | `candidate` |
| `allowed_tools` | `[]` |
| `network_policy.default` | `deny` |
| `script_policy.enabled` | `false` |
| `activation_conditions.executable` | `false` |
| Initial version | `0.1.0` |
| Schemas | input + output JSON Schema Draft 2020-12 |
| Validation | SKILL-01.2 production validator |
| Output contract | [SKILL-02-OUTPUT-CONTRACT-TAXONOMY.md](SKILL-02-OUTPUT-CONTRACT-TAXONOMY.md) |
| Projection | SKILL-01.3 registry read model |
| Audit/lineage | SKILL-01.6 / 01.7 in-memory only |

---

## 9. Versioning policy

- Package versions are **immutable** once frozen.
- Schema-breaking change → **major** version bump.
- Additive compatible schema change → **minor** bump.
- Documentation-only fix → **patch** bump.
- Dependency constraints use semver ranges in manifest notes.
- **Frozen** `ms.skill.market_validation` 0.1.0 is not silently modified.
- Compatibility migration → new version (0.2.0 or 1.0.0 per impact).
- **Transitional filesystem layout:** legacy frozen semver at package root; newer semver in nested directories — see [SKILL-02-transitional-version-layout.md](SKILL-02-transitional-version-layout.md). Root is never “latest”.

---

## 10. Quality gates (pre-freeze per package)

1. Manifest validation passes (SKILL-01.2).
2. Input/output schemas validate fixtures.
3. Package hash deterministic.
4. Registry projection valid; status remains `candidate`.
5. Production eligibility **false**.
6. Audit report has no blocker.
7. Lineage graph valid in-memory.
8. No tools / network / scripts.
9. Evidence discipline tested in package tests.
10. Eval manifest cases pass.

No package becomes `active` in SKILL-02.

---

## 11. Non-goals (SKILL-02 program)

Runtime orchestration, Skill composition engine, automatic routing, external tools, Connector access, persistence, API, UI, tenant-private packages, Discovery Engine, Draft Generator, activation, CWF.1 migration.

---

## 12. Related documents

- [SKILL-02-native-skill-matrix.md](../skills/SKILL-02-native-skill-matrix.md)
- [ms.skill.product_marketing_context.md](../skills/ms.skill.product_marketing_context.md)
- [SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md](SKILL-02-CUSTOMER-INTELLIGENCE-MODEL.md)
- [SKILL-02-MARKET-KNOWLEDGE-GRAPH.md](SKILL-02-MARKET-KNOWLEDGE-GRAPH.md)
- [SKILL-02-KNOWLEDGE-CORE-VISION.md](SKILL-02-KNOWLEDGE-CORE-VISION.md)
- [SKILL-ROADMAP.md](SKILL-ROADMAP.md)
