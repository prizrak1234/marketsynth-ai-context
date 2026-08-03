"""Marketer multi-subagent execution chains (Phase AI.14) — linear only."""

from __future__ import annotations

from typing import TypeAlias

from app.agents.marketer.contracts import MarketerSubAgentType

MarketingExecutionChain: TypeAlias = tuple[MarketerSubAgentType, ...]

MAX_SUBAGENT_CHAIN_LENGTH = 3
COMPACT_SUBAGENT_OUTPUT_MAX_BYTES = 4096

CONTENT_LAUNCH: MarketingExecutionChain = (
    MarketerSubAgentType.RESEARCHER,
    MarketerSubAgentType.STRATEGIST,
    MarketerSubAgentType.COPYWRITER,
)

CONTENT_PLAN: MarketingExecutionChain = (
    MarketerSubAgentType.STRATEGIST,
    MarketerSubAgentType.COPYWRITER,
)

RESEARCH: MarketingExecutionChain = (MarketerSubAgentType.RESEARCHER,)

REWRITE: MarketingExecutionChain = (MarketerSubAgentType.COPYWRITER,)

_SUPPORTED_CHAINS: tuple[MarketingExecutionChain, ...] = (
    CONTENT_LAUNCH,
    CONTENT_PLAN,
    RESEARCH,
    REWRITE,
)


def validate_chain(chain: MarketingExecutionChain) -> MarketingExecutionChain:
    if not chain:
        raise ValueError("Execution chain cannot be empty")
    if len(chain) > MAX_SUBAGENT_CHAIN_LENGTH:
        raise ValueError(f"Execution chain exceeds max length {MAX_SUBAGENT_CHAIN_LENGTH}")
    return chain
