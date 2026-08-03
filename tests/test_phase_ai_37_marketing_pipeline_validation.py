"""Phase AI.37 — Marketing pipeline dependency validation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.db.models.marketing_specialist_output import MarketingSpecialistOutputTable
from app.schemas.contracts import (
    MarketingPlanExecutionTaskSnapshot,
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.marketing_pipeline_execution_service import (
    MarketingPipelineExecutionService,
)


def _snapshot(
    specialist: MarketingSpecialistType,
    *,
    status: MarketingPlanExecutionTaskStatus = MarketingPlanExecutionTaskStatus.PENDING,
    output_ref: str | None = None,
) -> MarketingPlanExecutionTaskSnapshot:
    return MarketingPlanExecutionTaskSnapshot(
        specialist=specialist,
        objective="objective",
        expected_output="expected",
        status=status,
        output_ref=output_ref,
    )


def _output_row(
    specialist: MarketingSpecialistType,
    *,
    status: MarketingSpecialistOutputStatus = MarketingSpecialistOutputStatus.DRAFT,
) -> MarketingSpecialistOutputTable:
    return MarketingSpecialistOutputTable(
        owner_id=uuid4(),
        project_id=uuid4(),
        marketing_plan_id=uuid4(),
        execution_run_id=uuid4(),
        task_index=0,
        specialist=specialist.value,
        title="title",
        output_type="type",
        content="content",
        structured_data={},
        status=status,
        current_version_number=1,
    )


@pytest.mark.parametrize(
    ("specialist", "expected_deps"),
    [
        (MarketingSpecialistType.STRATEGIST, []),
        (MarketingSpecialistType.RESEARCHER, [MarketingSpecialistType.STRATEGIST]),
        (
            MarketingSpecialistType.CONTENT_PLANNER,
            [MarketingSpecialistType.STRATEGIST, MarketingSpecialistType.RESEARCHER],
        ),
        (
            MarketingSpecialistType.COPYWRITER,
            [
                MarketingSpecialistType.STRATEGIST,
                MarketingSpecialistType.RESEARCHER,
                MarketingSpecialistType.CONTENT_PLANNER,
            ],
        ),
        (
            MarketingSpecialistType.CRITIC,
            [
                MarketingSpecialistType.STRATEGIST,
                MarketingSpecialistType.RESEARCHER,
                MarketingSpecialistType.CONTENT_PLANNER,
                MarketingSpecialistType.COPYWRITER,
            ],
        ),
        (
            MarketingSpecialistType.ANALYST,
            [
                MarketingSpecialistType.STRATEGIST,
                MarketingSpecialistType.RESEARCHER,
                MarketingSpecialistType.CONTENT_PLANNER,
                MarketingSpecialistType.COPYWRITER,
                MarketingSpecialistType.CRITIC,
            ],
        ),
    ],
)
def test_dependency_matrix_for_all_roles(
    specialist: MarketingSpecialistType,
    expected_deps: list[MarketingSpecialistType],
) -> None:
    assert MarketingPipelineExecutionService.required_prior_specialists(specialist) == expected_deps


def test_strategist_has_no_dependencies() -> None:
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.STRATEGIST,
        task_index=0,
        snapshots=[_snapshot(MarketingSpecialistType.STRATEGIST)],
        run_outputs=[],
    )
    assert result.can_execute is True
    assert result.missing_dependencies == ()


def test_researcher_blocked_before_strategist() -> None:
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.RESEARCHER,
        task_index=1,
        snapshots=[
            _snapshot(MarketingSpecialistType.STRATEGIST),
            _snapshot(MarketingSpecialistType.RESEARCHER),
        ],
        run_outputs=[],
    )
    assert result.can_execute is False
    assert result.safe_error == "Researcher requires completed Strategist output"


def test_planner_blocked_before_researcher() -> None:
    snapshots = [
        _snapshot(
            MarketingSpecialistType.STRATEGIST,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
        _snapshot(MarketingSpecialistType.CONTENT_PLANNER),
    ]
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.CONTENT_PLANNER,
        task_index=1,
        snapshots=snapshots,
        run_outputs=[],
    )
    assert result.can_execute is False
    assert result.safe_error == "Content Planner requires completed Researcher output"


def test_copywriter_blocked_before_planner() -> None:
    snapshots = [
        _snapshot(
            MarketingSpecialistType.STRATEGIST,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
        _snapshot(
            MarketingSpecialistType.RESEARCHER,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
        _snapshot(MarketingSpecialistType.COPYWRITER),
    ]
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.COPYWRITER,
        task_index=2,
        snapshots=snapshots,
        run_outputs=[],
    )
    assert result.can_execute is False
    assert "Content Planner" in (result.safe_error or "")


def test_critic_blocked_before_copywriter() -> None:
    snapshots = [
        _snapshot(
            MarketingSpecialistType.STRATEGIST,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
        _snapshot(
            MarketingSpecialistType.RESEARCHER,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
        _snapshot(
            MarketingSpecialistType.CONTENT_PLANNER,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
        _snapshot(MarketingSpecialistType.CRITIC),
    ]
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.CRITIC,
        task_index=3,
        snapshots=snapshots,
        run_outputs=[],
    )
    assert result.can_execute is False
    assert result.safe_error == "Critic requires completed Copywriter output"


def test_analyst_blocked_before_critic() -> None:
    snapshots = [
        _snapshot(
            specialist,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        )
        for specialist in (
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.COPYWRITER,
        )
    ] + [_snapshot(MarketingSpecialistType.ANALYST)]
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.ANALYST,
        task_index=4,
        snapshots=snapshots,
        run_outputs=[],
    )
    assert result.can_execute is False
    assert result.safe_error == "Analyst requires completed Critic output"


def test_archived_output_does_not_satisfy_dependency() -> None:
    outputs = [
        _output_row(
            MarketingSpecialistType.STRATEGIST,
            status=MarketingSpecialistOutputStatus.ARCHIVED,
        ),
    ]
    assert (
        MarketingPipelineExecutionService.dependency_satisfied(
            MarketingSpecialistType.STRATEGIST,
            [],
            outputs,
        )
        is False
    )


def test_draft_output_satisfies_dependency() -> None:
    outputs = [_output_row(MarketingSpecialistType.STRATEGIST)]
    assert MarketingPipelineExecutionService.dependency_satisfied(
        MarketingSpecialistType.STRATEGIST,
        [],
        outputs,
    )


def test_specialist_completed_snapshot_satisfies_dependency() -> None:
    snapshots = [
        _snapshot(
            MarketingSpecialistType.STRATEGIST,
            status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
        ),
    ]
    assert MarketingPipelineExecutionService.dependency_satisfied(
        MarketingSpecialistType.STRATEGIST,
        snapshots,
        [],
    )


def test_first_missing_dependency_message_order() -> None:
    result = MarketingPipelineExecutionService.validate_task_execution(
        specialist=MarketingSpecialistType.ANALYST,
        task_index=5,
        snapshots=[_snapshot(MarketingSpecialistType.ANALYST)],
        run_outputs=[],
    )
    assert result.can_execute is False
    assert result.missing_dependencies[0] == MarketingSpecialistType.STRATEGIST
    assert result.safe_error == "Analyst requires completed Strategist output"


def test_pipeline_order_matches_mvp_six() -> None:
    assert MarketingPipelineExecutionService.pipeline_order() == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.ANALYST,
    ]
