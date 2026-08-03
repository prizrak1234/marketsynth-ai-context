"""Telegram publishing provider — gated, token from settings only (Phase AI.72)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublishingChannelTable
from app.publishing.providers.base import PublishingProvider
from app.publishing.providers.contracts import (
    PublishingExecutionInput,
    PublishingExecutionResult,
    PublishingProviderType,
)
from app.publishing.providers.safe_result import build_telegram_result_metadata
from app.publishing.providers.telegram_errors import normalize_telegram_error
from app.publishing.telegram_channel_config import (
    TelegramChannelConfig,
    validate_telegram_channel_config,
)


def assert_telegram_publishing_ready(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    if not resolved.telegram_publication_enabled:
        raise InvalidStateError("telegram_publishing_disabled")
    token = (
        resolved.telegram_publication_bot_token.get_secret_value()
        if resolved.telegram_publication_bot_token
        else ""
    )
    if not token.strip():
        raise InvalidStateError("telegram_missing_bot_token")


def build_message_text(payload_snapshot: dict[str, Any]) -> str:
    title = str(payload_snapshot.get("title", "")).strip()
    body = str(payload_snapshot.get("body", "")).strip()
    cta = payload_snapshot.get("cta")
    parts: list[str] = []
    if title:
        parts.append(title)
    if body:
        parts.append(body)
    if cta:
        parts.append(str(cta).strip())
    text = "\n\n".join(parts).strip()
    if not text:
        raise ValueError("payload_snapshot has no publishable text")
    return text[:4096]


def _telegram_api_url(token: str) -> str:
    return f"https://api.telegram.org/bot{token}/sendMessage"


class TelegramPublishingProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def publish(
        self,
        job: PublicationPackageJobTable,
        channel: PublishingChannelTable,
        payload_snapshot: dict[str, Any],
        *,
        execution_input: PublishingExecutionInput,
    ) -> PublishingExecutionResult:
        started = time.perf_counter()
        try:
            assert_telegram_publishing_ready(self._settings)
        except InvalidStateError as exc:
            detail = str(exc)
            if "missing_bot_token" in detail:
                error_code, error_message = (
                    "telegram_auth_failed",
                    "Telegram bot token is not configured",
                )
            elif "disabled" in detail:
                error_code, error_message = (
                    "telegram_unavailable",
                    "Telegram publishing is disabled",
                )
            else:
                error_code, error_message = "telegram_unavailable", detail
            return PublishingExecutionResult(
                success=False,
                provider=PublishingProviderType.TELEGRAM,
                error_code=error_code,
                error_message=error_message,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        token = self._settings.telegram_publication_bot_token.get_secret_value()  # type: ignore[union-attr]
        timeout = self._settings.telegram_publication_timeout_seconds

        try:
            config = validate_telegram_channel_config(channel.channel_config)
            text = build_message_text(payload_snapshot)
        except (InvalidStateError, ValueError) as exc:
            return PublishingExecutionResult(
                success=False,
                provider=PublishingProviderType.TELEGRAM,
                error_code="telegram_bad_request",
                error_message=str(exc)[:240],
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        payload: dict[str, Any] = {"chat_id": config.chat_id, "text": text}
        if config.parse_mode is not None:
            payload["parse_mode"] = config.parse_mode
        if config.disable_web_page_preview:
            payload["disable_web_page_preview"] = True

        status_code: int | None
        body: dict[str, Any] | None
        runtime_error: str | None = None
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=timeout) as client:
                resp = await client.post(_telegram_api_url(token), json=payload)
            status_code = resp.status_code
            try:
                parsed = resp.json()
                body = parsed if isinstance(parsed, dict) else None
            except Exception:
                body = None
        except httpx.TimeoutException:
            status_code = None
            body = {"ok": False, "description": "timeout"}
            runtime_error = "timeout"
        except httpx.HTTPError:
            status_code = None
            body = {"ok": False, "description": "network_error"}
            runtime_error = "network_error"

        latency_ms = int((time.perf_counter() - started) * 1000)
        if body and body.get("ok") is True:
            result = body.get("result")
            message_id = result.get("message_id") if isinstance(result, dict) else None
            return PublishingExecutionResult(
                success=True,
                provider=PublishingProviderType.TELEGRAM,
                result_metadata=build_telegram_result_metadata(
                    chat_id=config.chat_id,
                    message_id=int(message_id) if message_id is not None else None,
                ),
                latency_ms=latency_ms,
            )

        error_code, error_message = normalize_telegram_error(
            status_code=status_code,
            body=body,
            runtime_error=runtime_error,
        )
        return PublishingExecutionResult(
            success=False,
            provider=PublishingProviderType.TELEGRAM,
            error_code=error_code,
            error_message=error_message,
            latency_ms=latency_ms,
        )


def get_telegram_provider(settings: Settings | None = None) -> PublishingProvider:
    return TelegramPublishingProvider(settings=settings)
