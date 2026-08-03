# Phase 2 — LLM + read-only tools

Phase 2 delivers the production skeleton for LLM calls, function calling, read-only tool execution, standardized envelopes, audit logs, and dry-run agent runs. LangGraph and write tools are intentionally out of scope.

## AgentRunExecutor flow (dry-run)

```
POST /agent-runs/{id}/execute-dry-run
  → build prompts (app/prompts/)
  → LLM #1 (tools definitions attached when enabled)
  → if tool_calls:
        execute each call (SafeNoOpToolExecutor)
        apply context budget on results
        inject assistant + tool messages
        LLM #2 (no tools)
  → mark run succeeded with output_payload
```

Limits:

- **One tool round** only (nested tool calls from LLM #2 fail the run).
- **max_tool_calls_per_round** (default 5) — excess calls get `tool_call_limit_exceeded` envelope failures.
- **tool_results_total_max_bytes** (default 48_000) — compacts large combined tool payloads before LLM #2.

## LLMRequest / LLMResponse

- Created via `LLMRequestService` for each provider call.
- `input_payload` stores sanitized run input; `request_metadata` holds `tools_metadata`, observability, and phase tags (`initial` / `tool_follow_up`).
- Responses store compact `output_payload` (no raw provider dumps in `raw_response`).

## ToolRegistry

- Allow-list registry in `app/tools/registry.py`.
- `list_for_agent(agent_type)` applies per-agent profiles (`app/tools/agent_tool_profiles.py`).
- OpenAI schemas via `app/tools/openai_schema.py` when `TOOLS_PROVIDER_ENABLED=true`.

## SafeNoOpToolExecutor

Central dispatcher in `app/tools/executor.py`:

1. `evaluate_tool_access()` — permission matrix + agent allowlist.
2. `validate_tool_arguments()` — schema / forbidden keys (`invalid_arguments`).
3. Real read-only executors for allow-listed tools.
4. No-op skip for registered stubs (e.g. `search_brief`).
5. Audit via `ToolExecutionLogService` when configured.

## Real read-only tools

| Tool | Purpose |
|------|---------|
| `memory.search` | Text search in project memory |
| `project_context.get` | Compact project/agents/tasks/memory summary |
| `task.get` | Single task by id |
| `task.list_recent` | Recent tasks in project |

## ToolResultEnvelope

All real tool results use a unified JSON envelope (`app/tools/result_contracts.py`):

```json
{
  "ok": true,
  "tool": "memory.search",
  "data": { "count": 1, "items": [] },
  "meta": { "truncated": false, "items_count": 1 }
}
```

Errors use `ok: false` and `error.code` / `error.message`. Per-result size cap: `TOOL_RESULT_MAX_BYTES` (default 24_000).

## Audit table (`tool_execution_logs`)

- Safe previews only (no raw memory bodies).
- Filters on `GET /projects/{id}/tool-executions`: `tool_name`, `status`, `execution_mode`, `created_from`, `created_to`, `limit`, `offset`.
- Per-run: `GET /agent-runs/{id}/tool-executions`.

Agent run `output_payload.tools` summary:

```json
{
  "executed_count": 1,
  "failed_count": 0,
  "tool_names": ["project_context.get"]
}
```

## Permission model

- `app/tools/permissions.py` — execution modes, ownership checks, write-tool deny.
- `app/tools/agent_tool_profiles.py` — per-`AgentType` tool allowlists.

## Known limitations

- No write tools (memory.write, etc. are denied/skipped).
- One tool round per run; no LangGraph orchestration yet.
- No streaming responses.
- LiteLLM real provider requires keys; use `scripts/smoke_litellm_tools.py` locally.

## Manual smoke

```powershell
uv run python scripts/smoke_litellm_tools.py
```

Skips with exit code 0 when `OPENAI_API_KEY` is missing (CI-safe).

## Phase 3.0 — LangGraph skeleton (parallel path)

- Package: `app/graphs/` (`contracts`, `nodes`, `agent_graph`, `runner`)
- Default engine: `AGENT_EXECUTION_ENGINE=classic` — production path remains `AgentRunExecutor`
- Test endpoint: `POST /agent-runs/{id}/execute-graph-dry-run`
- Graph reuses `build_llm_messages`, `SafeNoOpToolExecutor`, audit, and LLM request logging
- State: `AgentGraphState` / `AgentGraphStateDict` (no secrets in graph state)

## Phase 3.1 — State hardening + checkpoints

- Trace fields: `trace_id`, `current_node`, `completed_nodes`, `step_count`, `max_steps`
- `run_graph_node()` lifecycle wrapper; in-memory `GraphCheckpointStore`
- Settings: `GRAPH_VERSION`, `GRAPH_MAX_STEPS`, `GRAPH_CHECKPOINTS_ENABLED`

## Phase 3.2 — Graph tool node hardening

- Package: `app/graphs/tool_node.py` — `plan_graph_tool_round`, `execute_graph_tool_round`, follow-up messages
- Graph nodes: `tool_prepare` → `tool_execute` → `tool_finalize` → `llm_follow_up`
- Routing: `app/graphs/routing.py` (conditional edges per phase)
- State: `pending_tool_calls`, `tool_calls_planned` / `executed` / `skipped`, `tool_round_status`
- Multi-tool in one round works on graph dry-run path (same limits as classic executor)
- Default `GRAPH_VERSION=3.2`, `GRAPH_MAX_STEPS=12`

## Phase 3.3 — Graph memory load node

- Package: `app/graphs/memory_node.py` — `load_graph_memory_context`, project-scoped `MemoryService.search`
- Graph node: `memory_load` runs before `build_prompt` (START → memory_load → build_prompt → …)
- State: `memory_load_status`, `memory_item_count`, `memory_query`, `memory_context` (sanitized previews only)
- Input controls: `memory_context` (skip auto-load), `skip_graph_memory_load`, `memory_query`
- Settings: `GRAPH_MEMORY_ENABLED`, `GRAPH_MEMORY_LIMIT`; default `GRAPH_VERSION=3.3`, `GRAPH_MAX_STEPS=13`
- Classic executor unchanged (memory still via `input_payload.memory_context` only)

## Phase 3.4 — Graph handoff skeleton

- Package: `app/graphs/handoff.py` — policy matrix, `evaluate_graph_handoff`, delegation output contract
- Graph nodes: `handoff_gate` (after `memory_load`) → `handoff_record` or continue to `build_prompt`
- Input: `handoff_to_agent_id`, optional `handoff_reason` (control keys stripped before prompt build)
- On success: run completes with `output_payload.handoff` (`child_run_enqueued: false` — no child execution yet)
- On reject: safe errors (`handoff_not_allowed`, `handoff_target_not_found`, …)
- Settings: `GRAPH_HANDOFF_ENABLED`; default `GRAPH_VERSION=3.4`, `GRAPH_MAX_STEPS=14`
- Classic executor unchanged

## Phase 3.5 — Handoff child run enqueue

- `enqueue_handoff_child_run()` creates a queued child `agent_run` on the target agent
- Child `input_payload`: parent prompt + handoff reason + optional parent `memory_context`
- Child `metadata`: `parent_agent_run_id`, `handoff_trace_id`, `handoff_depth`
- Controls: `handoff_enqueue_child` (default true), `handoff_execute_child` (default false)
- Optional sync execute when `GRAPH_HANDOFF_EXECUTE_CHILD=true` and `handoff_execute_child=true`
- `GRAPH_HANDOFF_MAX_DEPTH=1` blocks nested handoffs on child runs
- Parent `output_payload.handoff` includes `child_run_id`, `child_run_enqueued`, `child_run_executed`
- Default `GRAPH_VERSION=3.5`

## Phase 3.6 — Handoff child worker

- Worker: `app/workers/handoff_child_worker.py` — `HandoffChildRunWorker.process_batch()`
- API: `POST /agent-runs/process-handoff-children?limit=5` drains queued handoff children for the owner
- Identifies children via `metadata.execution_engine=langgraph-handoff-child` + `parent_agent_run_id`
- Executes children through `execute_handoff_child_run()` (LangGraph path)
- `child_run_pending_worker` in parent handoff output when enqueued but not inline-executed
- `GRAPH_HANDOFF_MAX_DEPTH=2` enables one chained handoff (e.g. orchestrator → researcher → copywriter)
- Settings: `GRAPH_HANDOFF_WORKER_ENABLED`, `GRAPH_HANDOFF_WORKER_BATCH_LIMIT`
- Default `GRAPH_VERSION=3.6`

## Phase 3.7 — Handoff queue + parent sync + scheduler

- Redis per-owner FIFO: `app/queues/handoff_child_queue.py` (`RPUSH` on child enqueue, `LPOP` in worker)
- Owner index set `botfazer:graph:handoff:owners` for scheduler ticks
- Parent `output_payload.handoff` patched when child completes (`parent_handoff_synced_at`, `child_run_executed`, …)
- `AgentRunService.patch_output_payload()` for non-status output updates
- Background scheduler: `app/workers/handoff_scheduler.py` (off by default; `GRAPH_HANDOFF_SCHEDULER_ENABLED=true`)
- Settings: `GRAPH_HANDOFF_QUEUE_ENABLED`, scheduler interval/owner cap
- Default `GRAPH_VERSION=3.7`

## Phase 3.8 — Handoff reliability (DLQ + outbox)

- Dead-letter: `app/queues/handoff_dead_letter_queue.py` (`botfazer:graph:handoff:dlq:{owner_id}`)
- Worker attempts tracked in `metadata.handoff_worker` (attempts, last_error, dead_lettered)
- `GRAPH_HANDOFF_MAX_ATTEMPTS=3` — retry via re-queue; at max → DLQ + parent `child_run_status=dead_lettered`
- DB outbox: `event_outbox` table + `EventOutboxService` (`graph.handoff.parent_synced`)
- Read-only API: `GET /projects/{id}/events?event_type=&status=`
- No outbound webhooks yet — outbox is the integration point for Phase 3.9+
- Default `GRAPH_VERSION=3.8`

## Phase 3.9 — Outbox dispatcher → project webhooks

- Table `project_webhooks` (URL, signing secret server-side, subscribed event types)
- `POST/GET/DELETE /projects/{id}/webhooks` — secret returned once on create (`bwhsec_…`)
- `EventOutboxDispatcher` POSTs signed JSON envelope to each active subscription
- Headers: `X-BotFazer-Event-Id`, `X-BotFazer-Event-Type`, `X-BotFazer-Timestamp`, `X-BotFazer-Signature`
- `POST /projects/{id}/events/dispatch` — manual drain (owner-scoped)
- Background: `OutboxDispatcherScheduler` (`EVENT_OUTBOX_DISPATCHER_ENABLED=false` by default)
- Delivery retries via `event_outbox.attempts`; `failed` after `EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS`
- Default `GRAPH_VERSION=3.9`

## Phase 3.10 — Delivery logs, outbox dead-letter, replay APIs

- Table `webhook_delivery_logs` — per-attempt audit (safe URL preview, truncated response/error)
- `EventOutboxDispatcher` logs every webhook attempt; `sent` if ≥1 webhook returns 2xx
- `EventOutboxStatus.DEAD_LETTERED` after max dispatch attempts with no success
- `GET /projects/{id}/webhook-deliveries` — filter by webhook_id, event_type, status
- `POST /projects/{id}/events/{event_id}/replay` — reset to pending (no auto-dispatch)
- `POST /agent-runs/{id}/handoff/replay` — reset DLQ child, re-queue Redis, update parent handoff
- Default `GRAPH_VERSION=3.10`

## Phase 3.11 — Operational metrics

- `GET /projects/{id}/operational-metrics` — 24h aggregates (runs, graph, handoff, outbox, webhooks)
- `GET /me/operational-metrics` — same metrics across all owner projects
- `GET /health/operations` — infra + scheduler flags + global pending outbox / queue owner count
- Redis queue depth via `app/queues/handoff_queue_metrics.py` (graceful degradation when Redis is down)
- See [phase_3_langgraph_handoff.md](phase_3_langgraph_handoff.md) for runbooks (queues, DLQ, replay, schedulers)
- Default `GRAPH_VERSION=3.11`

## Phase 3.12 — Batch replay and cleanup

- `POST /projects/{id}/events/replay-batch` — reset up to 100 failed/dead_lettered/pending events (no auto-dispatch)
- `POST /agent-runs/handoff/replay-batch` — re-queue DLQ handoff children for a project
- `DELETE /projects/{id}/webhook-deliveries/cleanup?older_than_days=30` — prune old delivery logs only
- Runbook: [phase_3_langgraph_handoff.md](phase_3_langgraph_handoff.md)
- Default `GRAPH_VERSION=3.12`

## Phase 3.13 — Controlled LangGraph production switch

- `POST /agent-runs/{id}/execute` — production entry with `execution_engine` in response
- `app/executors/engine_resolver.py` — classic ↔ langgraph with rollback flag
- `project.config.execution_engine` (JSON column + PATCH)
- Settings: `AGENT_EXECUTION_FORCE_CLASSIC`, `AGENT_EXECUTION_LANGGRAPH_ENABLED`, override flag
- `output_payload.execution` stamp; metrics `execution.*` on operational-metrics
- Default `GRAPH_VERSION=3.13`

## Next: Phase 3.14+

Admin UI; Prometheus/Grafana (optional).
