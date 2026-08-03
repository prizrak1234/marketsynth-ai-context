# Knowledge Governance Manifest

**Document type:** Subsystem Knowledge Manifest (architecture SoT index)  
**Policy version:** `kg.1`  
**ADR:** [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md)

This manifest enumerates the governed artifacts that define Knowledge Governance **as designed**. It is not a VectorDB index and not an execution `KnowledgeSnapshot`.

## Contract artifacts

| Artifact | Contract name | Purpose |
|----------|---------------|---------|
| Lifecycle | `KnowledgeGovernanceStatus` | Draft…Superseded |
| Object | `KnowledgeObject` | Mandatory governance metadata |
| Chunk | `SemanticChunk` | Title/Intent/Rule/Condition/Exception/References |
| Benchmark | `BenchmarkCase`, `BenchmarkDataset` | Validation cases |
| Pipeline | `KnowledgeValidationPipelineState` | Candidate→…→Publication |
| Citation | `CitationContract` | Answer/Evidence/Source/Confidence |
| Freshness | `KnowledgeFreshnessCheck` | ReviewDate/NextReview/Expired |
| Publication SoT | `KnowledgeGovernanceManifest` | Immutable published set hash |

## Compatibility bridge

| Governance field | Foundation field |
|------------------|------------------|
| `legacy_item_status` | `KnowledgeItemStatus` |
| `KNOWLEDGE_GOVERNANCE_TO_LEGACY_STATUS` | mapping constant in contracts |
| Published serving | Admission: only legacy `approved` / governance `published` |

## Pipeline

```
Knowledge Candidate
→ Human Review
→ Validation
→ Publication
```

## Freshness axes

- ReviewDate
- NextReview
- Expired (`freshness=expired`)
- Deprecated (`status=deprecated` or freshness deprecated)

## Citation envelope (mandatory)

```
Answer
Evidence
Source
Confidence
```

## Explicit exclusions (not in this manifest)

- Embedding tables
- Vector similarity scores as confidence
- Autonomous knowledge agents
- CSV as primary storage (PostgreSQL / typed JSON only)

## Related foundation manifests (unchanged)

- [knowledge_ingestion_manifest_v1.md](knowledge_ingestion_manifest_v1.md)
- [knowledge_migration_manifest.md](knowledge_migration_manifest.md)
- [knowledge_snapshot_policy.md](knowledge_snapshot_policy.md)
