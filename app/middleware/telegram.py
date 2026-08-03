"""Telegram webhook secret verification."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import Settings, get_settings

TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
TELEGRAM_WEBHOOK_PATH = "/webhooks/telegram"


def _configured_secret(settings: Settings) -> str | None:
    if settings.telegram_webhook_secret is None:
        return None
    value = settings.telegram_webhook_secret.get_secret_value()
    return value or None


def check_telegram_webhook_secret(request: Request, settings: Settings) -> None:
    """
    Validate X-Telegram-Bot-Api-Secret-Token for Telegram webhook requests.

    If secret is not configured, skip verification in development only.
    """
    expected = _configured_secret(settings)
    if expected is None:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Telegram webhook secret is not configured",
            )
        return

    header = request.headers.get(TELEGRAM_SECRET_HEADER)
    if not header or not secrets.compare_digest(header, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram webhook secret",
        )


async def verify_telegram_webhook_secret(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """FastAPI dependency for Telegram webhook routes."""
    check_telegram_webhook_secret(request, settings)


class TelegramWebhookMiddleware(BaseHTTPMiddleware):
    """Reject Telegram webhook calls with an invalid secret before handlers run."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if (
            request.method == "POST"
            and request.url.path.rstrip("/") == TELEGRAM_WEBHOOK_PATH
        ):
            settings = get_settings()
            try:
                check_telegram_webhook_secret(request, settings)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                )

        return await call_next(request)
