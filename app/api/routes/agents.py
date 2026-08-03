"""Agent registry API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tool_matrix import build_tool_matrix_api_payload
from app.api.dependencies.auth import require_active_user, require_agent_owner
from app.api.deps import get_session
from app.api.mappers import agent_to_contract
from app.core.config import get_settings
from app.db.models.agent import AgentTable
from app.db.models.user import UserTable
from app.schemas.agent_tool_matrix import AgentToolMatrixResponse, AgentToolMatrixRow
from app.schemas.contracts import Agent
from app.schemas.crud import AgentCreateRequest, AgentUpdateRequest
from app.services.agents import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Agent:
    service = AgentService(session)
    created = await service.create_agent(current_user.id, body)
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return agent_to_contract(created)


@router.get("/tool-matrix", response_model=AgentToolMatrixResponse)
async def get_agent_tool_matrix(
    current_user: UserTable = Depends(require_active_user),
) -> AgentToolMatrixResponse:
    _ = current_user
    payload = build_tool_matrix_api_payload(get_settings())
    return AgentToolMatrixResponse(
        write_globally_enabled=payload["write_globally_enabled"],
        create_draft_globally_enabled=payload["create_draft_globally_enabled"],
        agents=[AgentToolMatrixRow.model_validate(row) for row in payload["agents"]],
    )


@router.get("", response_model=list[Agent])
async def list_agents(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    project_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = 100,
) -> list[Agent]:
    service = AgentService(session)
    rows = await service.list_agents(
        current_user.id,
        project_id=project_id,
        include_archived=include_archived,
        limit=limit,
    )
    return [agent_to_contract(row) for row in rows]


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent: AgentTable = Depends(require_agent_owner),
) -> Agent:
    return agent_to_contract(agent)


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    body: AgentUpdateRequest,
    session: AsyncSession = Depends(get_session),
    agent: AgentTable = Depends(require_agent_owner),
) -> Agent:
    service = AgentService(session)
    updated = await service.update_agent(agent.id, agent.owner_id, body)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent_to_contract(updated)


@router.post("/{agent_id}/activate", response_model=Agent)
async def activate_agent(
    session: AsyncSession = Depends(get_session),
    agent: AgentTable = Depends(require_agent_owner),
) -> Agent:
    service = AgentService(session)
    updated = await service.activate_agent(agent.id, agent.owner_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent_to_contract(updated)


@router.post("/{agent_id}/pause", response_model=Agent)
async def pause_agent(
    session: AsyncSession = Depends(get_session),
    agent: AgentTable = Depends(require_agent_owner),
) -> Agent:
    service = AgentService(session)
    updated = await service.pause_agent(agent.id, agent.owner_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent_to_contract(updated)


@router.delete("/{agent_id}", response_model=Agent)
async def archive_agent(
    session: AsyncSession = Depends(get_session),
    agent: AgentTable = Depends(require_agent_owner),
) -> Agent:
    service = AgentService(session)
    archived = await service.archive_agent(agent.id, agent.owner_id)
    if archived is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent_to_contract(archived)
