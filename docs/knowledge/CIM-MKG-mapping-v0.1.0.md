# CIM ↔ MKG Mapping v0.1.0

**Status:** frozen (logical only)  
**CIM schema version:** 0.1.0  
**MKG RFC:** [SKILL-02-MARKET-KNOWLEDGE-GRAPH.md](../rfc/SKILL-02-MARKET-KNOWLEDGE-GRAPH.md)

No graph database, persistence, or runtime traversal in SKILL-02.5.

---

## Entity mappings

| CIM entity | MKG entity | Notes |
|------------|------------|-------|
| CustomerIntelligenceDocument | customer_intelligence | Root artifact |
| CustomerSegment | segment | Ranked segment record |
| JobToBeDone | job | Functional/emotional/social job |
| PainPoint (customer_claim) | pain | Via `claim_kind=pain_point` |
| DesiredOutcome (customer_claim) | outcome | Via `claim_kind=desired_outcome` |
| BuyingTrigger (customer_claim) | trigger | Via `claim_kind=buying_trigger` |
| BuyingBarrier (customer_claim) | barrier | Via `claim_kind=buying_barrier` |
| Objection (customer_claim) | objection | Via `claim_kind=objection` |
| DecisionRole | decision_role | Buying process role |
| TrustDriver (customer_claim) | trust_driver | Via `claim_kind=trust_driver` |
| EvidenceReference | evidence | From evidence_inventory / claim refs |
| CompetitorOverlap | competitor_relationship | Segment ↔ competitor linkage |

---

## Relation patterns (logical)

```
customer_intelligence HAS_SEGMENT segment
segment HAS_JOB job
segment HAS_PAIN pain
segment SEEKS_OUTCOME outcome
segment TRIGGERED_BY trigger
segment BLOCKED_BY barrier
segment HAS_OBJECTION objection
decision_role INFLUENCES segment_buying_process
segment TRUSTS trust_driver
segment OVERLAPS_WITH competitor_relationship
claim SUPPORTED_BY evidence
customer_intelligence SUPPORTED_BY evidence
```

Direction and naming frozen for Knowledge Core program; implementation deferred post SKILL-02.9.

---

## Lineage

All MKG views reference immutable Skill outputs by:

- `source_skill_id` / `source_skill_version`
- `source_output_hash`
- `evidence_references[]`

Primary CIM producer: `ms.skill.icp_segmentation` v0.1.0.

---

## Non-goals

- Neo4j / graph DB
- Vector store
- Automatic entity merge
- CRM contact records
