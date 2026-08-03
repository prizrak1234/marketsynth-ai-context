# Architecture Volume — Knowledge Governance

**Volume ID:** ARCH-KG-VOL-1  
**ADR:** [adr_knowledge_governance.md](adr_knowledge_governance.md)  
**Subsystem Standard:** [marketsynth_subsystem_standard.md](marketsynth_subsystem_standard.md)

## 1. Domain boundary

**In scope**

- Knowledge Object lifecycle and metadata governance
- Semantic Chunk structure
- Benchmark Dataset contracts
- Validation pipeline (Candidate → Human Review → Validation → Publication)
- Citation Contract for agent answers
- Freshness / review scheduling policy
- Governance Manifest as publication SoT

**Out of scope (this volume)**

- Vector indexes, embedding jobs, hybrid search implementation
- LLM prompt execution for retrieval or ranking
- Automatic unattended publication without human review

**Relationship to Knowledge Foundation (H2.1–H2.5)**

| Foundation piece | Governance role |
|------------------|-----------------|
| `KnowledgeItem` / `StoredKnowledgeItem` | Inventory + durable body |
| `KnowledgeItemStatus` | Legacy compatibility axis |
| `KnowledgeSnapshot` | Execution-time SoT for a skill run |
| `KnowledgeGovernanceStatus` / `KnowledgeObject` | Governance SoT axis |
| `KnowledgeGovernanceManifest` | Publication-set SoT |

## 2. Lifecycle

```
Draft
→ Validated
→ Published
→ Deprecated | Archived | Superseded
```

| Status | May serve specialists? | Notes |
|--------|------------------------|-------|
| Draft | No | Candidate work product |
| Validated | No | Passed human review + validation gates; not yet published |
| Published | Yes | Maps to legacy `approved` |
| Deprecated | No | Explicitly withdrawn; freshness=`deprecated` |
| Archived | No | Retained for audit |
| Superseded | No | Replaced by newer version |

## 3. Logical subsystem structure

```
Knowledge Governance
├── contracts          (contracts.py)
├── registry           (knowledge types / domains — existing)
├── admission          (extends knowledge_admission_policy)
├── manifest           (KnowledgeGovernanceManifest)
├── operator           (validation pipeline — future Operator)
├── policies           (freshness, citation, visibility)
├── readiness          (future)
├── quality            (BenchmarkDataset)
├── review             (Human Review stage)
├── lineage            (EvidenceChain + DecisionChain)
├── recipes            (future)
├── runbook            (developer guide + invariants)
└── tests              (architecture invariants)
```

## 4. Knowledge Object (required fields)

| Field | Contract |
|-------|----------|
| KnowledgeID | `knowledge_id` |
| Owner | `owner` |
| Reviewer | `reviewer` |
| ReviewDate | `review_date` |
| NextReview | `next_review` |
| Confidence | `confidence` |
| Freshness | `freshness` |
| Visibility | `visibility` |
| Tenant | `tenant` |
| Domain | `domain` |
| EvidenceChain | `evidence_chain` |
| DecisionChain | `decision_chain` |
| Version | `version` |
| Status | `status` (`KnowledgeGovernanceStatus`) |

## 5. Semantic Chunk

Arbitrary token windows are **not** the governance unit.

Each `SemanticChunk` stores: Title, Intent, Rule, Condition, Exception, References.

## 6. Benchmark Dataset

Each `BenchmarkCase`: Question, Expected Source, Expected Evidence, Expected Answer, Requires Expert, Acceptance Criteria.

Publication without a linked benchmark policy is non-compliant for factual / citation-required domains.

## 7. Validation Pipeline

```
Knowledge Candidate
→ Human Review
→ Validation (incl. benchmark where required)
→ Publication
```

## 8. Citation Contract

Any agent answer that uses governed knowledge **must** return:

- Answer
- Evidence
- Source
- Confidence

Missing any field is a runtime invariant failure (architecture).

## 9. Freshness automation

Inputs: `review_date`, `next_review`, `status`.  
Outputs: `fresh` | `due_for_review` | `expired` | `deprecated` | `unknown`.

Expired published knowledge must not be treated as operational truth until re-reviewed.

## 10. Setup vs Operation

| Setup | Operation |
|-------|-----------|
| Policy versions, allowlists, migrations | Candidate intake, review, validation, publish |
| Credential / storage configuration | Citation-bearing answers |
| Benchmark dataset authoring | Freshness scans |

No silent migration repair during ordinary product requests.

## 11. Lineage

```
Knowledge Candidate
→ Human Review decision
→ Validation / Benchmark result
→ KnowledgeGovernanceManifest
→ Published KnowledgeObject
→ (later) KnowledgeSnapshot on skill run
→ CitationContract on agent answer
```
