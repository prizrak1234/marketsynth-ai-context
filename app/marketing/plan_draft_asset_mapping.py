"""Mechanical mapping from campaign plan content_items to draft assets (Phase 11.0)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.security import sanitize_payload, sanitize_text
from app.marketing.contracts import ContentAssetType
from app.marketing.plan_payload_validation import CampaignPlanContentItem

PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS = 50
SOURCE_PLAN_DRAFT_ID_METADATA_KEY = "source_plan_draft_id"
PLAN_ITEM_INDEX_METADATA_KEY = "plan_item_index"
PLAN_DRAFT_GENERATION_PARTIAL_STATE = "plan_draft_generation_partial_state"


def resolve_asset_type_for_plan_item(channel: str, item_format: str) -> ContentAssetType:
    """Map plan channel/format to a content asset type (mechanical, no LLM)."""
    normalized_channel = channel.strip().lower()
    if normalized_channel in {"telegram", "tg"}:
        return ContentAssetType.TELEGRAM_POST
    if normalized_channel == "email":
        return ContentAssetType.EMAIL
    if normalized_channel in {"landing", "landing_page", "web"}:
        return ContentAssetType.LANDING_PAGE
    if normalized_channel in {"ad", "ads", "ad_copy"}:
        return ContentAssetType.AD_COPY
    if item_format.strip().lower() == "photo":
        return ContentAssetType.TELEGRAM_POST
    return ContentAssetType.ARTICLE


def metadata_source_plan_draft_id(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    value = metadata.get(SOURCE_PLAN_DRAFT_ID_METADATA_KEY)
    if value is None:
        return None
    return str(value)


def metadata_plan_item_index(metadata: dict[str, Any] | None) -> int | None:
    if not metadata:
        return None
    value = metadata.get(PLAN_ITEM_INDEX_METADATA_KEY)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def plan_draft_assets_cover_all_items(
    assets: list[object],
    *,
    expected_count: int,
) -> bool:
    if len(assets) != expected_count:
        return False
    indices: list[int] = []
    for asset in assets:
        index = metadata_plan_item_index(getattr(asset, "asset_metadata", None))
        if index is None:
            return False
        indices.append(index)
    return sorted(indices) == list(range(expected_count))


def build_asset_metadata_for_plan_item(
    *,
    draft_id: UUID,
    item: CampaignPlanContentItem,
    plan_item_index: int,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        SOURCE_PLAN_DRAFT_ID_METADATA_KEY: str(draft_id),
        PLAN_ITEM_INDEX_METADATA_KEY: plan_item_index,
        "channel": item.channel,
        "format": item.format,
    }
    scheduled_at = item.scheduled_at
    if scheduled_at is not None:
        metadata["planned_scheduled_at"] = scheduled_at
    sanitized = sanitize_payload(metadata)
    if not isinstance(sanitized, dict):
        return metadata
    if scheduled_at is not None:
        sanitized["planned_scheduled_at"] = scheduled_at
    return sanitized


def plan_item_to_asset_fields(
    *,
    draft_id: UUID,
    item: CampaignPlanContentItem,
    plan_item_index: int,
) -> dict[str, Any]:
    return {
        "asset_type": resolve_asset_type_for_plan_item(item.channel, item.format),
        "title": sanitize_text(item.title)[:512],
        "body": sanitize_text(item.notes or ""),
        "metadata": build_asset_metadata_for_plan_item(
            draft_id=draft_id,
            item=item,
            plan_item_index=plan_item_index,
        ),
    }
