"""Approved ContentAsset → MediaBrief draft (Phase AI.51)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.models.marketing import ContentAssetTable
from app.marketing.contracts import ContentAssetStatus


def assert_asset_eligible_for_media_brief(asset: ContentAssetTable) -> None:
    status = asset.status
    status_value = status.value if hasattr(status, "value") else str(status)
    if status_value != ContentAssetStatus.APPROVED.value:
        raise InvalidStateError("Only approved content assets can create media briefs")


def build_media_brief_fields_from_asset(
    asset: ContentAssetTable,
    *,
    title: str | None = None,
    goal: str | None = None,
    target_audience: str | None = None,
    platform: str | None = None,
    creative_direction: str | None = None,
    visual_style: str | None = None,
    composition: str | None = None,
    text_overlay: str | None = None,
    references: list[Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(asset.asset_metadata or {})
    final_title = sanitize_text(title or asset.title).strip()[:512]
    if not final_title:
        raise InvalidStateError("Media brief title cannot be empty")

    body_excerpt = sanitize_text(asset.body or "")[:2048]
    default_goal = body_excerpt or final_title
    final_goal = sanitize_text(goal or metadata.get("goal") or default_goal)[:4096]
    final_audience = sanitize_text(
        target_audience or metadata.get("target_audience") or "",
    )[:1024]
    final_platform = sanitize_text(platform or metadata.get("platform") or "social")[:128]
    final_direction = sanitize_text(
        creative_direction or metadata.get("creative_direction") or "",
    )[:4096]
    final_style = sanitize_text(visual_style or metadata.get("visual_style") or "")[:2048]
    final_composition = sanitize_text(composition or metadata.get("composition") or "")[:2048]
    final_overlay = sanitize_text(text_overlay or metadata.get("text_overlay") or "")[:1024]

    refs_raw = references if references is not None else metadata.get("references")
    if isinstance(refs_raw, list):
        final_refs = sanitize_payload(refs_raw) or []
    else:
        final_refs = []

    return {
        "title": final_title,
        "goal": final_goal,
        "target_audience": final_audience,
        "platform": final_platform,
        "creative_direction": final_direction,
        "visual_style": final_style,
        "composition": final_composition,
        "text_overlay": final_overlay,
        "references": final_refs,
    }
