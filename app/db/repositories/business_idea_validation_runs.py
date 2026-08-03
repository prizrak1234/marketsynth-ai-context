"""Repository for CMVP.1 Business Idea Validation runs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.biv_run_status_values import (
    BIV_RUN_ACTIVE_STATUSES,
    BIV_RUN_STATUS_FAILED,
    BIV_RUN_STATUS_QUEUED,
    BIV_RUN_STATUS_RUNNING,
    BIV_RUN_STATUS_SUCCEEDED,
)
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable


class BusinessIdeaValidationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: BusinessIdeaValidationRunTable) -> BusinessIdeaValidationRunTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: BusinessIdeaValidationRunTable) -> BusinessIdeaValidationRunTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, run_id: UUID) -> BusinessIdeaValidationRunTable | None:
        return await self._session.get(BusinessIdeaValidationRunTable, run_id)

    async def get_by_idempotency_key(
        self,
        owner_id: UUID,
        idempotency_key: str,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = select(BusinessIdeaValidationRunTable).where(
            BusinessIdeaValidationRunTable.owner_id == owner_id,
            BusinessIdeaValidationRunTable.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_user_request(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.user_request_id == user_request_id,
            )
            .order_by(BusinessIdeaValidationRunTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        active_statuses = BIV_RUN_ACTIVE_STATUSES
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
                BusinessIdeaValidationRunTable.status.in_(active_statuses),
            )
            .order_by(BusinessIdeaValidationRunTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_project_for_update(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        active_statuses = BIV_RUN_ACTIVE_STATUSES
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
                BusinessIdeaValidationRunTable.status.in_(active_statuses),
            )
            .order_by(BusinessIdeaValidationRunTable.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
            )
            .order_by(BusinessIdeaValidationRunTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_succeeded_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
                BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_SUCCEEDED,
            )
            .order_by(BusinessIdeaValidationRunTable.finished_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_succeeded_for_context(
        self,
        owner_id: UUID,
        project_id: UUID,
        analysis_context_id: UUID,
        input_snapshot_hash: str,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
                BusinessIdeaValidationRunTable.analysis_context_id == analysis_context_id,
                BusinessIdeaValidationRunTable.input_snapshot_hash == input_snapshot_hash,
                BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_SUCCEEDED,
            )
            .order_by(BusinessIdeaValidationRunTable.finished_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_partial_for_context(
        self,
        owner_id: UUID,
        project_id: UUID,
        analysis_context_id: UUID,
        input_snapshot_hash: str,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
                BusinessIdeaValidationRunTable.analysis_context_id == analysis_context_id,
                BusinessIdeaValidationRunTable.input_snapshot_hash == input_snapshot_hash,
                BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_FAILED,
                BusinessIdeaValidationRunTable.result_json.isnot(None),
            )
            .order_by(BusinessIdeaValidationRunTable.finished_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if row.result_json.get("result_kind") == "partial_research":
            return row
        return None

    async def get_latest_partial_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.project_id == project_id,
                BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_FAILED,
                BusinessIdeaValidationRunTable.result_json.isnot(None),
            )
            .order_by(BusinessIdeaValidationRunTable.finished_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if row.result_json.get("result_kind") == "partial_research":
            return row
        return None

    async def get_by_id_for_owner(
        self,
        owner_id: UUID,
        run_id: UUID,
    ) -> BusinessIdeaValidationRunTable | None:
        stmt = select(BusinessIdeaValidationRunTable).where(
            BusinessIdeaValidationRunTable.owner_id == owner_id,
            BusinessIdeaValidationRunTable.id == run_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def claim_queued(self, run_id: UUID) -> BusinessIdeaValidationRunTable | None:
        """Atomically transition queued → running; returns row or None if not claimable."""
        now = utc_now()
        stmt = (
            update(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.id == run_id,
                BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_QUEUED,
            )
            .values(status=BIV_RUN_STATUS_RUNNING, updated_at=now)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None
        await self._session.flush()
        return await self.get_by_id(run_id)

    async def list_queued_run_ids(self) -> list[UUID]:
        stmt = select(BusinessIdeaValidationRunTable.id).where(
            BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_QUEUED,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_stale_running_run_ids(self, stale_before: datetime) -> list[UUID]:
        stmt = select(BusinessIdeaValidationRunTable.id).where(
            BusinessIdeaValidationRunTable.status == BIV_RUN_STATUS_RUNNING,
            BusinessIdeaValidationRunTable.updated_at < stale_before,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_for_context(
        self,
        owner_id: UUID,
        analysis_context_id: UUID,
        input_snapshot_hash: str,
    ) -> BusinessIdeaValidationRunTable | None:
        active_statuses = BIV_RUN_ACTIVE_STATUSES
        stmt = (
            select(BusinessIdeaValidationRunTable)
            .where(
                BusinessIdeaValidationRunTable.owner_id == owner_id,
                BusinessIdeaValidationRunTable.analysis_context_id == analysis_context_id,
                BusinessIdeaValidationRunTable.input_snapshot_hash == input_snapshot_hash,
                BusinessIdeaValidationRunTable.status.in_(active_statuses),
            )
            .order_by(BusinessIdeaValidationRunTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
