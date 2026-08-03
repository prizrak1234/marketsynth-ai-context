"""Compact publication job payload preview (no secrets, no full body)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.marketing.contracts import ContentAssetType
from app.publishing.contracts import PublishingChannelType


def build_publication_payload_preview(
    *,
    asset_id: UUID,
    asset_version_number: int,
    asset_type: ContentAssetType,
    asset_title: str,
    channel_id: UUID,
    channel_name: str,
    channel_type: PublishingChannelType,
) -> dict[str, Any]:
    title = asset_title.strip()
    if len(title) > 120:
        title = f"{title[:117]}..."
    return {
        "asset_id": str(asset_id),
        "asset_version_number": asset_version_number,
        "asset_type": asset_type.value,
        "asset_title": title,
        "channel_id": str(channel_id),
        "channel_name": channel_name,
        "channel_type": channel_type.value,
    }
