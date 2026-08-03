# Phase AI.75 — Telegram publishing readiness audit

**Status:** Production freeze (AI.70–AI.74).  
**Prerequisite:** [AI.69 publishing reliability](phase_ai_69_publishing_reliability_readiness_audit.md).

## Canonical real publish flow

```
Approved PublicationPackage + active telegram channel (chat_id in config only)
  → PublicationPackageJob (queued)
  → POST .../publication-package-jobs/{id}/execute  (explicit)
  → snapshot_hash verified
  → Telegram sendMessage (when TELEGRAM_PUBLISHING_ENABLED=true + TELEGRAM_BOT_TOKEN)
  → status=succeeded | failed
```

Dry-run remains: `execute-dry-run` → `dry_run_succeeded`.

## Feature flags (default off)

| Setting | Default |
|---------|---------|
| `TELEGRAM_PUBLISHING_ENABLED` | `false` |
| `TELEGRAM_BOT_TOKEN` | unset (aliases: `TELEGRAM_PUBLICATION_*`) |

## Safety

- Bot token **only** in env/settings (`SecretStr`)
- Channel `config_metadata`: `chat_id`, `parse_mode`, `disable_web_page_preview` only
- No raw Telegram API response in DB/audit
- Safe `result_metadata`: `provider`, `chat_id_hash`, `chat_id_last4`, `message_id`, `status`

## Provider registry

| Channel | Real execute |
|---------|----------------|
| `telegram` | Telegram provider (gated) |
| `instagram`, `linkedin`, `blog` | **409** — not enabled |

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
  tests/test_phase_ai_70_publishing_provider_abstraction.py \
  tests/test_phase_ai_71_telegram_channel_secret_boundary.py \
  tests/test_phase_ai_72_telegram_provider_gated.py \
  tests/test_phase_ai_73_real_publish_endpoint.py \
  tests/test_phase_ai_74_telegram_publish_audit_metrics.py \
  tests/test_phase_ai_75_telegram_publishing_freeze_invariants.py -q
```
