"""LLM adapter factory."""

from __future__ import annotations

from app.core.exceptions import ExecutorError
from app.llm.base import BaseLLMAdapter
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.mock_adapter import MockLLMAdapter
from app.schemas.contracts import LLMProvider


def get_llm_adapter(provider: LLMProvider) -> BaseLLMAdapter:
    if provider == LLMProvider.MOCK:
        return MockLLMAdapter()
    if provider == LLMProvider.OPENAI:
        return LiteLLMAdapter()
    raise ExecutorError(f"Unsupported LLM provider: {provider.value}")
