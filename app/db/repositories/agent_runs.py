"""Agent run repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import AgentRunStatus


class AgentRunRepository(BaseRepository[AgentRunTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentRunTable)

    async def get_by_id_for_owner(self, run_id: UUID, owner_id: UUID) -> AgentRunTable | None:
        statement = select(AgentRunTable).where(
            AgentRunTable.id == run_id,
            AgentRunTable.owner_id == owner_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_ids_for_owner(
        self,
        run_ids: list[UUID],
        owner_id: UUID,
        *,
        project_id: UUID,
    ) -> list[AgentRunTable]:
        if not run_ids:
            return []
        statement = select(AgentRunTable).where(
            AgentRunTable.id.in_(run_ids),
            AgentRunTable.owner_id == owner_id,
            AgentRunTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
        agent_id: UUID | None = None,
        task_id: UUID | None = None,
        status: AgentRunStatus | None = None,
        limit: int = 100,
    ) -> list[AgentRunTable]:
        statement = select(AgentRunTable).where(AgentRunTable.owner_id == owner_id)
        if project_id is not None:
            statement = statement.where(AgentRunTable.project_id == project_id)
        if agent_id is not None:
            statement = statement.where(AgentRunTable.agent_id == agent_id)
        if task_id is not None:
            statement = statement.where(AgentRunTable.task_id == task_id)
        if status is not None:
            statement = statement.where(AgentRunTable.status == status)
        statement = statement.order_by(AgentRunTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID | None = None,
        limit: int = 100,
    ) -> list[AgentRunTable]:
        statement = select(AgentRunTable).where(AgentRunTable.project_id == project_id)
        if owner_id is not None:
            statement = statement.where(AgentRunTable.owner_id == owner_id)
        statement = statement.order_by(AgentRunTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_agent(
        self,
        agent_id: UUID,
        *,
        owner_id: UUID | None = None,
        limit: int = 100,
    ) -> list[AgentRunTable]:
        statement = select(AgentRunTable).where(AgentRunTable.agent_id == agent_id)
        if owner_id is not None:
            statement = statement.where(AgentRunTable.owner_id == owner_id)
        statement = statement.order_by(AgentRunTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_status(self, run: AgentRunTable, status: AgentRunStatus) -> AgentRunTable:
        run.status = status
        run.updated_at = utc_now()
        return await self.update(run)

    async def set_running(self, run: AgentRunTable) -> AgentRunTable:
        run.status = AgentRunStatus.RUNNING
        run.started_at = utc_now()
        run.updated_at = utc_now()
        return await self.update(run)

    async def claim_queued_run(self, run_id: UUID, owner_id: UUID) -> AgentRunTable | None:
        """Atomically transition queued → running; returns None if not claimable."""
        now = utc_now()
        statement = (
            update(AgentRunTable)
            .where(
                AgentRunTable.id == run_id,
                AgentRunTable.owner_id == owner_id,
                AgentRunTable.status == AgentRunStatus.QUEUED,
            )
            .values(
                status=AgentRunStatus.RUNNING,
                started_at=now,
                updated_at=now,
            )
            .returning(AgentRunTable)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def set_output_payload(
        self,
        run: AgentRunTable,
        output_payload: dict,
    ) -> AgentRunTable:
        run.output_payload = output_payload
        run.updated_at = utc_now()
        return await self.update(run)

    async def set_succeeded(
        self,
        run: AgentRunTable,
        output_payload: dict,
    ) -> AgentRunTable:
        run.status = AgentRunStatus.SUCCEEDED
        run.output_payload = output_payload
        run.error = None
        run.finished_at = utc_now()
        run.updated_at = utc_now()
        return await self.update(run)

    async def set_failed(self, run: AgentRunTable, error: str) -> AgentRunTable:
        run.status = AgentRunStatus.FAILED
        run.error = error
        run.finished_at = utc_now()
        run.updated_at = utc_now()
        return await self.update(run)

    async def set_cancelled(self, run: AgentRunTable) -> AgentRunTable:
        run.status = AgentRunStatus.CANCELLED
        run.finished_at = utc_now()
        run.updated_at = utc_now()
        return await self.update(run)

    async def set_run_metadata(
        self,
        run: AgentRunTable,
        metadata: dict,
    ) -> AgentRunTable:
        run.run_metadata = metadata
        run.updated_at = utc_now()
        return await self.update(run)

    async def reset_to_queued(self, run: AgentRunTable) -> AgentRunTable:
        run.status = AgentRunStatus.QUEUED
        run.error = None
        run.output_payload = None
        run.started_at = None
        run.finished_at = None
        run.updated_at = utc_now()
        return await self.update(run)

    async def count_children_by_parent(
        self,
        owner_id: UUID,
        parent_run_id: UUID,
    ) -> int:
        statement = select(AgentRunTable).where(
            AgentRunTable.owner_id == owner_id,
            AgentRunTable.parent_agent_run_id == parent_run_id,
        )
        result = await self.session.execute(statement)
        return len(list(result.scalars().all()))

    async def count_handoff_children_for_parent(
        self,
        owner_id: UUID,
        parent_run_id: UUID,
        *,
        limit: int = 500,
    ) -> int:
        """Count LangGraph handoff child runs linked to a parent agent run."""
        from app.graphs.handoff import is_handoff_child_run

        parent_str = str(parent_run_id)
        runs = await self.list_by_owner(owner_id, limit=limit)
        return sum(
            1
            for row in runs
            if is_handoff_child_run(dict(row.run_metadata or {}))
            and dict(row.run_metadata or {}).get("parent_agent_run_id") == parent_str
        )
