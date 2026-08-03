"""Approved MediaBrief → MediaAsset placeholder (Phase AI.54)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.models.media import MediaBriefTable
from app.marketing.media_contracts import MediaAssetType, MediaBriefStatus

_MEDIA_TYPE_VALUES = frozenset(t.value for t in MediaAssetType)
_PLACEHOLDER_PROVIDER = "placeholder"


def assert_brief_eligible_for_media_asset(brief: MediaBriefTable) -> None:
    status = brief.status
    status_value = status.value if hasattr(status, "value") else str(status)
    if status_value != MediaBriefStatus.APPROVED.value:
        raise InvalidStateError("Only approved media briefs can create media assets")


def parse_media_type(media_type: str) -> MediaAssetType:
    cleaned = sanitize_text(media_type).strip().lower()
    if cleaned not in _MEDIA_TYPE_VALUES:
        raise InvalidStateError(
            f"Unsupported media type: {media_type}. "
            f"Allowed: {', '.join(sorted(_MEDIA_TYPE_VALUES))}",
        )
    return MediaAssetType(cleaned)


def build_placeholder_media_asset_fields(
    brief: MediaBriefTable,
    *,
    media_type: MediaAssetType,
) -> dict[str, Any]:
    metadata = sanitize_payload(
        {
            "conversion_source": "approved_media_brief",
            "placeholder": True,
            "brief_title": brief.title,
            "brief_platform": brief.platform,
            "media_type": media_type.value,
        },
    ) or {}
    return {
        "generation_provider": _PLACEHOLDER_PROVIDER,
        "generation_metadata": metadata,
    }
