# Archive Intake — Боты в базу знаний.rar

**Archive ID:** `arc-bots-knowledge-rar`

## Confirmed contents

- n8n workflow JSON exports: **248**
- Markdown standards/methodology: **58**
- Binary docs: docx/pdf (deferred review)

**These are n8n exports (`nodes`, `connections`, `meta`) — NOT Make blueprints.**

## Workflow JSON static audit (pre-pattern-library)

| Risk marker | Count |
|-------------|-------|
| total_json | 248 |
| unique_hash | 242 |
| code_nodes | 185 |
| shell_nodes | 0 |
| credential_markers | 223 |
| publication_nodes | 119 |
| billing_markers | 22 |
| destructive_markers | 1 |
| community_nodes | 26 |
| ai_nodes | 157 |

## Decision

All workflow JSON → **quarantine** → `workflow_catalog_quarantine`

Pattern Library (KB-WPL-01.3) **blocked** until this inventory is accepted.

## MD material categories

- AI employee methodology → defer (not product runtime)
- Cursor Skill audit / quality gates → adapt_methodology
- n8n workflow architecture standards → adapt_methodology
- Codex/Gemini CLI setup → defer
- Session/timer commands → defer
