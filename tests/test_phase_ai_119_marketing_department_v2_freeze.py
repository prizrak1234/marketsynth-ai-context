"""Phase AI.119 — Marketing Department v2 freeze invariants."""

from __future__ import annotations

from app.agents.marketer.marketing_specialist_registry import (
    FROZEN_PIPELINE_ORDER,
    MARKETING_DEPARTMENT_V2_ROLE_COUNT,
    V2_EXECUTION_ENABLED_SPECIALISTS,
    V2_METADATA_ONLY_SPECIALISTS,
    get_marketing_specialist,
    list_marketing_specialists,
)
from app.agents.marketer.planning import build_marketing_execution_plan
from app.agents.marketer.specialists import executor as executor_module
from app.schemas.contracts import MarketingSpecialistType
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService


def test_fourteen_role_department_registered() -> None:
    assert len(MarketingSpecialistType) == MARKETING_DEPARTMENT_V2_ROLE_COUNT == 14
    assert len(list_marketing_specialists()) == 14


def test_frozen_six_unchanged() -> None:
    assert MarketingPipelineExecutionService.pipeline_order() == list(FROZEN_PIPELINE_ORDER)
    assert MarketingPipelineExecutionService.required_prior_specialists(
        MarketingSpecialistType.ANALYST,
    ) == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
    ]


def test_v2_execution_enabled_covers_eight_roles() -> None:
    assert len(V2_EXECUTION_ENABLED_SPECIALISTS) == 8
    assert V2_METADATA_ONLY_SPECIALISTS == frozenset()
    for specialist in V2_EXECUTION_ENABLED_SPECIALISTS:
        profile = get_marketing_specialist(specialist)
        assert profile.execution_enabled is True
        assert specialist in executor_module._ENABLED_SPECIALISTS


def test_orchestrator_planning_excludes_all_v2_roles() -> None:
    plan = build_marketing_execution_plan(message="Сделай контент-стратегию для стоматологии")
    selected = {task.specialist for task in plan.specialist_tasks}
    assert selected.isdisjoint(V2_EXECUTION_ENABLED_SPECIALISTS)


def test_v2_dependency_matrix_stable() -> None:
    v2 = MarketingPipelineExecutionService.v2_specialist_dependencies()
    assert v2[MarketingSpecialistType.CRO_SPECIALIST] == (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.SALES_COPYWRITER,
    )
    assert v2[MarketingSpecialistType.SMM_STRATEGIST] == (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.OFFER_STRATEGIST,
    )
    assert v2[MarketingSpecialistType.AD_CREATIVE_STRATEGIST] == (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.SALES_COPYWRITER,
    )


def test_freeze_doc_exists() -> None:
    from pathlib import Path

    doc = Path("docs/phase_ai_119_marketing_department_v2_freeze.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "14" in text
    assert "frozen six" in text.lower() or "Frozen six" in text
