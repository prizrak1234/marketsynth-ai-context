"""Beta feedback reports (Phase AI.91–AI.92)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.beta.safe_feedback_context import sanitize_feedback_context
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.beta_feedback_report import BetaFeedbackReportTable
from app.db.repositories.beta_feedback_reports import BetaFeedbackReportRepository
from app.schemas.beta_feedback import BetaFeedbackCreateRequest
from app.schemas.contracts import (
    BetaFeedbackSeverity,
    BetaFeedbackSource,
    BetaFeedbackStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_TERMINAL_STATUSES = frozenset(
    {
        BetaFeedbackStatus.RESOLVED,
        BetaFeedbackStatus.ARCHIVED,
    },
)


class BetaFeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BetaFeedbackReportRepository(session)
        self._projects = ProjectService(session)

    async def create(
        self,
        owner_id: UUID,
        body: BetaFeedbackCreateRequest,
    ) -> BetaFeedbackReportTable:
        if body.project_id is not None:
            project = await self._projects.get_by_id(body.project_id)
            if project is None or project.owner_id != owner_id:
                raise InvalidStateError("Project not found for feedback report")

        row = BetaFeedbackReportTable(
            owner_id=owner_id,
            project_id=body.project_id,
            source=body.source,
            severity=body.severity,
            status=BetaFeedbackStatus.OPEN,
            title=sanitize_text(body.title).strip()[:256],
            description=sanitize_text(body.description).strip()[:4096],
            safe_context=sanitize_feedback_context(body.safe_context),
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def get_for_owner(
        self,
        owner_id: UUID,
        report_id: UUID,
    ) -> BetaFeedbackReportTable | None:
        return await self._repo.get_by_id_for_owner(report_id, owner_id)

    async def list_for_owner(
        self,
        owner_id: UUID,
        *,
        status: BetaFeedbackStatus | None = None,
        limit: int = 100,
    ) -> list[BetaFeedbackReportTable]:
        return await self._repo.list_for_owner(owner_id, status=status, limit=limit)

    async def archive(
        self,
        owner_id: UUID,
        report_id: UUID,
    ) -> BetaFeedbackReportTable | None:
        row = await self._repo.get_by_id_for_owner(report_id, owner_id)
        if row is None:
            return None
        if row.status == BetaFeedbackStatus.ARCHIVED:
            return row
        row.status = BetaFeedbackStatus.ARCHIVED
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._repo.update(row)

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
        return await self._repo.list_admin(
            owner_id=owner_id,
            project_id=project_id,
            source=source,
            severity=severity,
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )

    async def triage(self, report_id: UUID) -> BetaFeedbackReportTable | None:
        row = await self._repo.get_by_id_admin(report_id)
        if row is None:
            return None
        if row.status in _TERMINAL_STATUSES:
            raise InvalidStateError("Resolved or archived feedback cannot be triaged")
        row.status = BetaFeedbackStatus.TRIAGED
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._repo.update(row)

    async def resolve(self, report_id: UUID) -> BetaFeedbackReportTable | None:
        row = await self._repo.get_by_id_admin(report_id)
        if row is None:
            return None
        if row.status == BetaFeedbackStatus.ARCHIVED:
            raise InvalidStateError("Archived feedback cannot be resolved")
        row.status = BetaFeedbackStatus.RESOLVED
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._repo.update(row)
