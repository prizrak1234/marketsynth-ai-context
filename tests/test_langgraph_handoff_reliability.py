"""Phase 3.8 — handoff DLQ, worker retries, and parent sync outbox."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from app.core.config import get_settings
from app.core.exceptions import ExecutorError
from app.events.contracts import HANDOFF_CHILD_STATUS_DEAD_LETTERED
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.handoff_worker_state import get_handoff_worker_state
from app.queues.handoff_dead_letter_queue import HandoffDeadLetterQueue
from app.schemas.contracts import AgentRunStatus, EventOutboxStatus, EventType
from app.workers.handoff_scheduler import HandoffChildScheduler
from fastapi.testclient import TestClient

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


def _patch_runner_with_store(store: InMemoryGraphCheckpointStore):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Reliability Project"}, headers=headers)
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


def _delegate_handoff_child(
    client: TestClient,
    headers: dict[str, str],
    orchestrator_id: str,
    researcher_id: str,
) -> tuple[dict, str]:
    run = _create_run(
        client,
        headers,
        orchestrator_id,
        input_payload={
            "prompt": "reliability handoff",
            "handoff_to_agent_id": researcher_id,
            "handoff_enqueue_child": True,
            "handoff_execute_child": False,
        },
    )
    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=headers,
        )
    assert response.status_code == 200
    parent = client.get(f"/agent-runs/{run['id']}", headers=headers).json()
    child_id = parent["output_payload"]["handoff"]["child_run_id"]
    return parent, child_id


@pytest.fixture
def max_attempts_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRAPH_HANDOFF_MAX_ATTEMPTS", "2")
    get_settings.cache_clear()


def test_failed_child_increments_attempts(
    client: TestClient,
    auth_headers: dict[str, str],
    max_attempts_two: None,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    _parent, child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )

    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=ExecutorError("transient_failure"),
    ):
        response = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["requeued_count"] >= 1

    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    worker_state = child["metadata"]["handoff_worker"]
    assert worker_state["attempts"] == 1
    assert worker_state["dead_lettered"] is False
    assert "transient_failure" in worker_state["last_error"]


def test_child_retried_when_attempts_below_max(
    client: TestClient,
    auth_headers: dict[str, str],
    max_attempts_two: None,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    _parent, child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )

    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=ExecutorError("retry_me"),
    ):
        first = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert first.status_code == 200
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child["status"] == "queued"
    assert child["metadata"]["handoff_worker"]["attempts"] == 1


def test_child_moved_to_dlq_after_max_attempts(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: object,
    max_attempts_two: None,
) -> None:
    from app.core.redis import get_redis

    asyncio.run(get_redis().flushall())
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    parent, child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )
    owner_uuid = UUID(parent["owner_id"])

    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=ExecutorError("always_fails"),
    ):
        client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
        response = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert response.status_code == 200
    assert response.json()["dead_lettered_count"] >= 1

    dlq = HandoffDeadLetterQueue()
    entries = asyncio.run(dlq.list_entries(owner_uuid, limit=10))
    assert len(entries) >= 1
    entry = entries[-1]
    assert entry["child_run_id"] == child_id
    assert entry["attempts"] == 2
    assert "Traceback" not in entry["last_error"]
    assert "always_fails" in entry["last_error"]


def test_parent_sync_marks_dead_lettered(
    client: TestClient,
    auth_headers: dict[str, str],
    max_attempts_two: None,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    parent, child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )

    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=ExecutorError("dlq_path"),
    ):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    parent_after = client.get(f"/agent-runs/{parent['id']}", headers=auth_headers).json()
    handoff = parent_after["output_payload"]["handoff"]
    assert handoff["child_run_status"] == HANDOFF_CHILD_STATUS_DEAD_LETTERED
    assert handoff["child_run_executed"] is False
    assert handoff["parent_handoff_synced_at"]

    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child["metadata"]["handoff_worker"]["dead_lettered"] is True


def test_one_failed_child_does_not_block_next(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.graphs import handoff as handoff_module

    monkeypatch.setenv("GRAPH_HANDOFF_MAX_ATTEMPTS", "5")
    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    _parent1, child1 = _delegate_handoff_child(client, auth_headers, orchestrator_id, researcher_id)
    _parent2, child2 = _delegate_handoff_child(client, auth_headers, orchestrator_id, researcher_id)

    fail_once = {child1}

    async def _execute_side_effect(session, *, owner_id, run_id, agent_runs=None):
        if str(run_id) in fail_once:
            fail_once.remove(str(run_id))
            raise ExecutorError("first_child_fails")
        return await handoff_module.execute_handoff_child_run(
            session,
            owner_id=owner_id,
            run_id=run_id,
            agent_runs=agent_runs,
        )

    store = InMemoryGraphCheckpointStore()
    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=_execute_side_effect,
    ), _patch_runner_with_store(store):
        response = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["processed_count"] >= 2
    assert body["requeued_count"] >= 1
    child2_after = client.get(f"/agent-runs/{child2}", headers=auth_headers).json()
    assert child2_after["status"] == "succeeded"


def test_db_fallback_respects_max_attempts(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    max_attempts_two: None,
) -> None:
    monkeypatch.setenv("GRAPH_HANDOFF_QUEUE_ENABLED", "false")
    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    _parent, child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )

    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=ExecutorError("db_fallback"),
    ):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})
        response = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert response.json()["dead_lettered_count"] >= 1
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child["metadata"]["handoff_worker"]["dead_lettered"] is True


def test_parent_sync_creates_outbox_event(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    parent, child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        worker_resp = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert worker_resp.status_code == 200

    events_resp = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"event_type": EventType.GRAPH_HANDOFF_PARENT_SYNCED.value},
    )
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    event = events[0]
    assert event["event_type"] == EventType.GRAPH_HANDOFF_PARENT_SYNCED.value
    assert event["status"] == EventOutboxStatus.PENDING.value
    assert event["payload"]["parent_run_id"] == parent["id"]
    assert event["payload"]["child_run_id"] == child_id
    assert "password" not in str(event["payload"]).lower()


def test_outbox_failure_does_not_break_parent_sync(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    parent, _child_id = _delegate_handoff_child(
        client, auth_headers, orchestrator_id, researcher_id,
    )

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store), patch(
        "app.events.outbox.EventOutboxService.append_event",
        new_callable=AsyncMock,
        return_value=None,
    ):
        worker_resp = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert worker_resp.status_code == 200
    assert worker_resp.json()["parent_synced_count"] >= 1

    parent_after = client.get(f"/agent-runs/{parent['id']}", headers=auth_headers).json()
    assert parent_after["output_payload"]["handoff"]["parent_handoff_synced_at"]


def test_events_api_enforces_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    response = client.get(f"/projects/{project_id}/events", headers=other_auth_headers)
    assert response.status_code == 404


def test_events_api_filters_by_type_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    _delegate_handoff_child(client, auth_headers, orchestrator_id, researcher_id)

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    pending = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={
            "event_type": EventType.GRAPH_HANDOFF_PARENT_SYNCED.value,
            "status": EventOutboxStatus.PENDING.value,
        },
    ).json()
    assert len(pending) >= 1
    assert all(row["status"] == EventOutboxStatus.PENDING.value for row in pending)

    empty = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.SENT.value},
    ).json()
    assert empty == []


@pytest.mark.asyncio
async def test_scheduler_still_works_when_dlq_enabled(
    database_url: str,
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.redis import init_redis
    from app.db.models.user import UserTable
    from app.db.repositories.user_repo import UserRepository
    from app.graphs.runner import AgentGraphRunner
    from app.queues.handoff_child_queue import HandoffChildQueue
    from app.schemas.contracts import AgentType
    from app.schemas.crud import AgentCreateRequest, ProjectCreate
    from app.services.agent_runs import AgentRunService
    from app.services.agents import AgentService
    from app.services.projects_service import ProjectService

    monkeypatch.setenv("GRAPH_HANDOFF_DLQ_ENABLED", "true")
    monkeypatch.setenv("GRAPH_HANDOFF_SCHEDULER_ENABLED", "true")
    get_settings.cache_clear()
    await init_redis()
    await fake_redis.flushall()

    from tests.conftest import _init_database_schema

    await _init_database_schema()
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        owner = await UserRepository(session).create(UserTable(telegram_id=9601))
        project = await ProjectService(session).create(
            ProjectCreate(owner_id=owner.id, name="Scheduler DLQ"),
        )
        researcher = await AgentService(session).create_agent(
            owner.id,
            AgentCreateRequest(
                project_id=project.id,
                type=AgentType.RESEARCHER,
                name="Sched DLQ",
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
        summary = await HandoffChildScheduler().run_once()
    assert summary["processed"] >= 1


def test_classic_executor_unaffected_by_handoff_reliability(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Classic"
    )
    run = _create_run(
        client,
        auth_headers,
        researcher_id,
        input_payload={"prompt": "classic only", "handoff_to_agent_id": researcher_id},
    )
    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "handoff" not in body.get("output_payload", {})
    assert "handoff_worker" not in body.get("metadata", {})


@pytest.mark.asyncio
async def test_handoff_worker_state_helpers(db_session) -> None:
    from app.db.models.agent_run import AgentRunTable
    from app.graphs.handoff_worker_state import (
        is_handoff_worker_eligible,
        mark_handoff_worker_dead_lettered,
        record_handoff_worker_attempt,
    )

    run = AgentRunTable(
        owner_id=UUID("00000000-0000-0000-0000-000000000001"),
        project_id=UUID("00000000-0000-0000-0000-000000000002"),
        agent_id=UUID("00000000-0000-0000-0000-000000000003"),
        status=AgentRunStatus.QUEUED,
        run_metadata={},
    )
    meta = record_handoff_worker_attempt({}, last_error="safe error")
    run.run_metadata = meta
    assert get_handoff_worker_state(meta)["attempts"] == 1
    assert is_handoff_worker_eligible(run, max_attempts=3)

    meta = mark_handoff_worker_dead_lettered(meta)
    run.run_metadata = meta
    assert is_handoff_worker_eligible(run, max_attempts=3) is False
