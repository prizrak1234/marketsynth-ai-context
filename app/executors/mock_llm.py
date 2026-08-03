"""Backward-compatible mock LLM wrapper — delegates to MockLLMAdapter."""

from __future__ import annotations

from typing import Any

from app.llm.contracts import LLMGenerateInput
from app.llm.mock_adapter import MOCK_MODEL, MockLLMAdapter, build_messages
from app.schemas.contracts import LLMProvider

__all__ = ["MOCK_MODEL", "generate"]


async def generate(input_payload: dict[str, Any] | None) -> dict[str, Any]:
    adapter = MockLLMAdapter()
    messages = build_messages(input_payload or {})
    output = await adapter.generate(
        LLMGenerateInput(
            provider=LLMProvider.MOCK,
            model=MOCK_MODEL,
            messages=messages,
            metadata={"legacy_wrapper": True},
        ),
    )
    return {
        "provider": output.provider.value,
        "model": output.model or MOCK_MODEL,
        "content": output.content,
        "input_echo": input_payload or {},
    }
