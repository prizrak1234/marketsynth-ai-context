"""Launch Pack request repository extensions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.launch_pack_request import LaunchPackRequestTable


class LaunchPackRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: LaunchPackRequestTable) -> LaunchPackRequestTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_for_verdict(
        self,
        owner_id: UUID,
        business_verdict_id: UUID,
    ) -> LaunchPackRequestTable | None:
        stmt = select(LaunchPackRequestTable).where(
            LaunchPackRequestTable.owner_id == owner_id,
            LaunchPackRequestTable.business_verdict_id == business_verdict_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        owner_id: UUID,
        launch_pack_id: UUID,
    ) -> LaunchPackRequestTable | None:
        stmt = select(LaunchPackRequestTable).where(
            LaunchPackRequestTable.owner_id == owner_id,
            LaunchPackRequestTable.id == launch_pack_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> LaunchPackRequestTable | None:
        stmt = (
            select(LaunchPackRequestTable)
            .where(
                LaunchPackRequestTable.owner_id == owner_id,
                LaunchPackRequestTable.project_id == project_id,
            )
            .order_by(LaunchPackRequestTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_verdict(
        self,
        owner_id: UUID,
        business_verdict_id: UUID,
    ) -> LaunchPackRequestTable | None:
        return await self.get_for_verdict(owner_id, business_verdict_id)
