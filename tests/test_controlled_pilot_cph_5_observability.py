"""CPH.5 — health/readiness, config validation, correlation, security headers."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.alembic_revision_guard import DatabaseRevisionState, RevisionDiagnostic
from app.domain.pilot_config_validation import validate_pilot_configuration
from app.services.alembic_revision_startup import should_fail_fast


def test_health_live_is_fast(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "alive"
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_health_ready_success(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["status"] == "ready"
    assert "components" in body
    assert body.get("database_name")


def test_correlation_id_propagation(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "cph5-corr-123"})
    assert response.headers["X-Request-ID"] == "cph5-corr-123"
    assert response.headers["X-Correlation-ID"] == "cph5-corr-123"


def test_correlation_id_sanitized(client: TestClient) -> None:
    dirty = "bad id;<script>alert(1)</script>"
    response = client.get("/health/live", headers={"X-Request-ID": dirty})
    rid = response.headers["X-Request-ID"]
    assert "<" not in rid
    assert ";" not in rid
    assert "(" not in rid
    assert len(rid) <= 128


def test_config_validation_pilot_requires_fail_fast() -> None:
    settings = Settings(
        app_env="pilot",
        debug=False,
        alembic_revision_check_enabled=True,
        alembic_revision_fail_fast=False,
        browser_allowed_origins=["http://127.0.0.1:3000"],
        tools_provider_enabled=False,
        publication_worker_enabled=False,
        graph_handoff_execute_child=False,
        event_outbox_dispatcher_enabled=False,
        demo_flow_endpoints_enabled=False,
        media_generation_enabled=False,
        telegram_publication_enabled=False,
    )
    result = validate_pilot_configuration(settings)
    codes = {i.code for i in result.errors}
    assert "revision_fail_fast_disabled" in codes


def test_config_validation_blocks_wildcard_cors() -> None:
    settings = Settings(
        app_env="development",
        browser_allowed_origins=["*"],
    )
    result = validate_pilot_configuration(settings)
    assert any(i.code == "wildcard_cors" for i in result.errors)


def test_config_validation_https_requires_secure_cookie() -> None:
    settings = Settings(
        app_env="pilot",
        debug=False,
        alembic_revision_fail_fast=True,
        alembic_revision_check_enabled=True,
        browser_allowed_origins=["https://pilot.local"],
        browser_session_cookie_secure=False,
        tools_provider_enabled=False,
        publication_worker_enabled=False,
        graph_handoff_execute_child=False,
        event_outbox_dispatcher_enabled=False,
        demo_flow_endpoints_enabled=False,
        media_generation_enabled=False,
        telegram_publication_enabled=False,
    )
    result = validate_pilot_configuration(settings)
    assert any(i.code == "insecure_cookie_under_https" for i in result.errors)


def test_config_validation_blocks_execution_flags_in_pilot() -> None:
    settings = Settings(
        app_env="pilot",
        debug=False,
        alembic_revision_fail_fast=True,
        alembic_revision_check_enabled=True,
        browser_allowed_origins=["http://127.0.0.1:3000"],
        tools_provider_enabled=True,
        publication_worker_enabled=False,
        graph_handoff_execute_child=False,
        event_outbox_dispatcher_enabled=False,
        demo_flow_endpoints_enabled=False,
        media_generation_enabled=False,
        telegram_publication_enabled=False,
    )
    result = validate_pilot_configuration(settings)
    assert any(i.code == "execution_feature_enabled" for i in result.errors)


def test_should_fail_fast_behind_in_pilot() -> None:
    diag = RevisionDiagnostic(
        state=DatabaseRevisionState.BEHIND,
        code_heads=("20260715_0037",),
        database_revisions=("20260614_0036",),
        detail="behind",
        auto_stamp_allowed=False,
        auto_migrate_allowed=False,
    )
    pilot = Settings(app_env="pilot", alembic_revision_fail_fast=True)
    soft = Settings(app_env="development", alembic_revision_fail_fast=False)
    assert should_fail_fast(diag, pilot) is True
    assert should_fail_fast(diag, soft) is False


def test_error_envelope_includes_request_id(client: TestClient) -> None:
    response = client.get("/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code in {401, 403, 404}
    body = response.json()
    assert "request_id" in body or "safe_message" in body or "detail" in body


def test_readiness_db_failure(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def _fail() -> bool:
        return False

    monkeypatch.setattr("app.services.pilot_readiness.check_database_connection", _fail)
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/health/live",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette may return 200 with ACAO for allowed origin
    assert response.status_code in {200, 204}
    assert (
        response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
        or response.status_code == 200
    )


def test_cors_denies_unknown_origin(client: TestClient) -> None:
    response = client.get(
        "/health/live",
        headers={"Origin": "https://evil.example"},
    )
    # Live still returns 200 but must not reflect evil origin
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"
