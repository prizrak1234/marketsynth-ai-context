# Knowledge maintenance routing fixtures

**Phase:** KB-WPL-01.8

| Task | Expected capability chain |
|------|---------------------------|
| Связать документы и найти дубли | `knowledge.knowledge_linking` |
| Связать знания | `knowledge.knowledge_linking` |

Mode: `knowledge_maintenance_lookup`

Skill candidate: `ms.skill.knowledge_linking`

Safe actions: `use_internal_skill_contract`, `gather_missing_evidence`.

No mutation of knowledge graph during discovery — read-only advisory only.
