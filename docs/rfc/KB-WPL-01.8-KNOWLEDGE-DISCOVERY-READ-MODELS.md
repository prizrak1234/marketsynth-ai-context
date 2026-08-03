# KB-WPL-01.8 — Knowledge Discovery Read Models

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.8 |
| **Status** | **READY** — read-only deterministic discovery layer |
| **Bundle** | `packages/knowledge/discovery/0.1.0/` |
| **Depends on** | KB-WPL-01.7 (Capability Model), KB-WPL-01.3C (WPL), KB-WPL-01.4–01.6 (Skills) |

## 1. Executive verdict

**READY.** Deterministic, explainable discovery over the frozen Profession → Capability → Skill →
Workflow Pattern → Connector/Tool model. Discovery is advisory only: `runtime_authorized=false`
always. No install, execute, deploy, vector search, LLM ranking, API, UI, persistence, or MCP.

## 2. Bundle identity

| Field | Value |
|-------|-------|
| bundle_hash | `9a4f05af83350893fe32ce2bacc6d7c2e963d6440d4d2b47d002a2b1b85304c8` |
| semantic_bundle_hash | `9a4f05af83350893fe32ce2bacc6d7c2e963d6440d4d2b47d002a2b1b85304c8` |
| bundle_status | `read_only_discovery_model` |
| runtime_authorized | false |
| external_discovery | false |
| vector_search | false |
| llm_ranking | false |
| persistence | false |
| installation_actions | false |

## 3. Objective

Discovery explains:

**Task → Profession → Capability → Skills → Patterns → Connector/Tool gaps → blockers → safe next action**

It does **not** install Skills, activate Connectors, execute Patterns, or mutate registry state.

## 4. Module location

```
app/knowledge/discovery/
├── contracts.py      # immutable enums and action sets
├── indexes.py        # in-memory deterministic indexes
├── tokenization.py   # RU/EN normalization + stem overlap
├── filters.py        # query/result validation, secret rejection
├── matching.py       # deterministic matching pipeline
├── ranking.py        # explainable weighted ranking
├── routing.py        # ProfessionalTaskRoute (advisory)
├── visibility.py     # tenant filtering before ranking
├── explanations.py   # candidate/route explain helpers
├── queries.py        # discover(), route_task(), find_*()
├── serialization.py  # bundle load + result hashing
└── errors.py
```

## 5. Owner decisions (frozen)

1. Governed internal artifacts only — no public internet search.
2. No Skill installation or draft generation in this phase.
3. No embeddings or vector DB.
4. Deterministic explainable ranking.
5. Tenant visibility filtering **before** candidate generation and ranking.
6. Rejected artifacts excluded by default; quarantined visible only in internal audit mode.
7. Capability gaps remain visible — Patterns cannot hide missing Skills.
8. Connector/Tool classes are conceptual — no credential binding or permission grant.
9. Safe next actions are review/adapt/defer only — never install/execute/deploy/publish/spend.

## 6. Query modes

| Mode | Primary outputs |
|------|-----------------|
| `task_routing` | profession, capability, skill, pattern, gaps |
| `capability_lookup` | capabilities |
| `skill_lookup` | internal skills |
| `workflow_pattern_lookup` | workflow patterns |
| `engineering_diagnosis_lookup` | n8n skills, error patterns |
| `knowledge_maintenance_lookup` | knowledge linking, lineage |
| `deliverable_lookup` | presentation, content architecture |
| `internal_audit_lookup` | quarantine/rejected metadata |

## 7. Verification

```bash
uv run pytest tests/test_kb_wpl_01_7_capability_mapping.py -q
uv run pytest tests/test_kb_wpl_01_8_knowledge_discovery.py -q
uv run ruff check app/knowledge/discovery tests/test_kb_wpl_01_8_knowledge_discovery.py tests/support
```

589 KB-WPL regression tests (01.0–01.8) must remain green.

## 8. Non-goals

- Skill Generator (KB-WPL-06 / RFC-SKILL-004 draft generation)
- External marketplace search
- Vector DB / embeddings / LLM routing
- Runtime orchestration
- HTTP API / UI / DB / MCP

## 9. Program status

**KB-WPL-01 closed** — see [KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md](KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md).

Next tracks (owner choice): Product (Offer Builder / CWF) or KB-WPL-02 Knowledge Core Persistence.

## 10. Related

- [Discovery model](../architecture/KNOWLEDGE-DISCOVERY-MODEL.md)
- [Ranking model](../architecture/DISCOVERY-RANKING-MODEL.md)
- [Alias catalog](../architecture/DISCOVERY-ALIAS-CATALOG.md)
- [Profession map](../architecture/PROFESSION-CAPABILITY-SKILL-PATTERN-MAP.md)
- [RFC-SKILL-004](RFC-SKILL-004-skill-discovery-and-draft-generation.md) — future draft generation (not implemented)
