"""PRODUCT-01.3A.2 — backend availability and migrated DB integration tests."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.domain.alembic_revision_guard import _compute_heads, is_revision_in_chain, list_code_revisions
from app.services.analysis_context_subsystem_readiness import inspect_analysis_context_subsystem
from scripts.repair_product_01_3a_dev_db import PRODUCT_01_3A_MIN_REVISION
from tests.test_product_01_3a_biv_intake_gate import _valid_fields

ROOT = Path(__file__).resolve().parents[1]


def _code_head() -> str:
    heads = _compute_heads(list_code_revisions())
    assert len(heads) == 1
    return heads[0]


def _run_repair(database_url: str, *, fresh: bool = True) -> dict:
    env = {**os.environ, "DATABASE_URL": database_url}
    args = ["uv", "run", "python", "scripts/repair_product_01_3a_dev_db.py"]
    if fresh:
        args.append("--fresh")
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


@pytest.fixture
def migrated_sqlite_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "product_01_3a_migrated.db"
    url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    report = _run_repair(url, fresh=True)
    assert report["status"] == "passed"
    assert report["after"]["ready"] is True

    import fakeredis.aioredis
    from app.core import redis as redis_module

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _init(_settings: object = None) -> None:
        redis_module._redis = client  # noqa: SLF001

    async def _close() -> None:
        await client.aclose()
        redis_module._redis = None  # noqa: SLF001

    monkeypatch.setattr(redis_module, "init_redis", _init)
    monkeypatch.setattr(redis_module, "close_redis", _close)

    from app.db.session import close_db, init_db, reset_db_state
    from app.main import app

    async def _boot() -> None:
        reset_db_state()
        await init_db()
        await _init()

    asyncio.run(_boot())
    yield app
    asyncio.run(_close())
    asyncio.run(close_db())
    get_settings.cache_clear()


@pytest.fixture
def migrated_client(migrated_sqlite_app) -> TestClient:
    with TestClient(migrated_sqlite_app) as test_client:
        yield test_client


def test_current_code_head_includes_product_01_3a_min_revision() -> None:
    head = _code_head()
    assert is_revision_in_chain(PRODUCT_01_3A_MIN_REVISION, head=head)


def test_repair_script_bootstraps_analysis_context_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "repair_only.db"
    url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    report = _run_repair(url, fresh=True)
    head = _code_head()
    assert report["stamped_revision"] == head
    assert report["code_head"] == head
    assert report["required_min_revision"] == PRODUCT_01_3A_MIN_REVISION
    assert report["required_min_revision_in_chain"] is True
    assert report["after"]["table_present"] is True
    assert report["after"]["biv_bridge_columns_present"] is True


@pytest.mark.asyncio
async def test_missing_analysis_context_table_fails_readiness(tmp_path: Path) -> None:
    db_file = tmp_path / "empty_schema.db"
    url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    engine = create_async_engine(url)
    try:
        status = await inspect_analysis_context_subsystem(engine)
    finally:
        await engine.dispose()
    assert status.ready is False
    assert status.table_present is False


def test_openapi_lists_analysis_context_paths(migrated_client: TestClient) -> None:
    openapi = migrated_client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json().get("paths", {})
    assert "/projects/{project_id}/analysis-contexts" in paths
    assert "/projects/{project_id}/analysis-contexts/current" in paths
    assert "/projects/{project_id}/analysis-contexts/{context_id}/confirm" in paths


def test_migrated_db_intake_flow_draft_confirm(
    migrated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.conftest import _create_user_with_api_key

    plain_key, _user = asyncio.run(_create_user_with_api_key())
    headers = {"Authorization": f"Bearer {plain_key}"}

    project = migrated_client.post("/projects", headers=headers, json={"name": "Migrated intake"})
    assert project.status_code == 201
    project_id = project.json()["id"]

    draft = migrated_client.post(
        f"/projects/{project_id}/analysis-contexts",
        headers=headers,
        json=_valid_fields().model_dump(),
    )
    assert draft.status_code == 201, draft.text
    context_id = draft.json()["context_id"]

    confirm = migrated_client.post(
        f"/projects/{project_id}/analysis-contexts/{context_id}/confirm",
        headers=headers,
        json={},
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["confirmed_by_user"] is True
    assert body["input_snapshot_hash"]

    current = migrated_client.get(
        f"/projects/{project_id}/analysis-contexts/current",
        headers=headers,
    )
    assert current.status_code == 200
    assert current.json()["context"]["state"] == "confirmed"
