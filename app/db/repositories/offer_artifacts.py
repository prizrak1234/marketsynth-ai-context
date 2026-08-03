"""Offer artifact repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commercial_upstream_snapshot import CommercialUpstreamSnapshotTable
from app.db.models.launch_pack_request import LaunchPackRequestTable
from app.db.models.offer_artifact import (
    OfferArtifactTable,
    OfferArtifactVersionTable,
    OfferReviewEventTable,
)


class OfferArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_artifact(self, row: OfferArtifactTable) -> OfferArtifactTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, owner_id: UUID, offer_id: UUID) -> OfferArtifactTable | None:
        stmt = select(OfferArtifactTable).where(
            OfferArtifactTable.owner_id == owner_id,
            OfferArtifactTable.id == offer_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        owner_id: UUID,
        offer_id: UUID,
    ) -> OfferArtifactTable | None:
        stmt = (
            select(OfferArtifactTable)
            .where(
                OfferArtifactTable.owner_id == owner_id,
                OfferArtifactTable.id == offer_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_launch_pack_for_update(
        self,
        owner_id: UUID,
        launch_pack_id: UUID,
    ) -> LaunchPackRequestTable | None:
        stmt = (
            select(LaunchPackRequestTable)
            .where(
                LaunchPackRequestTable.owner_id == owner_id,
                LaunchPackRequestTable.id == launch_pack_id,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_launch_pack(
        self,
        owner_id: UUID,
        launch_pack_request_id: UUID,
    ) -> OfferArtifactTable | None:
        stmt = select(OfferArtifactTable).where(
            OfferArtifactTable.owner_id == owner_id,
            OfferArtifactTable.launch_pack_request_id == launch_pack_request_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self,
        owner_id: UUID,
        idempotency_key: str,
    ) -> OfferArtifactTable | None:
        stmt = select(OfferArtifactTable).where(
            OfferArtifactTable.owner_id == owner_id,
            OfferArtifactTable.generation_idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_version(self, row: OfferArtifactVersionTable) -> OfferArtifactVersionTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_version(
        self,
        offer_artifact_id: UUID,
        version_number: int,
    ) -> OfferArtifactVersionTable | None:
        stmt = select(OfferArtifactVersionTable).where(
            OfferArtifactVersionTable.offer_artifact_id == offer_artifact_id,
            OfferArtifactVersionTable.version_number == version_number,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_version(
        self,
        offer: OfferArtifactTable,
    ) -> OfferArtifactVersionTable | None:
        if offer.current_version_id is None:
            return None
        stmt = select(OfferArtifactVersionTable).where(
            OfferArtifactVersionTable.id == offer.current_version_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        offer_artifact_id: UUID,
    ) -> list[OfferArtifactVersionTable]:
        stmt = (
            select(OfferArtifactVersionTable)
            .where(OfferArtifactVersionTable.offer_artifact_id == offer_artifact_id)
            .order_by(OfferArtifactVersionTable.version_number.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_review_event(self, row: OfferReviewEventTable) -> OfferReviewEventTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_upstream_snapshots(
        self,
        launch_pack_request_id: UUID,
    ) -> list[CommercialUpstreamSnapshotTable]:
        stmt = select(CommercialUpstreamSnapshotTable).where(
            CommercialUpstreamSnapshotTable.launch_pack_request_id == launch_pack_request_id,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_versions(self, offer_artifact_id: UUID) -> int:
        stmt = select(OfferArtifactVersionTable).where(
            OfferArtifactVersionTable.offer_artifact_id == offer_artifact_id,
        )
        result = await self._session.execute(stmt)
        return len(list(result.scalars().all()))
