# Commercial MVP P0.3 — Source API

## Project Sources

| Method | Path |
|--------|------|
| POST | `/projects/{project_id}/sources` |
| GET | `/projects/{project_id}/sources` |
| GET | `/projects/{project_id}/sources/{source_id}` |
| GET | `/projects/{project_id}/sources/{source_id}/versions` |
| GET | `/projects/{project_id}/sources/{source_id}/snapshot` |
| POST | `/projects/{project_id}/sources/{source_id}/supersede` |
| POST | `/projects/{project_id}/sources/{source_id}/archive` |
| POST | `/projects/{project_id}/sources/{source_id}/review-reliability` |

Filters: `source_type`, `provenance_type`, `freshness_status`, `reliability_level`, `status`, `publisher`, `domain`, pagination.

## Investigation links

| Method | Path |
|--------|------|
| POST | `/projects/{id}/investigations/{inv}/sources/{source_id}` |
| GET | `/projects/{id}/investigations/{inv}/sources` |
| PATCH | `/projects/{id}/investigations/{inv}/sources/{source_id}` |
| DELETE | soft-detach → link `excluded` (Source history kept) |

No side effects: no HTTP fetch to `url`, no Evidence, no Agent Run, no LLM.
