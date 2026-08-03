"""API models for agent tool matrix (Phase 5.8)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentToolMatrixRow(BaseModel):
    agent_type: str
    read_tools: list[str] = Field(default_factory=list)
    write_tools: list[str] = Field(default_factory=list)
    write_enabled: bool = False
    notes: str = ""


class AgentToolMatrixResponse(BaseModel):
    write_globally_enabled: bool
    create_draft_globally_enabled: bool
    agents: list[AgentToolMatrixRow] = Field(default_factory=list)
