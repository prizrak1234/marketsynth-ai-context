# Workspace Task projection

## Principle

Do not collapse Task, AgentRun, MarketingPlan.specialist_tasks, chat, and Project into one SoT table.

`WorkspaceTaskItem` is a **read/projection** view model.

## Current sources (Phase H1)

1. **Backend `UserRequest`** (`GET /user-requests`) — owner-scoped SoT for Home intake
   - `authority=backend`
   - `source_domain=user_request`
2. **LocalStorage fallback** `marketsynth.workspace.tasks.v1` only when API is unavailable
   - labelled `authority=local_draft` — never claimed as server SoT

Home conversation is rebuilt from the same UserRequest list after refresh.

## Explicit non-merges

- Project `Task` CRUD (agent work units)
- AgentRun (execution)
- MarketingPlan.specialist_tasks (plan snapshots)
- Chat sessions

No parallel Task engine.
