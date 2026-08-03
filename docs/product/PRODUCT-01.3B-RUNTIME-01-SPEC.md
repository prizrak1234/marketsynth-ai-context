# PRODUCT-01.3B-RUNTIME-01 — Research Runtime Progress and Partial Result Delivery

**Status:** `in_progress` — RUNTIME-01A implementation (2026-07-30)  
**Blocks:** full PRODUCT-01.3A closure (route unification deferred until PASS)  
**Does not set:** `owner_accepted`

---

## RUNTIME-01 increment sequence (single slice — no parallel tracks)

| Increment | Scope |
|-----------|--------|
| **01A** | Durable in-process run lifecycle (DB queue + dispatcher + startup recovery) — **current** |
| 01B | Workspace progress polling |
| 01C | Partial output on insufficient evidence |
| 01D | Customer-safe partial-result UI |
| **01E** | Intake routing unification (7-step) **+ commercial surface freeze** |
| 01F | Automated E2E |
| 01G | Owner smoke |

---

## Persistent async definition (mandatory correction)

**Persistent async** means run state and recoverability are defined by **persisted DB rows**, not by the existence of an `asyncio.Task` in process memory.

`asyncio.create_task()` is allowed only as the **execution mechanism after** a committed `queued` row — never as the source of truth for run state.

### Minimal durable lifecycle (01A)

```
POST /runs → persisted row status=queued → commit → dispatch run_id → 202 Accepted

Dispatcher: queued → claim → running → pipeline → succeeded | failed

Startup recovery:
  queued → re-dispatch
  stale running (no heartbeat / updated_at past timeout) → failed, error_code=research_execution_interrupted
  (no safe requeue until external-call idempotency is proven)
```

---

## PRODUCT-01.3A status (split, no logical mess)

| Sub-slice | Status |
|-----------|--------|
| **01.3A identity/persistence** | **owner verified PASS** |
| **01.3A full closure** | **deferred** — pending route unification after RUNTIME-01 PASS |
| **Current blocker** | **PRODUCT-01.3B-RUNTIME-01** |

We are **not** still fixing intake identity. The active defect is **research runtime execution and delivery**.

---

## Goal

Make real research **observable during execution** and deliver an **honest partial result** when evidence gates block verdict — without weakening gates.

## Priority order

1. Persistent async research execution  
2. Progress visibility  
3. Partial result persistence on evidence-gate failure  
4. Customer-safe insufficient-evidence UI  
5. Primary intake routing unification  

---

## Mandatory plan amendments (owner-approved)

### 1. No new DB enum unless proven necessary

**First approach (required):**

```
status = failed
error_code = high_impact_insufficient_sources
result_json.research_terminal_state = insufficient_evidence   # BivResearchTerminalState or string in JSON
partial_report + artifacts in result_json (output != null in API sense)
```

Frontend distinguishes:

- technical failure  
- evidence insufficiency  
- success  

`BusinessIdeaValidationRunStatus` is stored as `VARCHAR(32)` (Python StrEnum) — **no PostgreSQL enum constraint**. New status value is possible without Alembic but **not approved** until necessity is proven with migration + compatibility plan.

Use existing `BivResearchTerminalState.SUCCEEDED_INSUFFICIENT` or add `insufficient_evidence` **inside result_json only**.

### 2. True async — not frontend-only background promise

**Required server contract (01A):**

```
POST /user-requests/{id}/business-idea-validation/runs   → 202 Accepted, run_id, status=queued|running
GET  /user-requests/{id}/business-idea-validation/runs/{run_id}
GET  /user-requests/{id}/business-idea-validation/runs/{run_id}/progress
```

Pipeline continues **after HTTP response**, independent of browser tab. Refresh must restore via persisted run row + poll.

**Pre-implementation audit (2026-07-30):**

- No dedicated BIV background worker today (unlike `publication_worker`, `outbox_dispatcher_scheduler`).
- Run row + `progress_json` persistence already exist; idempotency returns existing active run.
- **01A v1:** commit `queued` row → internal dispatcher claims → `running` → pipeline with fresh DB session. `asyncio.create_task` is execution-only.
- Process restart: `queued` rows re-dispatched; stale `running` → `failed` / `research_execution_interrupted` (no silent eternal running).
- Do **not** mask sync POST with React fire-and-forget as final solution.
- Legacy sync `POST .../run` retained until Golden Path migrates in 01B+.

---

## Architecture constraints

### A. Async execution

- Run persisted before heavy pipeline  
- Return `run_id` without waiting for terminal state  
- Survive refresh via GET run/progress  
- Idempotent submit → no duplicate active runs (extend existing idempotency)

### B. Evidence insufficiency

`high_impact_insufficient_sources` ≠ technical error.

On stop:

- No verdict, no customer_report  
- Persist partial artifacts in `result_json`  
- API `output` must not be null for evidence stops  
- UI: findings, sources, coverage gaps, stop reason, remediation questions  

**Do not weaken evidence gate.**

### C. Status contract

Use persisted `status=failed` + structured `result_json.research_terminal_state` first.

### D. Intake routing + surface freeze (01E)

Primary entry (hero, validate-idea intent, free-text BIV) → **7-step Project Intake** (`/workspace/projects/new`).

**Commercial surface freeze (same increment — not a separate program):**
- One home card: «Проверить идею»
- Hide unsupported capability cards (content, grow, market, launch, website)
- Hide empty nav shells (Review, Channels)
- Disable legacy short BIV as **primary** entry (keep in code for recovery/rerun)

Short BIV form: recovery/clarify only — not primary entry.

---

## Scope / out of scope

**In:** async start, persisted progress, workspace poll, partial persistence, insufficient panel, route unification, refresh recovery, idempotent rerun.

**Out:** query quality, weaker floors, verdict logic, Launch Pack, PRODUCT-QA-01, form redesign, new providers, raw response storage without ADR.

---

## Tests (required)

1. POST start returns run_id before terminal  
2. Run survives navigation + refresh  
3. Progress persisted + readable  
4. `high_impact_insufficient_sources` → partial in result_json  
5. Insufficient → no verdict  
6. Partial contains: sources, findings, gaps, stop reason, remediation  
7. Provider failure stays technical failure  
8. Repeat submit → no duplicate active runs  
9. Primary intent → 7-step intake  
10. Short form not reachable from validate-idea primary path  
11. Playwright: workspace <10s, progress <15s, refresh, partial UI, no blank failure  

---

## PASS / FAIL

**PASS:** quick leave review, live progress, refresh restore, structured partial on insufficient, no fabricated verdict, no output=null on evidence stop, one intake path, E2E not skipped, owner re-smoke PASS.

**FAIL:** sync wait on review, progress only after terminal, generic failure on insufficient, discarded partials, verdict without evidence, duplicate runs, short form as primary entry.

---

## After RUNTIME-01 PASS

1. Close route inconsistency → full 01.3A closure  
2. Owner acceptance intake/runtime path  
3. Open PRODUCT-01.3B.2 (query strategy, coverage, evidence quality)

---

## Pre-implementation audit summary

| Question | Finding |
|----------|---------|
| Background executor for BIV? | **No** — sync in request handler |
| Reusable run model? | **Yes** — `business_idea_validation_runs` + idempotency |
| New endpoints needed? | **Yes** — POST/GET `/runs`, GET `/runs/{id}/progress` |
| Idempotency? | **Yes** — `get_by_idempotency_key`, returns RUNNING without duplicate |
| DB migration for status contract? | **No** for amendment #1 — use `failed` + result_json terminal state |
| Progress during run? | **Yes** — `progress_json` via `PersistingBivRunProgressTracker` |
| Why output=null today? | `ResearchPipelineError` handler returns `output=None`, skips `result_json` write |
