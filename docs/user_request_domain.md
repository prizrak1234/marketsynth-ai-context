# UserRequest domain (Phase H1)

## Decision

**Create** `UserRequest` — do not overload project `Task`, `AgentRun`, chat sessions, or `BusinessIntent`.

## Contract

`app/schemas/contracts.py` → `UserRequest`, `UserRequestStatus`, `UserRequestRouteCategory`, `UserRequestRouteKind`.

## Storage

- Table: `user_requests` (Alembic `20260716_0041`)
- Model: `app/db/models/user_request.py`
- Service: `app/services/user_requests_service.py`
- API: `POST/GET /user-requests`, `POST /user-requests/{id}/clarify`

## Ownership

Rows are filtered by `owner_id`. Cross-owner reads return 404 / empty list.

## Relationship to Task

Optional `task_id` / `project_id` reserved for later handoff. H1 never creates AgentRuns.
