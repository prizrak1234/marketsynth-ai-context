# Architecture roadmap — Subsystem Standard adoption

**Slice 0 (done):** Persist [Marketsynth Subsystem Standard](marketsynth_subsystem_standard.md), [ADR](adr_subsystem_standard.md), [compliance matrix](subsystem_compliance_matrix.md).

**Knowledge Governance (architecture done):** [adr_knowledge_governance.md](adr_knowledge_governance.md) · [knowledge_governance_volume.md](knowledge_governance_volume.md) · [../rfc_knowledge_governance.md](../rfc_knowledge_governance.md).

## Adoption sequence

| Order | Work | Notes |
|-------|------|-------|
| 0 | Standard + ADR + matrix + invariant test | Done |
| 0b | Knowledge Governance architecture + contracts | Done — no VectorDB/LLM impl |
| 1 | Finish H2.8E Identity Generation under the standard | No paid calls without owner approval |
| 2 | If identity provider unsuitable → H2.9 specialized adapter | Via IdentityImageProvider; not prompt tuning |
| 3 | Knowledge Governance persistence + Operator | Tables/API for Object/Chunk/Benchmark; enforce CitationContract |
| 4 | Integration Package Standard compliance (OpenAI → research → messaging) | Gap-driven, one provider at a time |
| 5 | CampaignExecutionManifest when needed | Do not invent dual campaign engines |
| 6 | Recipe catalogs for marketing scenarios / publishing | Recipes ≠ new skills |
| 7 | Future HR / legal / finance domains | Must pass standard checklist before coding |

## Non-goals of adoption

- Mass refactor of frozen AI phases.
- Parallel Runtime or Agent Registry.
- Enabling Make/n8n/ads writes as a side effect of documentation.
- VectorDB as a substitute for Knowledge Governance.
