# Phase 3 — Production readiness audit (freeze before Phase 4)

**Status:** Phase 3 frozen as the execution and delivery layer. No new Phase 3 features after 3.16; Phase 4 builds on this baseline.

**Graph version marker:** `GRAPH_VERSION=3.16` (see `.env.example`).

---

## Execution engines: classic / LangGraph

| Path | Entry | Claim guard | Idempotency |
|------|--------|-------------|-------------|
| Production | `POST /agent-runs/{id}/execute` | Yes (`execution_guard`) | Optional `Idempotency-Key` |
| Debug classic | `POST /agent-runs/{id}/execute-dry-run` | Internal (executor) | No |
| Debug graph | `POST /agent-runs/{id}/execute-graph-dry-run` | Internal (runner) | No |

**Resolver priority** (`engine_resolver`):

1. `AGENT_EXECUTION_FORCE_CLASSIC=true` → classic (rollback)
2. `?engine=` when `AGENT_EXECUTION_ENGINE_REQUEST_OVERRIDE_ENABLED=true`
3. `project.config.execution_engine`
4. `AGENT_EXECUTION_ENGINE` (default `classic`)

LangGraph runs only when `AGENT_EXECUTION_LANGGRAPH_ENABLED=true`.

---

## AgentRun lifecycle

```
queued → running → succeeded | failed | cancelled
```

- **Execute** only from `queued` (atomic claim to `running`).
- **Terminal runs** cannot be re-executed via `/execute` (409).
- **Failed / cancelled** recovery: `POST /agent-runs/{id}/replay` → new `queued` clone (Phase 3.15).
- **No in-place reset** of terminal runs (preserves audit trail).

---

## Idempotency and concurrency guard (3.14)

- Single winner on `claim_queued_run` (`UPDATE … WHERE status='queued'`).
- Concurrent `/execute` → second caller gets `already_running_or_claimed`.
- `Idempotency-Key` on succeeded run: same key returns cached result; different key → 409.
- Metadata: `output_payload.execution` (`engine`, `graph_version`, `started_at`, `finished_at`, `claim_source`).

---

## LangGraph checkpoints

- Checkpoint payload is a **subset** of graph state (`CHECKPOINT_STATE_KEYS`).
- `assert_no_graph_state_secrets` blocks credential-like keys/markers before persist.
- Default store: in-memory (tests); production should wire durable store before heavy load.
- Checkpoints are **per run** — replay clones do not copy parent checkpoints.

---

## Handoff parent / child flow

1. Parent LangGraph run may enqueue a **child** AgentRun (orchestrator → researcher).
2. Child tracked in parent `output_payload.handoff` and child `run_metadata` handoff fields.
3. Redis FIFO: `botfazer:graph:handoff:queue:{owner_id}`.
4. Worker: `POST /agent-runs/process-handoff-children` (feature-flagged).
5. Failures → DLQ: `botfazer:graph:handoff:dlq:{owner_id}` after `GRAPH_HANDOFF_MAX_ATTEMPTS`.

**Scheduler:** `GRAPH_HANDOFF_SCHEDULER_ENABLED` requires Redis for queue operations.

---

## Redis queues and fallback

- Handoff queue/DLQ depth exposed in operational metrics (`redis.queue_depth`, `dlq_depth`).
- If Redis is unavailable: metrics return `redis.available=false` and a safe error string; **HTTP 200** on metrics endpoints.
- Operations health reports `redis: error` and `status: degraded` when Redis is down.

---

## Outbox and webhook delivery

- Events written to `event_outbox` (handoff and other producers).
- Dispatcher: `POST /projects/{id}/events/dispatch` (optional background scheduler).
- Delivery attempts logged in `webhook_delivery_logs` (status, duration, **URL preview without query**).
- Signing: HMAC on body; `signing_secret` returned **once** on webhook create — never in list/metrics/logs.
- Terminal outbox states: `sent`, `failed`, `dead_lettered`; replay resets to `pending` for failed/dead_lettered only.

---

## Replay mechanisms

| Type | Endpoint | Behavior |
|------|----------|----------|
| AgentRun clone | `POST /agent-runs/{id}/replay` | New `queued` run; source unchanged |
| Outbox | `POST /projects/{id}/events/{event_id}/replay` | Reset event to `pending` |
| Outbox batch | `POST /projects/{id}/events/replay-batch` | Batch reset (no auto-dispatch) |
| Handoff DLQ | `POST /agent-runs/{id}/handoff/replay` | Re-queue **handoff child** only |
| Handoff batch | `POST /agent-runs/handoff/replay-batch` | DLQ children by project |

**Do not** use outbox/handoff replay to “re-run” a full parent AgentRun — use AgentRun clone + `/execute`.

---

## Operational metrics (24h window)

- `agent_runs`, `graph_runs`, `handoff`, `outbox`, `webhooks`, `execution`, `replay`, `redis`
- Project: `GET /projects/{id}/operational-metrics`
- Owner: `GET /me/operational-metrics`
- Health: `GET /health/operations` (+ `config_warnings` from 3.16)

---

## Known limitations (before Phase 4)

- Mock LLM default; real providers need keys and operational runbooks.
- Graph checkpoints in-memory unless external store configured.
- Handoff child auto-execute off by default (`GRAPH_HANDOFF_EXECUTE_CHILD=false`).
- No automatic AgentRun replay — manual clone + execute.
- Tool execution: read-only real tools; write tools denied by policy.
- SQLite used in tests; production expects PostgreSQL + Redis.
- Single-region / no multi-tenant rate limits in Phase 3.
- Outbox dispatch does not guarantee exactly-once delivery to webhooks (at-least-once with idempotent consumers recommended).

---

## Rollback strategy

### Immediate: force classic

```bash
AGENT_EXECUTION_FORCE_CLASSIC=true
```

Ignores project `execution_engine` and `?engine=langgraph`.

### Disable LangGraph globally

```bash
AGENT_EXECUTION_LANGGRAPH_ENABLED=false
AGENT_EXECUTION_ENGINE=classic
```

### Stop background workers

```bash
GRAPH_HANDOFF_SCHEDULER_ENABLED=false
EVENT_OUTBOX_DISPATCHER_ENABLED=false
```

### Verify

```bash
curl http://127.0.0.1:8000/health/operations
```

Check `config_warnings`, `redis`, `pending_outbox_count`, `graph_version`.

---

## Phase 3 freeze checklist

- [ ] `uv run pytest` green (invariants + full suite)
- [ ] `uv run ruff check app tests`
- [ ] `uv run alembic upgrade head`
- [ ] `AGENT_EXECUTION_FORCE_CLASSIC` rollback tested in staging
- [ ] `/health/operations` shows expected flags and `config_warnings`
- [ ] Operational metrics load with Redis up and down
- [ ] Webhook signing secret only on create response
- [ ] Failed AgentRun: replay clone → execute (not direct re-execute)
- [ ] Smoke scripts skipped in CI when `BOTFAZER_API_KEY` unset
- [ ] Read `docs/phase_3_langgraph_handoff.md` runbooks before Phase 4

---

## Related docs

- `docs/phase_3_langgraph_handoff.md` — runbooks and API notes
- `AGENTS.md` — assistant rules
- `tests/test_phase_3_invariants.py` — enforced safety rails
