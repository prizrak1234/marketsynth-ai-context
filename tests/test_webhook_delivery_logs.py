"""Phase 3.10 — webhook delivery logs."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from app.events.delivery_url import build_target_url_preview
from app.events.webhook_delivery import truncate_response_preview
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.schemas.contracts import WebhookDeliveryLogStatus
from fastapi.testclient import TestClient

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


def _patch_runner(store):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def test_target_url_preview_strips_query_and_token() -> None:
    preview = build_target_url_preview("https://api.example.com/hooks/bot?token=secret&x=1")
    assert preview == "https://api.example.com/hooks/bot"
    assert "token" not in preview
    assert "?" not in preview


def test_response_preview_truncated() -> None:
    long_text = "x" * 600
    assert len(truncate_response_preview(long_text)) == 500


def test_successful_webhook_creates_succeeded_delivery_log(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Delivery Log Project"}, headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/hook?sig=abc"},
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
                "prompt": "log test",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    mock_response = httpx.Response(200, request=httpx.Request("POST", "https://example.com/hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    logs = client.get(
        f"/projects/{project_id}/webhook-deliveries",
        headers=auth_headers,
        params={"status": WebhookDeliveryLogStatus.SUCCEEDED.value},
    ).json()
    assert len(logs) >= 1
    assert logs[0]["status"] == "succeeded"
    assert logs[0]["http_status_code"] == 200
    assert "bwhsec" not in str(logs).lower()
    assert "sig=abc" not in logs[0]["target_url_preview"]


def test_failing_webhook_creates_failed_delivery_log(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Fail Log"}, headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/fail-hook"},
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
                "prompt": "fail log",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    fail_resp = httpx.Response(500, request=httpx.Request("POST", "https://example.com/fail-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fail_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    logs = client.get(
        f"/projects/{project_id}/webhook-deliveries",
        headers=auth_headers,
        params={"status": WebhookDeliveryLogStatus.FAILED.value},
    ).json()
    assert len(logs) >= 1
    assert logs[0]["error_code"] == "http_500"
    assert "Traceback" not in (logs[0]["error_message"] or "")


def test_no_webhook_creates_skipped_delivery_log(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Skip Log"}, headers=auth_headers,
    ).json()["id"]
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
                "prompt": "skip",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)
    logs = client.get(
        f"/projects/{project_id}/webhook-deliveries",
        headers=auth_headers,
        params={"status": WebhookDeliveryLogStatus.SKIPPED.value},
    ).json()
    assert len(logs) >= 1
    assert logs[0]["error_code"] == "no_active_webhooks"


def test_delivery_logs_api_enforces_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Own Logs"}, headers=auth_headers,
    ).json()["id"]
    assert client.get(
        f"/projects/{project_id}/webhook-deliveries",
        headers=other_auth_headers,
    ).status_code == 404
