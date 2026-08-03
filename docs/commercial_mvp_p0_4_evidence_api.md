# Commercial MVP P0.4 — Evidence API

Base: `/projects/{project_id}/investigations/{investigation_id}/evidence`

| Method | Path |
|--------|------|
| POST | `` |
| GET | `` |
| GET | `/summary` |
| GET | `/{evidence_id}` |
| PATCH | `/{evidence_id}` (draft only) |
| POST | `/{id}/submit-review` |
| POST | `/{id}/accept` |
| POST | `/{id}/reject` |
| POST | `/{id}/mark-conflicting` |
| POST | `/{id}/mark-outdated` |
| POST | `/{id}/archive` |
| POST | `/{id}/supersede` |
| POST | `/{id}/sources/{source_id}` |

No Business Verdict endpoint. No Agent Run / LLM / fetch side effects.
