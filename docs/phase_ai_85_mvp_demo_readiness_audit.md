# Phase AI.85 — MVP demo readiness audit

**Status:** Production freeze (AI.80–AI.85).  
**Prerequisite:** [AI.79 publishing scheduler](phase_ai_79_publishing_scheduler_readiness_audit.md), [AI.75 Telegram publishing](phase_ai_75_telegram_publishing_readiness_audit.md).

## Full demo flow (frozen)

```
User task (chat / seed)
  → MarketingPlan (approved)
  → MarketingPlanExecutionRun (6 specialists)
  → Copywriter output (approved)
  → ContentAsset (approved)
  → MediaBrief (approved)
  → MediaAsset (placeholder)
  → PublicationPackage (approved)
  → PublishingFoundationChannel (Telegram, active, dry-run config)
  → PublicationPackageJob (queued, scheduled)
  → Explicit dispatch-due (dry_run | real gated)
```

**Out of scope:** Instagram/LinkedIn real adapters, background scheduler worker, billing, multi-user collaboration, new agents, auto-publish decisions.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.80** | `scripts/seed_e2e_demo.py` — idempotent full-chain seed |
| **AI.81** | `GET /projects/{id}/demo-flow/status` (dev/demo flag) |
| **AI.82** | Dashboard checklist panel (`E2eDemoFlowChecklist`) |
| **AI.83** | `GET /projects/{id}/provenance/content-production/{job_id}` |
| **AI.84** | `tests/test_phase_ai_84_mvp_safety_regression.py` |
| **AI.85** | **Freeze** — this doc |

---

## Commands

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run python scripts/seed_e2e_demo.py
# optional: --refresh-api-key  --reset-db (sqlite only)
```

Set UI env from seed output (`NEXT_PUBLIC_BOTFAZER_PROJECT_ID`, `NEXT_PUBLIC_BOTFAZER_API_KEY`).

Enable status/provenance in production only when needed:

```bash
DEMO_FLOW_ENDPOINTS_ENABLED=true
```

---

## API (read-only)

| Endpoint | Purpose |
|----------|---------|
| `GET .../demo-flow/status` | Aggregate statuses + `next_available_action` + resource link ids |
| `GET .../provenance/content-production/{job_id}` | Chain ids/statuses only |

No mutation. No raw bodies, prompts, or provider payloads in responses.

---

## Regression

```bash
uv run pytest \
  tests/test_phase_ai_80_e2e_demo_seed.py \
  tests/test_phase_ai_81_demo_flow_status.py \
  tests/test_phase_ai_83_content_production_provenance.py \
  tests/test_phase_ai_84_mvp_safety_regression.py \
  tests/test_phase_ai_76_scheduled_publication_jobs.py \
  tests/test_phase_ai_79_publishing_scheduler_freeze_invariants.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py \
  tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py -q
```

---

## Known limitations

- Seed uses **mock LLM** specialists (no external HTTP).
- Telegram **real** publish requires `TELEGRAM_PUBLISHING_ENABLED` + token; demo channel uses `chat_id` only in safe metadata.
- Checklist is **read-only**; actions happen in existing panels/routes.
- Legacy campaign plan draft seed (`seed_demo_marketing_flow.py`) is a separate UI path.
