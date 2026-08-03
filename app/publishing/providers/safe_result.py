"""Safe metadata builders for publishing providers (Phase AI.72)."""

from __future__ import annotations

import hashlib
from typing import Any

from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata


def hash_chat_id(chat_id: str) -> str:
    return hashlib.sha256(chat_id.encode("utf-8")).hexdigest()


def chat_id_last4(chat_id: str) -> str:
    cleaned = chat_id.strip()
    if len(cleaned) <= 4:
        return cleaned
    return cleaned[-4:]


def build_telegram_result_metadata(
    *,
    chat_id: str,
    message_id: int | None,
    status: str = "sent",
) -> dict[str, Any]:
    return sanitize_publishing_metadata(
        {
            "provider": "telegram",
            "chat_id_hash": hash_chat_id(chat_id),
            "chat_id_last4": chat_id_last4(chat_id),
            "message_id": message_id,
            "status": status,
        },
    )
