"""LLM request/response repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.base import utc_now
from app.db.models.llm import LLMRequestTable, LLMResponseTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import LLMProvider, LLMRequestStatus


class LLMRequestRepository(BaseRepository[LLMRequestTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LLMRequestTable)

    async def get_by_id_for_owner(
        self,
        request_id: UUID,
        owner_id: UUID,
    ) -> LLMRequestTable | None:
        statement = select(LLMRequestTable).where(
            LLMRequestTable.id == request_id,
            LLMRequestTable.owner_id == owner_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
        agent_id: UUID | None = None,
        agent_run_id: UUID | None = None,
        task_id: UUID | None = None,
        status: LLMRequestStatus | None = None,
        provider: LLMProvider | None = None,
        model: str | None = None,
        limit: int = 100,
    ) -> list[LLMRequestTable]:
        statement = select(LLMRequestTable).where(LLMRequestTable.owner_id == owner_id)
        if project_id is not None:
            statement = statement.where(LLMRequestTable.project_id == project_id)
        if agent_id is not None:
            statement = statement.where(LLMRequestTable.agent_id == agent_id)
        if agent_run_id is not None:
            statement = statement.where(LLMRequestTable.agent_run_id == agent_run_id)
        if task_id is not None:
            statement = statement.where(LLMRequestTable.task_id == task_id)
        if status is not None:
            statement = statement.where(LLMRequestTable.status == status)
        if provider is not None:
            statement = statement.where(LLMRequestTable.provider == provider)
        if model is not None:
            statement = statement.where(LLMRequestTable.model == model)
        statement = statement.order_by(LLMRequestTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def set_running(self, request: LLMRequestTable) -> LLMRequestTable:
        request.status = LLMRequestStatus.RUNNING
        request.started_at = utc_now()
        request.updated_at = utc_now()
        return await self.update(request)

    async def set_failed(self, request: LLMRequestTable, error: str) -> LLMRequestTable:
        request.status = LLMRequestStatus.FAILED
        request.error = error
        request.finished_at = utc_now()
        request.updated_at = utc_now()
        return await self.update(request)

    async def set_cancelled(self, request: LLMRequestTable) -> LLMRequestTable:
        request.status = LLMRequestStatus.CANCELLED
        request.finished_at = utc_now()
        request.updated_at = utc_now()
        return await self.update(request)

    async def set_succeeded(self, request: LLMRequestTable) -> LLMRequestTable:
        request.status = LLMRequestStatus.SUCCEEDED
        request.error = None
        request.finished_at = utc_now()
        request.updated_at = utc_now()
        return await self.update(request)


class LLMResponseRepository(BaseRepository[LLMResponseTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LLMResponseTable)

    async def get_by_request_id(self, llm_request_id: UUID) -> LLMResponseTable | None:
        statement = select(LLMResponseTable).where(
            LLMResponseTable.llm_request_id == llm_request_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def attach_response(self, response: LLMResponseTable) -> LLMResponseTable:
        return await self.create(response)
