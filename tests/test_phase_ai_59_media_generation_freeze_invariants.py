"""Phase AI.59 — Media generation layer freeze invariants (AI.56–AI.58)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.core.config import get_settings
from app.db.repositories.media_generation_jobs import MediaGenerationJobRepository
from app.marketing.media_contracts import MediaBriefStatus
from app.media_generation.contracts import MediaGenerationJobStatus, MediaGenerationProvider
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id, approve_media_brief

_FORBIDDEN_PATH_MARKERS = ("canva", "heygen", "figma", "flux/generate")
_FORBIDDEN_OPENAPI = ("midjourney", "heygen", "canva")


def _full_chain(client: TestClient, headers: dict[str, str]) -> tuple[str, str, str]:
    project_id = client.post("/projects", json={"name": "AI.59"}, headers=headers).json()["id"]
    asset_id = approved_content_asset_id(client, headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, headers, project_id, brief_id)
    job_id = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "mock"},
        headers=headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/media-generation-jobs/{job_id}/complete-mock",
        headers=headers,
    )
    return project_id, brief_id, job_id


def test_generation_flags_off_by_default() -> None:
    settings = get_settings()
    assert settings.media_generation_enabled is False
    assert settings.openai_images_enabled is False


def test_mock_provider_deterministic(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.59 mock"}, headers=auth_headers).json()[
        "id"
    ]
    brief_id = _full_chain(client, auth_headers)[1]
    jobs = client.get(
        f"/projects/{project_id}/media-generation-jobs",
        params={"media_brief_id": brief_id},
        headers=auth_headers,
    ).json()
    assert jobs[0]["provider"] == MediaGenerationProvider.MOCK.value
    assert jobs[0]["status"] == MediaGenerationJobStatus.SUCCEEDED.value
    assert jobs[0]["result_metadata"].get("mock") is True


@pytest.mark.asyncio
async def test_chain_starts_only_from_approved_brief(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, brief_id, job_id = _full_chain(client, auth_headers)
    brief = client.get(
        f"/projects/{project_id}/media-briefs/{brief_id}",
        headers=auth_headers,
    ).json()
    assert brief["status"] == MediaBriefStatus.APPROVED.value

    row = await MediaGenerationJobRepository(db_session).get_by_id_for_owner(
        UUID(job_id),
        UUID(brief["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    assert row.media_brief_id == UUID(brief_id)


def test_no_publishing_or_forbidden_provider_routes_in_openapi(
    client: TestClient,
) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    media_paths = [p for p in paths if "media-generation" in p or "generation-jobs" in p]
    assert media_paths
    for path_key in media_paths:
        for marker in _FORBIDDEN_PATH_MARKERS:
            assert marker not in path_key.lower()
        blob = path_key.lower()
        for marker in _FORBIDDEN_OPENAPI:
            assert marker not in blob


def test_flux_provider_not_selectable(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = client.post("/projects", json={"name": "AI.59 flux"}, headers=auth_headers).json()[
        "id"
    ]
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, auth_headers, project_id, brief_id)
    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "flux"},
        headers=auth_headers,
    )
    assert response.status_code == 409
