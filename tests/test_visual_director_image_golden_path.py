"""PRODUCT-CD-RUNTIME-02 — Visual Director Image Golden Path oracles."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _deterministic_visual_director(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CONTENT_DIRECTOR_IMAGE_DETERMINISTIC", "true")
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "cd-image"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _project(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Visual Director GP"},
        headers=headers,
    ).json()["id"]


def _create_request(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/visual-director/requests",
        headers=headers,
        json={
            "title": "Social image",
            "objective": "Announce offer visually",
            "scene_description": "Founder at desk with laptop, daylight",
            "subject": "Laptop and coffee",
            "style": "clean commercial",
            "audience": "SMB owners",
            "mood": "confident",
            "aspect_ratio": "1:1",
            "visual_format": "social_post_image",
            "requested_variants": 2,
            "text_overlay": "",
            "must_include": "product vibe",
            "must_avoid": "clutter",
            "language": "ru",
            "context_source": "manual",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["visual_format"] == "social_post_image"
    assert body["aspect_ratio"] == "1:1"
    assert body["context_source"] == "manual"
    return body["id"]


def test_create_request_and_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    got = client.get(
        f"/projects/{project_id}/visual-director/requests/{request_id}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.json()["id"] == request_id


def test_validation_rejects_empty_title(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    bad = client.post(
        f"/projects/{project_id}/visual-director/requests",
        headers=auth_headers,
        json={
            "title": "",
            "objective": "x",
            "scene_description": "scene",
            "subject": "subject",
            "audience": "audience",
        },
    )
    assert bad.status_code == 422


def test_duplicate_submit_reuses_idempotency_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    first = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "k1"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "succeeded"
    run_id = first.json()["id"]

    second = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "k1"},
    )
    assert second.status_code == 200
    assert second.json()["id"] == run_id


def test_candidates_checksum_mime_approve_immutable(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    gen = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    assert gen.status_code == 200, gen.text
    workspace = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    )
    assert workspace.status_code == 200
    candidates = workspace.json()["candidates"]
    assert 1 <= len(candidates) <= 4
    asset_id = candidates[0]["asset_id"]
    pinned_version = candidates[0]["visual_request_version"]
    assert candidates[0]["checksum"]
    assert candidates[0]["checksum"].startswith("sha256:")
    assert candidates[0]["mime_type"] == "image/png"
    assert candidates[0]["width"] and candidates[0]["height"]

    content = client.get(
        f"/projects/{project_id}/visual-director/candidates/{asset_id}/content",
        headers=auth_headers,
    )
    assert content.status_code == 200
    assert content.headers["content-type"].startswith("image/")
    assert content.content[:8] == b"\x89PNG\r\n\x1a\n"

    approved = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["visual_request_version"] == pinned_version

    blocked = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "after-approve"},
    )
    assert blocked.status_code == 409

    restored = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    )
    assert restored.status_code == 200
    assert restored.json()["approved_asset_id"] == asset_id
    assert restored.json()["next_action"] == "approved"
    assert restored.json()["applied_skill_id"] == "marketsynth.visual_generation"
    assert restored.json()["applied_skill_version"] == "1.0.0"

    # Second draft candidate on same request cannot replace the pin
    if len(candidates) >= 2:
        other = candidates[1]["asset_id"]
        second = client.post(
            f"/projects/{project_id}/visual-director/requests/{request_id}/candidates/{other}/approve",
            headers=auth_headers,
            json={},
        )
        assert second.status_code == 409
        pin = client.get(
            f"/projects/{project_id}/visual-director/workspace",
            headers=auth_headers,
            params={"request_id": request_id},
        ).json()
        assert pin["approved_asset_id"] == asset_id


def test_one_active_run_reused_while_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    import asyncio
    from uuid import UUID

    from sqlalchemy import select

    from app.db.models.visual_director import (
        VisualInputSnapshotTable,
        VisualRequestTable,
        VisualRunTable,
    )
    from app.db.session import get_session_factory
    from app.schemas.contracts import VisualRunStatus

    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)

    async def seed_running() -> str:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(VisualRequestTable).where(VisualRequestTable.id == UUID(request_id))
            )
            req = result.scalar_one()
            snap = VisualInputSnapshotTable(
                owner_id=req.owner_id,
                project_id=req.project_id,
                visual_request_id=req.id,
                visual_request_version=req.version,
                payload={
                    "visual_request_id": str(req.id),
                    "visual_request_version": req.version,
                },
            )
            session.add(snap)
            await session.flush()
            run = VisualRunTable(
                owner_id=req.owner_id,
                project_id=req.project_id,
                visual_request_id=req.id,
                visual_request_version=req.version,
                snapshot_id=snap.id,
                status=VisualRunStatus.RUNNING,
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
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "other-key"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == run_id
    assert second.json()["status"] == "running"


def test_regenerate_does_not_overwrite_prior_files(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "r1"},
    )
    ws1 = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    first_asset = ws1["candidates"][0]["asset_id"]
    first_checksum = ws1["candidates"][0]["checksum"]
    first_bytes = client.get(
        f"/projects/{project_id}/visual-director/candidates/{first_asset}/content",
        headers=auth_headers,
    ).content

    client.patch(
        f"/projects/{project_id}/visual-director/requests/{request_id}",
        headers=auth_headers,
        json={"scene_description": "Updated scene with window light"},
    )
    client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "r2"},
    )
    # Prior file still intact
    again = client.get(
        f"/projects/{project_id}/visual-director/candidates/{first_asset}/content",
        headers=auth_headers,
    )
    assert again.status_code == 200
    assert again.content == first_bytes
    assert first_checksum.startswith("sha256:")


def test_request_revision_marks_stale(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    ws_before = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    asset_id = ws_before["candidates"][0]["asset_id"]
    client.patch(
        f"/projects/{project_id}/visual-director/requests/{request_id}",
        headers=auth_headers,
        json={"mood": "calm"},
    )
    ws = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert ws["request"]["version"] >= 2
    assert ws["request"]["mood"] == "calm"
    assert ws["candidates"], "prior-run candidates must remain visible after revision"
    assert all(c["stale"] is True for c in ws["candidates"])
    blocked = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    assert blocked.status_code == 409


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
        f"/projects/{p2}/visual-director/requests/{request_id}",
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
        f"/projects/{project_id}/visual-director/requests/{request_id}",
        headers=other_auth_headers,
    )
    assert denied.status_code in (403, 404)


def test_provider_failure_normalization(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import InvalidStateError
    from app.services import visual_director_service as vds
    from app.services.visual_director_image_adapter import VisualDirectorImageAdapter

    calls = {"n": 0}

    async def _boom(self: object, *args: object, **kwargs: object) -> list[object]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise InvalidStateError("provider_failure: boom")
        assert isinstance(self, VisualDirectorImageAdapter)
        return self._deterministic_candidates(
            snapshot_payload=kwargs["snapshot_payload"],  # type: ignore[arg-type]
            count=int(kwargs["requested_variants"]),  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        vds.VisualDirectorImageAdapter,
        "generate_candidates",
        _boom,
    )
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    failed = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "fail-1"},
    )
    assert failed.status_code == 200, failed.text
    body = failed.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "provider_failure"
    assert body["error_message"] == "provider_failure"
    workspace = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert workspace["active_run"]["status"] == "failed"
    assert workspace["next_action"] != "wait_generation"
    again = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "fail-retry"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "succeeded"


def test_secret_redaction_in_candidate_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    ws = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    meta = ws["candidates"][0]["safe_metadata"]
    blob = str(meta).lower()
    assert "sk-" not in blob
    assert "api_key" not in blob
    assert "token" not in blob
    assert "http://" not in blob
    assert "https://" not in blob


def test_text_overlay_requires_confirmation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/visual-director/requests",
        headers=auth_headers,
        json={
            "title": "With overlay",
            "objective": "Show CTA",
            "scene_description": "Clean background",
            "subject": "Product box",
            "audience": "Buyers",
            "text_overlay": "Buy now",
            "requested_variants": 1,
        },
    )
    assert response.status_code == 201, response.text
    request_id = response.json()["id"]
    client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    asset_id = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()["candidates"][0]["asset_id"]
    blocked = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    assert blocked.status_code == 409
    ok = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={"confirm_text_overlay": True},
    )
    assert ok.status_code == 200, ok.text


def test_reference_asset_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from uuid import uuid4

    project_id = _project(client, auth_headers)
    bad = client.post(
        f"/projects/{project_id}/visual-director/requests",
        headers=auth_headers,
        json={
            "title": "Refs",
            "objective": "obj",
            "scene_description": "scene",
            "subject": "subject",
            "audience": "audience",
            "reference_asset_ids": [str(uuid4())],
        },
    )
    assert bad.status_code == 409


def test_skill_lineage_and_visual_approval_pin(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    import asyncio
    from uuid import UUID

    from sqlalchemy import select

    from app.db.models.visual_director import ImageAssetTable
    from app.db.session import get_session_factory

    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    gen = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    assert gen.status_code == 200, gen.text
    workspace = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert workspace["applied_skill_id"] == "marketsynth.visual_generation"
    assert workspace["applied_skill_version"] == "1.0.0"
    visual_run_id = workspace["active_run"]["id"]
    lineage = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.visual_generation",
            "trigger": "social_post_image",
            "input_type": "visual_request",
            "input_ref": {
                "visual_request_id": request_id,
                "visual_run_id": visual_run_id,
            },
            "idempotency_key": f"cd-visual-{visual_run_id}",
            "explicit": True,
        },
    )
    assert lineage.status_code == 200, lineage.text
    skill_run = lineage.json()
    assert skill_run["status"] == "succeeded"
    assert skill_run["skill_id"] == "marketsynth.visual_generation"
    assert skill_run["skill_version"] == "1.0.0"
    assert skill_run["idempotency_key"] == f"cd-visual-{visual_run_id}"

    asset_id = workspace["candidates"][0]["asset_id"]
    version = workspace["candidates"][0]["visual_request_version"]
    assert workspace["candidates"][0]["safe_metadata"]["skill_id"] == (
        "marketsynth.visual_generation"
    )
    assert workspace["candidates"][0]["safe_metadata"]["skill_version"] == "1.0.0"
    approved = client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/candidates/{asset_id}/approve",
        headers=auth_headers,
        json={},
    )
    assert approved.status_code == 200, approved.text

    async def load_approval() -> dict:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(ImageAssetTable).where(ImageAssetTable.id == UUID(asset_id))
            )
            asset = result.scalar_one()
            return dict((asset.asset_metadata or {}).get("approval") or {})

    approval = asyncio.run(load_approval())
    assert approval.get("type") == "visual_approval"
    assert approval.get("visual_request_id") == request_id
    assert approval.get("visual_request_version") == version
    assert approval.get("visual_run_id") == visual_run_id
    assert approval.get("asset_version") == 1


def test_interrupted_running_workspace_restore(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    import asyncio
    from uuid import UUID

    from sqlalchemy import select

    from app.db.models.visual_director import (
        VisualInputSnapshotTable,
        VisualRequestTable,
        VisualRunTable,
    )
    from app.db.session import get_session_factory
    from app.schemas.contracts import VisualRunStatus

    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)

    async def seed_running() -> None:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(VisualRequestTable).where(VisualRequestTable.id == UUID(request_id))
            )
            req = result.scalar_one()
            snap = VisualInputSnapshotTable(
                owner_id=req.owner_id,
                project_id=req.project_id,
                visual_request_id=req.id,
                visual_request_version=req.version,
                payload={
                    "visual_request_id": str(req.id),
                    "visual_request_version": req.version,
                },
            )
            session.add(snap)
            await session.flush()
            run = VisualRunTable(
                owner_id=req.owner_id,
                project_id=req.project_id,
                visual_request_id=req.id,
                visual_request_version=req.version,
                snapshot_id=snap.id,
                status=VisualRunStatus.RUNNING,
                attempt=1,
                idempotency_key="stuck-running",
            )
            session.add(run)
            await session.flush()
            req.current_run_id = run.id
            await session.commit()

    asyncio.run(seed_running())
    ws = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert ws["active_run"]["status"] == "running"
    assert ws["next_action"] == "wait_generation"
    assert ws["candidates"] == []
    assert ws["approved_asset_id"] is None


def test_failed_run_workspace_honest_next_action(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import InvalidStateError
    from app.services import visual_director_service as vds

    async def _boom(self: object, *args: object, **kwargs: object) -> list[object]:
        raise InvalidStateError("provider_failure: boom")

    monkeypatch.setattr(
        vds.VisualDirectorImageAdapter,
        "generate_candidates",
        _boom,
    )
    project_id = _project(client, auth_headers)
    request_id = _create_request(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/visual-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={"idempotency_key": "fail-ws"},
    )
    ws = client.get(
        f"/projects/{project_id}/visual-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert ws["active_run"]["status"] == "failed"
    assert ws["next_action"] == "generate"
    assert ws["approved_asset_id"] is None
    # No false-success candidates from the failed run
    assert all(c.get("status") != "approved" for c in ws.get("candidates") or [])
