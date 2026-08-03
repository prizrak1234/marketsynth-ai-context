"""Phase AI.83 — Content production provenance."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.demo.provenance_helpers import build_content_production_provenance
from app.services.e2e_demo_seed_service import E2eDemoSeedService


@pytest.mark.asyncio
async def test_provenance_chain_ids_only(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    from uuid import UUID

    bootstrap = client.post("/projects", json={"name": "AI.83 bootstrap"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    seed = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    provenance = await build_content_production_provenance(
        db_session,
        seed.user_id,
        seed.project_id,
        seed.publication_package_job_id,
    )
    assert provenance is not None
    assert provenance.marketing_plan is not None
    assert provenance.execution_run is not None
    assert provenance.copywriter_output is not None
    assert provenance.content_asset is not None
    assert provenance.publication_package is not None
    assert provenance.publication_package_job is not None

    http = client.get(
        f"/projects/{seed.project_id}/provenance/content-production/"
        f"{seed.publication_package_job_id}",
        headers=auth_headers,
    )
    assert http.status_code == 200
    body = http.json()
    assert str(seed.marketing_plan_id) == body["marketing_plan"]["id"]
    assert "content" not in body
    assert "prompt" not in str(body).lower()
