"""Marketing skills registry (Phase AI.228)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.marketing.skills import executors
from app.schemas.contracts import MarketingSkillDefinition, MarketingSkillType, MarketingToolType

SkillExecutor = Callable[
    [AsyncSession, UUID, UUID, dict[str, Any]],
    Awaitable[tuple[dict[str, Any], dict[str, Any], list[UUID]]],
]


@dataclass(frozen=True, slots=True)
class RegisteredMarketingSkill:
    definition: MarketingSkillDefinition
    executor: SkillExecutor


def _definitions() -> dict[MarketingSkillType, RegisteredMarketingSkill]:
    entries: list[RegisteredMarketingSkill] = [
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.SEGMENT_RESEARCH,
                name="Segment research",
                purpose="Collect structured segment profile before messaging",
                required_inputs=["target_audience"],
                optional_tools=[],
                output_type="segment_research",
                out_of_scope=["Auto-run Wordstat", "LLM web research"],
            ),
            executor=executors.execute_segment_research,
        ),
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.MEANING_UNPACKING,
                name="Meaning unpacking",
                purpose="Translate pains/desires into messaging building blocks",
                required_inputs=["offer"],
                optional_tools=[],
                output_type="meaning_unpacking",
                out_of_scope=["Final ad copy generation"],
            ),
            executor=executors.execute_meaning_unpacking,
        ),
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.OFFER_PACKAGING,
                name="Offer packaging",
                purpose="Structure a strong commercial offer",
                required_inputs=["offer", "target_audience"],
                optional_tools=[],
                output_type="offer_packaging",
                out_of_scope=["Pricing optimization ML"],
            ),
            executor=executors.execute_offer_packaging,
        ),
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.OFFER_JUSTIFICATION,
                name="Offer justification",
                purpose="Build business case and CTA for the offer",
                required_inputs=["offer"],
                optional_tools=[],
                output_type="offer_justification",
                out_of_scope=["Legal/compliance review"],
            ),
            executor=executors.execute_offer_justification,
        ),
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.WORDSTAT_RESEARCH,
                name="Wordstat research",
                purpose="Validate search demand and give business conclusion",
                required_inputs=["query"],
                optional_tools=[MarketingToolType.WORDSTAT],
                output_type="wordstat_research",
                out_of_scope=["Auto-call without create_tool_call=true"],
            ),
            executor=executors.execute_wordstat_research,
        ),
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.METRICA_ANALYSIS,
                name="Metrica analysis",
                purpose="Summarize site behavior and effectiveness",
                required_inputs=[],
                optional_tools=[MarketingToolType.METRICA],
                output_type="metrica_analysis",
                out_of_scope=["Auto-call without create_tool_call=true"],
            ),
            executor=executors.execute_metrica_analysis,
        ),
        RegisteredMarketingSkill(
            definition=MarketingSkillDefinition(
                skill_type=MarketingSkillType.VISUAL_REPORT,
                name="Visual report",
                purpose="Creative direction report with optional mock visual",
                required_inputs=["offer"],
                optional_tools=[MarketingToolType.IMAGE_GENERATION],
                output_type="visual_report",
                out_of_scope=["Brand book generation"],
            ),
            executor=executors.execute_visual_report,
        ),
    ]
    return {entry.definition.skill_type: entry for entry in entries}


class MarketingSkillRegistry:
    def __init__(self) -> None:
        self._skills = _definitions()

    def get(self, skill_type: MarketingSkillType) -> RegisteredMarketingSkill:
        skill = self._skills.get(skill_type)
        if skill is None:
            raise KeyError(f"Unsupported marketing skill: {skill_type.value}")
        return skill

    def list_definitions(self) -> list[MarketingSkillDefinition]:
        return [skill.definition for skill in self._skills.values()]


_registry: MarketingSkillRegistry | None = None


def get_marketing_skill_registry() -> MarketingSkillRegistry:
    global _registry
    if _registry is None:
        _registry = MarketingSkillRegistry()
    return _registry
