"""Marketing specialist pipeline validation (Phase AI.37) — dependencies only, no auto-run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.marketer.specialists.researcher import prior_output_from_row
from app.db.models.marketing_specialist_output import MarketingSpecialistOutputTable
from app.schemas.contracts import (
    MarketingPlanExecutionTaskSnapshot,
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistPriorOutput,
    MarketingSpecialistType,
)

_ACTIVE_OUTPUT_STATUSES = frozenset(
    {
        MarketingSpecialistOutputStatus.DRAFT,
        MarketingSpecialistOutputStatus.APPROVED,
    },
)

_PIPELINE_ORDER: tuple[MarketingSpecialistType, ...] = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.CRITIC,
    MarketingSpecialistType.ANALYST,
)

_DEPENDENCY_MATRIX: dict[MarketingSpecialistType, tuple[MarketingSpecialistType, ...]] = {
    MarketingSpecialistType.STRATEGIST: (),
    MarketingSpecialistType.RESEARCHER: (MarketingSpecialistType.STRATEGIST,),
    MarketingSpecialistType.CONTENT_PLANNER: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ),
    MarketingSpecialistType.COPYWRITER: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
    ),
    MarketingSpecialistType.CRITIC: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
    ),
    MarketingSpecialistType.ANALYST: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
    ),
}

_DEPENDENCY_ERROR_MESSAGES: dict[
    tuple[MarketingSpecialistType, MarketingSpecialistType],
    str,
] = {
    (
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.STRATEGIST,
    ): "Researcher requires completed Strategist output",
    (
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.STRATEGIST,
    ): "Content Planner requires completed Strategist output",
    (
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.RESEARCHER,
    ): "Content Planner requires completed Researcher output",
    (
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.STRATEGIST,
    ): "Copywriter requires completed Strategist output",
    (
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.RESEARCHER,
    ): "Copywriter requires completed Researcher output",
    (
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CONTENT_PLANNER,
    ): "Copywriter requires completed Content Planner output",
    (
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.STRATEGIST,
    ): "Critic requires completed Strategist output",
    (
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.RESEARCHER,
    ): "Critic requires completed Researcher output",
    (
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.CONTENT_PLANNER,
    ): "Critic requires completed Content Planner output",
    (
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.COPYWRITER,
    ): "Critic requires completed Copywriter output",
    (
        MarketingSpecialistType.ANALYST,
        MarketingSpecialistType.STRATEGIST,
    ): "Analyst requires completed Strategist output",
    (
        MarketingSpecialistType.ANALYST,
        MarketingSpecialistType.RESEARCHER,
    ): "Analyst requires completed Researcher output",
    (
        MarketingSpecialistType.ANALYST,
        MarketingSpecialistType.CONTENT_PLANNER,
    ): "Analyst requires completed Content Planner output",
    (
        MarketingSpecialistType.ANALYST,
        MarketingSpecialistType.COPYWRITER,
    ): "Analyst requires completed Copywriter output",
    (
        MarketingSpecialistType.ANALYST,
        MarketingSpecialistType.CRITIC,
    ): "Analyst requires completed Critic output",
}

V2_SPECIALIST_DEPENDENCIES: dict[
    MarketingSpecialistType,
    tuple[MarketingSpecialistType, ...],
] = {
    MarketingSpecialistType.OFFER_STRATEGIST: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ),
    MarketingSpecialistType.FUNNEL_ARCHITECT: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ),
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST: (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
    ),
    MarketingSpecialistType.SALES_COPYWRITER: (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ),
    MarketingSpecialistType.EMAIL_DM_SPECIALIST: (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.SALES_COPYWRITER,
    ),
    MarketingSpecialistType.CRO_SPECIALIST: (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.SALES_COPYWRITER,
    ),
    MarketingSpecialistType.SMM_STRATEGIST: (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ),
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST: (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.SALES_COPYWRITER,
    ),
}

_V2_DEPENDENCY_ERROR_MESSAGES: dict[
    tuple[MarketingSpecialistType, MarketingSpecialistType],
    str,
] = {
    (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.STRATEGIST,
    ): "Offer Strategist requires completed Strategist output",
    (
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ): "Offer Strategist requires completed Researcher output",
    (
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.STRATEGIST,
    ): "Funnel Architect requires completed Strategist output",
    (
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.RESEARCHER,
    ): "Funnel Architect requires completed Researcher output",
    (
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "Funnel Architect requires completed Offer Strategist output",
    (
        MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "Lead Magnet Specialist requires completed Offer Strategist output",
    (
        MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
    ): "Lead Magnet Specialist requires completed Funnel Architect output",
    (
        MarketingSpecialistType.SALES_COPYWRITER,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "Sales Copywriter requires completed Offer Strategist output",
    (
        MarketingSpecialistType.SALES_COPYWRITER,
        MarketingSpecialistType.RESEARCHER,
    ): "Sales Copywriter requires completed Researcher output",
    (
        MarketingSpecialistType.EMAIL_DM_SPECIALIST,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "Email/DM Specialist requires completed Offer Strategist output",
    (
        MarketingSpecialistType.EMAIL_DM_SPECIALIST,
        MarketingSpecialistType.SALES_COPYWRITER,
    ): "Email/DM Specialist requires completed Sales Copywriter output",
    (
        MarketingSpecialistType.CRO_SPECIALIST,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "CRO Specialist requires completed Offer Strategist output",
    (
        MarketingSpecialistType.CRO_SPECIALIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
    ): "CRO Specialist requires completed Funnel Architect output",
    (
        MarketingSpecialistType.CRO_SPECIALIST,
        MarketingSpecialistType.SALES_COPYWRITER,
    ): "CRO Specialist requires completed Sales Copywriter output",
    (
        MarketingSpecialistType.SMM_STRATEGIST,
        MarketingSpecialistType.STRATEGIST,
    ): "SMM Strategist requires completed Strategist output",
    (
        MarketingSpecialistType.SMM_STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ): "SMM Strategist requires completed Researcher output",
    (
        MarketingSpecialistType.SMM_STRATEGIST,
        MarketingSpecialistType.CONTENT_PLANNER,
    ): "SMM Strategist requires completed Content Planner output",
    (
        MarketingSpecialistType.SMM_STRATEGIST,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "SMM Strategist requires completed Offer Strategist output",
    (
        MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
        MarketingSpecialistType.OFFER_STRATEGIST,
    ): "Ad Creative Strategist requires completed Offer Strategist output",
    (
        MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
    ): "Ad Creative Strategist requires completed Researcher output",
    (
        MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
        MarketingSpecialistType.SALES_COPYWRITER,
    ): "Ad Creative Strategist requires completed Sales Copywriter output",
}

V2_EXECUTION_ENABLED_SPECIALISTS: frozenset[MarketingSpecialistType] = frozenset(
    V2_SPECIALIST_DEPENDENCIES.keys(),
)


@dataclass(frozen=True)
class MarketingPipelineValidationResult:
    can_execute: bool
    specialist: MarketingSpecialistType
    task_index: int
    missing_dependencies: tuple[MarketingSpecialistType, ...]
    prior_outputs: tuple[MarketingSpecialistPriorOutput, ...]
    safe_error: str | None = None


class MarketingPipelineExecutionService:
    """Central dependency matrix and prior-output assembly for specialist tasks."""

    @staticmethod
    def pipeline_order() -> list[MarketingSpecialistType]:
        return list(_PIPELINE_ORDER)

    @staticmethod
    def v2_specialist_dependencies() -> dict[
        MarketingSpecialistType,
        tuple[MarketingSpecialistType, ...],
    ]:
        return dict(V2_SPECIALIST_DEPENDENCIES)

    @staticmethod
    def execution_enabled_specialists() -> frozenset[MarketingSpecialistType]:
        return frozenset(_PIPELINE_ORDER) | V2_EXECUTION_ENABLED_SPECIALISTS

    @staticmethod
    def is_v2_execution_specialist(specialist: MarketingSpecialistType) -> bool:
        return specialist in V2_EXECUTION_ENABLED_SPECIALISTS

    @staticmethod
    def required_prior_specialists(
        specialist: MarketingSpecialistType,
    ) -> list[MarketingSpecialistType]:
        if specialist in V2_SPECIALIST_DEPENDENCIES:
            return list(V2_SPECIALIST_DEPENDENCIES[specialist])
        return list(_DEPENDENCY_MATRIX.get(specialist, ()))

    @staticmethod
    def dependency_error_message(
        specialist: MarketingSpecialistType,
        missing: MarketingSpecialistType,
    ) -> str:
        message = _V2_DEPENDENCY_ERROR_MESSAGES.get((specialist, missing))
        if message is not None:
            return message
        message = _DEPENDENCY_ERROR_MESSAGES.get((specialist, missing))
        if message is not None:
            return message
        label = missing.value.replace("_", " ").title()
        return f"{specialist.value.replace('_', ' ').title()} requires completed {label} output"

    @staticmethod
    def dependency_satisfied(
        required: MarketingSpecialistType,
        snapshots: list[MarketingPlanExecutionTaskSnapshot],
        run_outputs: list[MarketingSpecialistOutputTable],
    ) -> bool:
        has_completed_task = any(
            snap.specialist == required
            and snap.status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED
            for snap in snapshots
        )
        has_active_output = any(
            row.specialist == required.value
            and row.status in _ACTIVE_OUTPUT_STATUSES
            for row in run_outputs
        )
        return has_completed_task or has_active_output

    @classmethod
    def missing_dependencies(
        cls,
        specialist: MarketingSpecialistType,
        snapshots: list[MarketingPlanExecutionTaskSnapshot],
        run_outputs: list[MarketingSpecialistOutputTable],
    ) -> list[MarketingSpecialistType]:
        missing: list[MarketingSpecialistType] = []
        for required in cls.required_prior_specialists(specialist):
            if not cls.dependency_satisfied(required, snapshots, run_outputs):
                missing.append(required)
        return missing

    @classmethod
    def first_missing_dependency_message(
        cls,
        specialist: MarketingSpecialistType,
        snapshots: list[MarketingPlanExecutionTaskSnapshot],
        run_outputs: list[MarketingSpecialistOutputTable],
    ) -> str | None:
        missing = cls.missing_dependencies(specialist, snapshots, run_outputs)
        if not missing:
            return None
        first = missing[0]
        return cls.dependency_error_message(specialist, first)

    @classmethod
    def collect_prior_outputs(
        cls,
        specialist: MarketingSpecialistType,
        run_outputs: list[MarketingSpecialistOutputTable],
    ) -> list[MarketingSpecialistPriorOutput]:
        required = frozenset(cls.required_prior_specialists(specialist))
        prior: list[MarketingSpecialistPriorOutput] = []
        for row in run_outputs:
            row_specialist = MarketingSpecialistType(row.specialist)
            if row_specialist not in required:
                continue
            if row.status not in _ACTIVE_OUTPUT_STATUSES:
                continue
            prior.append(
                prior_output_from_row(
                    specialist=row_specialist,
                    title=row.title,
                    output_type=row.output_type,
                    content=row.content,
                    structured_data=(
                        dict(row.structured_data) if row.structured_data else None
                    ),
                ),
            )
        return prior

    @classmethod
    def validate_task_execution(
        cls,
        *,
        specialist: MarketingSpecialistType,
        task_index: int,
        snapshots: list[MarketingPlanExecutionTaskSnapshot],
        run_outputs: list[MarketingSpecialistOutputTable],
    ) -> MarketingPipelineValidationResult:
        missing = cls.missing_dependencies(specialist, snapshots, run_outputs)
        if missing:
            return MarketingPipelineValidationResult(
                can_execute=False,
                specialist=specialist,
                task_index=task_index,
                missing_dependencies=tuple(missing),
                prior_outputs=(),
                safe_error=cls.dependency_error_message(specialist, missing[0]),
            )
        prior = cls.collect_prior_outputs(specialist, run_outputs)
        return MarketingPipelineValidationResult(
            can_execute=True,
            specialist=specialist,
            task_index=task_index,
            missing_dependencies=(),
            prior_outputs=tuple(prior),
            safe_error=None,
        )

    @classmethod
    def all_tasks_specialist_completed(
        cls,
        snapshots: list[MarketingPlanExecutionTaskSnapshot],
    ) -> bool:
        if not snapshots:
            return False
        return all(
            snap.status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED
            for snap in snapshots
        )

    @classmethod
    def build_specialist_pipeline_result_summary(
        cls,
        snapshots: list[MarketingPlanExecutionTaskSnapshot],
    ) -> dict[str, Any]:
        specialists_in_run = {snap.specialist for snap in snapshots}
        completed_specialists = [
            specialist.value
            for specialist in _PIPELINE_ORDER
            if specialist in specialists_in_run
        ]
        output_ids_by_specialist: dict[str, str] = {}
        for snap in snapshots:
            if snap.output_ref:
                output_ids_by_specialist[snap.specialist.value] = snap.output_ref
        return {
            "mode": "specialist_pipeline",
            "completed_specialists": completed_specialists,
            "output_ids_by_specialist": output_ids_by_specialist,
            "task_count": len(snapshots),
        }
