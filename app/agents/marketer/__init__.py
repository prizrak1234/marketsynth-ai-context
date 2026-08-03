"""Marketer sub-agent registry and persona routing (Phase AI.10)."""

from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.registry import (
    MarketerSubAgentProfile,
    get_subagent,
    get_subagent_prompt,
    list_subagents,
)

__all__ = [
    "MarketerSubAgentProfile",
    "MarketerSubAgentType",
    "get_subagent",
    "get_subagent_prompt",
    "list_subagents",
]
