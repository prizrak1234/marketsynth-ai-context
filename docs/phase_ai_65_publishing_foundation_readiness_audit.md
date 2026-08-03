# Phase AI.65 — Publishing foundation readiness audit

**Status:** Production freeze (AI.60–AI.64).  
**Prerequisite:** [AI.45 content production freeze](phase_ai_45_content_production_readiness_audit.md).

## Canonical flow (frozen)

```
ContentAsset (approved)
  → PublicationPackage (draft → review → approved)
  → PublishingFoundationChannel (active)
  → PublicationPackageJob (queued → running → dry_run_succeeded)
```

**Not in this flow:** Telegram/Instagram/LinkedIn API calls, schedulers, auto-publish, publish from ContentAsset directly.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.60** | Foundation channel registry (`publishing-foundation/channels`) |
| **AI.61** | PublicationPackage review workflow |
| **AI.62** | `publication_package_jobs` skeleton + immutable snapshot |
| **AI.63** | Dry-run provider (deterministic, no HTTP) |
| **AI.64** | Audit events + project metrics |
| **AI.65** | **Freeze** — this doc + invariant tests |

---

## API surface

| Action | Endpoint |
|--------|----------|
| Channels CRUD | `GET/POST/PATCH .../publishing-foundation/channels` |
| Archive channel | `POST .../channels/{id}/archive` |
| Package review | `POST .../publication-packages/{id}/submit-review\|approve\|archive` |
| Create job | `POST .../publication-packages/{id}/publication-jobs?channel_id=` |
| Start / dry-run | `POST .../publication-package-jobs/{id}/start\|complete-dry-run\|execute-dry-run` |
| Metrics | `GET .../publishing-foundation/metrics` |

Legacy Phase 6 asset-based `publication_jobs` and worker remain separate and unchanged.

---

## Safety rules

- No tokens/secrets in `config_metadata`
- No full payload duplication in audit events
- `payload_snapshot` frozen at job creation
- Dry-run only — `dry_run_succeeded` terminal success

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
  tests/test_phase_ai_44_content_asset_publication_package_conversion.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py -q
```

Reliability freeze: [phase_ai_69_publishing_reliability_readiness_audit.md](phase_ai_69_publishing_reliability_readiness_audit.md)
