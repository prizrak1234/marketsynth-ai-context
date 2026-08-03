"""Phase 3.9 — outbox dispatcher and project webhooks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.events.webhook_delivery import build_webhook_envelope, sign_webhook_body
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.schemas.contracts import EventOutboxStatus, EventType
from app.workers.outbox_dispatcher_scheduler import OutboxDispatcherScheduler
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
    response = client.post("/projects", json={"name": "Outbox Project"}, headers=headers)
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


def test_webhook_signature_is_hmac_sha256() -> None:
    body = b'{"id":"evt-1","type":"test"}'
    signature = sign_webhook_body(
        signing_secret="bwhsec_test_secret",
        timestamp="2026-05-29T12:00:00+00:00",
        body=body,
    )
    assert signature.startswith("sha256=")
    assert len(signature) > len("sha256=")


def test_create_webhook_returns_signing_secret_once(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/webhooks",
        json={
            "url": "https://example.com/botfazer-hook",
            "subscribed_event_types": [EventType.GRAPH_HANDOFF_PARENT_SYNCED.value],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["signing_secret"].startswith("bwhsec_")
    assert "signing_secret" not in body["webhook"]

    listed = client.get(f"/projects/{project_id}/webhooks", headers=auth_headers).json()
    assert len(listed) == 1
    assert "signing_secret" not in listed[0]


def test_dispatch_delivers_pending_event_and_marks_sent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch",
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res",
    )

    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/hook"},
        headers=auth_headers,
    )

    run_resp = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator_id,
            "input_payload": {
                "prompt": "dispatch test",
                "handoff_to_agent_id": researcher_id,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    )
    run_id = run_resp.json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(f"/agent-runs/{run_id}/execute-graph-dry-run", headers=auth_headers)
        client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )

    pending_before = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.PENDING.value},
    ).json()
    assert len(pending_before) >= 1

    mock_response = httpx.Response(200, request=httpx.Request("POST", "https://example.com/hook"))
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        dispatch_resp = client.post(
            f"/projects/{project_id}/events/dispatch",
            headers=auth_headers,
            params={"limit": 10},
        )
    assert dispatch_resp.status_code == 200
    assert dispatch_resp.json()["dispatched_count"] >= 1
    assert mock_post.await_count >= 1
    call_kwargs = mock_post.await_args.kwargs
    headers_sent = call_kwargs.get("headers", {})
    assert headers_sent["X-BotFazer-Signature"].startswith("sha256=")

    sent = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.SENT.value},
    ).json()
    assert len(sent) >= 1


def test_dispatch_without_webhook_skips_event(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch",
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res",
    )
    run_resp = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator_id,
            "input_payload": {
                "prompt": "no webhook",
                "handoff_to_agent_id": researcher_id,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    )
    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(
            f"/agent-runs/{run_resp.json()['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
        client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )

    dispatch_resp = client.post(
        f"/projects/{project_id}/events/dispatch",
        headers=auth_headers,
    )
    assert dispatch_resp.status_code == 200
    assert dispatch_resp.json()["skipped_count"] >= 1

    pending = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.PENDING.value},
    ).json()
    assert len(pending) >= 1


def test_dispatch_failure_increments_attempts(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/fail-hook"},
        headers=auth_headers,
    )
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch",
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res",
    )
    run_resp = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator_id,
            "input_payload": {
                "prompt": "fail dispatch",
                "handoff_to_agent_id": researcher_id,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    )
    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(
            f"/agent-runs/{run_resp.json()['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
        client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )

    fail_request = httpx.Request("POST", "https://example.com/fail-hook")
    mock_response = httpx.Response(500, request=fail_request)
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    pending = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.PENDING.value},
    ).json()
    assert pending[0]["attempts"] >= 1


def test_webhook_api_enforces_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    response = client.get(f"/projects/{project_id}/webhooks", headers=other_auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_outbox_scheduler_run_once(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings
    from app.db.models.user import UserTable
    from app.db.repositories.user_repo import UserRepository
    from app.events.outbox import EventOutboxService
    from app.schemas.crud import ProjectCreate
    from app.services.projects_service import ProjectService

    monkeypatch.setenv("EVENT_OUTBOX_DISPATCHER_ENABLED", "true")
    get_settings.cache_clear()

    from tests.conftest import _init_database_schema

    await _init_database_schema()
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        owner = await UserRepository(session).create(UserTable(telegram_id=9701))
        project = await ProjectService(session).create(
            ProjectCreate(owner_id=owner.id, name="Scheduler Outbox"),
        )
        await EventOutboxService(session).append_event(
            owner_id=owner.id,
            project_id=project.id,
            event_type=EventType.GRAPH_HANDOFF_PARENT_SYNCED,
            aggregate_type="agent_run",
            aggregate_id=owner.id,
            payload={"parent_run_id": str(owner.id), "child_run_id": str(owner.id)},
        )

    mock_response = httpx.Response(200, request=httpx.Request("POST", "https://example.com/x"))
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        summary = await OutboxDispatcherScheduler().run_once()
    assert summary["skipped"] >= 1


def test_build_webhook_envelope_is_compact(db_session) -> None:
    from app.db.models.event_outbox import EventOutboxTable

    event = EventOutboxTable(
        owner_id=__import__("uuid").uuid4(),
        project_id=__import__("uuid").uuid4(),
        event_type=EventType.GRAPH_HANDOFF_PARENT_SYNCED,
        aggregate_type="agent_run",
        aggregate_id=__import__("uuid").uuid4(),
        payload={"parent_run_id": "p", "child_run_id": "c"},
    )
    envelope = build_webhook_envelope(event)
    assert envelope["type"] == EventType.GRAPH_HANDOFF_PARENT_SYNCED.value
    assert "data" in envelope
    assert "password" not in str(envelope).lower()
