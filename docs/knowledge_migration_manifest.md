# Knowledge Migration Manifest (Phase H2.1)

Curated actions for the imported corpus — **do not migrate automatically**.

| Action | Meaning |
|--------|---------|
| `include` | First approved pack / ready after metadata |
| `include_after_review` | Candidate — human review required |
| `split_into_atomic_knowledge_items` | Directory too coarse |
| `keep_as_historical_record` | Phase reports, staging mirrors |
| `exclude` | Never operational knowledge |
| `obsolete` | Legacy BotFazer / conflicting docs |

Machine-readable list: `app/knowledge_foundation/migration_manifest.py`.

## Excluded by default

- `docs/phase_ai_*` audits and freezes  
- `workflows/raw/`  
- `knowledge_import/` staging  
- `tests/`, mocks, secrets, `.env`  
- Raw prompt dumps as specialist knowledge  
- Bulk `knowledge/misc` automation JSON  

## First approved pack IDs

`FIRST_APPROVED_PACK_IDS` in the same module.
