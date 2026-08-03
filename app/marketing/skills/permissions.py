"""Marketing skills permissions (Phase AI.228)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.schemas.contracts import MarketingSkillType
from app.tools.security import find_forbidden_tool_key


def marketing_skills_enabled(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    if cfg.marketing_skills_enabled:
        return True
    return cfg.is_development and cfg.marketing_skills_mock_enabled


def assert_skill_enabled(skill_type: MarketingSkillType) -> None:
    settings = get_settings()
    if not marketing_skills_enabled(settings):
        raise InvalidStateError("marketing_skills_disabled")
    if settings.is_production and not settings.marketing_skills_enabled:
        raise InvalidStateError("marketing_skills_disabled")
    _ = skill_type


def assert_safe_skill_input(payload: dict[str, Any]) -> dict[str, Any]:
    forbidden = find_forbidden_tool_key(payload)
    if forbidden is not None:
        raise InvalidStateError("marketing_skill_forbidden_input_key")
    sanitized = sanitize_payload(payload)
    if not isinstance(sanitized, dict):
        raise InvalidStateError("marketing_skill_invalid_input")
    return sanitized
