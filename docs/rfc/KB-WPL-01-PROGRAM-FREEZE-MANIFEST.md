# KB-WPL-01 Program Freeze Manifest

**Program:** KB-WPL-01  
**Version:** 0.1.0  
**Status:** `frozen_read_only_knowledge_program`  
**Owner decision:** `accepted_as_non_executable_foundation`

## Integrated bundle

Path: `packages/knowledge/kb_wpl_program/0.1.0/`

| Artifact | Purpose |
|----------|---------|
| `integrated_manifest.json` | Program-level freeze record |
| `component_index.json` | All 10 phase components |
| `invariant_map.json` | 60 architectural invariants |
| `hash_registry.json` | All frozen bundle and skill hashes |
| `accepted_limitations.json` | Known non-runtime limitations |
| `deferred_work.json` | Future KB-WPL-02+ work |
| `freeze_findings.json` | Audit blockers/warnings/verdict |

## Hashes

| Field | Value |
|-------|-------|
| bundle_hash | `43e2cab328dec889ee7fe755bf208311522baec1dd761ef4bb9eac73a53aa4a4` |
| semantic_hash | `9abd421e96a2402d86d2b44c98431a132b60ef68f3c93448db895228acdaa462` |

## Runtime boundary (all false)

- runtime_authorized
- production_eligible
- external_discovery
- vector_search
- llm_ranking
- persistence
- API_available
- UI_available
- connector_activation_available
- workflow_execution_available
- skill_execution_available

## Components

1. KB-WPL-01.0 — Archive Intake
2. KB-WPL-01.1 — Shared Knowledge Contracts
3. KB-WPL-01.2 — Workflow Catalog Quarantine
4. KB-WPL-01.2.1 — Catalog Quality Repair
5. KB-WPL-01.3 — Workflow Pattern Library (20 patterns, frozen_reviewed_library)
6. KB-WPL-01.4 — n8n Engineering Skills (3)
7. KB-WPL-01.5 — Knowledge Linking Skill
8. KB-WPL-01.6 — Presentation Architecture Skill
9. KB-WPL-01.7 — Capability Model (4 professions, 49 capabilities)
10. KB-WPL-01.8 — Knowledge Discovery Read Models

Regenerate:

```bash
uv run python scripts/generate_kb_wpl_program_manifest.py
```
