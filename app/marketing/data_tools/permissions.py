"""Marketing data tool permissions and input safety (Phase AI.221)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.schemas.contracts import MarketingToolType
from app.tools.security import find_forbidden_tool_key


def marketing_tools_enabled(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    if cfg.marketing_data_tools_enabled:
        return True
    return cfg.is_development and cfg.marketing_data_tools_mock_enabled


def assert_tool_enabled(tool_type: MarketingToolType) -> None:
    settings = get_settings()
    if not marketing_tools_enabled(settings):
        raise InvalidStateError("marketing_data_tools_disabled")
    if settings.is_production and not settings.marketing_data_tools_enabled:
        raise InvalidStateError("marketing_data_tools_disabled")


def assert_safe_input_payload(payload: dict[str, Any]) -> dict[str, Any]:
    forbidden = find_forbidden_tool_key(payload)
    if forbidden is not None:
        raise InvalidStateError("marketing_tool_forbidden_input_key")
    sanitized = sanitize_payload(payload)
    if not isinstance(sanitized, dict):
        raise InvalidStateError("marketing_tool_invalid_input")
    return sanitized
