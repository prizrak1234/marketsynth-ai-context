# Knowledge Inventory (Phase H2.1)

Governed catalogue of knowledge **candidates and approved items**.  
Classification only in this phase — **no bulk repository ingestion**.

## Classes

| Type | Use |
|------|-----|
| `constitutional_policy` | Marketsynth invariants (no guesses as facts, INSUFFICIENT_DATA, tenant isolation, approval boundaries) |
| `domain_methodology` | Research / content / programmer / strategy methods |
| `workflow_instruction` | Process steps (when curated) |
| `output_template` | Report, plan, spec templates |
| `quality_standard` | Quality gates |
| `verified_fact` | Proven facts (usually via Source/Evidence) |
| `project_knowledge` | Briefs, approved decisions — project-scoped |
| `example` | Reference examples — never treated as facts |
| `historical_record` | Phase reports / audits — not operational |
| `operational_document` | Ops notes — limited |
| `obsolete` | Legacy BotFazer / superseded instructions |
| `forbidden` | Secrets, raw workflows, unreviewed dumps |

## Inventory source

Code registry: `app/knowledge_foundation/inventory.py`  
Allowlists: `app/knowledge_foundation/allowlists.py`  
API: `GET /knowledge-foundation/inventory`

## First approved pack

See `FIRST_APPROVED_PACK_IDS` in `app/knowledge_foundation/migration_manifest.py`:

- constitutional rules (EN + RU metadata)
- research / content / programmer methodologies
- output templates + content quality gates

## Explicit non-goals

- No recursive `/docs` indexing
- No embeddings in H2.1–H2.2
- No specialist execution
