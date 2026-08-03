"""Tool execution audit log repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.base import BaseRepository
from app.tools.audit_contracts import ToolExecutionLogMode, ToolExecutionLogStatus


class ToolExecutionLogRepository(BaseRepository[ToolExecutionLogTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ToolExecutionLogTable)

    async def get_by_id_for_owner(
        self,
        log_id: UUID,
        owner_id: UUID,
    ) -> ToolExecutionLogTable | None:
        statement = select(ToolExecutionLogTable).where(
            ToolExecutionLogTable.id == log_id,
            ToolExecutionLogTable.owner_id == owner_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_run(
        self,
        owner_id: UUID,
        agent_run_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolExecutionLogTable]:
        statement = (
            select(ToolExecutionLogTable)
            .where(
                ToolExecutionLogTable.owner_id == owner_id,
                ToolExecutionLogTable.agent_run_id == agent_run_id,
            )
            .order_by(ToolExecutionLogTable.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        tool_name: str | None = None,
        status: ToolExecutionLogStatus | None = None,
        execution_mode: ToolExecutionLogMode | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolExecutionLogTable]:
        statement = select(ToolExecutionLogTable).where(
            ToolExecutionLogTable.owner_id == owner_id,
            ToolExecutionLogTable.project_id == project_id,
        )
        if tool_name is not None:
            statement = statement.where(ToolExecutionLogTable.tool_name == tool_name)
        if status is not None:
            statement = statement.where(ToolExecutionLogTable.status == status)
        if execution_mode is not None:
            statement = statement.where(ToolExecutionLogTable.execution_mode == execution_mode)
        if created_from is not None:
            statement = statement.where(ToolExecutionLogTable.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(ToolExecutionLogTable.created_at <= created_to)
        statement = (
            statement.order_by(
                ToolExecutionLogTable.created_at.desc(),
                ToolExecutionLogTable.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
