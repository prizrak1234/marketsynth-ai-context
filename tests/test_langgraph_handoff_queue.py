"""Phase 3.7 — Redis handoff queue, parent sync, scheduler."""

from __future__ import annotations

import asyncio
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from app.graphs.handoff_sync import merge_handoff_child_completion
from app.queues.handoff_child_queue import HandoffChildQueue, handoff_queue_key
from app.workers.handoff_scheduler import HandoffChildScheduler
from fastapi.testclient import TestClient


def test_merge_handoff_child_completion_updates_parent_handoff() -> None:
    merged = merge_handoff_child_completion(
        {
            "handoff": {
                "child_run_pending_worker": True,
                "child_run_executed": False,
                "child_run_status": "queued",
            },
        },
        child_status="succeeded",
        child_error=None,
        synced_at="2026-05-29T12:00:00+00:00",
    )
    handoff = merged["handoff"]
    assert handoff["child_run_executed"] is True
    assert handoff["child_run_pending_worker"] is False
    assert handoff["child_run_status"] == "succeeded"
    assert handoff["parent_handoff_synced_at"] == "2026-05-29T12:00:00+00:00"


@pytest.mark.asyncio
async def test_handoff_child_queue_enqueue_dequeue(fake_redis: object) -> None:
    from app.core.redis import init_redis

    await init_redis()
    await fake_redis.flushall()
    owner_id = uuid4()
    run_id = uuid4()
    queue = HandoffChildQueue()
    assert await queue.enqueue(owner_id, run_id) is True
    assert await queue.pending_count(owner_id) == 1
    owners = await queue.list_owners_with_pending()
    assert owner_id in owners
    dequeued = await queue.dequeue_batch(owner_id, limit=5)
    assert dequeued == [run_id]
    assert await queue.pending_count(owner_id) == 0
    owners_after = await queue.list_owners_with_pending()
    assert owner_id not in owners_after


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Queue Project"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_type: str,
    name: str,
) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": agent_type, "name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    agent_id: str,
    *,
    input_payload: dict,
) -> dict:
    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": input_payload, "metadata": {}},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _patch_runner_with_store(store):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def test_handoff_enqueue_pushes_redis_and_worker_syncs_parent(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings
    from app.core.redis import get_redis
    from app.graphs.checkpoints import InMemoryGraphCheckpointStore

    monkeypatch.setenv("GRAPH_HANDOFF_QUEUE_ENABLED", "true")
    get_settings.cache_clear()
    asyncio.run(get_redis().flushall())
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    run = _create_run(
        client,
        auth_headers,
        orchestrator_id,
        input_payload={
            "prompt": "queue handoff",
            "handoff_to_agent_id": researcher_id,
            "handoff_enqueue_child": True,
            "handoff_execute_child": False,
        },
    )

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        parent_resp = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert parent_resp.status_code == 200

    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    child_id = parent["output_payload"]["handoff"]["child_run_id"]
    owner_uuid = UUID(parent["owner_id"])
    redis = get_redis()
    assert asyncio.run(redis.llen(handoff_queue_key(owner_uuid))) == 1
    assert asyncio.run(redis.lindex(handoff_queue_key(owner_uuid), 0)) == child_id

    child_before = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child_before["status"] == "queued"

    parent_before = parent["output_payload"]["handoff"]
    assert parent_before["child_run_pending_worker"] is True
    assert "parent_handoff_synced_at" not in parent_before

    with _patch_runner_with_store(store):
        worker_resp = client.post(
            "/agent-runs/process-handoff-children",
            headers=auth_headers,
            params={"limit": 5},
        )
    assert worker_resp.status_code == 200
    body = worker_resp.json()
    assert body["parent_synced_count"] >= 1

    parent_after = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    handoff = parent_after["output_payload"]["handoff"]
    assert handoff["child_run_executed"] is True
    assert handoff["child_run_pending_worker"] is False
    assert handoff["child_run_status"] == "succeeded"
    assert handoff["parent_handoff_synced_at"]

    child_after = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child_after["status"] == "succeeded"
    assert asyncio.run(redis.llen(handoff_queue_key(owner_uuid))) == 0


@pytest.mark.asyncio
async def test_scheduler_run_once_processes_queued_child(
    database_url: str,
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings
    from app.core.redis import init_redis
    from app.db.models.user import UserTable
    from app.db.repositories.user_repo import UserRepository
    from app.graphs.checkpoints import InMemoryGraphCheckpointStore
    from app.graphs.runner import AgentGraphRunner
    from app.schemas.contracts import AgentType
    from app.schemas.crud import AgentCreateRequest, ProjectCreate
    from app.services.agent_runs import AgentRunService
    from app.services.agents import AgentService
    from app.services.projects_service import ProjectService

    monkeypatch.setenv("GRAPH_HANDOFF_SCHEDULER_ENABLED", "true")
    get_settings.cache_clear()
    await init_redis()
    await fake_redis.flushall()

    from tests.conftest import _init_database_schema

    await _init_database_schema()
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        owner = await UserRepository(session).create(UserTable(telegram_id=9501))
        project = await ProjectService(session).create(
            ProjectCreate(owner_id=owner.id, name="Scheduler Project"),
        )
        researcher = await AgentService(session).create_agent(
            owner.id,
            AgentCreateRequest(
                project_id=project.id,
                type=AgentType.RESEARCHER,
                name="Sched Agent",
            ),
        )
        assert researcher is not None
        runs = AgentRunService(session)
        child = await runs.create_run(
            owner.id,
            agent_id=researcher.id,
            task_id=None,
            input_payload={"prompt": "child"},
            metadata={
                "parent_agent_run_id": str(owner.id),
                "execution_engine": "langgraph-handoff-child",
            },
        )
        assert child is not None
        await HandoffChildQueue().enqueue(owner.id, child.id)

    store = InMemoryGraphCheckpointStore()

    class _RunnerWithStore(AgentGraphRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    with patch("app.graphs.runner.AgentGraphRunner", _RunnerWithStore):
        scheduler = HandoffChildScheduler()
        summary = await scheduler.run_once()

    assert summary["processed"] >= 1
    async with factory() as session:
        finished = await AgentRunService(session).get_run(owner.id, child.id)
        assert finished is not None
        assert finished.status.value == "succeeded"
