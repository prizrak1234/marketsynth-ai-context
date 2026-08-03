"""Phase 3.16 — runtime configuration sanity warnings."""

from __future__ import annotations

from app.core.config import Settings
from app.core.config_sanity import validate_runtime_config
from fastapi.testclient import TestClient


def _settings(**overrides: object) -> Settings:
    base = Settings().model_dump()
    base.update(overrides)
    return Settings(**base)


def test_force_classic_with_langgraph_engine_warns() -> None:
    warnings = validate_runtime_config(
        _settings(
            agent_execution_force_classic=True,
            agent_execution_engine="langgraph",
        ),
    )
    codes = {warning.code for warning in warnings}
    assert "force_classic_overrides_langgraph_engine" in codes


def test_scheduler_without_redis_warns() -> None:
    warnings = validate_runtime_config(
        _settings(graph_handoff_scheduler_enabled=True),
        redis_available=False,
    )
    assert any(w.code == "handoff_scheduler_without_redis" for w in warnings)


def test_langgraph_disabled_warns() -> None:
    warnings = validate_runtime_config(
        _settings(agent_execution_langgraph_enabled=False),
    )
    assert any(w.code == "langgraph_globally_disabled" for w in warnings)


def test_invalid_outbox_attempts_warn() -> None:
    settings = Settings.model_construct(event_outbox_dispatch_max_attempts=0)
    warnings = validate_runtime_config(settings)
    assert any(w.code == "outbox_dispatch_max_attempts_invalid" for w in warnings)


def test_invalid_handoff_attempts_warn() -> None:
    settings = Settings.model_construct(graph_handoff_max_attempts=0)
    warnings = validate_runtime_config(settings)
    assert any(w.code == "handoff_max_attempts_invalid" for w in warnings)


def test_publication_worker_without_database_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(publication_worker_enabled=True),
        database_available=False,
    )
    assert any(w.code == "publication_worker_enabled_without_database" for w in warnings)


def test_invalid_publication_job_max_attempts_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(publication_job_max_attempts=0),
    )
    assert any(w.code == "publication_job_max_attempts_lt_1" for w in warnings)


def test_invalid_publication_delivery_timeout_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(publication_delivery_timeout_seconds=0),
    )
    assert any(w.code == "publication_delivery_timeout_invalid" for w in warnings)


def test_publication_worker_interval_too_low_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(publication_worker_interval_seconds=1),
    )
    assert any(w.code == "publication_worker_interval_too_low" for w in warnings)


def test_telegram_publication_enabled_without_token_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(telegram_publication_enabled=True),
    )
    assert any(w.code == "telegram_publication_enabled_without_token" for w in warnings)


def test_telegram_publication_timeout_invalid_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(telegram_publication_timeout_seconds=0),
    )
    assert any(w.code == "telegram_publication_timeout_invalid" for w in warnings)


def test_telegram_publication_enabled_without_worker_warns() -> None:
    warnings = validate_runtime_config(
        Settings.model_construct(
            telegram_publication_enabled=True,
            publication_worker_enabled=False,
        ),
    )
    assert any(w.code == "telegram_publication_enabled_without_worker" for w in warnings)


def test_health_operations_exposes_config_warnings(client: TestClient) -> None:
    response = client.get("/health/operations")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "config_warnings_count" in body
    assert "config_warnings" in body
    assert isinstance(body["config_warnings"], list)
    assert body["config_warnings_count"] == len(body["config_warnings"])
