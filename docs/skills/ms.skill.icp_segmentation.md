# ms.skill.icp_segmentation

**Status:** candidate · non-executable · frozen 0.1.0 (SKILL-02.4)  
**Architecture:** [SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md](../rfc/SKILL-02-NATIVE-SKILL-SET-ARCHITECTURE.md)

---

## Purpose

Transform **Product Marketing Context 0.2.x**, **Market Research 0.1.x**, and **Competitor Analysis 0.1.x** outputs into an evidence-aware **Customer Intelligence Document (CIM)** with ranked segments and ICP candidates — without positioning, offers, commercial verdicts, or web research.

**Positioning is a CIM consumer, not a second segmentation engine.**

---

## Package identity

| Field | Value |
|-------|-------|
| skill_id | `ms.skill.icp_segmentation` |
| version | `0.1.0` |
| output_contract_type | `research` |
| status | candidate |
| executable | false |
| package_hash | `075a4f1989a9050614babec004dda54a420d7f7bd717d9ac7e8a34b41e8ae71a` |
| path | `packages/skills/ms.skill.icp_segmentation/` |

---

## Dependencies

| Upstream | Constraint | Relationship |
|----------|------------|--------------|
| `ms.skill.product_marketing_context` | `>=0.2.0,<1.0.0` | required (0.1.0 **not** compatible) |
| `ms.skill.market_research` | `>=0.1.0,<1.0.0` | required |
| `ms.skill.competitor_analysis` | `>=0.1.0,<1.0.0` | required |

Methodology/data only — no runtime orchestration. Upstream hashes, evidence refs, unknowns, and conflicts preserved.

---

## CIM role

Primary payload: `customer_intelligence` field containing `CustomerIntelligenceDocument`.

- **Package-local schema (frozen 0.1.0):** `schemas/customer_intelligence.schema.json` with `cim_version: 0.1.0-draft`
- **Canonical shared contract (SKILL-02.5):** `packages/knowledge/customer_intelligence/0.1.0/` with `cim_version: 0.1.0`
- **Canonical URI base:** `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/`
- **Compatibility mapping:** `icp-local-compatibility.json` — local draft normalizes to shared 0.1.0 for validation

ICP 0.1.0 package bytes remain unchanged; shared CIM is the authoritative contract for downstream Skills.

CIM includes ranked segments, ICP candidates, JTBD, pains, outcomes, triggers, barriers, objections, decision roles, trust drivers, conflicts, unknowns, and **readiness** (not a commercial verdict).

---

## Input contract

Requires dependency references for PMC, Market Research, and Competitor Analysis with `source_skill_id`, `source_skill_version`, `source_output_hash`.

Optional: segmentation objectives, candidate segments, customer data, interview/survey/behavioral/transaction/channel evidence, scope, geography, constraints.

---

## Segment record

Finite segment types: `behavioral`, `demographic`, `firmographic`, `geographic`, `psychographic`, `needs_based`, `value_based`, `lifecycle`, `channel_based`, `hybrid`, `unknown`.

Each segment includes boundaries, JTBD, customer claims, decision roles, priority assessment with explainable dimensions and `tier_rationale`.

---

## JTBD model

Structured jobs with situation, motivation, functional/emotional/social dimensions, switching triggers, success criteria. Verified only with evidence or explicit user statement.

---

## Pain/outcome/trigger/barrier model

Unified `customer_claim` records with `claim_kind`: pain_point, desired_outcome, buying_trigger, buying_barrier, objection, trust_driver.

Verified claims require `evidence_references`. Inferences cannot be verified by default.

---

## Decision roles

Finite role types including user, initiator, influencer, evaluator, decision_maker, buyer, approver, blocker, champion, unknown. Supports consolidated B2C roles.

---

## Priority assessment

Multi-dimension model: strategic_fit, problem_intensity, demand_signal_strength, evidence_quality, budget_fit, urgency, reachability, competitive_pressure, switching_difficulty, and more.

Aggregate `priority_tier` requires `tier_rationale` — no single opaque score as sole output.

---

## Output contract

`output_contract_type: research` — required discriminators: `research_status`, `evidence_quality`, `coverage`, `evidence_gaps`.

Forbidden: `verdict`, `positioning`, `final_offer`, `execution_status`, `proceed`, `stop`, `viable`, `unviable`.

---

## Evidence discipline

Separate claim, evidence, inference, assumption, unknown, and conflict layers. Upstream evidence preserved in output references.

---

## CIM readiness

Inside CIM only (not a viability verdict): `ready_for_downstream_use`, `partially_ready`, `insufficient_customer_evidence`, `conflicted`, `out_of_scope`.

---

## Downstream consumers

| Consumer | Consumes | Must not recompute |
|----------|----------|-------------------|
| `ms.skill.positioning` (02.7) | ICP, segments, JTBD, pains, objections, trust drivers | Customer intelligence fields |
| `ms.skill.market_validation` 0.2.0 (02.6) | Priority, demand signals, evidence quality, blockers | Final verdict (MV issues it) |
| Offer Builder, Content, SEO, CRM (future) | CIM fields per consumer contract | Parallel customer models |

---

## MKG mapping (logical only — no persistence)

| CIM entity | MKG entity |
|------------|------------|
| CustomerIntelligenceDocument | customer_intelligence |
| CustomerSegment | segment |
| JobToBeDone | job |
| PainPoint | pain |
| DesiredOutcome | outcome |
| BuyingTrigger | trigger |
| BuyingBarrier | barrier |
| Objection | objection |
| DecisionRole | decision_role |
| TrustDriver | trust_driver |
| EvidenceReference | evidence |
| CompetitorOverlap | competitor_relationship |

Relations: `segment HAS_JOB job`, `segment HAS_PAIN pain`, `segment SEEKS_OUTCOME outcome`, `claim SUPPORTED_BY evidence`, etc.

---

## Limitations

- Non-executable skeleton — no runtime loader.
- Package-local CIM schema frozen at 0.1.0-draft; canonical shared CIM 0.1.0 promoted in SKILL-02.5.
- No autonomous web research, connectors, CRM writes, or graph DB.

---

## Non-executable status

`executable: false`, `allowed_tools: []`, `network: deny`, `scripts: disabled`.

---

## Test coverage

`tests/test_skill_02_4_icp_segmentation.py` — 56 cases including schema, fixtures, registry, audit, lineage, consumer stubs, frozen hash regression.
