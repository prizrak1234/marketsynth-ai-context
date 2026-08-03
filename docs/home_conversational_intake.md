# Home conversational intake (Phase H1)

Authenticated Home accepts natural-language tasks and routes them without redesigning Hero/USP.

## Flow

1. User submits text (or quick scenario).
2. `POST /user-requests` creates an owner-scoped **UserRequest**.
3. Deterministic router returns category, specialist alias, next action (no LLM).
4. Home shows conversation turn + route metadata (localized labels).
5. Same records appear on `/workspace/tasks`.
6. Ambiguous requests stay `needs_clarification` until `POST /user-requests/{id}/clarify`.

## Non-goals

- No AgentRun / LLM / Campaign / publication / budget side effects.
- No parallel Task engine or Runtime.
- Hero visual freeze remains.

## Persistence

Backend `user_requests` is SoT. LocalStorage is labelled fallback only when API is down.
