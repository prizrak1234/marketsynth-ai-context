"""Direct specialist chat contracts (Phase AI.18)."""

from __future__ import annotations

from app.schemas.contracts import AgentType

ENTRYPOINT_DIRECT_SPECIALIST = "direct_specialist"
ENTRYPOINT_GENERAL_DELEGATION = "general_delegation"

DIRECT_SPECIALIST_DOMAIN_BY_AGENT: dict[AgentType, str] = {
    AgentType.ORCHESTRATOR: "marketing",
    AgentType.PROGRAMMER: "programmer",
    AgentType.MEDIA: "media",
}

DIRECT_SPECIALIST_AGENT_TYPES: frozenset[AgentType] = frozenset(
    DIRECT_SPECIALIST_DOMAIN_BY_AGENT.keys(),
)


def specialist_domain_for_agent(agent_type: AgentType) -> str | None:
    return DIRECT_SPECIALIST_DOMAIN_BY_AGENT.get(agent_type)
