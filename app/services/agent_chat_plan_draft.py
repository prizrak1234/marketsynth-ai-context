"""Plan draft artifacts from agent chat runs (Phase AI.3)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.campaign_plan_drafts import CampaignPlanDraftTable
from app.schemas.agent_chat import AgentChatPlanDraftCreated
from app.tools.marketing_tools import CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME


def format_plan_draft_chat_assistant_message(
    *,
    draft_id: UUID,
    campaign_id: UUID,
    llm_content: str,
) -> str:
    intro = llm_content.strip()
    lines: list[str] = []
    if intro:
        lines.append(intro)
        lines.append("")
    lines.extend(
        [
            "Campaign plan draft created.",
            f"draft_id: {draft_id}",
            f"campaign_id: {campaign_id}",
            "Next step: open the campaign in the UI and use Generate Assets.",
            "No assets, publication jobs, approve, schedule, or publish were performed.",
        ],
    )
    return "\n".join(lines)


async def find_plan_drafts_by_run_ids(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    agent_run_ids: list[UUID],
) -> dict[UUID, AgentChatPlanDraftCreated]:
    if not agent_run_ids:
        return {}

    statement = (
        select(CampaignPlanDraftTable)
        .where(
            CampaignPlanDraftTable.owner_id == owner_id,
            CampaignPlanDraftTable.project_id == project_id,
            CampaignPlanDraftTable.source_agent_run_id.in_(agent_run_ids),
        )
        .order_by(CampaignPlanDraftTable.created_at.desc())
    )
    result = await session.execute(statement)
    rows = list(result.scalars().all())
    by_run: dict[UUID, AgentChatPlanDraftCreated] = {}
    for row in rows:
        if row.source_agent_run_id is None or row.source_agent_run_id in by_run:
            continue
        by_run[row.source_agent_run_id] = AgentChatPlanDraftCreated(
            draft_id=row.id,
            campaign_id=row.campaign_id,
            title=row.title,
        )
    return by_run


async def find_plan_draft_created_by_run(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    agent_run_id: UUID,
) -> AgentChatPlanDraftCreated | None:
    statement = (
        select(CampaignPlanDraftTable)
        .where(
            CampaignPlanDraftTable.owner_id == owner_id,
            CampaignPlanDraftTable.project_id == project_id,
            CampaignPlanDraftTable.source_agent_run_id == agent_run_id,
        )
        .order_by(CampaignPlanDraftTable.created_at.desc())
        .limit(1)
    )
    result = await session.execute(statement)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return AgentChatPlanDraftCreated(
        draft_id=row.id,
        campaign_id=row.campaign_id,
        title=row.title,
    )


def plan_draft_tool_was_executed(tool_names: list[str]) -> bool:
    return CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME in tool_names
