# Profession → Capability → Skill → Pattern → Connector → Tool

**Status:** mapped_read_only_model (KB-WPL-01.7)  
**Canonical URI:** `https://schemas.marketsynth.ai/capability-model/0.1.0/` (identity only)

## Hierarchy

```
Profession
  └── Capability (business competence)
        └── Skill (versioned methodology package)
              └── Workflow Pattern (reusable process architecture)
                    └── Connector (provider boundary — conceptual)
                          └── Tool (concrete action — conceptual)
```

## Professions

| ID | Domain | runtime_authorized |
|----|--------|-------------------|
| `profession.ai_marketing_director` | marketing | false |
| `profession.automation_architect` | automation_engineering | false |
| `profession.knowledge_architect` | knowledge_management | false |
| `profession.content_deliverables_architect` | content_and_deliverables | false |

## Readiness dimensions (never collapsed)

| Dimension | Meaning |
|-----------|---------|
| methodology_exists | Capability specified in bundle |
| package_exists | Skill package present in repo |
| pattern_exists | Frozen WPL pattern referenced |
| connector_exists | Connector implemented (false in 01.7) |
| tool_exists | Tool allowlist active (false in 01.7) |
| runtime_exists | Executable runtime (false) |
| approval_exists | Approval boundary defined |
| production_release_exists | Production eligible (false) |

## Bundle

Path: `packages/knowledge/capability_model/0.1.0/`  
Hash: `e1e2bbeb025a3348944a5dab43e5661d31e2ac559e9e8de4989836c50831e42b`

Validation: `app/knowledge/capability_model/`

## Discovery layer (KB-WPL-01.8)

Read-only deterministic discovery over this map: `app/knowledge/discovery/`.

- Alias catalog: [DISCOVERY-ALIAS-CATALOG.md](DISCOVERY-ALIAS-CATALOG.md)
- Discovery model: [KNOWLEDGE-DISCOVERY-MODEL.md](KNOWLEDGE-DISCOVERY-MODEL.md)
- Bundle: `packages/knowledge/discovery/0.1.0/` (hash `9a4f05af83350893fe32ce2bacc6d7c2e963d6440d4d2b47d002a2b1b85304c8`)

Discovery explains routes and gaps; it does not activate runtime components.
