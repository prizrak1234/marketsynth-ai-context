# Commercial MVP P1.1 — ImplementationPlan API

Prefix: `/projects/{project_id}/implementation-plans`

| Method | Path | Notes |
|--------|------|-------|
| POST | `` | Create draft |
| POST | `/build-draft` | Deterministic draft from approved Strategy |
| GET | `` | List + filters |
| GET | `/latest` | Latest version |
| GET | `/{id}` | Get |
| PATCH | `/{id}` | Draft only |
| GET | `/{id}/handoff-preview` | Read-only P1.2 preview |
| POST | `/{id}/submit-review` | |
| POST | `/{id}/approve` | Immutable; no MarketingPlan side effect |
| POST | `/{id}/reject` | |
| POST | `/{id}/return-draft` | |
| POST | `/{id}/block` | |
| POST | `/{id}/unblock` | |
| POST | `/{id}/archive` | |
| POST | `/{id}/supersede` | New version |

Owner via `require_project_owner`. Conflicts → HTTP 409.
