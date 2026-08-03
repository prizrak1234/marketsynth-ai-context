## Phase 8.4 — Scheduling readiness audit (freeze)

This document freezes the **scheduled publication** feature set introduced in Phase 8.0–8.3.
It is intentionally **read-only / invariant-focused**: no new functionality is introduced here.

### Scope

- Status model and timestamps
- UTC-only datetime rules (create/reschedule/calendar)
- Scheduling APIs (create/reschedule/cancel)
- Calendar read model API
- Operational metrics for scheduling (Phase 8.3)
- Worker-driven release flow (no cron)
- Replay policy
- Approved-only + pinned asset version invariants
- Known limitations / operational notes

---

## Status model

`PublicationJobStatus` includes (relevant subset):

- `scheduled`: waiting until `scheduled_at` becomes due
- `queued`: ready for worker claim/dispatch
- `running` → `succeeded` / `failed`
- `cancelled`

### Scheduling timestamps

- `scheduled_at`: required for `status=scheduled`
- `queued_at`: set when the job first becomes `queued` (immediate queue or via release)

Operationally:

- A scheduled job has `queued_at = null`.
- When released into queue, `queued_at` is set to the release time.

---

## UTC-only rule

All scheduling times are **timezone-aware UTC datetimes**.

### Enforcement points

- **Create** (`POST /projects/{project_id}/publication-jobs`):
  - `scheduled_at` must include timezone (`Z` or offset).
  - must be strictly in the future.
  - normalized to UTC.

- **Reschedule** (`POST /projects/{project_id}/publication-jobs/{job_id}/reschedule`):
  - same rule as create: aware + future-only + normalized to UTC.

- **Calendar filters** (`GET /projects/{project_id}/publication-calendar`):
  - `from_at` / `to_at` must be timezone-aware
  - naive datetimes are rejected (422) — we do not guess timezones.

---

## APIs

### Create

`POST /projects/{project_id}/publication-jobs`

- With `scheduled_at` → creates `status=scheduled` and sets `scheduled_at`, keeps `queued_at=null`.
- Without `scheduled_at` → creates `status=queued` and sets `queued_at`.

### Reschedule

`POST /projects/{project_id}/publication-jobs/{job_id}/reschedule`

- Allowed only for `status=scheduled`
- Updates `scheduled_at`
- Ensures `queued_at=null` after reschedule

### Cancel

`POST /projects/{project_id}/publication-jobs/{job_id}/cancel`

- Allowed for `status=queued` and `status=scheduled`
- For scheduled jobs:
  - sets `status=cancelled`
  - sets `finished_at`
  - writes `error="scheduled_job_cancelled_by_user"`
  - clears `queued_at` to avoid confusing “queued” semantics

---

## Calendar API (read model)

`GET /projects/{project_id}/publication-calendar`

### Default view

By default returns only non-terminal “planning/execution” statuses:

- `scheduled`, `queued`, `running`

### Data exposure (safety)

Calendar items intentionally include only:

- job identifiers and status
- `scheduled_at` / `queued_at`
- `asset_id`, `asset_title`, `asset_version_number`
- channel identifiers and public metadata (`channel_id`, `channel_name`, `channel_type`)

The calendar API must **not** expose:

- asset body
- channel config
- delivery logs / request or response payloads

---

## Operational metrics (Phase 8.3)

Scheduling metrics are exposed under `publishing` in:

- `GET /projects/{id}/operational-metrics`
- `GET /me/operational-metrics` (aggregated across all projects owned by the user)

Fields:

- `scheduled_jobs_count`: current jobs with `status=scheduled`
- `due_scheduled_jobs_count`: scheduled jobs with `scheduled_at <= now`
- `next_scheduled_publication_at`: nearest future scheduled publication time (or `null`)
- `cancelled_scheduled_jobs_24h`: cancelled jobs in last 24h with non-null `scheduled_at`

Safety:

- metrics return **aggregates only**
- no asset body
- no channel config

---

## Worker-driven release flow (no cron)

There is no standalone scheduler process in Phase 8.

Release happens when the publication worker is invoked:

1. `PublicationJobProcessor.process_batch` calls `PublicationSchedulerService.release_due_jobs()`
2. Only after release, it lists queued jobs and processes them.

### Release selection & transitions

Release considers:

- `status=scheduled`
- `scheduled_at <= now`

On success, it transitions a job to:

- `status=queued`
- `queued_at = now`

### Fail-closed behavior

If preconditions are missing or invariants no longer hold, release fails closed:

- job becomes `failed`
- a safe `error` code is written (`scheduled_job_*`)

This prevents infinite “stuck scheduled job” situations.

---

## Replay policy

Replay is intentionally constrained:

- Only `failed` and `cancelled` jobs are replayable.
- `scheduled` jobs are **not replayable** (409).
- Replay always resets to `queued` (never back to `scheduled`).
- Replay does not auto-dispatch; processing remains explicit via `POST .../publication-jobs/process`.

---

## Approved-only + pinned version invariants

Scheduling does **not** weaken the publishing safety boundary:

- Jobs can be created only from **approved** assets.
- A job pins the asset version via `asset_version_number` (derived from `approved_version_number` at creation).
- Release-time checks ensure the job still matches the currently approved version and fails closed on mismatch.

---

## Limitations / notes

- Phase 8 assumes DB schema is at **Alembic head** (includes `scheduled_at` / `queued_at`).
- No “cron” / background scheduler in this phase; scheduled jobs are released when the worker runs.
- Scheduling is UTC-only; UI/client must provide timezone-aware datetimes.

---

## Freeze checklist

```bash
uv run pytest tests/test_phase_8_scheduling_invariants.py
uv run pytest tests/test_publication_scheduling.py
uv run pytest tests/test_publication_scheduling_actions.py
uv run pytest tests/test_publication_scheduling_metrics.py
```

