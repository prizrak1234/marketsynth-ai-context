# Knowledge Import Plan

How external knowledge enters the BotFazer repository and eventually maps to Agent OS layers — **without** blind execution or product code changes during import phases.

## Source folders (expected staging)

Place archives and folders here before organization:

```
knowledge_import/
  knowledge_base/           # antigravity corpus (workflows, prompts, standards, manuals)
  Боты в базу знаний/       # bot templates, prompts, legacy agent material
  skills/                   # optional pre-structured skill folders
  extracted_*/              # zip extracts (workflows_sync, prompts_sync, …)
```

See also: [KNOWLEDGE_IMPORT_REPORT.md](KNOWLEDGE_IMPORT_REPORT.md) for what was already imported in AI.255.1.

## Target folders (repository corpus)

```
knowledge/          # Domain facts, prompts, manuals, topical JSON/PDF
skills/             # skill-name/SKILL.md + references/ examples/ templates/
workflows/raw/      # Original n8n/Make JSON — archive only
workflows/mapped/   # Curated BotFazer CampaignWorkflowTemplate mappings (future)
standards/          # memory/ skills/ tools/ commands/ supervisor/ workflows/ misc/
```

Inventory: [PROJECT_KNOWLEDGE_MAP.md](PROJECT_KNOWLEDGE_MAP.md)

## Pipeline (classify → document → convert)

```
External sources
  → knowledge_import/ (staging, read-only mirror)
  → organize script → knowledge/ skills/ workflows/raw/ standards/
  → human/AI curation → workflows/mapped/ + contract updates
  → product registry (explicit phase only)
```

| Step | Action | Forbidden |
|------|--------|-----------|
| **1. Stage** | Copy sources into `knowledge_import/` | Modifying `app/` |
| **2. Classify** | Topic tags, skill bundles, standards buckets | Auto-running n8n JSON |
| **3. Document** | Update PROJECT_KNOWLEDGE_MAP, import report | Storing secrets in corpus |
| **4. Convert** | Map best workflows → `CampaignWorkflowTemplate` | Bulk import 400+ workflows into runtime |
| **5. Productize** | Contracts → DB → API → tests | Skipping approval gates |

## Workflows: raw material only

- `workflows/raw/` holds **~1000+ legacy JSON** files — reference library.
- They are input for future **Skill Packs** and **Workflow Templates**, not executors.
- Do **not** wire Make/n8n graphs into `app/` without a dedicated phase, contracts, and tests.
- Do **not** rename or delete raw files during import; dedupe on copy only.

## Skills from knowledge

Each curated skill folder:

```
skills/{skill-id}/
  SKILL.md
  references/
  examples/
  templates/
```

Map to `MarketingSkillType` only after review — registry in `app/marketing/skills/registry.py`.

## Re-run organization

```bash
uv run python scripts/organize_knowledge_import.py
uv run python scripts/knowledge_import_stats.py
uv run python scripts/generate_knowledge_docs.py
```

## Related docs

- [KNOWLEDGE_ARCHITECTURE.md](KNOWLEDGE_ARCHITECTURE.md)
- [AGENT_OS_ARCHITECTURE.md](AGENT_OS_ARCHITECTURE.md)
- [CURSOR_OPERATING_RULES.md](CURSOR_OPERATING_RULES.md)
