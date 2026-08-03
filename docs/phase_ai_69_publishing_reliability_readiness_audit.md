# Phase AI.69 — Publishing reliability readiness audit

**Status:** Production freeze (AI.66–AI.68).  
**Prerequisite:** [AI.65 publishing foundation](phase_ai_65_publishing_foundation_readiness_audit.md).

## Canonical flow (frozen)

```
Approved PublicationPackage + active channel
  → Create job (optional Idempotency-Key → hashed, no raw key stored)
  → payload_snapshot + snapshot_hash frozen at creation
  → start / execute-dry-run verifies hash (tamper → failed + error_code=snapshot_tampered)
  → dry_run_succeeded
  → replay (failed/cancelled only) → new queued job, same snapshot + replay_of_job_id
```

**Still not in scope:** real Telegram/Instagram/LinkedIn APIs, schedulers, platform tokens, webhooks.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.66** | `Idempotency-Key` on job create — hash + fingerprint, no raw key |
| **AI.67** | `POST .../publication-package-jobs/{id}/replay` |
| **AI.68** | `snapshot_hash` + tamper detection on start/execute |
| **AI.69** | **Freeze** — this doc + invariant tests |

---

## Idempotency rules

| Case | Result |
|------|--------|
| Same key + same owner/project/package/channel | **200** — existing job |
| Same key + different package or channel | **409** `idempotency_fingerprint_conflict` |
| No key | Normal create; duplicate active job → **409** |

Stored columns: `idempotency_key_hash`, `idempotency_fingerprint` — never the raw header value.

---

## Replay rules

| Source status | Replay |
|---------------|--------|
| `failed`, `cancelled` | **201** new queued job |
| `queued`, `running`, `dry_run_succeeded` | **409** |

New job copies `payload_snapshot`, `snapshot_hash`, sets `replay_of_job_id`.

---

## Regression

```bash
uv run alembic upgrade head
uv run pytest \
  tests/test_phase_ai_60_publishing_channel_registry.py \
  tests/test_phase_ai_61_publication_package_approval.py \
  tests/test_phase_ai_62_publication_job_skeleton.py \
  tests/test_phase_ai_63_dry_run_publisher.py \
  tests/test_phase_ai_64_publishing_observability.py \
  tests/test_phase_ai_65_publishing_foundation_freeze_invariants.py \
  tests/test_phase_ai_66_publication_job_idempotency.py \
  tests/test_phase_ai_67_publication_job_replay.py \
  tests/test_phase_ai_68_payload_snapshot_integrity.py \
  tests/test_phase_ai_69_publishing_reliability_freeze_invariants.py \
  tests/test_phase_ai_43_publication_package_foundation.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py -q
```

---

## After AI.69

**Done next:** [AI.70–AI.75 Telegram publishing](phase_ai_75_telegram_publishing_readiness_audit.md) (Telegram only).

Other platform adapters — post-Telegram freeze and ops review.
