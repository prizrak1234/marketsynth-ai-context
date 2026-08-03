# ADR — Knowledge Governance Architecture

**ADR ID:** ADR-KG-001  
**Status:** Accepted  
**Date:** 2026-07-19  
**Phase:** Knowledge Governance (architecture)  
**Standard:** [marketsynth_subsystem_standard.md](marketsynth_subsystem_standard.md)

## Decision

Marketsynth adopts a **Knowledge Governance Subsystem** as a bounded product capability layered on top of the existing Knowledge Foundation (H2.1–H2.5) SoT — without introducing a second Runtime, VectorDB, or LLM retrieval implementation in this phase.

## Context

Existing foundation provides inventory, admission, snapshots, and deterministic retrieval policy. Gaps for a governed knowledge product:

- incomplete lifecycle (no explicit Draft / Validated / Published / Deprecated);
- Knowledge Objects lack mandatory Owner / Reviewer / Freshness / EvidenceChain / DecisionChain fields as a single contract;
- chunking is not semantically structured;
- no benchmark dataset contract;
- citation is a boolean flag, not a mandatory answer envelope;
- freshness / NextReview automation is undefined.

## Decision details

1. **Governance lifecycle** (`KnowledgeGovernanceStatus`): Draft → Validated → Published → Deprecated | Archived | Superseded, with explicit mapping to legacy `KnowledgeItemStatus`.
2. **KnowledgeObject** is the required governance metadata contract.
3. **SemanticChunk** replaces arbitrary window chunking as the architectural unit of knowledge structure.
4. **BenchmarkDataset** gates Validation → Publication.
5. **CitationContract** is mandatory for any agent answer that uses governed knowledge.
6. **Freshness policy** evaluates ReviewDate / NextReview / Expired / Deprecated without LLM judgment.
7. **KnowledgeGovernanceManifest** is the immutable publication SoT (PostgreSQL/typed JSON — not CSV).

## Non-goals (this phase)

- No VectorDB / embedding pipeline.
- No new LLM retrieval implementation.
- No mass migration of existing approved items (classify / map only).
- No second Knowledge store or Agent Registry.

## Alternatives rejected

| Alternative | Why rejected |
|-------------|--------------|
| Replace Knowledge Foundation wholesale | Breaks H2.1–H2.5 / snapshots |
| Vector-first governance | Confuses similarity with confidence |
| Docs-only without contracts | Drifts; violates Subsystem Standard |
| Autonomous “knowledge agent” Runtime | Forbidden parallel Runtime |

## Consequences

- Contracts live in `app/schemas/contracts.py`.
- Policy helpers in `app/domain/knowledge_governance.py` (pure).
- Compliance matrix Knowledge Foundation row updates toward governance subsystem.
- Implementation of persistence/API is a later phase after this architecture lands.

## References

- [knowledge_governance_volume.md](knowledge_governance_volume.md)
- [../rfc_knowledge_governance.md](../rfc_knowledge_governance.md)
- [../knowledge_governance_manifest.md](../knowledge_governance_manifest.md)
- [../knowledge_governance_runtime_invariants.md](../knowledge_governance_runtime_invariants.md)
- [../knowledge_governance_developer_guide.md](../knowledge_governance_developer_guide.md)
