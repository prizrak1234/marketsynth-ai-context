# Phase AI.79 — Publishing scheduler readiness audit

**Status:** Production freeze (AI.76–AI.79).  
**Prerequisite:** [AI.75 Telegram publishing freeze](phase_ai_75_telegram_publishing_readiness_audit.md), [AI.69 reliability freeze](phase_ai_69_publishing_reliability_readiness_audit.md).

## Canonical flow (frozen)

```
Approved PublicationPackage + active PublishingFoundationChannel
  → PublicationPackageJob (queued, immutable payload_snapshot + snapshot_hash)
  → POST schedule (future scheduled_for)
  → GET scheduled-jobs/due (explicit scan, no background worker)
  → POST dispatch-due (dry_run | real; real Telegram only when feature-flagged)
  → schedule_status=dispatched, job terminal status from provider
```

**Not in this flow:** auto-generated content, approval bypass, recurring campaigns, Instagram/LinkedIn real adapters, background scheduler loops.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.76** | `scheduled_for`, `schedule_status`, dispatch attempt fields + schedule/unschedule API |
| **AI.77** | `PublishingScheduleService` — due list, mark due, explicit dispatch |
| **AI.78** | Scheduler audit events + metrics (`scheduled_jobs_*`, `due_jobs_*`, …) |
| **AI.79** | **Freeze** — this doc + invariant tests |

---

## API surface

| Action | Endpoint |
|--------|----------|
| Schedule job | `POST .../publication-package-jobs/{id}/schedule` |
| Unschedule job | `POST .../publication-package-jobs/{id}/unschedule` |
| List due | `GET .../publishing-foundation/scheduled-jobs/due` |
| Dispatch due | `POST .../publishing-foundation/scheduled-jobs/{id}/dispatch-due` |

Immediate execute paths (`execute`, `execute-dry-run`) from AI.63–75 remain unchanged.

---

## Safety rules

- Only **queued** jobs can be scheduled; `scheduled_for` must be in the future at schedule time.
- Terminal jobs (`dry_run_succeeded`, `succeeded`, `failed`, `cancelled`) cannot be scheduled.
- Package edits after job creation do not alter `payload_snapshot`.
- Due dispatch still runs `snapshot_hash` verification via `PublicationPackageJobService`.
- Real dispatch requires provider registry + `TELEGRAM_PUBLISHING_ENABLED` (Telegram only).
- No tokens, secrets, or raw payload bodies in audit `safe_metadata`.

---

## Regression

```bash
uv run alembic upgrade head
uv run pytest \
  tests/test_phase_ai_76_scheduled_publication_jobs.py \
  tests/test_phase_ai_77_publishing_schedule_service.py \
  tests/test_phase_ai_78_scheduler_audit_metrics.py \
  tests/test_phase_ai_79_publishing_scheduler_freeze_invariants.py \
  tests/test_phase_ai_60_publishing_channel_registry.py \
  tests/test_phase_ai_65_publishing_foundation_freeze_invariants.py \
  tests/test_phase_ai_66_publication_job_idempotency.py \
  tests/test_phase_ai_69_publishing_reliability_freeze_invariants.py \
  tests/test_phase_ai_70_publishing_provider_abstraction.py \
  tests/test_phase_ai_75_telegram_publishing_freeze_invariants.py -q
```

Foundation freeze: [phase_ai_65_publishing_foundation_readiness_audit.md](phase_ai_65_publishing_foundation_readiness_audit.md)
