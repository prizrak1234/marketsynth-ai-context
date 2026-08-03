"""Asset revision artifacts from agent chat runs (Phase AI.7)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.agent_chat import AgentChatRevisedAsset
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_REVISION_TOOL_NAME

AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS = 20


def format_revision_chat_assistant_message(*, revised_count: int) -> str:
    if revised_count == 0:
        return "Не удалось обновить черновики. Проверьте логи инструментов или попробуйте снова."
    if revised_count == 1:
        return (
            "Черновик обновлён.\n"
            "Следующий шаг: Review Queue → проверить и утвердить."
        )
    return (
        f"Черновики обновлены: {revised_count}.\n"
        "Следующий шаг: Review Queue → проверить и утвердить."
    )


def _parse_revised_asset_from_preview(
    result_preview: dict[str, object],
) -> AgentChatRevisedAsset | None:
    if not result_preview.get("ok"):
        return None
    asset_id = result_preview.get("asset_id")
    version = result_preview.get("current_version_number")
    if not isinstance(asset_id, str) or not isinstance(version, int):
        return None
    return AgentChatRevisedAsset(
        asset_id=UUID(asset_id),
        version=version,
    )


async def find_revised_assets_from_run(
    session: AsyncSession,
    owner_id: UUID,
    agent_run_id: UUID,
) -> list[AgentChatRevisedAsset]:
    logs = await ToolExecutionLogRepository(session).list_by_run(owner_id, agent_run_id)
    revised: list[AgentChatRevisedAsset] = []
    seen: set[str] = set()
    for log in logs:
        if log.tool_name != CONTENT_ASSET_CREATE_REVISION_TOOL_NAME:
            continue
        if log.status != "succeeded":
            continue
        parsed = _parse_revised_asset_from_preview(dict(log.result_preview or {}))
        if parsed is None:
            continue
        key = str(parsed.asset_id)
        if key in seen:
            continue
        seen.add(key)
        revised.append(parsed)
    return revised


def revision_tool_was_executed(tool_names: list[str]) -> bool:
    return CONTENT_ASSET_CREATE_REVISION_TOOL_NAME in tool_names
