"""RUNTIME-01F — server-side deterministic fixture (NOT in public HTTP contract)."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories.biv_e2e_deterministic_fixtures import (
    BivE2eDeterministicFixtureRepository,
)


class E2eDeterministicOutcome(StrEnum):
    VERDICT = "verdict"
    PARTIAL = "partial"
    TECHNICAL = "technical"


class E2eDeterministicFixtureService:
    """Tenant-scoped fixture binding for Level-1 E2E only."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = BivE2eDeterministicFixtureRepository(session)

    @property
    def allowed(self) -> bool:
        return self._settings.biv_e2e_deterministic_allowed

    async def bind_for_owner(
        self,
        owner_id: UUID,
        outcome: E2eDeterministicOutcome,
        *,
        e2e_run_id: str,
    ) -> None:
        if not self.allowed:
            raise RuntimeError("e2e_deterministic_fixture_forbidden")
        await self._repo.upsert(owner_id=owner_id, outcome=outcome.value, e2e_run_id=e2e_run_id)

    async def resolve_for_owner(self, owner_id: UUID) -> E2eDeterministicOutcome | None:
        if not self.allowed:
            return None
        row = await self._repo.get_by_owner(owner_id)
        if row is None:
            return None
        try:
            return E2eDeterministicOutcome(row.outcome)
        except ValueError:
            return None

    async def clear_for_owner(self, owner_id: UUID) -> None:
        await self._repo.delete_for_owner(owner_id)

    async def clear_for_e2e_run(self, e2e_run_id: str) -> int:
        return await self._repo.delete_for_e2e_run(e2e_run_id)
