"""Security entry point — re-exports for backward compatibility."""

from __future__ import annotations

from app.middleware.telegram import check_telegram_webhook_secret, verify_telegram_webhook_secret
from app.security.pii import mask_email, mask_phone, sanitize_payload, sanitize_text

verify_telegram_secret = verify_telegram_webhook_secret


def sanitize_text_for_logs(text: str) -> str:
    return sanitize_text(text)


__all__ = [
    "check_telegram_webhook_secret",
    "mask_email",
    "mask_phone",
    "sanitize_payload",
    "sanitize_text",
    "sanitize_text_for_logs",
    "verify_telegram_secret",
    "verify_telegram_webhook_secret",
]
