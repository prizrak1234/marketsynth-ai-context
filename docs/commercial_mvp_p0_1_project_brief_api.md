# Commercial MVP P0.1 — ProjectBrief API

Prefix: `/projects/{project_id}/briefs` (owner-scoped via `require_project_owner`)

| Method | Path | Effect |
|--------|------|--------|
| POST | `` | Create **draft** (409 if draft exists) |
| GET | `` | List history (`status`, `limit`, `offset`) |
| GET | `/latest` | Latest submitted else latest any |
| GET | `/{brief_id}` | Get one |
| PATCH | `/{brief_id}` | Update **draft** only (409 if submitted) |
| POST | `/{brief_id}/submit` | Draft→submitted; previous submitted→superseded; duplicate fingerprint 409 |
| POST | `/{brief_id}/supersede` | New draft version from submitted (optional body) |

No Investigation / Agent Run / provider side effects.
