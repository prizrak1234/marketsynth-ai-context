"""Media generation job persistence (Phase AI.56)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.media import MediaGenerationJobTable
from app.media_generation.contracts import MediaGenerationJobStatus


class MediaGenerationJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: MediaGenerationJobTable) -> MediaGenerationJobTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: MediaGenerationJobTable) -> MediaGenerationJobTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        job_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MediaGenerationJobTable | None:
        statement = select(MediaGenerationJobTable).where(
            MediaGenerationJobTable.id == job_id,
            MediaGenerationJobTable.owner_id == owner_id,
            MediaGenerationJobTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        media_brief_id: UUID,
        *,
        limit: int = 50,
    ) -> list[MediaGenerationJobTable]:
        statement = (
            select(MediaGenerationJobTable)
            .where(
                MediaGenerationJobTable.owner_id == owner_id,
                MediaGenerationJobTable.project_id == project_id,
                MediaGenerationJobTable.media_brief_id == media_brief_id,
            )
            .order_by(MediaGenerationJobTable.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_for_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        media_brief_id: UUID,
    ) -> MediaGenerationJobTable | None:
        active = (
            MediaGenerationJobStatus.QUEUED,
            MediaGenerationJobStatus.RUNNING,
        )
        statement = select(MediaGenerationJobTable).where(
            MediaGenerationJobTable.owner_id == owner_id,
            MediaGenerationJobTable.project_id == project_id,
            MediaGenerationJobTable.media_brief_id == media_brief_id,
            MediaGenerationJobTable.status.in_(active),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
