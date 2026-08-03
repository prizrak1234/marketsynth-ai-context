"""LiteLLM adapter — normalized errors, controlled retries, observability."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.llm.contracts import LLMGenerateInput, LLMGenerateOutput
from app.llm.errors import LLMAuthenticationError, LLMUnknownProviderError, normalize_provider_error
from app.llm.message_serialization import llm_message_to_provider_dict
from app.llm.observability import (
    estimate_llm_cost,
    log_llm_event,
    measure_llm_call,
    metrics_from_output,
)
from app.llm.provider_config import get_provider_runtime_config
from app.llm.retry import retry_policy_from_runtime, with_llm_retries
from app.schemas.contracts import LLMProvider


class LiteLLMAdapter:
    async def generate(self, data: LLMGenerateInput) -> LLMGenerateOutput:
        if data.provider != LLMProvider.OPENAI:
            raise LLMUnknownProviderError(
                f"LiteLLMAdapter supports openai provider, got {data.provider.value}",
                provider=data.provider,
                model=data.model,
                original_error_type="UnsupportedProvider",
            )

        runtime = get_provider_runtime_config(data.provider)
        if not runtime.api_key:
            raise LLMAuthenticationError(
                "Missing API key for provider: openai",
                provider=data.provider,
                model=data.model,
                original_error_type="MissingAPIKey",
            )

        try:
            import litellm
        except ImportError as exc:
            raise LLMUnknownProviderError(
                "litellm is not installed",
                provider=data.provider,
                model=data.model,
                original_error_type="ImportError",
            ) from exc

        timeout_seconds = (
            data.timeout_seconds if data.timeout_seconds is not None else runtime.timeout_seconds
        )
        max_retries = data.max_retries if data.max_retries is not None else runtime.max_retries
        runtime_with_overrides = runtime.model_copy(
            update={"timeout_seconds": timeout_seconds, "max_retries": max_retries},
        )
        policy = retry_policy_from_runtime(runtime_with_overrides)

        async def _completion_call() -> Any:
            kwargs: dict[str, Any] = {
                "model": data.model,
                "messages": [llm_message_to_provider_dict(message) for message in data.messages],
                "api_key": runtime.api_key,
                "timeout": timeout_seconds,
                "num_retries": 0,
            }
            if data.temperature is not None:
                kwargs["temperature"] = data.temperature
            if data.max_tokens is not None:
                kwargs["max_tokens"] = data.max_tokens

            settings = get_settings()
            if settings.tools_provider_enabled and data.tools:
                from app.tools.openai_schema import tool_definitions_to_openai_tools

                openai_tools = tool_definitions_to_openai_tools(data.tools)
                if openai_tools:
                    kwargs["tools"] = openai_tools
                    kwargs["tool_choice"] = data.tool_choice or "auto"
                    log_llm_event(
                        "llm.call.tools_attached",
                        {
                            "provider": data.provider.value,
                            "model": data.model,
                            "tool_count": len(openai_tools),
                            "tool_names": [
                                tool["function"]["name"] for tool in openai_tools
                            ],
                        },
                    )

            try:
                return await litellm.acompletion(**kwargs)
            except Exception as exc:
                raise normalize_provider_error(
                    exc,
                    provider=data.provider,
                    model=data.model,
                ) from exc

        async with measure_llm_call(provider=data.provider, model=data.model) as retry_state:
            retry_result = await with_llm_retries(
                _completion_call,
                policy,
                provider=data.provider,
                model=data.model,
                retry_state=retry_state,
            )
            response = retry_result.value

        latency_ms = int((time.perf_counter() - retry_state["started_at"]) * 1000)
        choice = response.choices[0]
        content = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None)
        usage_raw = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage_raw, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage_raw, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage_raw, "total_tokens", 0) or 0)
        usage = {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
        resolved_model = getattr(response, "model", data.model)
        estimated_cost = estimate_llm_cost(
            provider=data.provider,
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        tool_calls = None
        raw_tool_calls = getattr(choice.message, "tool_calls", None)
        if raw_tool_calls:
            from app.tools.parser import parse_tool_calls

            tool_calls = parse_tool_calls(_normalize_provider_tool_calls(raw_tool_calls))

        output = LLMGenerateOutput(
            content=content,
            raw_response={},
            usage=usage,
            model=resolved_model,
            provider=LLMProvider.OPENAI,
            latency_ms=latency_ms,
            retry_count=retry_result.retry_count,
            estimated_cost_usd=estimated_cost,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )
        log_llm_event("llm.call.succeeded", metrics_from_output(output).to_log_payload())
        return output


def _normalize_provider_tool_calls(raw_tool_calls: Any) -> list[Any]:
    normalized: list[Any] = []
    for item in raw_tool_calls:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        function = getattr(item, "function", None)
        normalized.append(
            {
                "id": getattr(item, "id", None),
                "type": getattr(item, "type", "function"),
                "function": {
                    "name": getattr(function, "name", None) if function is not None else None,
                    "arguments": (
                        getattr(function, "arguments", None) if function is not None else None
                    ),
                },
            },
        )
    return normalized
