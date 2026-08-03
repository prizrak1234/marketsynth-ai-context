# Knowledge Profession Map

**Profession:** `profession.knowledge_architect`  
**Phase:** KB-WPL-01.7

## Path

```
source_ingestion → provenance_management → knowledge_linking
→ duplicate/contradiction review → knowledge_candidate_review → (future persistence)
```

## Skill bindings

| Capability | Skill / Pattern |
|------------|-----------------|
| knowledge_linking | `ms.skill.knowledge_linking` |
| lineage_integrity | `source_lineage_preservation` |
| knowledge_quality | `quality_gate_after_generation`, `evidence_grounded_generation` |
| knowledge_candidate_review | `customer_feedback_to_learning_candidate` |

## Deferred

knowledge_discovery (KB-WPL-01.8), source_ingestion persistence.

## Authoritative module

`app/knowledge/knowledge_linking/` — legacy `app/knowledge/linking/` not removed.
