"""Foundation channel config validation by type (Phase AI.71)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError
from app.publishing.telegram_channel_config import (
    telegram_channel_config_to_dict,
    validate_telegram_channel_config,
)
from app.publishing_foundation.safe_config import sanitize_channel_config_metadata


def normalize_foundation_channel_config(
    raw: dict[str, Any] | None,
    *,
    channel_type: str,
) -> dict[str, Any]:
    cleaned = sanitize_channel_config_metadata(raw)
    if channel_type == "telegram":
        validated = validate_telegram_channel_config(cleaned)
        return telegram_channel_config_to_dict(validated)
    allowed = {"locale", "handle", "page_id"}
    if cleaned and not set(cleaned.keys()).issubset(allowed):
        raise InvalidStateError(
            f"Unsupported config_metadata keys for channel type {channel_type}",
        )
    return cleaned
