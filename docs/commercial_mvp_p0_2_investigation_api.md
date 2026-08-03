# Commercial MVP P0.2 — Investigation API

Base: `/projects/{project_id}/investigations`

Auth: active user + project owner. Owner derived server-side.

## CRUD / list

| Method | Path | Notes |
|--------|------|-------|
| POST | `` | Create draft from submitted Brief + version + fingerprint |
| GET | `` | List; filters `status`, `limit`, `offset` |
| GET | `/latest` | Deterministic latest |
| GET | `/{investigation_id}` | By id |
| PATCH | `/{investigation_id}` | Limited fields; not completed/superseded |

## Lifecycle

| Method | Path | Transition |
|--------|------|------------|
| POST | `.../start` | draft→ready→active (or ready→active); sets `started_at` |
| POST | `.../block` | ready/active → blocked |
| POST | `.../resume` | blocked → ready |
| POST | `.../submit-review` | active → under_review |
| POST | `.../complete` | under_review → completed |
| POST | `.../cancel` | draft/ready/active → cancelled |
| POST | `.../supersede` | completed → superseded + new draft |

## Stages

| Method | Path |
|--------|------|
| PATCH | `.../stages/{stage}` |

Stage status: `not_started` \| `queued` \| `in_progress` \| `blocked` \| `completed` \| `needs_review`.

## Errors (domain)

`brief_not_submitted`, `brief_version_mismatch`, `fingerprint_mismatch`, `active_investigation_exists`, `investigation_invalid_transition`, `brief_not_found`, plus standard 401/403/404.

No Agent Run / LLM / Source / Evidence side effects on any route.
