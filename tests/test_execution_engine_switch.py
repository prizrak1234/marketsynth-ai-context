"""Phase 3.13 — controlled LangGraph production switch."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.core.config import Settings, get_settings
from app.executors.engine_resolver import resolve_execution_engine
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from fastapi.testclient import TestClient


def _settings(**overrides: object) -> Settings:
    base = get_settings().model_dump()
    base.update(overrides)
    return Settings(**base)


def _project_stub(execution_engine: str | None = None) -> object:
    project_config: dict = {}
    if execution_engine is not None:
        project_config["execution_engine"] = execution_engine

    class _Project:
        config = project_config

    return _Project()


def test_default_resolver_returns_classic() -> None:
    assert resolve_execution_engine(_settings(agent_execution_engine="classic")) == "classic"


def test_settings_langgraph_returns_langgraph() -> None:
    settings = _settings(
        agent_execution_engine="langgraph",
        agent_execution_langgraph_enabled=True,
    )
    assert resolve_execution_engine(settings) == "langgraph"


def test_request_override_works_when_enabled() -> None:
    settings = _settings(
        agent_execution_engine="classic",
        agent_execution_engine_request_override_enabled=True,
        agent_execution_langgraph_enabled=True,
    )
    assert resolve_execution_engine(settings, request_override="langgraph") == "langgraph"


def test_request_override_ignored_when_disabled() -> None:
    settings = _settings(
        agent_execution_engine="langgraph",
        agent_execution_engine_request_override_enabled=False,
        agent_execution_langgraph_enabled=True,
    )
    assert resolve_execution_engine(settings, request_override="classic") == "langgraph"


def test_project_config_overrides_settings() -> None:
    settings = _settings(
        agent_execution_engine="classic",
        agent_execution_langgraph_enabled=True,
    )
    assert resolve_execution_engine(settings, project=_project_stub("langgraph")) == "langgraph"


def test_force_classic_overrides_all() -> None:
    settings = _settings(
        agent_execution_engine="langgraph",
        agent_execution_force_classic=True,
        agent_execution_engine_request_override_enabled=True,
        agent_execution_langgraph_enabled=True,
    )
    assert (
        resolve_execution_engine(
            settings,
            project=_project_stub("langgraph"),
            request_override="langgraph",
        )
        == "classic"
    )


def test_unknown_engine_falls_back_to_classic() -> None:
    settings = _settings(agent_execution_engine="classic")
    assert resolve_execution_engine(settings, request_override="not-a-real-engine") == "classic"


def test_langgraph_disabled_falls_back_to_classic() -> None:
    settings = _settings(
        agent_execution_engine="langgraph",
        agent_execution_langgraph_enabled=False,
    )
    assert resolve_execution_engine(settings) == "classic"


def _patch_graph_runner(store):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.executors.agent_run_coordinator.AgentGraphRunner", _RunnerWithStore)


def _create_run(client: TestClient, auth_headers: dict[str, str]) -> tuple[str, str]:
    project_id = client.post(
        "/projects", json={"name": "Engine switch"}, headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "execute"}},
        headers=auth_headers,
    ).json()["id"]
    return project_id, run_id


def test_unified_endpoint_executes_classic(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "classic")
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "false")
    get_settings.cache_clear()
    _project_id, run_id = _create_run(client, auth_headers)

    response = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["execution_engine"] == "classic"
    assert body["status"] == "succeeded"
    assert body["output_payload"]["execution"]["engine"] == "classic"


def test_unified_endpoint_executes_langgraph(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "langgraph")
    monkeypatch.setenv("AGENT_EXECUTION_LANGGRAPH_ENABLED", "true")
    get_settings.cache_clear()
    _project_id, run_id = _create_run(client, auth_headers)
    store = InMemoryGraphCheckpointStore()

    with _patch_graph_runner(store):
        response = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["execution_engine"] == "langgraph"
    assert body["status"] == "succeeded"
    assert body["output_payload"]["execution"]["engine"] == "langgraph"


def test_response_includes_execution_engine(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE_REQUEST_OVERRIDE_ENABLED", "true")
    get_settings.cache_clear()
    _project_id, run_id = _create_run(client, auth_headers)

    body = client.post(
        f"/agent-runs/{run_id}/execute",
        headers=auth_headers,
        params={"engine": "langgraph"},
    ).json()

    assert body["execution_engine"] == "classic"
    assert body["output_payload"]["execution"]["engine"] == "classic"


def test_operational_metrics_include_engine_counts(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    project_id, run_id = _create_run(client, auth_headers)
    client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers)

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert metrics["execution"]["agent_runs_by_execution_engine"]["classic"]["total"] >= 1


def test_old_dry_run_endpoints_still_work(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, run_id = _create_run(client, auth_headers)

    classic = client.post(
        f"/agent-runs/{run_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert classic.status_code == 200
    assert "execution" not in (classic.json().get("output_payload") or {})

    agent_id = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["agent_id"]
    run2_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "graph endpoint"}},
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


def test_classic_executor_unaffected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, run_id = _create_run(client, auth_headers)
    response = client.post(
        f"/agent-runs/{run_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_project_patch_stores_execution_engine_config(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Config project"}, headers=auth_headers,
    ).json()["id"]
    updated = client.patch(
        f"/projects/{project_id}",
        json={"config": {"execution_engine": "langgraph"}},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["config"]["execution_engine"] == "langgraph"


def test_project_config_routes_execute_to_langgraph(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "classic")
    monkeypatch.setenv("AGENT_EXECUTION_LANGGRAPH_ENABLED", "true")
    get_settings.cache_clear()

    project_id = client.post(
        "/projects", json={"name": "Route graph"}, headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/projects/{project_id}",
        json={"config": {"execution_engine": "langgraph"}},
        headers=auth_headers,
    )
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "route"}},
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()

    with _patch_graph_runner(store):
        body = client.post(f"/agent-runs/{run_id}/execute", headers=auth_headers).json()

    assert body["execution_engine"] == "langgraph"
    assert body["output_payload"]["execution"]["engine"] == "langgraph"
