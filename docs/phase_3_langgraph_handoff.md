# Phase 3 — LangGraph handoff, outbox, webhooks, operations

LangGraph runs alongside the classic `AgentRunExecutor`. Production default remains `AGENT_EXECUTION_ENGINE=classic`.

**Production entry:** `POST /agent-runs/{id}/execute` — resolves engine via settings, project config, or query override.

**Debug / emergency endpoints (unchanged):**

- `POST /agent-runs/{id}/execute-dry-run` — always classic
- `POST /agent-runs/{id}/execute-graph-dry-run` — always LangGraph

## Execution engine switch (Phase 3.13)

Resolver priority (highest first):

1. `AGENT_EXECUTION_FORCE_CLASSIC=true` → always classic (rollback)
2. `?engine=classic|langgraph` when `AGENT_EXECUTION_ENGINE_REQUEST_OVERRIDE_ENABLED=true`
3. `project.config.execution_engine`
4. `AGENT_EXECUTION_ENGINE` (global default, classic)

LangGraph is only used when `AGENT_EXECUTION_LANGGRAPH_ENABLED=true`.

### Enable LangGraph globally

```bash
# .env
AGENT_EXECUTION_ENGINE=langgraph
AGENT_EXECUTION_LANGGRAPH_ENABLED=true
AGENT_EXECUTION_FORCE_CLASSIC=false
```

### Rollback to classic immediately

```bash
AGENT_EXECUTION_FORCE_CLASSIC=true
```

Ignores project config and request overrides until set back to `false`.

### Per-request override (staging)

```bash
AGENT_EXECUTION_ENGINE_REQUEST_OVERRIDE_ENABLED=true

curl -X POST "http://127.0.0.1:8000/agent-runs/<run-id>/execute?engine=langgraph" \
  -H "Authorization: Bearer bfz_..."
```

### Per-project override

```bash
curl -X PATCH "http://127.0.0.1:8000/projects/<project-id>" \
  -H "Authorization: Bearer bfz_..." \
  -H "Content-Type: application/json" \
  -d '{"config":{"execution_engine":"langgraph"}}'
```

Runs record `output_payload.execution.engine` and `graph_version` (LangGraph only). Operational metrics expose `execution.agent_runs_by_execution_engine` and success/failed rates.

## Execution idempotency and concurrency (Phase 3.14)

`POST /agent-runs/{id}/execute` is the only production entry that uses the unified claim guard. Debug endpoints (`execute-dry-run`, `execute-graph-dry-run`) still claim inside the classic/graph runners and do **not** accept `Idempotency-Key`.

### Safe execute flow

1. Run must be `queued`. The API atomically claims `queued → running` before invoking classic or LangGraph.
2. Concurrent execute requests for the same run: one claim wins; the other gets **409** `already_running_or_claimed`.
3. Runs in `running`, `failed`, or `cancelled` cannot be executed again via `/execute` (also **409**).
4. A `succeeded` run cannot be re-executed. Without a key you get **409** `agent_run_already_completed`.

### Idempotency-Key header (optional)

```bash
curl -X POST "http://127.0.0.1:8000/agent-runs/<run-id>/execute" \
  -H "Authorization: Bearer bfz_..." \
  -H "Idempotency-Key: my-safe-key-1"
```

- Max **128** characters; allowed charset: `[a-zA-Z0-9._:-]`.
- Stored in `run.metadata.execution.idempotency_key` and echoed in `output_payload.execution` when the run finishes.
- **Same key** on an already `succeeded` run: returns the existing run (no second execution).
- **Different key** on a completed run: **409** `idempotency_key_mismatch`.
- Keys are not treated as secrets — do not put credentials in them.

### Execution metadata block

Successful `/execute` responses include:

```json
"execution": {
  "engine": "classic|langgraph",
  "graph_version": "3.14",
  "idempotency_key": "optional",
  "started_at": "ISO-8601",
  "finished_at": "ISO-8601",
  "claim_source": "execute_endpoint"
}
```

If the header is omitted, `idempotency_key` is omitted from the block.

### Failed runs

If the executor fails after claim, the run becomes `failed`. A later `/execute` without reset returns **409** (`agent_run_not_executable:failed`). Use **AgentRun replay** (clone) below — not in-place reset.

## AgentRun replay — clone only (Phase 3.15)

**Not the same as** outbox or handoff replay:

| Mechanism | What it retries |
|-----------|-----------------|
| `POST /projects/{id}/events/{event_id}/replay` | Event outbox delivery |
| `POST /agent-runs/{id}/handoff/replay` | Handoff child queue entry |
| `POST /agent-runs/{id}/replay` | **New** queued AgentRun cloned from a failed/cancelled parent |

AgentRun replay **never** mutates the source run (audit, LLM/tool logs, idempotency keys stay intact). It creates a new `queued` run with the same `input_payload`, `agent_id`, `project_id`, and `task_id` (if any).

### Allowed / forbidden

- **Allowed:** `failed`, `cancelled`
- **Forbidden:** `queued`, `running`, `succeeded`, archived agent

### Workflow

```bash
# 1. Source run failed (or cancelled)
curl -H "Authorization: Bearer bfz_..." \
  http://127.0.0.1:8000/agent-runs/<failed-run-id>

# 2. Clone into new queued run (does NOT execute)
curl -X POST "http://127.0.0.1:8000/agent-runs/<failed-run-id>/replay" \
  -H "Authorization: Bearer bfz_..." \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual_retry_after_provider_failure"}'

# 3. Execute the clone via production endpoint
curl -X POST "http://127.0.0.1:8000/agent-runs/<new-run-id>/execute" \
  -H "Authorization: Bearer bfz_..."
```

Clone metadata (`metadata.replay`):

```json
{
  "source_run_id": "<uuid>",
  "source_status": "failed",
  "reason": "optional",
  "created_at": "ISO-8601"
}
```

Operational metrics expose `replay.replayed_runs_count`, `replay.failed_runs_replayed_count`, and `replay.replay_source_status_counts` (24h window).

## Graph handoff controls (Phase 3.4+, orchestrator Phase 5.6)

LangGraph path: `memory_load` → **`handoff_gate`** → (`handoff_record` if delegated | else LLM/tools). When delegated, the **parent does not call the source LLM**; it enqueues (or inline-executes) a child run and returns `output_payload.handoff`.

### `input_payload` control keys (stripped before child build)

| Key | Purpose |
|-----|---------|
| `handoff_to_agent_id` | Target agent UUID |
| `handoff_target_agent_type` | Resolve first agent of type in project (orchestrator) |
| `handoff_reason` | Note appended to child prompt |
| `handoff_enqueue_child` | Create child run (default `true`) |
| `handoff_execute_child` | Run child inline when `GRAPH_HANDOFF_EXECUTE_CHILD=true` |

**Orchestrator-only** (`app/marketing/orchestration.py`):

- `agent.config.orchestration.handoff_enabled` — disable auto-resolution when `false` (explicit `handoff_to_agent_id` still works).
- `orchestration.max_child_runs` — cap children per parent (`handoff_max_children_exceeded`).
- `orchestration.default_inline_child_execution` — default for `handoff_execute_child` when omitted.
- `mock_orchestrator_flow` — auto-route from `goal` at gate when no explicit target id.

Child payloads use specialist field conventions (see [phase_5_marketing_agents.md](phase_5_marketing_agents.md#phase-56--orchestrator-agent-mvp)).

Classic `execute-dry-run` **does not** evaluate handoff — use `execute-graph-dry-run` or production `/execute` with LangGraph engine.

## Operational metrics (Phase 3.11)

Read-only aggregates for the last **24 hours** (plus queue depths from Redis).

### Project scope

```bash
curl -H "Authorization: Bearer bfz_..." \
  http://127.0.0.1:8000/projects/<project-id>/operational-metrics
```

### Owner scope (all projects)

```bash
curl -H "Authorization: Bearer bfz_..." \
  http://127.0.0.1:8000/me/operational-metrics
```

Response sections:

| Section | Contents |
|---------|----------|
| `agent_runs` | Counts by status (`queued`, `running`, `succeeded`, …) |
| `graph_runs` | LangGraph parent runs (`succeeded` / `failed`) |
| `handoff` | Child runs: `queued`, `failed`, `dead_lettered`, `oldest_queued_age_seconds` |
| `outbox` | `pending`, `sent`, `failed`, `dead_lettered`, `oldest_pending_age_seconds` |
| `webhooks` | Delivery log counts, avg/max `duration_ms`, `failed_count_by_webhook_id` |
| `execution` | Engine counts and success/failed rates |
| `replay` | `replayed_runs_count`, `failed_runs_replayed_count`, `replay_source_status_counts` |
| `redis` | `queue_depth`, `dlq_depth`, `available` |

If Redis is down, metrics still return with `redis.available=false` and a safe `error` string — the HTTP call does not fail.

### Operations health (no auth)

```bash
curl http://127.0.0.1:8000/health/operations
```

Shows database/redis probe, scheduler flags, `graph_version`, global `pending_outbox_count`, and `handoff_queue_known_owners_count`. No owner IDs, webhook URLs, or secrets.

## Queues — what to watch

| Redis key | Meaning |
|-----------|---------|
| `botfazer:graph:handoff:queue:{owner_id}` | FIFO of queued handoff child run IDs |
| `botfazer:graph:handoff:dlq:{owner_id}` | Dead-letter entries (JSON payloads) |
| `botfazer:graph:handoff:owners` | Owners with non-empty handoff queue |
| `botfazer:graph:handoff:dlq:owners` | Owners with DLQ entries |

Use `operational-metrics` → `redis.queue_depth` / `dlq_depth` instead of `redis-cli` when possible.

## Dead-letter and replay

### When to use single vs batch replay

| Situation | Use |
|-----------|-----|
| One known failed event / child run | Single replay endpoints |
| Many `dead_lettered` / failed after an outage | Batch replay, then manual drain |
| Routine hygiene on old audit rows | Delivery log cleanup (not outbox) |

**Never** auto-dispatch after batch replay — reset first, then drain separately to avoid webhook storms.

### Outbox (webhook dispatch exhausted)

1. List: `GET /projects/{id}/events?status=dead_lettered`
2. Inspect attempts: `GET /projects/{id}/webhook-deliveries?status=failed`
3. **Single:** `POST /projects/{id}/events/{event_id}/replay` → `pending`
4. **Batch:** `POST /projects/{id}/events/replay-batch` (see below)
5. Drain: `POST /projects/{id}/events/dispatch`

```bash
# Batch — failed + dead_lettered only (sent untouched)
curl -X POST "http://127.0.0.1:8000/projects/<project-id>/events/replay-batch" \
  -H "Authorization: Bearer bfz_..." \
  -H "Content-Type: application/json" \
  -d '{"statuses":["failed","dead_lettered"],"event_type":"graph.handoff.parent_synced","limit":50}'

# Then drain when ready
curl -X POST "http://127.0.0.1:8000/projects/<project-id>/events/dispatch" \
  -H "Authorization: Bearer bfz_..."
```

### Handoff child worker DLQ

1. Child metadata: `handoff_worker.dead_lettered=true`
2. Redis DLQ list (optional): key above
3. **Single:** `POST /agent-runs/{child_run_id}/handoff/replay`
4. **Batch:** `POST /agent-runs/handoff/replay-batch`
5. Drain: `POST /agent-runs/process-handoff-children` or enable scheduler

```bash
curl -X POST "http://127.0.0.1:8000/agent-runs/handoff/replay-batch" \
  -H "Authorization: Bearer bfz_..." \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<project-uuid>","limit":50}'
```

### Delivery log cleanup (Phase 3.12)

Removes **webhook_delivery_logs** older than the threshold only — does **not** delete `event_outbox` rows.

```bash
curl -X DELETE "http://127.0.0.1:8000/projects/<project-id>/webhook-deliveries/cleanup?older_than_days=30" \
  -H "Authorization: Bearer bfz_..."
```

`older_than_days` must be between **7** and **365**.

## Background schedulers

| Setting | Default | Role |
|---------|---------|------|
| `GRAPH_HANDOFF_SCHEDULER_ENABLED` | `false` | Drains handoff Redis queue per owner |
| `EVENT_OUTBOX_DISPATCHER_ENABLED` | `false` | Dispatches pending outbox events to webhooks |

Manual drains always work via the POST endpoints above.

## Phase 3 freeze checklist (3.16)

Phase 3 is **feature-frozen**. Full audit: `docs/phase_3_production_readiness_audit.md`.

### How to rollback to classic

```bash
AGENT_EXECUTION_FORCE_CLASSIC=true
```

Restart the app. All `/execute` calls use classic regardless of project config or `?engine=`.

### How to debug a failed webhook

1. `GET /projects/{id}/events?status=failed` (or `dead_lettered`)
2. `GET /projects/{id}/webhook-deliveries` — check `status`, `error`, `target_url_preview` (no query tokens)
3. Signing secret is **not** in list/logs; use the secret saved at webhook create time
4. Replay: `POST /projects/{id}/events/{event_id}/replay` then `POST /projects/{id}/events/dispatch`
5. `GET /health/operations` — `pending_outbox_count`, `config_warnings`

### How to replay a failed AgentRun safely

1. Confirm source run is `failed` or `cancelled`
2. `POST /agent-runs/{source_id}/replay` → new run `queued` with `metadata.replay`
3. `POST /agent-runs/{new_id}/execute` (optional `Idempotency-Key`)
4. **Do not** call `/execute` on the failed source run (409)

### Known limitations before Phase 4

- Mock LLM by default; production keys and SLOs are operator-owned
- In-memory graph checkpoints unless you plug a durable store
- At-least-once webhook delivery — consumers should be idempotent
- Write tools (`memory.write`, `task.create`, …) are policy-denied
- No in-place AgentRun reset

### Config warnings

`GET /health/operations` returns `config_warnings` (compact codes) when env combinations are risky, e.g. scheduler on without Redis, or `FORCE_CLASSIC` with `AGENT_EXECUTION_ENGINE=langgraph`.

## Phase history

- **3.9** — Outbox → signed project webhooks
- **3.10** — Delivery logs, `dead_lettered`, replay APIs
- **3.11** — Operational metrics + `/health/operations`
- **3.12** — Batch replay (outbox + handoff DLQ) + delivery log cleanup
- **3.13** — Unified `POST /agent-runs/{id}/execute` + engine resolver + rollback
- **3.14** — Execute idempotency + concurrency guard
- **3.15** — AgentRun clone replay (`POST /agent-runs/{id}/replay`)
- **3.16** — Production readiness audit + invariants + config warnings (freeze)
