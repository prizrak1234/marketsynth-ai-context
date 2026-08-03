"""LLM adapter protocol."""

from __future__ import annotations

from typing import Protocol

from app.llm.contracts import LLMGenerateInput, LLMGenerateOutput


class BaseLLMAdapter(Protocol):
    async def generate(self, data: LLMGenerateInput) -> LLMGenerateOutput:
        ...
