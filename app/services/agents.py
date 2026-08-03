"""Agent registry business logic — no LLM execution."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.db.base import utc_now
from app.db.models.agent import AgentTable
from app.db.repositories.agent_repo import AgentRepository
from app.db.repositories.project_repo import ProjectRepository
from app.schemas.contracts import AgentStatus
from app.schemas.crud import AgentCreateRequest, AgentUpdateRequest
from app.services.transaction import transactional


class AgentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AgentRepository(session)
        self._projects = ProjectRepository(session)

    async def _ensure_project_owned(self, project_id: UUID, owner_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _build_agent_row(
        self,
        *,
        owner_id: UUID,
        body: AgentCreateRequest,
    ) -> AgentTable:
        template = DEFAULT_AGENT_TEMPLATES[body.type]
        capabilities = body.capabilities
        if capabilities is None:
            capabilities = template["capabilities"]

        return AgentTable(
            project_id=body.project_id,
            owner_id=owner_id,
            type=body.type,
            name=body.name or template["name"],
            description=body.description or template["description"],
            status=AgentStatus.DRAFT,
            config=body.config if body.config is not None else template["default_config"],
            capabilities=[cap.model_dump() for cap in capabilities],
        )

    async def create_agent(self, owner_id: UUID, body: AgentCreateRequest) -> AgentTable | None:
        if not await self._ensure_project_owned(body.project_id, owner_id):
            return None

        row = self._build_agent_row(owner_id=owner_id, body=body)
        async with transactional(self._session):
            return await self._repo.create(row)

    async def get_agent(self, agent_id: UUID, owner_id: UUID) -> AgentTable | None:
        return await self._repo.get_by_id_for_owner(agent_id, owner_id)

    async def list_agents(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[AgentTable]:
        if project_id is not None and not await self._ensure_project_owned(project_id, owner_id):
            return []
        return await self._repo.list_by_owner(
            owner_id,
            project_id=project_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def update_agent(
        self,
        agent_id: UUID,
        owner_id: UUID,
        body: AgentUpdateRequest,
    ) -> AgentTable | None:
        row = await self._repo.get_by_id_for_owner(agent_id, owner_id)
        if row is None or row.status == AgentStatus.ARCHIVED:
            return None

        updates = body.model_dump(exclude_unset=True)
        if not updates:
            return row

        async with transactional(self._session):
            if "name" in updates and updates["name"] is not None:
                row.name = updates["name"]
            if "description" in updates:
                row.description = updates["description"]
            if "config" in updates and updates["config"] is not None:
                row.config = updates["config"]
            if "capabilities" in updates and updates["capabilities"] is not None:
                row.capabilities = updates["capabilities"]
            row.updated_at = utc_now()
            return await self._repo.update(row)

    async def archive_agent(self, agent_id: UUID, owner_id: UUID) -> AgentTable | None:
        row = await self._repo.get_by_id_for_owner(agent_id, owner_id)
        if row is None or row.status == AgentStatus.ARCHIVED:
            return None

        async with transactional(self._session):
            row.status = AgentStatus.ARCHIVED
            row.updated_at = utc_now()
            return await self._repo.update(row)

    async def activate_agent(self, agent_id: UUID, owner_id: UUID) -> AgentTable | None:
        return await self._set_status(agent_id, owner_id, AgentStatus.ACTIVE)

    async def pause_agent(self, agent_id: UUID, owner_id: UUID) -> AgentTable | None:
        return await self._set_status(agent_id, owner_id, AgentStatus.PAUSED)

    async def _set_status(
        self,
        agent_id: UUID,
        owner_id: UUID,
        status: AgentStatus,
    ) -> AgentTable | None:
        row = await self._repo.get_by_id_for_owner(agent_id, owner_id)
        if row is None or row.status == AgentStatus.ARCHIVED:
            return None

        async with transactional(self._session):
            row.status = status
            row.updated_at = utc_now()
            return await self._repo.update(row)
