"""Campaign plan_payload validation — size limits and secret key rejection (Phase 10.1)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.llm.secrets_boundary import find_sensitive_key

PLAN_PAYLOAD_MAX_JSON_BYTES = 32_768
CONTENT_ITEM_FORMATS = frozenset({"text", "photo"})


class CampaignPlanContentItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    channel: str = Field(min_length=1, max_length=64)
    format: str = Field(min_length=1, max_length=32)
    scheduled_at: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in CONTENT_ITEM_FORMATS:
            raise ValueError(f"format must be one of: {', '.join(sorted(CONTENT_ITEM_FORMATS))}")
        return normalized

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("scheduled_at must be ISO 8601 datetime") from exc
        if parsed.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware (UTC)")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


class CampaignPlanPayloadShape(BaseModel):
    goal: str = ""
    target_audience: str = ""
    key_message: str = ""
    content_items: list[CampaignPlanContentItem] = Field(default_factory=list)

    @field_validator("goal", "target_audience", "key_message")
    @classmethod
    def sanitize_strings(cls, value: str) -> str:
        return sanitize_text(value or "")[:4000]

    @field_validator("content_items")
    @classmethod
    def limit_content_items(
        cls,
        value: list[CampaignPlanContentItem],
    ) -> list[CampaignPlanContentItem]:
        if len(value) > 100:
            raise ValueError("content_items exceeds maximum of 100 items")
        return value


def _restore_plan_item_scheduled_at(
    sanitized: dict[str, Any],
    items: list[CampaignPlanContentItem],
) -> None:
    """PII sanitize must not corrupt ISO datetimes in content_items.scheduled_at."""
    raw_items = sanitized.get("content_items")
    if not isinstance(raw_items, list):
        return
    for index, item in enumerate(items):
        if index >= len(raw_items) or not isinstance(raw_items[index], dict):
            continue
        if item.scheduled_at is not None:
            raw_items[index]["scheduled_at"] = item.scheduled_at


def validate_and_normalize_plan_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate plan_payload shape, reject secrets, enforce JSON size limit."""
    sensitive = find_sensitive_key(raw)
    if sensitive is not None:
        raise InvalidStateError(f"Sensitive key not allowed in plan_payload: {sensitive}")

    try:
        shape = CampaignPlanPayloadShape.model_validate(raw)
    except ValidationError as exc:
        raise InvalidStateError("Invalid plan_payload") from exc

    normalized = shape.model_dump(mode="json")
    sanitized = sanitize_payload(normalized)
    assert isinstance(sanitized, dict)
    _restore_plan_item_scheduled_at(sanitized, shape.content_items)

    encoded = json.dumps(sanitized, ensure_ascii=True, sort_keys=True).encode("utf-8")
    if len(encoded) > PLAN_PAYLOAD_MAX_JSON_BYTES:
        raise InvalidStateError("plan_payload exceeds size limit")

    return sanitized
