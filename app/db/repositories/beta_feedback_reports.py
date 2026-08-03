"""Beta feedback report repository (Phase AI.91)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.beta_feedback_report import BetaFeedbackReportTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    BetaFeedbackSeverity,
    BetaFeedbackSource,
    BetaFeedbackStatus,
)


class BetaFeedbackReportRepository(BaseRepository[BetaFeedbackReportTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BetaFeedbackReportTable)

    async def get_by_id_for_owner(
        self,
        report_id: UUID,
        owner_id: UUID,
    ) -> BetaFeedbackReportTable | None:
        statement = select(BetaFeedbackReportTable).where(
            BetaFeedbackReportTable.id == report_id,
            BetaFeedbackReportTable.owner_id == owner_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_owner(
        self,
        owner_id: UUID,
        *,
        status: BetaFeedbackStatus | None = None,
        limit: int = 100,
    ) -> list[BetaFeedbackReportTable]:
        statement = (
            select(BetaFeedbackReportTable)
            .where(BetaFeedbackReportTable.owner_id == owner_id)
            .order_by(BetaFeedbackReportTable.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(BetaFeedbackReportTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_admin(
        self,
        *,
        owner_id: UUID | None = None,
        project_id: UUID | None = None,
        source: BetaFeedbackSource | None = None,
        severity: BetaFeedbackSeverity | None = None,
        status: BetaFeedbackStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 200,
    ) -> list[BetaFeedbackReportTable]:
        statement = select(BetaFeedbackReportTable).order_by(
            BetaFeedbackReportTable.created_at.desc(),
        ).limit(limit)
        if owner_id is not None:
            statement = statement.where(BetaFeedbackReportTable.owner_id == owner_id)
        if project_id is not None:
            statement = statement.where(BetaFeedbackReportTable.project_id == project_id)
        if source is not None:
            statement = statement.where(BetaFeedbackReportTable.source == source)
        if severity is not None:
            statement = statement.where(BetaFeedbackReportTable.severity == severity)
        if status is not None:
            statement = statement.where(BetaFeedbackReportTable.status == status)
        if date_from is not None:
            statement = statement.where(BetaFeedbackReportTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(BetaFeedbackReportTable.created_at <= date_to)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_admin(self, report_id: UUID) -> BetaFeedbackReportTable | None:
        statement = select(BetaFeedbackReportTable).where(
            BetaFeedbackReportTable.id == report_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_by_status(
        self,
        *,
        owner_id: UUID | None = None,
    ) -> dict[BetaFeedbackStatus, int]:
        statement = (
            select(BetaFeedbackReportTable.status, func.count())
            .group_by(BetaFeedbackReportTable.status)
        )
        if owner_id is not None:
            statement = statement.where(BetaFeedbackReportTable.owner_id == owner_id)
        rows = (await self.session.execute(statement)).all()
        return {status: int(count) for status, count in rows}

    async def count_by_severity(
        self,
        *,
        owner_id: UUID | None = None,
        severities: tuple[BetaFeedbackSeverity, ...],
    ) -> dict[BetaFeedbackSeverity, int]:
        statement = (
            select(BetaFeedbackReportTable.severity, func.count())
            .where(BetaFeedbackReportTable.severity.in_(severities))
            .group_by(BetaFeedbackReportTable.severity)
        )
        if owner_id is not None:
            statement = statement.where(BetaFeedbackReportTable.owner_id == owner_id)
        rows = (await self.session.execute(statement)).all()
        return {severity: int(count) for severity, count in rows}
