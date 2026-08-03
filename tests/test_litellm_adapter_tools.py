"""LiteLLM adapter tool-definition forwarding tests — no network."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings, get_settings
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.provider_config import get_provider_runtime_config
from app.schemas.contracts import LLMProvider
from app.tools.contracts import ToolDefinition
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


def _sample_tool(*, enabled: bool = True, name: str = "search_brief") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Search marketing brief snippets",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        enabled=enabled,
    )


@pytest.fixture
def runtime(settings: object) -> SimpleNamespace:
    return get_provider_runtime_config(LLMProvider.OPENAI, settings)


@pytest.fixture
def fake_litellm_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        model="gpt-4o-mini",
    )


@pytest.mark.asyncio
async def test_passes_tools_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
    runtime: SimpleNamespace,
    fake_litellm_response: SimpleNamespace,
) -> None:
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()

    completion = AsyncMock(return_value=fake_litellm_response)
    fake_litellm = SimpleNamespace(acompletion=completion)
    adapter = LiteLLMAdapter()

    with (
        patch("app.llm.litellm_adapter.get_provider_runtime_config", return_value=runtime),
        patch.dict(sys.modules, {"litellm": fake_litellm}),
    ):
        output = await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
                tools=[_sample_tool()],
            ),
        )

    assert output.content == "ok"
    call_kwargs = completion.await_args.kwargs
    assert call_kwargs["tool_choice"] == "auto"
    assert call_kwargs["tools"][0]["function"]["name"] == "search_brief"
    assert "parameters" in call_kwargs["tools"][0]["function"]
    assert "tools" not in output.raw_response


@pytest.mark.asyncio
async def test_tool_choice_defaults_to_auto(
    monkeypatch: pytest.MonkeyPatch,
    runtime: SimpleNamespace,
    fake_litellm_response: SimpleNamespace,
) -> None:
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()

    completion = AsyncMock(return_value=fake_litellm_response)
    fake_litellm = SimpleNamespace(acompletion=completion)
    adapter = LiteLLMAdapter()

    with (
        patch("app.llm.litellm_adapter.get_provider_runtime_config", return_value=runtime),
        patch.dict(sys.modules, {"litellm": fake_litellm}),
    ):
        await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
                tools=[_sample_tool()],
                tool_choice=None,
            ),
        )

    assert completion.await_args.kwargs["tool_choice"] == "auto"


@pytest.mark.asyncio
async def test_disabled_tools_are_filtered_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    runtime: SimpleNamespace,
    fake_litellm_response: SimpleNamespace,
) -> None:
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()

    completion = AsyncMock(return_value=fake_litellm_response)
    fake_litellm = SimpleNamespace(acompletion=completion)
    adapter = LiteLLMAdapter()

    with (
        patch("app.llm.litellm_adapter.get_provider_runtime_config", return_value=runtime),
        patch.dict(sys.modules, {"litellm": fake_litellm}),
    ):
        await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
                tools=[
                    _sample_tool(name="search_brief", enabled=True),
                    _sample_tool(name="legacy_tool", enabled=False),
                ],
            ),
        )

    tool_names = [tool["function"]["name"] for tool in completion.await_args.kwargs["tools"]]
    assert tool_names == ["search_brief"]


@pytest.mark.asyncio
async def test_flag_false_does_not_pass_tools_to_provider(
    monkeypatch: pytest.MonkeyPatch,
    runtime: SimpleNamespace,
    fake_litellm_response: SimpleNamespace,
) -> None:
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "false")
    get_settings.cache_clear()

    completion = AsyncMock(return_value=fake_litellm_response)
    fake_litellm = SimpleNamespace(acompletion=completion)
    adapter = LiteLLMAdapter()

    with (
        patch("app.llm.litellm_adapter.get_provider_runtime_config", return_value=runtime),
        patch.dict(sys.modules, {"litellm": fake_litellm}),
    ):
        output = await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
                tools=[_sample_tool()],
            ),
        )

    call_kwargs = completion.await_args.kwargs
    assert "tools" not in call_kwargs
    assert "tool_choice" not in call_kwargs
    assert output.raw_response == {}
