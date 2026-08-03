"""Telegram adapter for approved asset publication (Phase 7.0)."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import get_settings
from app.events.webhook_delivery import sanitize_delivery_error, truncate_response_preview
from app.publishing.contracts import PublicationDeliveryLogStatus
from app.publishing.dispatch_result import PublicationDispatchResult, truncate_preview
from app.publishing.telegram_channel_config import (
    TelegramChannelConfig,
    validate_telegram_channel_config,
)


def _telegram_api_url(token: str, *, method: str = "sendMessage") -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def _normalize_telegram_error(*, status_code: int | None, body: object | None) -> tuple[str, str]:
    if status_code in (401, 403):
        return "auth_error", "telegram_auth_or_permission_error"
    if status_code == 429:
        return "rate_limit", "telegram_rate_limited"
    if status_code == 400:
        return "bad_request", "telegram_bad_request"
    if status_code is None:
        return "network_error", "telegram_network_error"
    return "http_error", f"telegram_http_error_{status_code}"


def _validate_media_url(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, "media_url_invalid"
    query = parse_qs(parsed.query)
    lower_keys = {k.lower() for k in query}
    forbidden = {"token", "api_key", "apikey", "secret", "key"}
    if lower_keys & forbidden:
        return False, "media_url_contains_secret_params"
    for values in query.values():
        for value in values:
            lowered = value.lower()
            if any(word in lowered for word in ("token", "api_key", "apikey", "secret", "key=")):
                return False, "media_url_contains_secret_values"
    return True, None


async def send_text(
    *,
    config: TelegramChannelConfig,
    text: str,
    timeout_seconds: int,
) -> tuple[int | None, dict[str, Any] | None]:
    settings = get_settings()
    if not settings.telegram_publication_enabled:
        raise RuntimeError("telegram_publication_disabled")
    token = (
        settings.telegram_publication_bot_token.get_secret_value()
        if settings.telegram_publication_bot_token
        else ""
    )
    if not token.strip():
        raise RuntimeError("telegram_publication_missing_bot_token")

    payload: dict[str, Any] = {"chat_id": config.chat_id, "text": text}
    if config.parse_mode is not None:
        payload["parse_mode"] = config.parse_mode
    if config.disable_web_page_preview:
        payload["disable_web_page_preview"] = True

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=timeout_seconds) as client:
            resp = await client.post(_telegram_api_url(token, method="sendMessage"), json=payload)
    except httpx.TimeoutException:
        return None, {"ok": False, "description": "timeout"}
    except httpx.HTTPError:
        return None, {"ok": False, "description": "network_error"}

    try:
        parsed = resp.json()
        if isinstance(parsed, dict):
            return resp.status_code, parsed
    except Exception:
        pass
    return resp.status_code, None


async def send_photo(
    *,
    config: TelegramChannelConfig,
    photo_url: str,
    caption: str | None,
    timeout_seconds: int,
) -> tuple[int | None, dict[str, Any] | None]:
    settings = get_settings()
    if not settings.telegram_publication_enabled:
        raise RuntimeError("telegram_publication_disabled")
    token = (
        settings.telegram_publication_bot_token.get_secret_value()
        if settings.telegram_publication_bot_token
        else ""
    )
    if not token.strip():
        raise RuntimeError("telegram_publication_missing_bot_token")

    payload: dict[str, Any] = {"chat_id": config.chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    if config.parse_mode is not None:
        payload["parse_mode"] = config.parse_mode
    if config.disable_web_page_preview:
        payload["disable_web_page_preview"] = True

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=timeout_seconds) as client:
            resp = await client.post(_telegram_api_url(token, method="sendPhoto"), json=payload)
    except httpx.TimeoutException:
        return None, {"ok": False, "description": "timeout"}
    except httpx.HTTPError:
        return None, {"ok": False, "description": "network_error"}

    try:
        parsed = resp.json()
        if isinstance(parsed, dict):
            return resp.status_code, parsed
    except Exception:
        pass
    return resp.status_code, None


async def dispatch_telegram_publication(
    channel_config: dict[str, Any] | None,
    *,
    text: str,
    media_url: str | None,
) -> PublicationDispatchResult:
    settings = get_settings()
    if not settings.telegram_publication_enabled:
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.SKIPPED,
            duration_ms=0,
            error_code="telegram_publication_disabled",
            error_message=sanitize_delivery_error("telegram_publication_disabled"),
        )
    if settings.telegram_publication_bot_token is None or not (
        settings.telegram_publication_bot_token.get_secret_value().strip()
    ):
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.SKIPPED,
            duration_ms=0,
            error_code="telegram_publication_missing_bot_token",
            error_message=sanitize_delivery_error("telegram_publication_missing_bot_token"),
        )

    config = validate_telegram_channel_config(channel_config)
    trimmed_text = text.strip()

    is_photo = bool(media_url)
    if is_photo and trimmed_text and len(trimmed_text) > 1024:
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.SKIPPED,
            duration_ms=0,
            error_code="caption_too_long",
            error_message=sanitize_delivery_error("telegram_caption_too_long"),
        )

    if is_photo and media_url:
        ok, media_error = _validate_media_url(media_url)
        if not ok:
            code = "media_url_rejected_for_secrets"
            if media_error == "media_url_invalid":
                code = media_error
            return PublicationDispatchResult(
                status=PublicationDeliveryLogStatus.SKIPPED,
                duration_ms=0,
                error_code=code,
                error_message=sanitize_delivery_error(code),
            )

    started = time.perf_counter()
    if is_photo and media_url:
        status_code, body = await send_photo(
            config=config,
            photo_url=media_url,
            caption=trimmed_text or None,
            timeout_seconds=settings.telegram_publication_timeout_seconds,
        )
        method_label = "sendPhoto"
        media_type_label = "photo"
    else:
        status_code, body = await send_text(
            config=config,
            text=trimmed_text,
            timeout_seconds=settings.telegram_publication_timeout_seconds,
        )
        method_label = "sendMessage"
        media_type_label = "text"
    duration_ms = int((time.perf_counter() - started) * 1000)

    ok_flag = isinstance(body, dict) and body.get("ok") is True
    if ok_flag:
        result = body.get("result")
        message_id = None
        if isinstance(result, dict):
            message_id = result.get("message_id")
        preview_parts = [f"method={method_label}", f"media_type={media_type_label}"]
        if message_id is not None:
            preview_parts.append(f"telegram_message_id={message_id}")
        preview = " ".join(preview_parts)
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.SUCCEEDED,
            duration_ms=duration_ms,
            response_preview=truncate_preview(truncate_response_preview(preview)),
        )

    if status_code is None and isinstance(body, dict) and body.get("description") == "timeout":
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=duration_ms,
            error_code="timeout",
            error_message=sanitize_delivery_error("telegram_timeout"),
            response_preview=truncate_preview(truncate_response_preview("timeout")),
        )

    error_code, label = _normalize_telegram_error(status_code=status_code, body=body)
    safe_error = sanitize_delivery_error(label)
    response_preview = None
    if isinstance(body, dict):
        # Keep preview compact and safe. Never include token or request payload.
        description = body.get("description")
        if isinstance(description, str) and description.strip():
            response_preview = truncate_preview(truncate_response_preview(description))
    terminal = error_code in ("auth_error", "bad_request")
    return PublicationDispatchResult(
        status=PublicationDeliveryLogStatus.SKIPPED
        if terminal
        else PublicationDeliveryLogStatus.FAILED,
        duration_ms=duration_ms,
        error_code=error_code,
        error_message=safe_error,
        response_preview=response_preview,
    )

