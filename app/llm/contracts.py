"""LLM adapter input/output contracts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.contracts import LLMProvider
from app.tools.contracts import ToolCall, ToolDefinition


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class LLMGenerateInput(BaseModel):
    provider: LLMProvider
    model: str
    messages: list[LLMMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str | dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMGenerateOutput(BaseModel):
    content: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    model: str | None = None
    provider: LLMProvider
    latency_ms: int | None = None
    retry_count: int = 0
    estimated_cost_usd: Decimal | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: str | None = None
