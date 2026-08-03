# RFC — Knowledge Governance Subsystem

**RFC ID:** RFC-KG-001  
**Status:** Accepted (architecture)  
**ADR:** [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md)  
**Volume:** [architecture/knowledge_governance_volume.md](architecture/knowledge_governance_volume.md)

## Problem

Marketsynth needs trustworthy, reviewable, citable knowledge for agents and specialists. Today’s Knowledge Foundation covers inventory and snapshots, but lacks a complete governance lifecycle, semantic structuring, benchmarks, mandatory citations, and freshness automation.

## Proposal

Introduce the **Knowledge Governance** subsystem as contracts + policies + documentation layered on H2.1–H2.5:

1. Governance lifecycle statuses.
2. Required Knowledge Object metadata.
3. Semantic Chunk model.
4. Benchmark Dataset.
5. Validation pipeline stages.
6. Citation Contract.
7. Freshness evaluation from ReviewDate / NextReview.
8. Knowledge Governance Manifest (immutable publication SoT).

## Explicit non-goals

- No VectorDB / embedding index implementation.
- No new LLM retrieval ranking.
- No automatic publish without human review.
- No second Runtime.

## Interfaces (contracts only)

| Contract | Module |
|----------|--------|
| `KnowledgeGovernanceStatus` | `app/schemas/contracts.py` |
| `KnowledgeObject` | same |
| `SemanticChunk` | same |
| `BenchmarkCase` / `BenchmarkDataset` | same |
| `KnowledgeValidationPipelineState` | same |
| `CitationContract` | same |
| `KnowledgeFreshnessCheck` | same |
| `KnowledgeGovernanceManifest` | same |
| Freshness helpers | `app/domain/knowledge_governance.py` |

## Compatibility

Legacy `KnowledgeItemStatus` remains. Mapping:

| Governance | Legacy |
|------------|--------|
| draft | candidate |
| validated | under_review |
| published | approved |
| deprecated | archived (serving forbidden) |
| archived | archived |
| superseded | superseded |

## Rollout

1. Land architecture + contracts + invariants (this RFC).
2. Later phase: persist KnowledgeObject / SemanticChunk / Benchmark tables + Operator.
3. Later phase: enforce CitationContract at specialist answer boundaries.
4. Never claim vector similarity as factual confidence.

## Open questions (deferred)

- Exact NextReview SLA per domain.
- Whether Benchmark is mandatory for all domains or only `citation_required` types.
- UI for review queue (not this RFC).
