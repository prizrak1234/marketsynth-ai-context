"""Map approved Copywriter specialist output to ContentAsset fields (Phase AI.40)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.marketing.contracts import ContentAssetType
from app.marketing.copywriter_output_parser import clean_copywriter_title
from app.schemas.contracts import MarketingSpecialistType

_COPYWRITER_OUTPUT_TYPE = "content_copy"
_MAX_BODY = 8000
_MAX_TITLE = 512


def channel_to_content_asset_type(channel: str) -> ContentAssetType:
    normalized = (channel or "").strip().lower()
    if normalized in {"email", "newsletter"}:
        return ContentAssetType.EMAIL
    if normalized in {"ad", "ads", "ad_copy"}:
        return ContentAssetType.AD_COPY
    if normalized in {"telegram", "social", "telegram_post"}:
        return ContentAssetType.TELEGRAM_POST
    if normalized in {"blog", "article"}:
        return ContentAssetType.ARTICLE
    return ContentAssetType.EMAIL


def extract_content_items(structured_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not structured_data:
        return []
    raw = structured_data.get("content_items")
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        title = entry.get("headline") or entry.get("title")
        body = entry.get("body") or entry.get("text")
        if title and body:
            items.append(entry)
    return items


def build_asset_body_from_items(items: list[dict[str, Any]], *, fallback: str) -> str:
    if not items:
        return sanitize_text(fallback).strip()[:_MAX_BODY]
    sections: list[str] = []
    for index, item in enumerate(items, start=1):
        headline = sanitize_text(str(item.get("headline", ""))).strip()
        hook = sanitize_text(str(item.get("hook", ""))).strip()
        body = sanitize_text(str(item.get("body", ""))).strip()
        cta = sanitize_text(str(item.get("cta", ""))).strip()
        channel = sanitize_text(str(item.get("channel", ""))).strip()
        stage = sanitize_text(str(item.get("funnel_stage", ""))).strip()
        sections.append(
            f"## Item {index}: {headline}\n"
            f"Channel: {channel} · Funnel: {stage}\n\n"
            f"{hook}\n\n{body}\n\nCTA: {cta}",
        )
    combined = "\n\n---\n\n".join(sections)
    return combined[:_MAX_BODY]


def build_single_item_body(item: dict[str, Any]) -> str:
    hook = sanitize_text(str(item.get("hook") or "")).strip()
    body = sanitize_text(str(item.get("body") or item.get("text") or "")).strip()
    cta = sanitize_text(str(item.get("cta") or "")).strip()
    channel = sanitize_text(str(item.get("channel") or "")).strip()
    stage = sanitize_text(str(item.get("funnel_stage") or "")).strip()

    parts: list[str] = []
    if hook:
        parts.append(hook)
    if body:
        parts.append(body)
    if cta:
        parts.append(f"CTA: {cta}")
    combined = "\n\n".join(parts).strip()
    if channel or stage:
        prefix = f"Channel: {channel} · Funnel: {stage}\n\n" if channel or stage else ""
        combined = f"{prefix}{combined}".strip()
    if not combined:
        return ""
    return combined[:_MAX_BODY]


def build_content_asset_fields_from_copywriter_item(
    *,
    item: dict[str, Any],
    slot_index: int,
    fallback_title: str,
    structured_data: dict[str, Any] | None,
    content_planner_output_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    headline = clean_copywriter_title(
        str(item.get("headline") or item.get("title") or ""),
    )
    body = build_single_item_body(item)
    if not headline or not body:
        return None

    channel = str(item.get("channel") or "telegram").strip().lower()
    asset_type = channel_to_content_asset_type(channel)
    asset_title = headline[:_MAX_TITLE] or sanitize_text(fallback_title).strip()[:_MAX_TITLE]

    llm_provider = None
    llm_model = None
    if structured_data:
        llm_provider = structured_data.get("llm_provider")
        llm_model = structured_data.get("model")

    metadata: dict[str, Any] = {
        "conversion_source": "copywriter_specialist_output",
        "content_slot": slot_index,
        "content_item_index": slot_index,
        "quality_state": "draft_ready_for_review",
        "content_factory_generation": True,
        "channel_adaptation": sanitize_text(str(channel)).strip()[:64],
        "content_angle": sanitize_text(str(item.get("angle") or "")).strip()[:200],
        "funnel_stage": sanitize_text(str(item.get("funnel_stage", ""))).strip()[:64],
        "content_pillar": sanitize_text(str(item.get("content_pillar", ""))).strip()[:200],
    }
    if content_planner_output_id:
        metadata["source_content_planner_output_id"] = content_planner_output_id
    if idempotency_key:
        metadata["content_factory_idempotency_key"] = idempotency_key
    if llm_provider:
        metadata["llm_provider"] = str(llm_provider)
    if llm_model:
        metadata["llm_model"] = str(llm_model)

    return {
        "asset_type": asset_type,
        "title": asset_title,
        "body": body,
        "metadata": metadata,
    }


def build_content_asset_fields_from_copywriter(
    *,
    title: str,
    content: str,
    structured_data: dict[str, Any] | None,
) -> dict[str, Any]:
    items = extract_content_items(structured_data)
    asset_title = sanitize_text(title).strip() or "Content copy"
    asset_title = asset_title[:_MAX_TITLE]
    first_channel = str(items[0].get("channel", "email")) if items else "email"
    asset_type = channel_to_content_asset_type(first_channel)
    body = build_asset_body_from_items(items, fallback=content)
    safe_items = [
        {
            key: sanitize_text(str(item.get(key, ""))).strip()[:500]
            for key in (
                "headline",
                "hook",
                "body",
                "cta",
                "funnel_stage",
                "content_pillar",
                "channel",
            )
            if item.get(key)
        }
        for item in items[:10]
    ]
    metadata = {
        "conversion_source": "copywriter_specialist_output",
        "content_item_count": len(items),
        "content_items_preview": safe_items,
    }
    return {
        "asset_type": asset_type,
        "title": asset_title,
        "body": body,
        "metadata": metadata,
    }


def assert_copywriter_output_eligible(
    *,
    specialist: MarketingSpecialistType | str,
    status: str,
    output_type: str,
) -> None:
    specialist_value = (
        specialist.value if isinstance(specialist, MarketingSpecialistType) else str(specialist)
    )
    if specialist_value != MarketingSpecialistType.COPYWRITER.value:
        raise InvalidStateError("Only copywriter specialist outputs can create content assets")
    if status != "approved":
        raise InvalidStateError(
            "Copywriter output must be approved before creating a content asset",
        )
    if output_type != _COPYWRITER_OUTPUT_TYPE:
        raise InvalidStateError("Specialist output is not a copywriter content_copy package")
