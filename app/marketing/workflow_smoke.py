"""Demo marketing workspace helpers for E2E tests and smoke scripts (Phase 5.7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.marketing.funnel_contracts import FunnelStepType
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.marketing_funnel_service import MarketingFunnelService
from app.services.projects_service import ProjectService

DEFAULT_WORKFLOW_GOAL = "build content plan for launch funnel"
DEFAULT_BRIEF_TITLE = "Workflow demo brief"
DEFAULT_FUNNEL_TITLE = "Workflow demo funnel"


@dataclass(frozen=True)
class DemoMarketingWorkspace:
    owner_id: UUID
    project_id: UUID
    brief_id: UUID
    funnel_id: UUID
    orchestrator_agent_id: UUID
    content_planner_agent_id: UUID
    critic_agent_id: UUID


def create_orchestrator_run_payload(
    *,
    brief_id: UUID | str,
    funnel_id: UUID | str,
    goal: str = DEFAULT_WORKFLOW_GOAL,
    handoff_target_agent_type: str = "content_planner",
) -> dict[str, Any]:
    """Input payload for orchestrator LangGraph delegation to content planner."""
    return {
        "goal": goal,
        "prompt": goal,
        "brief_id": str(brief_id),
        "funnel_id": str(funnel_id),
        "handoff_target_agent_type": handoff_target_agent_type,
    }


def create_critic_run_payload(
    *,
    source_asset_id: UUID | str,
    brief_id: UUID | str | None = None,
    funnel_id: UUID | str | None = None,
    goal: str = "review content plan before human approval",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "goal": goal,
        "prompt": goal,
        "source_asset_id": str(source_asset_id),
    }
    if brief_id is not None:
        payload["brief_id"] = str(brief_id)
    if funnel_id is not None:
        payload["funnel_id"] = str(funnel_id)
    return payload


def agent_config_with_mock_flow(
    base_config: dict[str, Any] | None,
    flow_key: str,
) -> dict[str, Any]:
    config = dict(base_config or {})
    config[flow_key] = True
    return config


async def build_demo_marketing_project(
    session: AsyncSession,
    owner_id: UUID,
    *,
    project_name: str = "Marketing workflow demo",
) -> UUID:
    project = await ProjectService(session).create(
        ProjectCreate(owner_id=owner_id, name=project_name),
    )
    return project.id


async def seed_demo_brief(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    *,
    title: str = DEFAULT_BRIEF_TITLE,
    offer: str = "Demo offer for workflow smoke",
) -> UUID:
    brief = await MarketingBriefService(session).create(
        owner_id,
        project_id,
        title=title,
        offer=offer,
    )
    if brief is None:
        raise RuntimeError("failed to seed demo brief")
    return brief.id


async def seed_demo_funnel(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    brief_id: UUID,
    *,
    title: str = DEFAULT_FUNNEL_TITLE,
) -> UUID:
    funnels = MarketingFunnelService(session)
    funnel = await funnels.create_funnel(
        owner_id,
        project_id,
        title=title,
        brief_id=brief_id,
    )
    if funnel is None:
        raise RuntimeError("failed to seed demo funnel")
    await funnels.create_step(
        owner_id,
        project_id,
        funnel.id,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    return funnel.id


async def seed_demo_agents(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
) -> tuple[UUID, UUID, UUID]:
    agents = AgentService(session)
    orchestrator = await agents.create_agent(
        owner_id,
        AgentCreateRequest(
            project_id=project_id,
            type=AgentType.ORCHESTRATOR,
            config=agent_config_with_mock_flow(None, "mock_orchestrator_flow"),
        ),
    )
    planner = await agents.create_agent(
        owner_id,
        AgentCreateRequest(
            project_id=project_id,
            type=AgentType.CONTENT_PLANNER,
            config=agent_config_with_mock_flow(None, "mock_content_planner_flow"),
        ),
    )
    critic = await agents.create_agent(
        owner_id,
        AgentCreateRequest(
            project_id=project_id,
            type=AgentType.CRITIC,
            config=agent_config_with_mock_flow(None, "mock_critic_flow"),
        ),
    )
    if orchestrator is None or planner is None or critic is None:
        raise RuntimeError("failed to seed demo agents")
    return orchestrator.id, planner.id, critic.id


async def seed_demo_marketing_workspace(
    session: AsyncSession,
    owner_id: UUID,
    *,
    project_name: str = "Marketing workflow demo",
) -> DemoMarketingWorkspace:
    project_id = await build_demo_marketing_project(
        session,
        owner_id,
        project_name=project_name,
    )
    brief_id = await seed_demo_brief(session, owner_id, project_id)
    funnel_id = await seed_demo_funnel(session, owner_id, project_id, brief_id)
    orchestrator_id, planner_id, critic_id = await seed_demo_agents(
        session,
        owner_id,
        project_id,
    )
    return DemoMarketingWorkspace(
        owner_id=owner_id,
        project_id=project_id,
        brief_id=brief_id,
        funnel_id=funnel_id,
        orchestrator_agent_id=orchestrator_id,
        content_planner_agent_id=planner_id,
        critic_agent_id=critic_id,
    )
