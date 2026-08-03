# Phase 7 — Telegram publication adapter readiness audit (freeze)

**Status:** Telegram adapter frozen at Phase 7.2 as first production publishing channel.  
**Scope:** Approved content assets → publication jobs → worker → Telegram Bot API (`sendMessage` / `sendPhoto`) → delivery logs → replay.

```text
approved asset (pinned version) → publication job → worker → telegram adapter → delivery log
                                          ↑
                                        replay (failed only, no auto-dispatch)
```

---

## Text publish

**Flow:**

- Channel: `PublishingChannelType.TELEGRAM` with `chat_id` + optional `parse_mode` + `disable_web_page_preview`.
- Job creation: only for `ContentAssetStatus.APPROVED` with non-null `approved_version_number`.
- Worker:
  - Loads `ContentAssetVersion` for `asset_version_number` (approved pinned version).
  - Builds text from approved version `body` (fallback: `title`).
  - Calls Telegram adapter `sendMessage` with:
    - `chat_id` from channel config.
    - `text` from approved version.
    - optional `parse_mode`, `disable_web_page_preview`.

**Success:** `PublicationDeliveryLog` row with:

- `status = succeeded`
- `response_preview` like `method=sendMessage media_type=text telegram_message_id=123`.

---

## Photo publish

**Media source:**

- `ContentAssetVersion.version_metadata` (approved version snapshot) may contain:
  - `media_url` (preferred) or `image_url`.
- Only **remote** HTTP/HTTPS URLs are used; server does **not** download media in Phase 7.2.

**Flow:**

- If `media_url` / `image_url` present and valid:
  - Adapter calls `sendPhoto` with:
    - `chat_id` from channel config.
    - `photo` = media URL.
    - `caption` = approved version `body` (truncated at API boundary only as needed).
    - optional `parse_mode`, `disable_web_page_preview`.
- Otherwise: falls back to text-only `sendMessage`.

**Success:** `PublicationDeliveryLog` row with:

- `status = succeeded`
- `response_preview` like `method=sendPhoto media_type=photo telegram_message_id=777`.

---

## Approved-only invariant

- Jobs created **only** for `ContentAssetStatus.APPROVED` with non-null `approved_version_number`.
- Draft assets or assets without `approved_version_number` → `409` on job create (Phase 6 tests).
- Telegram adapter does not bypass or weaken this rule:
  - Worker always loads `ContentAssetVersion` for `asset_version_number`.
  - No direct publish from raw asset or drafts.

---

## Pinned version invariant

- `PublicationJob.asset_version_number` is pinned to `approved_version_number` at job creation.
- Worker always fetches the exact approved version snapshot:
  - `ContentAssetVersion` for `(asset_id, asset_version_number, owner_id, project_id)`.
- Replay re-queues failed jobs **without** changing `asset_version_number`:
  - Only allowed when:
    - Asset is still `approved`.
    - `asset.approved_version_number` equals `job.asset_version_number`.
- Telegram adapter sees a stable, immutable payload (text + media metadata) per job.

---

## Secret boundaries

**Bot token:**

- Stored only in env/settings (`TELEGRAM_PUBLICATION_BOT_TOKEN` as `SecretStr`).
- Never persisted in DB (`channel_config` validation forbids `bot_token/token/api_key/secret` keys).
- Redacted from `Settings.safe_dict()` for logs.

**Channel config:**

- For `telegram` channels:
  - Allowed fields: `chat_id`, `parse_mode`, `disable_web_page_preview`.
  - Any secret-like keys (bot token, API keys) → `409` on create/update.
  - `config_preview` is derived from config and never contains secrets.

**Media URL:**

- Only remote URLs (`http`/`https` with host).
- Query string is inspected:
  - Secret-like keys (`token`, `api_key`, `apikey`, `secret`, `key`) or values containing these markers → media URL rejected.
  - Job attempt is `skipped` with safe `error_code` (no HTTP call made).
- Media URL is **not** logged: delivery logs contain only safe labels (`method`, `media_type`, `message_id`).

---

## Error taxonomy (Telegram)

Adapter normalizes Telegram errors into stable `error_code` values:

| Condition | `error_code` | Behavior |
|----------|--------------|----------|
| 401/403 | `auth_error` | terminal, `skipped` |
| 400 | `bad_request` | terminal, `skipped` |
| 429 | `rate_limit` | retryable, `failed` |
| timeout | `timeout` | retryable, `failed` |
| network error | `network_error` | retryable, `failed` |
| generic non-2xx | `http_error_<status>` | retryable, `failed` |

Additionally:

- `telegram_publication_disabled` — `telegrams_publication_enabled=false` (no HTTP).
- `telegram_publication_missing_bot_token` — enabled but no token (no HTTP).
- `caption_too_long` — media with caption >1024 chars, terminal skipped (no HTTP).
- `media_url_invalid` / `media_url_*secret*` — media URL rejected due to invalid or secret-looking query (no HTTP).

All error messages are passed through `sanitize_delivery_error` before logging.

---

## Replay behavior

- Replay uses the same rules as generic publishing:
  - Only `failed` / `cancelled` jobs can be replayed (`409` otherwise).
  - Asset must still be `approved`.
  - `asset.approved_version_number` must match `job.asset_version_number`.
  - Channel must be `active`.
- Replay resets:
  - `status=queued`, `attempts=0`, `error=null`, `started_at=null`, `finished_at=null`.
- Telegram adapter is not invoked during replay:
  - Replay only re-queues.
  - Actual dispatch happens via `POST .../publication-jobs/process`.

**Terminal skipped jobs:**

- Auth/bad request/caption-too-long/media-url-secret cases are terminal for a given job:
  - Adapter returns `SKIPPED` with specific `error_code`.
  - Worker marks job `failed` with that error.
  - Replay is allowed (same rules as для других каналов), but repeated runs remain skipped until config/content is fixed.

---

## Smoke workflow

Script: `scripts/smoke_publication_telegram.py`

Modes (via env):

- `TELEGRAM_PUBLICATION_SMOKE_MODE=text|photo` (default: `text`).
- `TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL` — required for `photo` mode.

Behavior:

- Safe skip when:
  - Missing `BOTFAZER_API_KEY`/`SMOKE_API_KEY`.
  - Missing `TELEGRAM_PUBLICATION_BOT_TOKEN`.
  - Missing `TELEGRAM_PUBLICATION_CHAT_ID`.
  - `TELEGRAM_PUBLICATION_SMOKE_MODE=photo` but no `TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL`.
- Text mode:
  - Creates email asset with body only.
  - Approves.
  - Creates telegram channel for `chat_id`.
  - Queues job and processes via worker.
- Photo mode:
  - Creates asset with `metadata.media_url = TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL`.
  - Approves (media URL captured in version metadata).
  - Same queue/process pipeline.
- At the end prints job status, attempts, and first delivery status.

No agent execution is involved in smoke scenarios — only HTTP + worker.

---

## Config sanity

`validate_runtime_config` and `GET /health/operations` expose configuration issues via `config_warnings`:

Telegram-specific expectations:

- Warning if `TELEGRAM_PUBLICATION_ENABLED=true` but:
  - `TELEGRAM_PUBLICATION_BOT_TOKEN` is missing.
  - `TELEGRAM_PUBLICATION_TIMEOUT_SECONDS` is outside the expected range (<=0 or >120).
- Warning if Telegram publication is enabled but `PUBLICATION_WORKER_ENABLED=false`:
  - Ensures we do not “enable” Telegram without a worker to actually drain jobs.

These warnings are surfaced on `/health/operations` along with other publication/runtime checks.

---

## Known limitations

- Only `sendMessage` and `sendPhoto` are supported — no other Telegram methods (no albums, no documents, no video) in Phase 7.2.
- Media is referenced by **remote URL** only — server does not fetch files:
  - Good for simplicity and security, but caller must host media.
- No per-channel rate limits or exponential backoff beyond simple retries (`PUBLICATION_JOB_MAX_ATTEMPTS`).
- No idempotent publish semantics — replay on `succeeded` remains forbidden (side effects on Telegram are not automatically deduped).
- MarkdownV2 is allowed via `parse_mode`, but content correctness remains caller’s responsibility (Phase 7.2 does not auto-escape).

---

## Template for future adapters

Telegram adapter establishes the baseline pattern for production publishing channels:

- Approved-only queue and pinned version invariant.
- Clear separation between config (with secrets) and previews/logs (no secrets).
- Structured error taxonomy with terminal vs retryable semantics.
- Replay policy that never auto-dispatches.
- Dedicated smoke script with safe-skip behavior and explicit env variables.

Subsequent adapters (email, Tilda, etc.) should mirror these invariants and safety guarantees.

