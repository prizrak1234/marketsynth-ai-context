"""Scenario wizard run repository (Phase AI.137)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.scenario_wizard_run import ScenarioWizardRunTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import ScenarioWizardRunStatus


class ScenarioWizardRunRepository(BaseRepository[ScenarioWizardRunTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ScenarioWizardRunTable)

    async def get_by_id_for_owner(
        self,
        run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ScenarioWizardRunTable | None:
        statement = select(ScenarioWizardRunTable).where(
            ScenarioWizardRunTable.id == run_id,
            ScenarioWizardRunTable.owner_id == owner_id,
            ScenarioWizardRunTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: ScenarioWizardRunStatus | None = None,
        limit: int = 50,
    ) -> list[ScenarioWizardRunTable]:
        statement = (
            select(ScenarioWizardRunTable)
            .where(
                ScenarioWizardRunTable.owner_id == owner_id,
                ScenarioWizardRunTable.project_id == project_id,
            )
            .order_by(ScenarioWizardRunTable.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(ScenarioWizardRunTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
