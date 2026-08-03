# Knowledge Governance — Developer Guide

**Audience:** humans and Cursor agents.  
**Do first:** read [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md) and [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md).

## What exists now (KG.1 + KG.2)

| Layer | Location |
|-------|----------|
| Contracts | `app/schemas/contracts.py` (Knowledge Governance block) |
| Pure policy | `app/domain/knowledge_governance.py` |
| Ops package | `app/knowledge_governance/` (lifecycle, operator, snapshot, citation, benchmark) |
| Persistence | `app/db/models/knowledge_governance.py` · Alembic `20260719_0050` |
| Operator API | `/knowledge-governance/*` |
| Operator UI | `/workspace/knowledge/manage` (governance tabs) |
| Runtime hook | `attach_skill_context` → `create_governed_snapshot` for industrial domains |
| Foundation (do not replace) | `app/knowledge_foundation/`, H2.1–H2.5 |

## Runtime enforcement

For `content.telegram_post` in drilling / industrial_safety / oil_and_gas (when `KNOWLEDGE_GOVERNANCE_RUNTIME_ENFORCED=true`):

UserRequest → skill → published+fresh filter → immutable KnowledgeSnapshot → PromptPackage.

If Snapshot empty/expired → `execution_readiness=blocked`, `insufficient_governed_knowledge`.

## What must NOT be done

- Stand up VectorDB / Pinecone / embedding jobs as “governance”.
- Auto-approve or auto-publish knowledge.
- Skip CitationContract on knowledge-backed answers.
- Invent a second Agent Registry or Knowledge Runtime.
- Treat retrieval similarity scores as Confidence.
- Mass-index `/docs` or the whole repository.

## Operator flow

1. `POST /knowledge-governance/candidates`
2. Assign owner/reviewer
3. Validate (human review → `validated`)
4. Publish (requires owner, reviewer, review dates, source)
5. Runtime may attach Snapshot
6. Deprecate / supersede / archive as needed

## Tests

```bash
uv run pytest tests/test_architecture_knowledge_governance.py tests/test_phase_kg2_knowledge_governance_ops.py -q
```
