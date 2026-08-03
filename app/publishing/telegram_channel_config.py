"""Telegram publishing channel config — validation and safe previews (Phase 7.0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from app.core.exceptions import InvalidStateError

TelegramParseMode = Literal["HTML", "MarkdownV2"]


@dataclass(frozen=True)
class TelegramChannelConfig:
    chat_id: str
    parse_mode: TelegramParseMode | None = None
    disable_web_page_preview: bool = False


def _require_non_empty_str(value: object, *, field: str) -> str:
    if isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        raise InvalidStateError(f"Telegram channel config field '{field}' must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise InvalidStateError(f"Telegram channel config field '{field}' is required")
    return cleaned


def _require_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    raise InvalidStateError(f"Telegram channel config field '{field}' must be a boolean")


def validate_telegram_channel_config(config: dict[str, Any] | None) -> TelegramChannelConfig:
    """Validate and normalize telegram channel config for persistence.

    Safety: bot token must never be persisted in DB config.
    """
    if not config:
        raise InvalidStateError("Telegram channel config requires 'chat_id'")

    lowered_keys = {str(key).strip().lower() for key in config}
    forbidden = {"bot_token", "token", "api_key", "secret"}
    if lowered_keys & forbidden:
        raise InvalidStateError("Telegram channel config must not include a bot token or secrets")

    chat_id = _require_non_empty_str(config.get("chat_id"), field="chat_id")

    parse_mode_raw = config.get("parse_mode")
    parse_mode: TelegramParseMode | None = None
    if parse_mode_raw is not None:
        mode = _require_non_empty_str(parse_mode_raw, field="parse_mode")
        if mode not in ("HTML", "MarkdownV2"):
            raise InvalidStateError(
                "Telegram channel config field 'parse_mode' must be HTML, MarkdownV2, or null",
            )
        parse_mode = cast(TelegramParseMode, mode)

    disable_web_page_preview = _require_bool(
        config.get("disable_web_page_preview"),
        field="disable_web_page_preview",
    )

    return TelegramChannelConfig(
        chat_id=chat_id,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


def telegram_channel_config_to_dict(config: TelegramChannelConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {"chat_id": config.chat_id}
    if config.parse_mode is not None:
        payload["parse_mode"] = config.parse_mode
    if config.disable_web_page_preview:
        payload["disable_web_page_preview"] = True
    return payload


def build_telegram_config_preview(config: dict[str, Any] | None) -> dict[str, Any]:
    if not config:
        return {}
    # No secrets are allowed, but keep preview defensive.
    preview: dict[str, Any] = {}
    if "chat_id" in config:
        preview["chat_id"] = str(config.get("chat_id")).strip()
    if "parse_mode" in config:
        preview["parse_mode"] = config.get("parse_mode")
    if "disable_web_page_preview" in config:
        preview["disable_web_page_preview"] = bool(config.get("disable_web_page_preview"))
    return preview

