# Knowledge Governance Subsystem (overview)

Status: **architecture + contracts landed; no VectorDB/LLM retrieval implementation.**

## Documents

| Doc | Path |
|-----|------|
| ADR | [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md) |
| Architecture Volume | [architecture/knowledge_governance_volume.md](architecture/knowledge_governance_volume.md) |
| RFC | [rfc_knowledge_governance.md](rfc_knowledge_governance.md) |
| Developer Guide | [knowledge_governance_developer_guide.md](knowledge_governance_developer_guide.md) |
| Manifest | [knowledge_governance_manifest.md](knowledge_governance_manifest.md) |
| Runtime Invariants | [knowledge_governance_runtime_invariants.md](knowledge_governance_runtime_invariants.md) |
| Subsystem Standard | [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md) |

## Contracts

`app/schemas/contracts.py` — Knowledge Governance block.

## Policy helpers

`app/domain/knowledge_governance.py` — freshness + citation completeness (pure).

## Tests

```bash
uv run pytest tests/test_architecture_knowledge_governance.py tests/test_architecture_subsystem_standard.py -q
```
