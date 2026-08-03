"""Repository for PRODUCT-01.3A analysis contexts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_context import AnalysisContextTable


class AnalysisContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: AnalysisContextTable) -> AnalysisContextTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: AnalysisContextTable) -> AnalysisContextTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, owner_id: UUID, context_id: UUID) -> AnalysisContextTable | None:
        stmt = select(AnalysisContextTable).where(
            AnalysisContextTable.owner_id == owner_id,
            AnalysisContextTable.id == context_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> AnalysisContextTable | None:
        stmt = (
            select(AnalysisContextTable)
            .where(
                AnalysisContextTable.owner_id == owner_id,
                AnalysisContextTable.project_id == project_id,
                AnalysisContextTable.is_active.is_(True),
            )
            .order_by(AnalysisContextTable.updated_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_project_contexts(self, owner_id: UUID, project_id: UUID) -> None:
        stmt = (
            update(AnalysisContextTable)
            .where(
                AnalysisContextTable.owner_id == owner_id,
                AnalysisContextTable.project_id == project_id,
                AnalysisContextTable.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await self._session.execute(stmt)
