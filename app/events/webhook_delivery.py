"""HTTP delivery of outbox events to project webhook URLs."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.event_outbox import EventOutboxTable
from app.db.models.project_webhook import ProjectWebhookTable

RESPONSE_PREVIEW_MAX = 500
ERROR_MESSAGE_MAX = 500


@dataclass(frozen=True)
class WebhookDeliveryResult:
    status: str
    http_status_code: int | None
    duration_ms: int
    error_code: str | None
    error_message: str | None
    response_preview: str | None


def build_webhook_envelope(event: EventOutboxTable) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "type": event.event_type.value,
        "project_id": str(event.project_id),
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "created_at": event.created_at.isoformat(),
        "data": dict(event.payload or {}),
    }


def sign_webhook_body(*, signing_secret: str, timestamp: str, body: bytes) -> str:
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(
        signing_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def sanitize_delivery_error(message: str, *, max_length: int = ERROR_MESSAGE_MAX) -> str:
    cleaned = sanitize_text(message or "webhook_delivery_failed")
    if "traceback" in cleaned.lower():
        cleaned = "webhook_delivery_failed"
    if len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned


def truncate_response_preview(text: str, *, max_length: int = RESPONSE_PREVIEW_MAX) -> str:
    cleaned = sanitize_text(text or "")
    if len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned


async def deliver_event_to_webhook(
    event: EventOutboxTable,
    webhook: ProjectWebhookTable,
    *,
    client: httpx.AsyncClient | None = None,
) -> WebhookDeliveryResult:
    settings = get_settings()
    envelope = build_webhook_envelope(event)
    body = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    timestamp = utc_now().isoformat()
    signature = sign_webhook_body(
        signing_secret=webhook.signing_secret,
        timestamp=timestamp,
        body=body,
    )
    headers = {
        "Content-Type": "application/json",
        "X-BotFazer-Event-Id": str(event.id),
        "X-BotFazer-Event-Type": event.event_type.value,
        "X-BotFazer-Timestamp": timestamp,
        "X-BotFazer-Signature": signature,
    }

    owns_client = client is None
    http = client or httpx.AsyncClient(
        timeout=httpx.Timeout(settings.event_outbox_webhook_timeout_seconds),
        trust_env=False,
    )
    started = time.perf_counter()
    try:
        response = await http.post(webhook.url, content=body, headers=headers)
        duration_ms = int((time.perf_counter() - started) * 1000)
        preview = truncate_response_preview(response.text)
        if response.status_code >= 400:
            return WebhookDeliveryResult(
                status="failed",
                http_status_code=response.status_code,
                duration_ms=duration_ms,
                error_code=f"http_{response.status_code}",
                error_message=sanitize_delivery_error(f"webhook_http_{response.status_code}"),
                response_preview=preview,
            )
        return WebhookDeliveryResult(
            status="succeeded",
            http_status_code=response.status_code,
            duration_ms=duration_ms,
            error_code=None,
            error_message=None,
            response_preview=preview,
        )
    except httpx.TimeoutException:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return WebhookDeliveryResult(
            status="failed",
            http_status_code=None,
            duration_ms=duration_ms,
            error_code="timeout",
            error_message=sanitize_delivery_error("webhook_timeout"),
            response_preview=None,
        )
    except httpx.HTTPError as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return WebhookDeliveryResult(
            status="failed",
            http_status_code=None,
            duration_ms=duration_ms,
            error_code="http_error",
            error_message=sanitize_delivery_error(str(exc)),
            response_preview=None,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return WebhookDeliveryResult(
            status="failed",
            http_status_code=None,
            duration_ms=duration_ms,
            error_code="delivery_error",
            error_message=sanitize_delivery_error(str(exc)),
            response_preview=None,
        )
    finally:
        if owns_client:
            await http.aclose()
