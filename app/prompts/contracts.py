"""Prompt builder contracts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.llm.contracts import LLMMessage
from app.schemas.contracts import AgentType


class PromptBuildInput(BaseModel):
    agent_id: UUID
    agent_type: AgentType
    agent_config: dict[str, Any] = Field(default_factory=dict)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    memory_context: list[Any] | dict[str, Any] | None = None
    system_overrides: str | None = None
    user_context: dict[str, Any] | None = None


class PromptBuildOutput(BaseModel):
    messages: list[LLMMessage]
    metadata: dict[str, Any] = Field(default_factory=dict)
