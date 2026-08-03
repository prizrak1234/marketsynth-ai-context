"""Real webhook adapter for approved asset publication (Phase 6.2)."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.db.base import utc_now
from app.db.models.marketing import ContentAssetVersionTable
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.events.delivery_url import build_target_url_preview
from app.events.webhook_delivery import (
    sanitize_delivery_error,
    sign_webhook_body,
    truncate_response_preview,
)
from app.publishing.contracts import PublicationDeliveryLogStatus
from app.publishing.dispatch_result import PublicationDispatchResult
from app.publishing.webhook_channel_config import (
    validate_webhook_channel_config,
)

_RESERVED_HEADER_NAMES = frozenset(
    {
        "content-type",
        "x-botfazer-publication-job-id",
        "x-botfazer-asset-id",
        "x-botfazer-asset-version",
        "x-botfazer-timestamp",
        "x-botfazer-signature",
    },
)


def build_publication_payload(
    job: PublicationJobTable,
    channel: PublishingChannelTable,
    asset_version: ContentAssetVersionTable,
) -> dict[str, Any]:
    return {
        "publication_job_id": str(job.id),
        "project_id": str(job.project_id),
        "asset": {
            "id": str(job.asset_id),
            "version_number": job.asset_version_number,
            "type": str((job.payload_preview or {}).get("asset_type", "email")),
            "title": asset_version.title,
            "body": asset_version.body,
            "metadata": dict(asset_version.version_metadata or {}),
        },
        "channel": {
            "id": str(channel.id),
            "type": "webhook",
            "name": channel.name,
        },
    }


def build_publication_request_headers(
    *,
    job: PublicationJobTable,
    timestamp: str,
    body: bytes,
    signing_secret: str | None,
    extra_headers: dict[str, str] | None,
) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-BotFazer-Publication-Job-Id": str(job.id),
        "X-BotFazer-Asset-Id": str(job.asset_id),
        "X-BotFazer-Asset-Version": str(job.asset_version_number),
        "X-BotFazer-Timestamp": timestamp,
    }
    if signing_secret:
        headers["X-BotFazer-Signature"] = sign_webhook_body(
            signing_secret=signing_secret,
            timestamp=timestamp,
            body=body,
        )
    if extra_headers:
        for key, value in extra_headers.items():
            if key.lower() in _RESERVED_HEADER_NAMES:
                continue
            headers[key] = value
    return headers


def _safe_response_preview(
    *,
    target_url: str,
    http_status: int | None,
    response_text: str | None,
) -> str:
    prefix = build_target_url_preview(target_url)
    if http_status is not None:
        prefix = f"{prefix} http_{http_status}"
    if response_text:
        body_preview = truncate_response_preview(response_text)
        combined = f"{prefix} {body_preview}".strip()
        return truncate_response_preview(combined)
    return truncate_response_preview(prefix)


async def dispatch_webhook_publication(
    job: PublicationJobTable,
    channel: PublishingChannelTable,
    asset_version: ContentAssetVersionTable,
    *,
    timeout_seconds: int,
    client: httpx.AsyncClient | None = None,
) -> PublicationDispatchResult:
    """POST approved asset payload to the channel webhook URL."""
    try:
        webhook_config = validate_webhook_channel_config(channel.channel_config)
    except Exception as exc:
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=0,
            error_code="invalid_webhook_config",
            error_message=sanitize_delivery_error(str(exc)),
            response_preview=build_target_url_preview(
                str((channel.channel_config or {}).get("url", "")),
            ),
        )

    payload = build_publication_payload(job, channel, asset_version)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    timestamp = utc_now().isoformat()
    headers = build_publication_request_headers(
        job=job,
        timestamp=timestamp,
        body=body,
        signing_secret=webhook_config.signing_secret,
        extra_headers=webhook_config.headers,
    )

    owns_client = client is None
    http = client or httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        trust_env=False,
    )
    started = time.perf_counter()
    try:
        response = await http.post(
            webhook_config.url,
            content=body,
            headers=headers,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        preview = _safe_response_preview(
            target_url=webhook_config.url,
            http_status=response.status_code,
            response_text=response.text,
        )
        if response.status_code >= 400:
            return PublicationDispatchResult(
                status=PublicationDeliveryLogStatus.FAILED,
                duration_ms=duration_ms,
                error_code=f"http_{response.status_code}",
                error_message=sanitize_delivery_error(
                    f"publication_webhook_http_{response.status_code}",
                ),
                response_preview=preview,
            )
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.SUCCEEDED,
            duration_ms=duration_ms,
            response_preview=preview,
        )
    except httpx.TimeoutException:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=duration_ms,
            error_code="timeout",
            error_message=sanitize_delivery_error("publication_webhook_timeout"),
            response_preview=build_target_url_preview(webhook_config.url),
        )
    except httpx.HTTPError:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=duration_ms,
            error_code="http_error",
            error_message=sanitize_delivery_error("publication_webhook_http_error"),
            response_preview=build_target_url_preview(webhook_config.url),
        )
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=duration_ms,
            error_code="delivery_error",
            error_message=sanitize_delivery_error("publication_webhook_delivery_failed"),
            response_preview=build_target_url_preview(webhook_config.url),
        )
    finally:
        if owns_client:
            await http.aclose()
