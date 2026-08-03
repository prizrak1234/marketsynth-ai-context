# Knowledge Scope and Tenancy (Phase H2.1)

| Scope | Visibility |
|-------|------------|
| `global` | All authenticated owners (approved constitutional / methodology) |
| `owner` | Owning tenant only |
| `project` | Owning tenant **and** matching `project_id` |

## Denied

- Cross-owner retrieval of owner/project knowledge
- Project knowledge outside its Project
- KnowledgeCandidate crossing tenant boundaries
- Secrets / credentials
- Unreviewed audits as operational truth

Implementation: `app/knowledge_foundation/scopes.py`.
