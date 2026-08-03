"""Campaign-aware revision context for agent chat (Phase AI.8)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ContentAssetTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.repositories.campaign_plan_drafts import CampaignPlanDraftRepository
from app.marketing.contracts import ContentAssetStatus
from app.marketing.plan_payload_validation import CampaignPlanPayloadShape
from app.services.campaign_overview_service import CampaignOverviewService
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.tools.marketing_tools import body_preview

REVISION_CONTEXT_MAX_BYTES = 8192
APPROVED_EXAMPLES_MAX = 3
DESCRIPTION_MAX_CHARS = 600
STRING_FIELD_MAX_CHARS = 400
BODY_PREVIEW_MAX_CHARS = 320

FORBIDDEN_REVISION_CONTEXT_KEYS = frozenset(
    {
        "plan_payload",
        "content_items",
        "campaign_metadata",
        "channel_config",
        "delivery_logs",
        "recent_jobs",
        "delivery",
    },
)


def extract_plan_messaging(plan_payload: dict[str, Any] | None) -> dict[str, str]:
    if not plan_payload:
        return {"target_audience": "", "key_message": "", "channel": ""}
    try:
        shape = CampaignPlanPayloadShape.model_validate(plan_payload)
    except Exception:
        return {"target_audience": "", "key_message": "", "channel": ""}
    channel = ""
    if shape.content_items:
        channel = shape.content_items[0].channel.strip()
    return {
        "target_audience": _truncate(shape.target_audience, STRING_FIELD_MAX_CHARS),
        "key_message": _truncate(shape.key_message, STRING_FIELD_MAX_CHARS),
        "channel": _truncate(channel, 64),
    }


def _truncate(value: str, max_chars: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1].rstrip()}…"


def _asset_channel(asset: ContentAssetTable, *, default_channel: str) -> str:
    metadata = dict(asset.asset_metadata or {})
    for key in ("channel", "target_channel"):
        raw = metadata.get(key)
        if isinstance(raw, str) and raw.strip():
            return _truncate(raw.strip(), 64)
    asset_type = getattr(asset.asset_type, "value", str(asset.asset_type))
    if asset_type == "telegram_post":
        return "telegram"
    if asset_type == "email":
        return "email"
    return default_channel


def build_current_asset_snapshot(
    asset: ContentAssetTable,
    *,
    default_channel: str,
) -> dict[str, Any]:
    return {
        "asset_id": str(asset.id),
        "title": _truncate(asset.title or "", 200),
        "status": getattr(asset.status, "value", str(asset.status)),
        "type": getattr(asset.asset_type, "value", str(asset.asset_type)),
        "channel": _asset_channel(asset, default_channel=default_channel),
        "body_preview": body_preview(asset.body or "")[:BODY_PREVIEW_MAX_CHARS],
        "current_version_number": asset.current_version_number,
    }


def build_approved_asset_example(
    asset: ContentAssetTable,
    *,
    default_channel: str,
) -> dict[str, Any]:
    return {
        "asset_id": str(asset.id),
        "title": _truncate(asset.title or "", 200),
        "channel": _asset_channel(asset, default_channel=default_channel),
        "body_preview": body_preview(asset.body or "")[:BODY_PREVIEW_MAX_CHARS],
    }


def build_campaign_history_summary(counts: object | None) -> dict[str, int]:
    if counts is None:
        return {}
    fields = (
        "assets_total",
        "assets_draft",
        "assets_approved",
        "assets_archived",
        "jobs_total",
        "jobs_scheduled",
        "jobs_succeeded",
    )
    summary: dict[str, int] = {}
    for name in fields:
        value = getattr(counts, name, None)
        if isinstance(value, int):
            summary[name] = value
    return summary


def trim_revision_context(context: dict[str, Any]) -> dict[str, Any]:
    """Enforce REVISION_CONTEXT_MAX_BYTES by shrinking lists and string fields."""
    trimmed = json.loads(json.dumps(context, ensure_ascii=True))
    if _encoded_size(trimmed) <= REVISION_CONTEXT_MAX_BYTES:
        return trimmed

    trimmed["context_truncated"] = True

    examples = trimmed.get("approved_assets_examples")
    if isinstance(examples, list) and len(examples) > 1:
        while len(examples) > 1 and _encoded_size(trimmed) > REVISION_CONTEXT_MAX_BYTES:
            examples.pop()

    current = trimmed.get("current_asset")
    if isinstance(current, dict):
        preview = current.get("body_preview")
        if isinstance(preview, str) and len(preview) > 120:
            current["body_preview"] = _truncate(preview, 120)

    for key in ("campaign_description", "target_audience", "key_message"):
        value = trimmed.get(key)
        if isinstance(value, str) and len(value) > 200:
            trimmed[key] = _truncate(value, 200)

    if _encoded_size(trimmed) > REVISION_CONTEXT_MAX_BYTES:
        trimmed.pop("campaign_history", None)

    if _encoded_size(trimmed) > REVISION_CONTEXT_MAX_BYTES and isinstance(examples, list):
        trimmed["approved_assets_examples"] = examples[:1]

    if _encoded_size(trimmed) > REVISION_CONTEXT_MAX_BYTES:
        trimmed.pop("current_asset", None)

    return trimmed


def missing_campaign_revision_context(*, workflow_state: str = "") -> dict[str, Any]:
    return trim_revision_context(
        {
            "campaign_missing": True,
            "campaign_title": "",
            "campaign_description": "",
            "workflow_state": workflow_state or "unknown",
            "target_audience": "",
            "key_message": "",
            "channel": "",
            "approved_assets_examples": [],
            "campaign_history": {},
        },
    )


def _encoded_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8"))


async def build_campaign_revision_context(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    campaign_id: UUID,
    *,
    current_asset_id: UUID | None = None,
) -> dict[str, Any]:
    campaign_row = await _load_campaign(session, owner_id, project_id, campaign_id)
    if campaign_row is None:
        return missing_campaign_revision_context()

    workflow = await CampaignWorkflowService(session).get_workflow(
        owner_id,
        project_id,
        campaign_id,
    )
    if workflow is not None:
        workflow_state = getattr(
            workflow.workflow_state,
            "value",
            str(workflow.workflow_state),
        )
    else:
        workflow_state = "unknown"

    plan_repo = CampaignPlanDraftRepository(session)
    plan_drafts = await plan_repo.list_by_campaign(
        owner_id,
        project_id,
        campaign_id,
        include_archived=False,
        limit=1,
    )
    plan_signals = extract_plan_messaging(
        dict(plan_drafts[0].plan_payload or {}) if plan_drafts else None,
    )

    assets = await _load_campaign_assets(session, owner_id, project_id, campaign_id)
    approved_examples = [
        build_approved_asset_example(
            row,
            default_channel=plan_signals["channel"],
        )
        for row in assets
        if getattr(row.status, "value", str(row.status)) == ContentAssetStatus.APPROVED.value
    ][:APPROVED_EXAMPLES_MAX]

    current_asset: dict[str, Any] | None = None
    if current_asset_id is not None:
        match = next((row for row in assets if row.id == current_asset_id), None)
        if match is not None:
            current_asset = build_current_asset_snapshot(
                match,
                default_channel=plan_signals["channel"],
            )
    else:
        drafts = [
            row
            for row in assets
            if getattr(row.status, "value", str(row.status)) == ContentAssetStatus.DRAFT.value
        ]
        if len(drafts) == 1:
            current_asset = build_current_asset_snapshot(
                drafts[0],
                default_channel=plan_signals["channel"],
            )

    overview = await CampaignOverviewService(session).get_overview(
        owner_id=owner_id,
        project_id=project_id,
        campaign_id=campaign_id,
    )
    campaign_history = (
        build_campaign_history_summary(overview.counts) if overview is not None else {}
    )

    context: dict[str, Any] = {
        "campaign_title": _truncate(campaign_row.title or "", 200),
        "campaign_description": _truncate(
            campaign_row.description or "",
            DESCRIPTION_MAX_CHARS,
        ),
        "workflow_state": workflow_state,
        "target_audience": plan_signals["target_audience"],
        "key_message": plan_signals["key_message"],
        "channel": plan_signals["channel"],
        "approved_assets_examples": approved_examples,
        "campaign_history": campaign_history,
    }
    if current_asset is not None:
        context["current_asset"] = current_asset

    return trim_revision_context(context)


async def _load_campaign(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    campaign_id: UUID,
) -> MarketingCampaignTable | None:
    statement = select(MarketingCampaignTable).where(
        MarketingCampaignTable.id == campaign_id,
        MarketingCampaignTable.owner_id == owner_id,
        MarketingCampaignTable.project_id == project_id,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _load_campaign_assets(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    campaign_id: UUID,
) -> list[ContentAssetTable]:
    statement = (
        select(ContentAssetTable)
        .where(
            ContentAssetTable.owner_id == owner_id,
            ContentAssetTable.project_id == project_id,
            ContentAssetTable.campaign_id == campaign_id,
        )
        .order_by(ContentAssetTable.updated_at.desc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
