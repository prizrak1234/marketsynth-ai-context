# Phase 8.0 — Publication scheduling (freeze)

## Goal

Add **safe deferred publishing** without external cron: a publication job can be created as `scheduled` and will be released into `queued` when its scheduled time arrives.

This keeps the pipeline stable:

```text
approved asset → job (scheduled) → release → queued → worker → adapter → delivery log → replay
```

## Why `scheduled`

We already have reliable production adapters (Telegram/webhook). Scheduling enables:

- “publish at the right time” without manual operator intervention
- consistent behavior across channels (same job model, same logs, same replay policy)
- no new agent permissions (still HTTP-only and approved-only)

## Status model

`PublicationJobStatus` now includes:

- `scheduled` — waiting until `scheduled_at` is due
- `queued` — ready for worker claim/dispatch
- `running` → `succeeded` / `failed`
- `cancelled`

Scheduling-specific timestamps:

- `scheduled_at` — required when `status=scheduled`
- `queued_at` — set when the job first becomes `queued` (immediate queue or release)

## UTC-only rule

Scheduling uses **UTC-aware datetimes only**.

- `scheduled_at` must include timezone info (`Z` or `+00:00`).
- Naive datetimes are **rejected** (we do not guess timezones).
- `scheduled_at` must be strictly in the **future** at creation time.

## API

Endpoint: `POST /projects/{project_id}/publication-jobs`

If `scheduled_at` is present → job is created with `status=scheduled`.  
If not present → job is created with `status=queued` (as before).

Example:

```json
{
  "asset_id": "00000000-0000-0000-0000-000000000000",
  "channel_id": "00000000-0000-0000-0000-000000000000",
  "scheduled_at": "2026-06-03T15:00:00Z"
}
```

## Release behavior (worker-driven)

There is no separate cron process in Phase 8.0.

The publication worker calls `PublicationSchedulerService.release_due_jobs()` before draining queued jobs.  
Release selects jobs:

- `status=scheduled`
- `scheduled_at <= now`
- channel is `active`
- approved-only + pinned version invariants are still valid at release time

Then transitions them to:

- `status=queued`
- `queued_at = now`

If invariants no longer hold (channel paused, asset not approved, version mismatch, missing resources), release **fails closed**:

- job is marked `failed`
- safe `error` code is written to the job (`scheduled_job_*`)

## Replay behavior

Replay policy remains unchanged:

- only `failed` / `cancelled` jobs are replayable
- replay always resets to `queued` (never back to `scheduled`)
- replay does not auto-dispatch; processing still happens via `POST .../publication-jobs/process`

In particular:

- `scheduled` jobs cannot be replayed (`409`)

## Tests

Freeze guard:

```bash
uv run pytest tests/test_publication_scheduling.py
```

## Phase 8.3 — Scheduling operational metrics

Operational metrics now expose scheduling state under the `publishing` block:

- `scheduled_jobs_count`: current jobs with `status=scheduled`
- `due_scheduled_jobs_count`: scheduled jobs with `scheduled_at <= now`
- `next_scheduled_publication_at`: nearest future scheduled publication time (or `null`)
- `cancelled_scheduled_jobs_24h`: cancelled jobs in last 24h with non-null `scheduled_at`

Test:

```bash
uv run pytest tests/test_publication_scheduling_metrics.py
```

