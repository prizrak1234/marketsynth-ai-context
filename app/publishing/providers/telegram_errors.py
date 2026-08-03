"""Telegram API error normalization (Phase AI.72)."""

from __future__ import annotations

from typing import Any


def normalize_telegram_error(
    *,
    status_code: int | None,
    body: dict[str, Any] | None,
    runtime_error: str | None = None,
) -> tuple[str, str]:
    if runtime_error == "telegram_publication_disabled":
        return "telegram_unavailable", "Telegram publishing is disabled"
    if runtime_error == "telegram_publication_missing_bot_token":
        return "telegram_auth_failed", "Telegram bot token is not configured"
    if runtime_error in ("timeout", "network_error") or status_code is None:
        return "telegram_unavailable", "Telegram API is unavailable"
    if status_code in (401, 403):
        return "telegram_auth_failed", "Telegram authentication failed"
    if status_code == 429:
        return "telegram_rate_limited", "Telegram rate limit exceeded"
    if status_code == 400:
        description = ""
        if isinstance(body, dict):
            description = str(body.get("description", ""))[:200]
        return "telegram_bad_request", description or "Telegram rejected the request"
    if status_code and status_code >= 500:
        return "telegram_unavailable", f"Telegram server error ({status_code})"
    return "telegram_unknown_error", f"Telegram error (HTTP {status_code})"
