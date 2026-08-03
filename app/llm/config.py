"""Agent LLM config resolution for executor."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import ExecutorError, InvalidStateError
from app.llm.secrets_boundary import assert_no_sensitive_keys
from app.schemas.contracts import LLMProvider


def resolve_llm_config(
    agent_config: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[LLMProvider, str, float | None, int | None]:
    resolved_settings = settings or get_settings()
    llm_config = agent_config.get("llm") or {}
    assert_no_sensitive_keys(llm_config)

    provider_raw = llm_config.get("provider", resolved_settings.default_llm_provider)
    try:
        provider = LLMProvider(provider_raw)
    except ValueError as exc:
        raise ExecutorError(f"Unsupported LLM provider: {provider_raw}") from exc

    model = llm_config.get("model", resolved_settings.default_llm_model)
    temperature = llm_config.get("temperature")
    max_tokens = llm_config.get("max_tokens")
    return provider, model, temperature, max_tokens


def validate_llm_request_payload(
    *,
    input_payload: dict[str, Any],
    prompt_metadata: dict[str, Any],
    request_metadata: dict[str, Any],
) -> None:
    """Ensure LLM request logging payloads never carry secrets."""
    for payload in (input_payload, prompt_metadata, request_metadata):
        try:
            assert_no_sensitive_keys(payload)
        except InvalidStateError as exc:
            raise InvalidStateError(str(exc).replace("agent config", "LLM request")) from exc
