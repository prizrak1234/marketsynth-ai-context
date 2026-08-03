"""Phase AI.110 — Marketing department v2 roadmap (metadata only; frozen pipeline intact)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.marketer.marketing_specialist_registry import (
    FROZEN_PIPELINE_ORDER,
    MARKETING_DEPARTMENT_V2_ROLE_COUNT,
    V2_EXECUTION_ENABLED_SPECIALISTS,
    V2_METADATA_ONLY_SPECIALISTS,
    get_marketing_specialist,
    list_frozen_pipeline_specialists,
    list_marketing_specialists,
)
from app.agents.marketer.specialists import executor as executor_module
from app.schemas.contracts import MarketingSpecialistType
from app.agents.marketer.planning import build_marketing_execution_plan
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService

FROZEN_SIX = frozenset(FROZEN_PIPELINE_ORDER)

ALL_FOURTEEN = frozenset(MarketingSpecialistType)

V2_EIGHT = V2_EXECUTION_ENABLED_SPECIALISTS

# AI.27 baseline — five display fields for frozen roles must not drift.
FROZEN_PROFILE_TEXT_SNAPSHOT: dict[MarketingSpecialistType, dict[str, str]] = {
    MarketingSpecialistType.STRATEGIST: {
        "name": "Strategist",
        "description": "Positioning, offer, and campaign direction.",
        "default_objective": "Define positioning and strategic direction",
        "default_expected_output": "Positioning summary and strategic pillars",
    },
    MarketingSpecialistType.RESEARCHER: {
        "name": "Researcher",
        "description": "Audience, market, and brief research.",
        "default_objective": "Research audience and market context",
        "default_expected_output": "Audience insights and evidence-backed notes",
    },
    MarketingSpecialistType.CONTENT_PLANNER: {
        "name": "Content Planner",
        "description": "Editorial calendar and content structure.",
        "default_objective": "Build a structured content plan",
        "default_expected_output": "Channel-aware content plan outline",
    },
    MarketingSpecialistType.COPYWRITER: {
        "name": "Copywriter",
        "description": "Drafts and copy variants for channels.",
        "default_objective": "Prepare channel-ready copy drafts",
        "default_expected_output": "Copy variants aligned to strategy",
    },
    MarketingSpecialistType.ANALYST: {
        "name": "Analyst",
        "description": "Campaign performance and workflow analysis.",
        "default_objective": "Analyze campaign workflow and performance signals",
        "default_expected_output": "Fact-based recommendations for next steps",
    },
    MarketingSpecialistType.CRITIC: {
        "name": "Critic",
        "description": "Quality review before publication.",
        "default_objective": "Review deliverables for clarity and brand fit",
        "default_expected_output": "Quality checklist and revision notes",
    },
}

FROZEN_OUTPUT_TYPES: dict[MarketingSpecialistType, str] = {
    MarketingSpecialistType.STRATEGIST: "strategy",
    MarketingSpecialistType.RESEARCHER: "research",
    MarketingSpecialistType.CONTENT_PLANNER: "content_plan",
    MarketingSpecialistType.COPYWRITER: "content_copy",
    MarketingSpecialistType.CRITIC: "critique",
    MarketingSpecialistType.ANALYST: "analysis",
}

V2_OUTPUT_TYPES: dict[MarketingSpecialistType, str] = {
    MarketingSpecialistType.OFFER_STRATEGIST: "offer_strategy",
    MarketingSpecialistType.FUNNEL_ARCHITECT: "funnel_design",
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST: "lead_magnet",
    MarketingSpecialistType.SALES_COPYWRITER: "sales_copy",
    MarketingSpecialistType.EMAIL_DM_SPECIALIST: "email_sequence",
    MarketingSpecialistType.CRO_SPECIALIST: "cro_recommendations",
    MarketingSpecialistType.SMM_STRATEGIST: "smm_strategy",
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST: "ad_creative_strategy",
}


def test_roadmap_doc_exists() -> None:
    doc = Path("docs/phase_ai_110_marketing_department_v2_roadmap.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    for slug in (
        "offer_strategist",
        "funnel_architect",
        "lead_magnet_specialist",
        "sales_copywriter",
        "email_dm_specialist",
        "cro_specialist",
        "smm_strategist",
        "ad_creative_strategist",
    ):
        assert slug in text


def test_all_fourteen_roles_registered_in_enum_and_registry() -> None:
    assert len(MarketingSpecialistType) == MARKETING_DEPARTMENT_V2_ROLE_COUNT == 14
    profiles = list_marketing_specialists()
    assert len(profiles) == MARKETING_DEPARTMENT_V2_ROLE_COUNT
    assert {p.specialist_type for p in profiles} == ALL_FOURTEEN


def test_frozen_six_plus_v2_eight_partition_department() -> None:
    assert FROZEN_SIX | V2_EIGHT == ALL_FOURTEEN
    assert FROZEN_SIX.isdisjoint(V2_EIGHT)
    assert len(V2_EIGHT) == 8


def test_frozen_six_profile_display_fields_unchanged() -> None:
    for specialist, expected in FROZEN_PROFILE_TEXT_SNAPSHOT.items():
        profile = get_marketing_specialist(specialist)
        for field, value in expected.items():
            assert getattr(profile, field) == value


def test_frozen_six_output_types_and_execution_enabled() -> None:
    for specialist, output_type in FROZEN_OUTPUT_TYPES.items():
        profile = get_marketing_specialist(specialist)
        assert profile.output_type == output_type
        assert profile.execution_enabled is True


def test_v2_execution_enabled_roles_have_execution_flag() -> None:
    for specialist in V2_EXECUTION_ENABLED_SPECIALISTS:
        profile = get_marketing_specialist(specialist)
        assert profile.execution_enabled is True
        assert profile.output_type == V2_OUTPUT_TYPES[specialist]
        assert profile.dependencies
        assert profile.structured_data_keys


def test_v2_metadata_only_roles_empty_after_ai119() -> None:
    assert V2_METADATA_ONLY_SPECIALISTS == frozenset()


def test_v2_eight_have_documented_dependencies_within_department() -> None:
    for specialist in V2_EIGHT:
        profile = get_marketing_specialist(specialist)
        for dep in profile.dependencies:
            assert dep in ALL_FOURTEEN
            assert dep != specialist


def test_list_frozen_pipeline_specialists_matches_mvp_six() -> None:
    frozen = list_frozen_pipeline_specialists()
    assert len(frozen) == 6
    assert [p.specialist_type for p in frozen] == list(FROZEN_PIPELINE_ORDER)


def test_planning_mode_excludes_all_v2_execution_roles() -> None:
    plan = build_marketing_execution_plan(
        message="Сделай контент-стратегию для стоматологии",
    )
    selected = {task.specialist for task in plan.specialist_tasks}
    assert selected.isdisjoint(V2_EIGHT)
    assert MarketingSpecialistType.STRATEGIST in selected


def test_frozen_pipeline_order_unchanged() -> None:
    assert MarketingPipelineExecutionService.pipeline_order() == list(FROZEN_PIPELINE_ORDER)


def test_pipeline_matrix_unchanged_for_frozen_six() -> None:
    assert MarketingPipelineExecutionService.required_prior_specialists(
        MarketingSpecialistType.STRATEGIST,
    ) == []
    assert MarketingPipelineExecutionService.required_prior_specialists(
        MarketingSpecialistType.RESEARCHER,
    ) == [MarketingSpecialistType.STRATEGIST]
    assert MarketingPipelineExecutionService.required_prior_specialists(
        MarketingSpecialistType.ANALYST,
    ) == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
    ]


def test_ai_39_canonical_pipeline_order_invariant() -> None:
    assert MarketingPipelineExecutionService.pipeline_order() == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.ANALYST,
    ]


def test_v2_dependency_matrix_separate_from_frozen_pipeline() -> None:
    v2 = MarketingPipelineExecutionService.v2_specialist_dependencies()
    assert MarketingSpecialistType.OFFER_STRATEGIST in v2
    assert MarketingSpecialistType.STRATEGIST not in v2
    assert MarketingPipelineExecutionService.required_prior_specialists(
        MarketingSpecialistType.OFFER_STRATEGIST,
    ) == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ]
    assert MarketingPipelineExecutionService.required_prior_specialists(
        MarketingSpecialistType.EMAIL_DM_SPECIALIST,
    ) == [
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.SALES_COPYWRITER,
    ]


def test_no_metadata_only_roles_in_executor() -> None:
    from app.agents.marketer.specialists import executor as executor_module

    assert V2_METADATA_ONLY_SPECIALISTS == frozenset()
    assert len(executor_module._ENABLED_SPECIALISTS) == 14


@pytest.mark.parametrize(
    "specialist",
    sorted(V2_EXECUTION_ENABLED_SPECIALISTS, key=lambda s: s.value),
)
def test_executor_accepts_v2_execution_enabled_roles(specialist: MarketingSpecialistType) -> None:
    from app.agents.marketer.specialists import executor as executor_module

    assert specialist in executor_module._ENABLED_SPECIALISTS


def test_executor_still_accepts_frozen_strategist_gate() -> None:
    from app.agents.marketer.specialists import executor as executor_module

    assert MarketingSpecialistType.STRATEGIST in executor_module._ENABLED_SPECIALISTS
    assert V2_METADATA_ONLY_SPECIALISTS.isdisjoint(executor_module._ENABLED_SPECIALISTS)
