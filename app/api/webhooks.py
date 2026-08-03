"""Inbound webhooks (Telegram) — validation and PII sanitization only; no business logic yet."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.security import sanitize_payload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = get_logger(__name__)


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    body: dict[str, Any] = await request.json()
    safe_body = sanitize_payload(body, enabled=settings.pii_sanitizer_enabled)

    update_id = safe_body.get("update_id")
    log.info("telegram_webhook_received", update_id=update_id)

    return {"status": "accepted"}
