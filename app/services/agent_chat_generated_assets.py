"""Generate-assets artifacts from agent chat runs (Phase AI.5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.agent_chat import AgentChatGeneratedAssets
from app.tools.marketing_tools import CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME


def format_generate_assets_chat_assistant_message(
    *,
    created_count: int,
    already_generated: bool,
) -> str:
    if already_generated:
        return "Черновики уже были созданы ранее. Открой Review Queue."
    return (
        f"Черновики созданы: {created_count}.\n"
        "Следующий шаг: Review Queue → проверить и утвердить."
    )


def _parse_generated_assets_from_preview(
    *,
    arguments_preview: dict[str, object],
    result_preview: dict[str, object],
) -> AgentChatGeneratedAssets | None:
    if not result_preview.get("ok"):
        return None

    campaign_id = arguments_preview.get("campaign_id")
    draft_id = arguments_preview.get("draft_id")
    if not isinstance(campaign_id, str) or not isinstance(draft_id, str):
        return None

    created_count = result_preview.get("created_count")
    already_generated = result_preview.get("already_generated")
    asset_ids_raw = result_preview.get("asset_ids")
    if not isinstance(created_count, int) or not isinstance(already_generated, bool):
        return None
    if not isinstance(asset_ids_raw, list):
        return None

    asset_ids = [str(item) for item in asset_ids_raw]
    return AgentChatGeneratedAssets(
        campaign_id=UUID(campaign_id),
        draft_id=UUID(draft_id),
        created_count=created_count,
        already_generated=already_generated,
        asset_ids=[UUID(item) for item in asset_ids],
    )


async def find_generated_assets_from_run(
    session: AsyncSession,
    owner_id: UUID,
    agent_run_id: UUID,
) -> AgentChatGeneratedAssets | None:
    logs = await ToolExecutionLogRepository(session).list_by_run(owner_id, agent_run_id)
    for log in reversed(logs):
        if log.tool_name != CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME:
            continue
        if log.status != "succeeded":
            continue
        parsed = _parse_generated_assets_from_preview(
            arguments_preview=dict(log.arguments_preview or {}),
            result_preview=dict(log.result_preview or {}),
        )
        if parsed is not None:
            return parsed
    return None


def generate_assets_tool_was_executed(tool_names: list[str]) -> bool:
    return CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME in tool_names
