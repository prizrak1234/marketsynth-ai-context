"""LLM provider config and secrets boundary tests — no network calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.llm.config import resolve_llm_config
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.errors import LLMAuthenticationError
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.provider_config import get_provider_runtime_config
from app.llm.secrets_boundary import assert_no_sensitive_keys, find_sensitive_key
from app.schemas.contracts import LLMProvider
from fastapi.testclient import TestClient
from pydantic import SecretStr


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return Settings(
        openai_api_key=SecretStr("test-openai-key"),
        default_llm_provider="mock",
        default_llm_model="mock-model",
        llm_timeout_seconds=45,
        llm_max_retries=3,
    )


def test_mock_runtime_config_does_not_require_api_key(settings: Settings) -> None:
    runtime = get_provider_runtime_config(LLMProvider.MOCK, settings)
    assert runtime.api_key is None
    assert runtime.timeout_seconds == 45
    assert runtime.max_retries == 3


def test_openai_runtime_config_reads_openai_api_key(settings: Settings) -> None:
    runtime = get_provider_runtime_config(LLMProvider.OPENAI, settings)
    assert runtime.api_key == "test-openai-key"


def test_openai_without_key_allowed_at_config_resolution_level() -> None:
    bare_settings = Settings(openai_api_key=None)
    runtime = get_provider_runtime_config(LLMProvider.OPENAI, bare_settings)
    assert runtime.api_key is None


@pytest.mark.asyncio
async def test_litellm_adapter_raises_if_openai_key_missing() -> None:
    adapter = LiteLLMAdapter()
    with (
        patch(
            "app.llm.litellm_adapter.get_provider_runtime_config",
            return_value=SimpleNamespace(
                api_key=None,
                timeout_seconds=60,
                max_retries=2,
            ),
        ),
        pytest.raises(LLMAuthenticationError, match="Missing API key for provider: openai"),
    ):
        await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
            ),
        )


@pytest.mark.asyncio
async def test_litellm_adapter_uses_runtime_api_key_without_network(settings: Settings) -> None:
    adapter = LiteLLMAdapter()
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        model="gpt-4o-mini",
    )
    completion = AsyncMock(return_value=fake_response)
    runtime = get_provider_runtime_config(LLMProvider.OPENAI, settings)

    import sys

    fake_litellm = SimpleNamespace(acompletion=completion)
    with (
        patch(
            "app.llm.litellm_adapter.get_provider_runtime_config",
            return_value=runtime,
        ),
        patch.dict(sys.modules, {"litellm": fake_litellm}),
    ):
        output = await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
            ),
        )

    assert output.content == "ok"
    completion.assert_awaited_once()
    call_kwargs = completion.await_args.kwargs
    assert call_kwargs["api_key"] == "test-openai-key"
    assert call_kwargs["timeout"] == settings.llm_timeout_seconds
    assert call_kwargs["num_retries"] == 0


def test_resolve_llm_config_uses_settings_defaults(settings: Settings) -> None:
    provider, model, temperature, max_tokens = resolve_llm_config({}, settings)
    assert provider == LLMProvider.MOCK
    assert model == "mock-model"
    assert temperature is None
    assert max_tokens is None


def test_resolve_llm_config_agent_llm_overrides_provider_model(settings: Settings) -> None:
    provider, model, temperature, max_tokens = resolve_llm_config(
        {
            "llm": {
                "provider": "mock",
                "model": "custom-model",
                "temperature": 0.3,
                "max_tokens": 512,
            },
        },
        settings,
    )
    assert provider == LLMProvider.MOCK
    assert model == "custom-model"
    assert temperature == 0.3
    assert max_tokens == 512


def test_resolve_llm_config_with_api_key_raises_invalid_state_error(settings: Settings) -> None:
    with pytest.raises(InvalidStateError, match="api_key"):
        resolve_llm_config({"llm": {"provider": "mock", "api_key": "sk-bad"}}, settings)


def test_nested_secret_key_raises_invalid_state_error(settings: Settings) -> None:
    with pytest.raises(InvalidStateError, match="credentials"):
        resolve_llm_config(
            {"llm": {"provider": "mock", "auth": {"credentials": "secret-value"}}},
            settings,
        )


def test_find_sensitive_key_detects_nested_token() -> None:
    path = find_sensitive_key({"llm": {"nested": {"access_token": "x"}}})
    assert path == "llm.nested.access_token"


def test_sensitive_keys_not_written_into_llm_request_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Secrets Project"}, headers=auth_headers)
    project_id = project.json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "safe"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]

    response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    metadata_blob = str(llm_request["request_metadata"]).lower()
    assert "api_key" not in metadata_blob
    assert "secret" not in metadata_blob
    assert "sk-" not in metadata_blob


def test_agent_config_with_api_key_returns_409_on_execute(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Bad Config Project"}, headers=auth_headers)
    project_id = project.json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]
    client.patch(
        f"/agents/{agent_id}",
        json={"config": {"llm": {"provider": "mock", "api_key": "sk-forbidden"}}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "nope"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]

    response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409
    assert "api_key" in response.json()["detail"].lower()

    run_state = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()
    assert run_state["status"] == "queued"


def test_env_defaults_do_not_break_tests(client: TestClient, auth_headers: dict[str, str]) -> None:
    project = client.post("/projects", json={"name": "Defaults Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "defaults"}},
        headers=auth_headers,
    )
    response = client.post(
        f"/agent-runs/{run.json()['id']}/execute-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_assert_no_sensitive_keys_accepts_safe_payload() -> None:
    assert_no_sensitive_keys({"provider": "mock", "model": "mock-model", "temperature": 0.2})


def test_settings_safe_dict_redacts_api_keys(settings: Settings) -> None:
    safe = settings.safe_dict()
    assert safe["openai_api_key"] == "***"
