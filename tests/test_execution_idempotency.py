"""Phase 3.14 — execution idempotency and concurrency guard."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.services.agent_runs import AgentRunService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _create_run(client: TestClient, auth_headers: dict[str, str]) -> str:
    project_id = client.post(
        "/projects",
        json={"name": "Idempotency"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    return client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "run"}},
        headers=auth_headers,
    ).json()["id"]


def _patch_graph_runner(store: InMemoryGraphCheckpointStore):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.executors.agent_run_coordinator.AgentGraphRunner", _RunnerWithStore)


@pytest.mark.asyncio
async def test_queued_run_can_be_claimed_once(
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    client: TestClient,
) -> None:
    run_id = _create_run(client, auth_headers)
    owner_id = UUID(client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["owner_id"])
    service = AgentRunService(db_session)
    claimed = await service.claim_queued_run(owner_id, UUID(run_id))
    assert claimed is not None
    assert claimed.status.value == "running"


@pytest.mark.asyncio
async def test_second_concurrent_claim_returns_none(
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    client: TestClient,
) -> None:
    run_id = _create_run(client, auth_headers)
    owner_id = UUID(client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["owner_id"])
    run_uuid = UUID(run_id)
    service = AgentRunService(db_session)

    first = await service.claim_queued_run(owner_id, run_uuid)
    second = await service.claim_queued_run(owner_id, run_uuid)
    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_execute_rejects_running_run(
    db_session: AsyncSession,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from uuid import UUID

    run_id = _create_run(client, auth_headers)
    owner_id = UUID(client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["owner_id"])
    claimed = await AgentRunService(db_session).claim_queued_run(owner_id, UUID(run_id))
    assert claimed is not None

    response = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert response.status_code == 409
    assert "already_running_or_claimed" in response.json()["detail"]


def test_execute_rejects_succeeded_run(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)
    assert client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers).status_code == 200

    retry = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert retry.status_code == 409
    assert "agent_run_already_completed" in retry.json()["detail"]


def test_execute_rejects_failed_run(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)

    with patch(
        "app.executors.agent_run_executor.build_llm_messages",
        side_effect=RuntimeError("executor boom"),
    ):
        failed = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert failed.status_code == 500
    assert client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["status"] == "failed"

    retry = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert retry.status_code == 409
    assert "agent_run_not_executable:failed" in retry.json()["detail"]


def test_same_idempotency_key_on_completed_run_returns_cached(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)
    headers = {**auth_headers, "Idempotency-Key": "idem-abc-1"}

    first = client.post(f"/agent-runs/{run_id}/execute", headers=headers)
    assert first.status_code == 200
    first_body = first.json()

    with patch(
        "app.executors.agent_run_coordinator.AgentRunExecutor.execute_run",
    ) as execute_mock:
        second = client.post(f"/agent-runs/{run_id}/execute", headers=headers)
        execute_mock.assert_not_called()

    assert second.status_code == 200
    assert second.json()["id"] == first_body["id"]
    assert second.json()["status"] == "succeeded"


def test_different_idempotency_key_on_completed_run_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)
    client.post(
        f"/agent-runs/{run_id}/execute",
        headers={**auth_headers, "Idempotency-Key": "key-one"},
    )

    conflict = client.post(
        f"/agent-runs/{run_id}/execute",
        headers={**auth_headers, "Idempotency-Key": "key-two"},
    )
    assert conflict.status_code == 409
    assert "idempotency_key_mismatch" in conflict.json()["detail"]


@pytest.mark.parametrize(
    ("key", "expected_fragment"),
    [
        ("x" * 129, "idempotency_key_too_long"),
        ("bad key spaces", "invalid_idempotency_key"),
        ("key/with/slash", "invalid_idempotency_key"),
    ],
)
def test_invalid_idempotency_key_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    key: str,
    expected_fragment: str,
) -> None:
    run_id = _create_run(client, auth_headers)
    response = client.post(
        f"/agent-runs/{run_id}/execute",
        headers={**auth_headers, "Idempotency-Key": key},
    )
    assert response.status_code == 409
    assert expected_fragment in response.json()["detail"]


def test_classic_execute_writes_execution_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)
    body = client.post(
        f"/agent-runs/{run_id}/execute",
        headers={**auth_headers, "Idempotency-Key": "meta-classic"},
    ).json()
    execution = body["output_payload"]["execution"]
    assert execution["engine"] == "classic"
    assert execution["idempotency_key"] == "meta-classic"
    assert execution["claim_source"] == "execute_endpoint"
    assert execution.get("started_at")
    assert execution.get("finished_at")


def test_langgraph_execute_writes_execution_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "langgraph")
    monkeypatch.setenv("AGENT_EXECUTION_LANGGRAPH_ENABLED", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)
    store = InMemoryGraphCheckpointStore()

    with _patch_graph_runner(store):
        body = client.post(
            f"/agent-runs/{run_id}/execute",
            headers={**auth_headers, "Idempotency-Key": "meta-graph"},
        ).json()

    execution = body["output_payload"]["execution"]
    assert execution["engine"] == "langgraph"
    assert execution["graph_version"]
    assert execution["idempotency_key"] == "meta-graph"
    assert execution["claim_source"] == "execute_endpoint"
    assert execution.get("started_at")
    assert execution.get("finished_at")


def test_executor_failure_after_claim_marks_run_failed(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    run_id = _create_run(client, auth_headers)

    with patch(
        "app.executors.agent_run_executor.build_llm_messages",
        side_effect=RuntimeError("boom after claim"),
    ):
        response = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)

    assert response.status_code == 500
    run = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert run.get("error")

    retry = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert retry.status_code == 409


def test_dry_run_endpoints_unchanged(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    run_id = _create_run(client, auth_headers)
    classic = client.post(
        f"/agent-runs/{run_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert classic.status_code == 200
    assert "execution" not in (classic.json().get("output_payload") or {})

    agent_id = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["agent_id"]
    run2_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "graph dry"}},
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with patch("app.api.routes.agent_runs.AgentGraphRunner") as mock_cls:
        from app.graphs.runner import AgentGraphRunner as RealRunner

        mock_cls.side_effect = lambda *args, **kwargs: RealRunner(
            *args,
            **kwargs,
            checkpoint_store=store,
        )
        graph = client.post(
            f"/agent-runs/{run2_id}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert graph.status_code == 200
