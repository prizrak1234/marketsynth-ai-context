"""Funnel step ↔ content asset link repository (Phase 4.8)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing import ContentAssetTable
from app.db.models.marketing_funnels import FunnelStepAssetLinkTable
from app.db.repositories.base import BaseRepository
from app.marketing.funnel_contracts import FunnelStepAssetRole


@dataclass(frozen=True)
class FunnelStepAssetLinkRow:
    link_id: UUID
    asset_id: UUID
    role: FunnelStepAssetRole
    asset_title: str
    asset_type: str
    asset_status: str
    created_at: datetime


class FunnelStepAssetLinkRepository(BaseRepository[FunnelStepAssetLinkTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FunnelStepAssetLinkTable)

    async def get_link(
        self,
        step_id: UUID,
        asset_id: UUID,
        funnel_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> FunnelStepAssetLinkTable | None:
        statement = select(FunnelStepAssetLinkTable).where(
            FunnelStepAssetLinkTable.step_id == step_id,
            FunnelStepAssetLinkTable.asset_id == asset_id,
            FunnelStepAssetLinkTable.funnel_id == funnel_id,
            FunnelStepAssetLinkTable.owner_id == owner_id,
            FunnelStepAssetLinkTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_step(
        self,
        step_id: UUID,
        funnel_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[FunnelStepAssetLinkRow]:
        statement = (
            select(
                FunnelStepAssetLinkTable,
                ContentAssetTable,
            )
            .join(
                ContentAssetTable,
                FunnelStepAssetLinkTable.asset_id == ContentAssetTable.id,
            )
            .where(
                FunnelStepAssetLinkTable.step_id == step_id,
                FunnelStepAssetLinkTable.funnel_id == funnel_id,
                FunnelStepAssetLinkTable.owner_id == owner_id,
                FunnelStepAssetLinkTable.project_id == project_id,
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
            )
            .order_by(FunnelStepAssetLinkTable.created_at.asc())
        )
        result = await self.session.execute(statement)
        rows: list[FunnelStepAssetLinkRow] = []
        for link, asset in result.all():
            rows.append(
                FunnelStepAssetLinkRow(
                    link_id=link.id,
                    asset_id=asset.id,
                    role=link.role,
                    asset_title=asset.title,
                    asset_type=asset.asset_type.value,
                    asset_status=asset.status.value,
                    created_at=link.created_at,
                ),
            )
        return rows

    async def list_by_funnel(
        self,
        funnel_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[FunnelStepAssetLinkTable]:
        statement = (
            select(FunnelStepAssetLinkTable)
            .where(
                FunnelStepAssetLinkTable.funnel_id == funnel_id,
                FunnelStepAssetLinkTable.owner_id == owner_id,
                FunnelStepAssetLinkTable.project_id == project_id,
            )
            .order_by(FunnelStepAssetLinkTable.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
