"""Phase 3.16 — system invariants for the frozen execution layer."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.executors.engine_resolver import resolve_execution_engine
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.contracts import AgentGraphState, assert_no_graph_state_secrets
from app.schemas.contracts import AgentType
from app.tools.permissions import WRITE_TOOL_NAMES, evaluate_tool_access
from app.tools.registry import get_tool_registry
from app.tools.result_builder import build_tool_error, build_tool_success
from app.tools.result_contracts import ToolExecutionErrorCode, is_tool_result_envelope
from fastapi.testclient import TestClient


def _project_agent(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    project_id = client.post(
        "/projects",
        json={"name": "Invariant project"},
        headers=headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=headers,
    ).json()["id"]
    return project_id, agent_id


def _run(client: TestClient, headers: dict[str, str], agent_id: str) -> str:
    return client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "inv"}},
        headers=headers,
    ).json()["id"]


def test_succeeded_agent_run_cannot_execute_again(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    _project_id, agent_id = _project_agent(client, auth_headers)
    run_id = _run(client, auth_headers, agent_id)
    assert client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers).status_code == 200

    retry = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert retry.status_code == 409


def test_failed_agent_run_cannot_execute_directly(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id = _project_agent(client, auth_headers)
    run_id = _run(client, auth_headers, agent_id)
    client.post(
        f"/agent-runs/{run_id}/failed",
        json={"error": "boom"},
        headers=auth_headers,
    )

    response = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert response.status_code == 409
    assert "agent_run_not_executable:failed" in response.json()["detail"]


def test_failed_agent_run_replay_only_via_clone(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id = _project_agent(client, auth_headers)
    run_id = _run(client, auth_headers, agent_id)
    client.post(
        f"/agent-runs/{run_id}/failed",
        json={"error": "boom"},
        headers=auth_headers,
    )

    clone = client.post(f"/agent-runs/{run_id}/replay", headers=auth_headers)
    assert clone.status_code == 201
    assert clone.json()["id"] != run_id
    assert clone.json()["status"] == "queued"


def test_replay_clone_does_not_copy_output_or_logs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id = _project_agent(client, auth_headers)
    run_id = _run(client, auth_headers, agent_id)
    client.post(f"/agent-runs/{run_id}/running", headers=auth_headers)
    client.post(
        f"/agent-runs/{run_id}/failed",
        json={"error": "boom"},
        headers=auth_headers,
    )
    client.post(
        "/llm-requests",
        json={
            "agent_run_id": run_id,
            "provider": "mock",
            "model": "mock-model",
            "input_payload": {"input": {"prompt": "x"}},
        },
        headers=auth_headers,
    )

    clone_id = client.post(f"/agent-runs/{run_id}/replay", headers=auth_headers).json()["id"]
    clone = client.get(f"/agent-runs/{clone_id}", headers=auth_headers).json()
    assert clone.get("output_payload") is None
    assert clone.get("error") is None

    source_logs = client.get(
        f"/llm-requests?agent_run_id={run_id}",
        headers=auth_headers,
    ).json()
    clone_logs = client.get(
        f"/llm-requests?agent_run_id={clone_id}",
        headers=auth_headers,
    ).json()
    assert len(source_logs) >= 1
    assert clone_logs == []


def test_classic_available_when_langgraph_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_LANGGRAPH_ENABLED", "false")
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "langgraph")
    get_settings.cache_clear()
    settings = get_settings()
    assert resolve_execution_engine(settings) == "classic"


def test_force_classic_overrides_project_and_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "langgraph")
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE_REQUEST_OVERRIDE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_LANGGRAPH_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    class _Project:
        config = {"execution_engine": "langgraph"}

    assert (
        resolve_execution_engine(
            settings,
            project=_Project(),
            request_override="langgraph",
        )
        == "classic"
    )


def test_webhook_signing_secret_not_in_list_or_metrics(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, _agent_id = _project_agent(client, auth_headers)
    created = client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://hooks.example.com/invariant"},
        headers=auth_headers,
    ).json()
    secret = created["signing_secret"]

    listed = client.get(f"/projects/{project_id}/webhooks", headers=auth_headers).json()
    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()

    blob = f"{listed}{metrics}".lower()
    assert secret.lower() not in blob
    assert "bwhsec" not in blob


def test_delivery_logs_strip_url_query(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.events.delivery_url import build_target_url_preview

    preview = build_target_url_preview("https://api.example.com/hook?token=secret")
    assert "?" not in preview
    assert "token" not in preview


def test_redis_failure_does_not_break_metrics_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id, _agent_id = _project_agent(client, auth_headers)

    async def _boom(_owner_id: object) -> int:
        raise ConnectionError("redis down")

    monkeypatch.setattr(
        "app.queues.handoff_queue_metrics.get_owner_queue_depth",
        _boom,
    )
    response = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["redis"]["available"] is False


def test_handoff_dlq_replay_rejects_parent_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id = _project_agent(client, auth_headers)
    run_id = _run(client, auth_headers, agent_id)
    client.post(
        f"/agent-runs/{run_id}/failed",
        json={"error": "not a handoff child"},
        headers=auth_headers,
    )

    response = client.post(f"/agent-runs/{run_id}/handoff/replay", headers=auth_headers)
    assert response.status_code == 409


def test_outbox_replay_rejects_sent_event(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from unittest.mock import AsyncMock

    import httpx

    project_id = client.post(
        "/projects",
        json={"name": "Outbox invariant"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/hook"},
        headers=auth_headers,
    )
    orch = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator", "name": "O"},
        headers=auth_headers,
    ).json()["id"]
    res = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orch,
            "input_payload": {
                "prompt": "outbox",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()

    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    with patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(
            "/agent-runs/process-handoff-children",
            headers=auth_headers,
            params={"limit": 5},
        )

    events = client.get(f"/projects/{project_id}/events", headers=auth_headers).json()
    event_id = events[0]["id"]
    ok_resp = httpx.Response(200, request=httpx.Request("POST", "https://example.com/hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    replay = client.post(
        f"/projects/{project_id}/events/{event_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 409


def test_tool_result_envelope_shape() -> None:
    success = build_tool_success("memory.search", {"items": []})
    assert is_tool_result_envelope(success)
    assert success["ok"] is True
    assert success["tool"] == "memory.search"
    assert "meta" in success
    assert "error" not in success

    failure = build_tool_error(
        "memory.search",
        code=ToolExecutionErrorCode.PERMISSION_DENIED,
        message="denied",
    )
    assert is_tool_result_envelope(failure)
    assert failure["ok"] is False
    assert failure["error"]["code"]


def test_write_tools_not_enabled() -> None:
    for tool_name in WRITE_TOOL_NAMES:
        decision = evaluate_tool_access(
            agent_type=AgentType.RESEARCHER,
            tool_name=tool_name,
            registry=get_tool_registry(),
        )
        assert not decision.allowed


def test_graph_checkpoints_reject_secrets() -> None:
    state = AgentGraphState(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        input_payload={"api_key": "sk-secret"},
    )
    with pytest.raises(ValueError, match="forbidden"):
        assert_no_graph_state_secrets(state)


def test_execute_stamps_execution_engine(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    _project_id, agent_id = _project_agent(client, auth_headers)
    run_id = _run(client, auth_headers, agent_id)
    body = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers).json()
    assert body["output_payload"]["execution"]["engine"] == "classic"
    assert body["output_payload"]["execution"]["claim_source"] == "execute_endpoint"
