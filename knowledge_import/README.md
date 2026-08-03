# Knowledge import staging (AI.255.1)

Read-only mirror of external sources before organization into:

- `knowledge/`
- `skills/`
- `workflows/raw/`
- `standards/`

## Primary sources

- Desktop `.gemini/antigravity/knowledge_base`
- Desktop `.gemini/*.zip` archives (`knowledge_base_sync`, `workflows_sync`, `prompts_sync`)
- Desktop project folders (prompts/manuals/workflows/standards — knowledge files only)

## Re-organize

```bash
uv run python scripts/organize_knowledge_import.py
uv run python scripts/knowledge_import_stats.py
uv run python scripts/generate_knowledge_docs.py
```

Do **not** delete this folder until curated mapping into product registries is complete.
