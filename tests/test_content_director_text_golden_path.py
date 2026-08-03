"""PRODUCT-CD-RUNTIME-01 — Content Director Text Golden Path oracles."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _deterministic_content_director(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTENT_DIRECTOR_DETERMINISTIC", "true")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _project(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Content Director GP"},
        headers=headers,
    ).json()["id"]


def _create_request(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/content-director/requests",
        headers=headers,
        json={
            "title": "Launch post",
            "objective": "Announce offer",
            "audience_description": "SMB owners",
            "key_message": "Save time with Marketsynth",
            "offer_value_proposition": "Launch pack in days",
            "tone": "confident",
            "language": "ru",
            "length": "medium",
            "cta": "Start free",
            "must_include": "Telegram",
            "must_avoid": "hype",
            "requested_variants": 2,
            "channel": "telegram",
            "content_type": "telegram_post",
            "context_source": "manual",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["context_source"] == "manual"
    assert body["channel"] == "telegram"
    assert body["content_type"] == "telegram_post"
    return body["id"]


def test_create_request_and_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    got = client.get(
        f"/projects/{project_id}/content-director/requests/{request_id}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.json()["id"] == request_id


def test_duplicate_submit_reuses_idempotency_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    first = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "k1"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "succeeded"
    run_id = first.json()["id"]

    second = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "k1"},
    )
    assert second.status_code == 200
    assert second.json()["id"] == run_id


def test_candidates_edit_approve_immutable(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    gen = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    assert gen.status_code == 200
    workspace = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    )
    assert workspace.status_code == 200
    candidates = workspace.json()["candidates"]
    assert 1 <= len(candidates) <= 3
    asset_id = candidates[0]["asset_id"]
    pinned_version = candidates[0]["content_request_version"]

    edited = client.patch(
        f"/projects/{project_id}/content-director/requests/{request_id}/candidates/{asset_id}",
        headers=auth_headers,
        json={"body": "Edited telegram body for golden path"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["body"] == "Edited telegram body for golden path"
    assert edited.json()["current_version_number"] >= 2
    assert edited.json()["content_request_version"] == pinned_version

    approved = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    blocked = client.patch(
        f"/projects/{project_id}/content-director/requests/{request_id}/candidates/{asset_id}",
        headers=auth_headers,
        json={"body": "should fail"},
    )
    assert blocked.status_code == 409

    restored = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    )
    assert restored.status_code == 200
    assert restored.json()["approved_asset_id"] == asset_id
    assert restored.json()["next_action"] == "approved"


def test_cross_project_denied(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    p1 = _project(client, auth_headers)
    p2 = client.post(
        "/projects",
        json={"name": "Other"},
        headers=auth_headers,
    ).json()["id"]
    request_id = _create_request(client, auth_headers, p1)
    denied = client.get(
        f"/projects/{p2}/content-director/requests/{request_id}",
        headers=auth_headers,
    )
    assert denied.status_code == 404


def test_cross_tenant_denied(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    denied = client.get(
        f"/projects/{project_id}/content-director/requests/{request_id}",
        headers=other_auth_headers,
    )
    assert denied.status_code in (403, 404)


def test_regenerate_blocked_after_approve(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    workspace = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    asset_id = workspace["candidates"][0]["asset_id"]
    prior_run_id = workspace["active_run"]["id"]
    client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    asset_before = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    blocked = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "after-approve"},
    )
    assert blocked.status_code == 409, blocked.text
    asset_after = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset_after["status"] == "approved"
    assert asset_after["body"] == asset_before["body"]
    assert asset_after["approved_version_number"] == asset_before["approved_version_number"]
    restored = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert restored["approved_asset_id"] == asset_id
    assert restored["active_run"]["id"] == prior_run_id
    assert any(c["asset_id"] == asset_id for c in restored["candidates"])


def test_provider_failure_normalizes(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import InvalidStateError
    from app.services import content_director_service as cds

    calls = {"n": 0}

    async def _boom(self: object, *args: object, **kwargs: object) -> list[object]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise InvalidStateError("provider_failure: RuntimeError")
        from app.services.content_director_text_adapter import ContentDirectorTextAdapter

        return ContentDirectorTextAdapter._deterministic_candidates(  # noqa: SLF001
            self,  # type: ignore[arg-type]
            snapshot_payload=kwargs["snapshot_payload"],  # type: ignore[arg-type]
            count=int(kwargs["requested_variants"]),  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        cds.ContentDirectorTextAdapter,
        "generate_candidates",
        _boom,
    )
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    failed = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "fail-1"},
    )
    assert failed.status_code == 200, failed.text
    body = failed.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "provider_failure"
    assert body["error_message"] == "provider_failure"
    workspace = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert workspace["active_run"]["status"] == "failed"
    assert workspace["next_action"] != "wait_generation"
    again = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "fail-retry"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "succeeded"


def test_one_active_run_reused_while_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    import asyncio
    from uuid import UUID

    from sqlalchemy import select

    from app.db.models.content_director import ContentInputSnapshotTable, ContentRequestTable, ContentRunTable
    from app.db.session import get_session_factory
    from app.schemas.contracts import ContentRunStatus

    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)

    async def seed_running() -> str:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(ContentRequestTable).where(ContentRequestTable.id == UUID(request_id))
            )
            req = result.scalar_one()
            snap = ContentInputSnapshotTable(
                owner_id=req.owner_id,
                project_id=req.project_id,
                content_request_id=req.id,
                content_request_version=req.version,
                payload={
                    "content_request_id": str(req.id),
                    "content_request_version": req.version,
                },
            )
            session.add(snap)
            await session.flush()
            run = ContentRunTable(
                owner_id=req.owner_id,
                project_id=req.project_id,
                content_request_id=req.id,
                content_request_version=req.version,
                snapshot_id=snap.id,
                status=ContentRunStatus.RUNNING,
                attempt=1,
                idempotency_key="in-flight",
            )
            session.add(run)
            await session.flush()
            req.current_run_id = run.id
            await session.commit()
            return str(run.id)

    run_id = asyncio.run(seed_running())
    second = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "other-key"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == run_id
    assert second.json()["status"] == "running"


def test_approve_pins_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    workspace = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    asset_id = workspace["candidates"][0]["asset_id"]
    run_id = workspace["active_run"]["id"]
    version = workspace["candidates"][0]["content_request_version"]
    approved = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    assert approved.status_code == 200
    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    approval = (asset.get("metadata") or {}).get("approval") or {}
    assert approval.get("type") == "content_approval"
    assert approval.get("content_request_id") == request_id
    assert approval.get("content_request_version") == version
    assert approval.get("content_run_id") == run_id
    assert approval.get("asset_version") == asset["approved_version_number"]
