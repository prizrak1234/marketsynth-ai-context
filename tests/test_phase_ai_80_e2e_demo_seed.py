"""Phase AI.80 — E2E demo seed."""

from __future__ import annotations

import pytest
from app.services.e2e_demo_seed_service import E2eDemoSeedService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_e2e_seed_idempotent(db_session: AsyncSession) -> None:
    service = E2eDemoSeedService(db_session)
    first = await service.seed()
    second = await service.seed()
    await db_session.commit()

    assert first.project_id == second.project_id
    assert first.marketing_plan_id == second.marketing_plan_id
    assert first.publication_package_job_id == second.publication_package_job_id
    assert first.content_asset_id == second.content_asset_id
