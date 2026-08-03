"""Repository for internal BIV E2E deterministic fixtures."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.base import utc_now
from app.db.models.biv_e2e_deterministic_fixture import BivE2eDeterministicFixtureTable


class BivE2eDeterministicFixtureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_owner(self, owner_id: UUID) -> BivE2eDeterministicFixtureTable | None:
        result = await self._session.execute(
            select(BivE2eDeterministicFixtureTable).where(
                BivE2eDeterministicFixtureTable.owner_id == owner_id,
            ),
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        owner_id: UUID,
        outcome: str,
        e2e_run_id: str,
    ) -> BivE2eDeterministicFixtureTable:
        existing = await self.get_by_owner(owner_id)
        now = utc_now()
        if existing is None:
            row = BivE2eDeterministicFixtureTable(
                owner_id=owner_id,
                outcome=outcome,
                e2e_run_id=e2e_run_id,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            existing.outcome = outcome
            existing.e2e_run_id = e2e_run_id
            existing.updated_at = now
            row = existing
        await self._session.flush()
        return row

    async def delete_for_owner(self, owner_id: UUID) -> None:
        await self._session.execute(
            delete(BivE2eDeterministicFixtureTable).where(
                BivE2eDeterministicFixtureTable.owner_id == owner_id,
            ),
        )
        await self._session.flush()

    async def delete_for_e2e_run(self, e2e_run_id: str) -> int:
        result = await self._session.execute(
            delete(BivE2eDeterministicFixtureTable).where(
                BivE2eDeterministicFixtureTable.e2e_run_id == e2e_run_id,
            ),
        )
        await self._session.flush()
        return int(result.rowcount or 0)
