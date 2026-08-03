"""ImplementationPlan service (Commercial MVP P1.1).

Durable delivery plan from approved MarketingStrategy.
Never creates MarketingPlan, specialist tasks, Campaign, Agent Run, or execution approvals.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.implementation_plan import ImplementationPlanTable
from app.db.repositories.implementation_plans import ImplementationPlanRepository
from app.db.repositories.marketing_strategies import MarketingStrategyRepository
from app.domain.implementation_plan_engine import (
    assert_strategy_allows_plan,
    build_handoff_preview,
    compute_plan_readiness,
    detect_dependency_cycles,
    validate_tasks_acceptance,
    validate_unsupported_roles,
)
from app.schemas.contracts import (
    ImplApprovalGate,
    ImplApprovalGateType,
    ImplAssumption,
    ImplAssumptionStatus,
    ImplBudgetCategory,
    ImplBudgetGate,
    ImplBudgetItem,
    ImplBudgetPlan,
    ImplBudgetValueType,
    ImplConditionRef,
    ImplConditionSourceType,
    ImplDeliverable,
    ImplDependency,
    ImplDependencyNodeType,
    ImplDependencyType,
    ImplLocalGateStatus,
    ImplMilestone,
    ImplMilestoneStatus,
    ImplPeriodSpec,
    ImplPriority,
    ImplRisk,
    ImplRoadmapHorizon,
    ImplRoadmapPhase,
    ImplRoleAssignment,
    ImplRoleType,
    ImplTargetPeriodMode,
    ImplTask,
    ImplTaskMappingEligibility,
    ImplTaskStatus,
    ImplWorkstream,
    ImplWorkstreamStatus,
    ImplWorkstreamType,
    ImplementationPlanBuildDraftRequest,
    ImplementationPlanCreate,
    ImplementationPlanHandoffPreview,
    ImplementationPlanLifecycleStatus,
    ImplementationPlanOrigin,
    ImplementationPlanReviewRequest,
    ImplementationPlanUpdate,
    MarketingStrategyLifecycleStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_LIFECYCLE: dict[
    ImplementationPlanLifecycleStatus, frozenset[ImplementationPlanLifecycleStatus]
] = {
    ImplementationPlanLifecycleStatus.DRAFT: frozenset(
        {
            ImplementationPlanLifecycleStatus.UNDER_REVIEW,
            ImplementationPlanLifecycleStatus.BLOCKED,
            ImplementationPlanLifecycleStatus.ARCHIVED,
            ImplementationPlanLifecycleStatus.SUPERSEDED,
        }
    ),
    ImplementationPlanLifecycleStatus.UNDER_REVIEW: frozenset(
        {
            ImplementationPlanLifecycleStatus.DRAFT,
            ImplementationPlanLifecycleStatus.APPROVED,
            ImplementationPlanLifecycleStatus.REJECTED,
            ImplementationPlanLifecycleStatus.BLOCKED,
            ImplementationPlanLifecycleStatus.SUPERSEDED,
        }
    ),
    ImplementationPlanLifecycleStatus.BLOCKED: frozenset(
        {
            ImplementationPlanLifecycleStatus.DRAFT,
            ImplementationPlanLifecycleStatus.UNDER_REVIEW,
            ImplementationPlanLifecycleStatus.ARCHIVED,
            ImplementationPlanLifecycleStatus.SUPERSEDED,
        }
    ),
    ImplementationPlanLifecycleStatus.APPROVED: frozenset(
        {
            ImplementationPlanLifecycleStatus.SUPERSEDED,
            ImplementationPlanLifecycleStatus.ARCHIVED,
        }
    ),
    ImplementationPlanLifecycleStatus.REJECTED: frozenset(
        {
            ImplementationPlanLifecycleStatus.ARCHIVED,
            ImplementationPlanLifecycleStatus.SUPERSEDED,
        }
    ),
    ImplementationPlanLifecycleStatus.SUPERSEDED: frozenset(),
    ImplementationPlanLifecycleStatus.ARCHIVED: frozenset(),
}


def _dump(items: list[Any] | Any) -> list[dict[str, Any]] | dict[str, Any]:
    if isinstance(items, list):
        out: list[dict[str, Any]] = []
        for item in items:
            out.append(item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item))
        return out
    if hasattr(items, "model_dump"):
        return items.model_dump(mode="json")
    return dict(items)


class ImplementationPlanService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._plans = ImplementationPlanRepository(session)
        self._strategies = MarketingStrategyRepository(session)

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _transition(
        self,
        row: ImplementationPlanTable,
        target: ImplementationPlanLifecycleStatus,
    ) -> None:
        current = ImplementationPlanLifecycleStatus(row.lifecycle_status)
        if target not in _LIFECYCLE.get(current, frozenset()):
            raise InvalidStateError("invalid_transition")
        if current == ImplementationPlanLifecycleStatus.APPROVED and target not in (
            ImplementationPlanLifecycleStatus.SUPERSEDED,
            ImplementationPlanLifecycleStatus.ARCHIVED,
        ):
            raise InvalidStateError("immutable_plan")
        row.lifecycle_status = target
        row.updated_at = utc_now()

    def _append_review_event(
        self,
        row: ImplementationPlanTable,
        *,
        action: str,
        actor_id: UUID,
        note: str | None,
        previous: str,
        new_status: str,
    ) -> None:
        meta = dict(row.metadata_json or {})
        events = list(meta.get("review_events") or [])
        events.append(
            {
                "action": action,
                "actor_id": str(actor_id),
                "note": note,
                "previous_status": previous,
                "new_status": new_status,
                "marketing_strategy_id": str(row.marketing_strategy_id),
                "marketing_strategy_version": row.marketing_strategy_version,
                "business_verdict_id": str(row.business_verdict_id),
                "business_verdict_version": row.business_verdict_version,
                "evidence_snapshot_hash": row.evidence_snapshot_hash,
                "at": utc_now().isoformat(),
            }
        )
        meta["review_events"] = events
        meta["creates_marketing_plan"] = False
        meta["creates_specialist_tasks"] = False
        meta["creates_campaign"] = False
        meta["creates_execution_approval"] = False
        meta["creates_agent_run"] = False
        row.metadata_json = meta

    def _validate_structure(self, body: ImplementationPlanCreate | ImplementationPlanUpdate) -> None:
        deps = getattr(body, "dependencies", None)
        if deps is not None:
            detect_dependency_cycles(list(deps))
        tasks = getattr(body, "tasks", None)
        if tasks is not None:
            missing = validate_tasks_acceptance(list(tasks))
            if missing and isinstance(body, ImplementationPlanCreate):
                raise InvalidStateError("missing_acceptance_criteria")
        roles = getattr(body, "role_assignments", None)
        if roles is not None:
            validate_unsupported_roles(list(roles))

    def _recompute_readiness(self, row: ImplementationPlanTable) -> None:
        readiness, reasons = compute_plan_readiness(
            workstreams=row.workstreams or [],
            milestones=row.milestones or [],
            tasks=row.tasks or [],
            dependencies=row.dependencies or [],
            deliverables=row.deliverables or [],
            budget_gates=row.budget_gates or [],
            approval_gates=row.approval_gates or [],
            conditions=row.conditions or [],
            assumptions=row.assumptions or [],
            implementation_risks=row.implementation_risks or [],
            role_assignments=row.role_assignments or [],
        )
        row.readiness_status = readiness
        row.readiness_reasons = reasons

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: ImplementationPlanCreate,
    ) -> ImplementationPlanTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        strategy = await self._strategies.get_by_id_for_owner(
            body.marketing_strategy_id, owner_id, project_id
        )
        if strategy is None:
            raise InvalidStateError("strategy_not_found")
        if int(strategy.version) != int(body.marketing_strategy_version):
            raise InvalidStateError("strategy_version_mismatch")
        assert_strategy_allows_plan(strategy)
        self._validate_structure(body)

        version = await self._plans.next_version(owner_id, project_id)
        row = ImplementationPlanTable(
            owner_id=owner_id,
            project_id=project_id,
            marketing_strategy_id=strategy.id,
            marketing_strategy_version=strategy.version,
            business_verdict_id=strategy.business_verdict_id,
            business_verdict_version=strategy.business_verdict_version,
            evidence_snapshot_id=strategy.evidence_snapshot_id,
            evidence_snapshot_hash=strategy.evidence_snapshot_hash,
            version=version,
            lifecycle_status=ImplementationPlanLifecycleStatus.DRAFT,
            plan_origin=body.plan_origin,
            title=sanitize_text(body.title).strip()[:240],
            summary=sanitize_text(body.summary).strip()[:4000],
            implementation_horizon=sanitize_text(body.implementation_horizon).strip()[:240],
            workstreams=_dump(list(body.workstreams)),
            milestones=_dump(list(body.milestones)),
            tasks=_dump(list(body.tasks)),
            role_assignments=_dump(list(body.role_assignments)),
            dependencies=_dump(list(body.dependencies)),
            deliverables=_dump(list(body.deliverables)),
            budget_plan=_dump(body.budget_plan),
            budget_gates=_dump(list(body.budget_gates)),
            approval_gates=_dump(list(body.approval_gates)),
            conditions=_dump(list(body.conditions)),
            implementation_risks=_dump(list(body.implementation_risks)),
            assumptions=_dump(list(body.assumptions)),
            roadmap=_dump(list(body.roadmap)),
            supersedes_plan_id=body.supersedes_plan_id,
            metadata_json={
                "creates_marketing_plan": False,
                "creates_specialist_tasks": False,
                "creates_campaign": False,
                "creates_execution_approval": False,
                "creates_publication_approval": False,
                "creates_agent_run": False,
                "budget_gates_authorize_spend": False,
                "approval_gates_are_local_only": True,
                "review_events": [],
            },
        )
        self._recompute_readiness(row)
        async with transactional(self._session):
            return await self._plans.create(row)

    async def build_deterministic_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: ImplementationPlanBuildDraftRequest,
    ) -> ImplementationPlanTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        strategy = await self._strategies.get_by_id_for_owner(
            body.marketing_strategy_id, owner_id, project_id
        )
        if strategy is None:
            raise InvalidStateError("strategy_not_found")
        assert_strategy_allows_plan(strategy)

        obj_ids = [
            str(o.get("id") if isinstance(o, dict) else getattr(o, "id", f"obj_{i}"))
            for i, o in enumerate(strategy.objectives or [])
        ] or ["obj_primary"]

        ws_validation = ImplWorkstream(
            id="ws_validation",
            title="Validation & Evidence Closure",
            purpose="Close open Verdict/Strategy conditions before acquisition spend",
            workstream_type=ImplWorkstreamType.VALIDATION,
            linked_strategy_objective_ids=obj_ids[:1],
            owner_role="Research Director",
            reviewer_role="Client Owner",
            priority=ImplPriority.CRITICAL,
            lifecycle_status=ImplWorkstreamStatus.READY,
            planned_start=ImplPeriodSpec(
                mode=ImplTargetPeriodMode.RELATIVE_HORIZON, label="Week 1–2"
            ),
            planned_finish=ImplPeriodSpec(
                mode=ImplTargetPeriodMode.RELATIVE_HORIZON, label="Month 1"
            ),
            deliverable_ids=["del_validation_report"],
            budget_range="unknown — requires_approval",
            success_criteria=["Open conditions have validation owners and tasks"],
        )
        ws_positioning = ImplWorkstream(
            id="ws_positioning",
            title="Positioning & Offer Packaging",
            purpose="Translate Strategy positioning and offers into delivery artifacts",
            workstream_type=ImplWorkstreamType.POSITIONING,
            linked_strategy_objective_ids=obj_ids[:1],
            owner_role="Chief Marketing Strategist",
            reviewer_role="Client Owner",
            priority=ImplPriority.HIGH,
            deliverable_ids=["del_positioning_doc", "del_offer_matrix"],
            budget_range="unknown",
            success_criteria=["Positioning document accepted locally"],
        )
        ws_acq = ImplWorkstream(
            id="ws_acquisition",
            title="Acquisition Test Planning",
            purpose="Plan acquisition tests without authorizing spend or execution",
            workstream_type=ImplWorkstreamType.ACQUISITION,
            linked_strategy_objective_ids=obj_ids[:1],
            owner_role="Performance Marketer",
            reviewer_role="Chief Marketing Strategist",
            priority=ImplPriority.MEDIUM,
            dependencies=["ws_validation"],
            deliverable_ids=["del_channel_test_plan"],
            budget_range="requires_approval",
            success_criteria=["Channel test plan defined with acceptance criteria"],
            blockers=["Pending budget gate"],
        )

        ms1 = ImplMilestone(
            id="ms_validation",
            title="Validation package ready",
            description="Conditions ownered and validation tasks ready",
            target_period=ImplPeriodSpec(
                mode=ImplTargetPeriodMode.RELATIVE_HORIZON, label="Week 1–2"
            ),
            linked_workstream_ids=["ws_validation"],
            required_deliverable_ids=["del_validation_report"],
            entry_criteria=["Approved Strategy linked"],
            exit_criteria=["Validation report planned with acceptance criteria"],
            approval_required=True,
            approval_gate_id="ag_validation",
            status=ImplMilestoneStatus.PLANNED,
        )
        ms2 = ImplMilestone(
            id="ms_offer",
            title="Offer & positioning artifacts ready",
            description="Strategy packaging translated to deliverables",
            target_period=ImplPeriodSpec(
                mode=ImplTargetPeriodMode.RELATIVE_HORIZON, label="Month 1"
            ),
            linked_workstream_ids=["ws_positioning"],
            required_deliverable_ids=["del_positioning_doc", "del_offer_matrix"],
            entry_criteria=["Strategy positioning available"],
            exit_criteria=["Offer matrix acceptance criteria defined"],
            approval_required=True,
            approval_gate_id="ag_offer",
            status=ImplMilestoneStatus.PLANNED,
        )

        tasks = [
            ImplTask(
                id="task_val_plan",
                title="Plan condition validation package",
                description="Map Verdict/Strategy conditions to validation tasks",
                workstream_id="ws_validation",
                milestone_id="ms_validation",
                responsible_role="Research Director",
                reviewer_role="Client Owner",
                priority=ImplPriority.CRITICAL,
                lifecycle_status=ImplTaskStatus.READY,
                expected_output="Validation plan deliverable outline",
                acceptance_criteria=[
                    "Each open condition has owner_role and success_criterion",
                    "Does not mark Verdict conditions as satisfied",
                ],
                mapping_eligibility=ImplTaskMappingEligibility.TRANSFORMABLE,
                linked_strategy_element_refs=["conditions"],
            ),
            ImplTask(
                id="task_positioning",
                title="Draft positioning document outline",
                description="Operationalize Strategy positioning (no content generation)",
                workstream_id="ws_positioning",
                milestone_id="ms_offer",
                responsible_role="Chief Marketing Strategist",
                reviewer_role="Client Owner",
                priority=ImplPriority.HIGH,
                expected_output="Positioning document outline",
                acceptance_criteria=[
                    "References exact Strategy version",
                    "Avoids slogan-only claims",
                ],
                mapping_eligibility=ImplTaskMappingEligibility.TRANSFORMABLE,
                linked_strategy_element_refs=["positioning"],
            ),
            ImplTask(
                id="task_channel_plan",
                title="Define channel test plan structure",
                description="Planning-only channel tests; no spend authorization",
                workstream_id="ws_acquisition",
                responsible_role="Performance Marketer",
                reviewer_role="Chief Marketing Strategist",
                priority=ImplPriority.MEDIUM,
                dependency_ids=["dep_val_before_acq"],
                expected_output="Channel test plan outline",
                acceptance_criteria=[
                    "Budget gate referenced",
                    "No provider or execution step included",
                ],
                budget_impact="requires_approval",
                approval_required=True,
                approval_gate_id="ag_budget",
                mapping_eligibility=ImplTaskMappingEligibility.TRANSFORMABLE,
                linked_strategy_element_refs=["channel_strategy"],
            ),
        ]

        roles = [
            ImplRoleAssignment(
                implementation_role="Client Owner",
                backend_role_mapping=None,
                role_type=ImplRoleType.CLIENT_OWNER,
                responsibility="Approve local plan gates; final stop/go on delivery readiness",
                decision_authority="Local ImplementationPlan approvals only",
                execution_mapping_allowed=False,
            ),
            ImplRoleAssignment(
                implementation_role="Chief Marketing Strategist",
                backend_role_mapping="strategist",
                role_type=ImplRoleType.EXACT_BACKEND_ROLE,
                responsibility="Own positioning/offer workstreams",
                execution_mapping_allowed=False,
            ),
            ImplRoleAssignment(
                implementation_role="Project Manager",
                backend_role_mapping=None,
                role_type=ImplRoleType.FRONTEND_ALIAS,
                responsibility="Coordinate dependencies and readiness",
                execution_mapping_allowed=False,
            ),
            ImplRoleAssignment(
                implementation_role="Research Director",
                backend_role_mapping="researcher",
                role_type=ImplRoleType.EXACT_BACKEND_ROLE,
                responsibility="Validation workstream",
                execution_mapping_allowed=False,
            ),
            ImplRoleAssignment(
                implementation_role="Performance Marketer",
                backend_role_mapping=None,
                role_type=ImplRoleType.FRONTEND_ALIAS,
                responsibility="Acquisition test planning (not spend)",
                execution_mapping_allowed=False,
            ),
            ImplRoleAssignment(
                implementation_role="Risk Officer",
                backend_role_mapping=None,
                role_type=ImplRoleType.FRONTEND_ALIAS,
                responsibility="Track implementation risks and stop conditions",
                execution_mapping_allowed=False,
            ),
        ]

        deps = [
            ImplDependency(
                id="dep_val_before_acq",
                predecessor_type=ImplDependencyNodeType.WORKSTREAM,
                predecessor_id="ws_validation",
                successor_type=ImplDependencyNodeType.WORKSTREAM,
                successor_id="ws_acquisition",
                dependency_type=ImplDependencyType.FINISH_TO_START,
                blocking=True,
                resolution_action="Complete validation workstream before acquisition tests",
            ),
            ImplDependency(
                id="dep_budget_gate",
                predecessor_type=ImplDependencyNodeType.BUDGET_GATE,
                predecessor_id="bg_acq",
                successor_type=ImplDependencyNodeType.TASK,
                successor_id="task_channel_plan",
                dependency_type=ImplDependencyType.BUDGET_GATE,
                blocking=True,
                resolution_action="Local budget gate must clear before acquisition task advances",
            ),
        ]

        deliverables = [
            ImplDeliverable(
                id="del_validation_report",
                name="Audience / condition validation report outline",
                deliverable_type="audience_validation_report",
                workstream_id="ws_validation",
                owner_role="Research Director",
                acceptance_criteria=["Condition refs preserved without status overwrite"],
            ),
            ImplDeliverable(
                id="del_positioning_doc",
                name="Positioning document outline",
                deliverable_type="positioning_document",
                workstream_id="ws_positioning",
                owner_role="Chief Marketing Strategist",
                acceptance_criteria=["Links to Strategy positioning fields"],
                approval_required=True,
                approval_gate_id="ag_offer",
            ),
            ImplDeliverable(
                id="del_offer_matrix",
                name="Offer matrix outline",
                deliverable_type="offer_matrix",
                workstream_id="ws_positioning",
                owner_role="Chief Marketing Strategist",
                acceptance_criteria=["Maps Strategy offers without inventing prices"],
            ),
            ImplDeliverable(
                id="del_channel_test_plan",
                name="Channel test plan outline",
                deliverable_type="channel_test_plan",
                workstream_id="ws_acquisition",
                owner_role="Performance Marketer",
                acceptance_criteria=["No spend authorization"],
                approval_required=True,
                approval_gate_id="ag_budget",
            ),
        ]

        budget_plan = ImplBudgetPlan(
            notes="Planned structure only — not budget authorization",
            items=[
                ImplBudgetItem(
                    id="bi_validation",
                    category=ImplBudgetCategory.RESEARCH_AND_VALIDATION,
                    value_type=ImplBudgetValueType.UNKNOWN,
                    rationale="Validation before acquisition",
                    linked_workstream_ids=["ws_validation"],
                    requires_approval=True,
                ),
                ImplBudgetItem(
                    id="bi_acq",
                    category=ImplBudgetCategory.ACQUISITION_TESTING,
                    value_type=ImplBudgetValueType.REQUIRES_APPROVAL,
                    rationale="Test budget TBD — gate required",
                    linked_workstream_ids=["ws_acquisition"],
                    requires_approval=True,
                ),
            ],
        )
        budget_gates = [
            ImplBudgetGate(
                id="bg_acq",
                title="Acquisition test budget gate (local)",
                amount_or_range="unknown — requires_approval",
                prerequisite="Validation workstream entry criteria met",
                approval_owner_role="Client Owner",
                release_condition="Local approval only — not financial authorization",
                blocked_workstream_ids=["ws_acquisition"],
                lifecycle_status=ImplLocalGateStatus.PENDING,
            )
        ]
        approval_gates = [
            ImplApprovalGate(
                id="ag_plan_review",
                gate_type=ImplApprovalGateType.IMPLEMENTATION_PLAN_REVIEW,
                title="Implementation Plan review",
                decision_owner_role="Client Owner",
                subject_refs=["plan"],
                lifecycle_status=ImplLocalGateStatus.PENDING,
                consequence_if_rejected="Return plan to draft",
            ),
            ImplApprovalGate(
                id="ag_validation",
                gate_type=ImplApprovalGateType.VALIDATION_COMPLETION,
                title="Validation completion gate",
                decision_owner_role="Client Owner",
                target_milestone_id="ms_validation",
                lifecycle_status=ImplLocalGateStatus.PENDING,
                consequence_if_rejected="Block acquisition workstream",
                affected_task_ids=["task_channel_plan"],
            ),
            ImplApprovalGate(
                id="ag_offer",
                gate_type=ImplApprovalGateType.OFFER_REVIEW,
                title="Offer/positioning review",
                decision_owner_role="Client Owner",
                target_milestone_id="ms_offer",
                lifecycle_status=ImplLocalGateStatus.PENDING,
                consequence_if_rejected="Revise positioning deliverables",
            ),
            ImplApprovalGate(
                id="ag_budget",
                gate_type=ImplApprovalGateType.BUDGET_REVIEW,
                title="Budget review (local)",
                decision_owner_role="Client Owner",
                lifecycle_status=ImplLocalGateStatus.PENDING,
                consequence_if_rejected="Acquisition tasks remain blocked",
                affected_task_ids=["task_channel_plan"],
            ),
        ]

        conditions: list[ImplConditionRef] = []
        for c in strategy.verdict_conditions or []:
            data = c if isinstance(c, dict) else (
                c.model_dump() if hasattr(c, "model_dump") else dict(c)
            )
            cid = str(data.get("verdict_condition_id") or data.get("id") or "")
            if not cid:
                continue
            conditions.append(
                ImplConditionRef(
                    id=f"cond_{cid}",
                    source_type=ImplConditionSourceType.BUSINESS_VERDICT,
                    source_id=cid,
                    source_version=strategy.business_verdict_version,
                    current_status_snapshot=str(
                        data.get("current_status_snapshot") or "open"
                    ),
                    required_action=str(data.get("validation_action") or ""),
                    owner_role="Research Director",
                    validation_method="Evidence package under Investigation rules",
                    success_criterion="Verdict domain updates condition status",
                    required_evidence=True,
                    blocking_task_ids=["task_val_plan"],
                )
            )

        risks = [
            ImplRisk(
                id="risk_premature_acq",
                title="Premature acquisition before validation",
                source_ref="strategy_conditions",
                probability=ImplPriority.HIGH,
                severity=ImplPriority.CRITICAL,
                affected_workstream_ids=["ws_acquisition"],
                early_warning_indicator="Budget gate cleared without validation exit",
                mitigation="Keep budget gate and validation dependency blocking",
                contingency_action="Return acquisition tasks to blocked",
                stop_condition="Attempted MarketingPlan create without ready_for_handoff",
                linked_strategy_risk_id=None,
            )
        ]
        assumptions = [
            ImplAssumption(
                id="asm_strategy_stable",
                statement="Approved Strategy version remains the planning basis until superseded",
                source_ref=str(strategy.id),
                confidence=ImplPriority.HIGH,
                validation_action="Detect strategy version drift on plan edit",
                lifecycle_status=ImplAssumptionStatus.ACCEPTED_FOR_PLANNING,
            )
        ]
        roadmap = [
            ImplRoadmapPhase(
                id="rp_w12",
                title="Stabilization & validation",
                horizon=ImplRoadmapHorizon.WEEK_1_2,
                workstream_ids=["ws_validation"],
                milestone_ids=["ms_validation"],
                entry_criteria=["Approved Strategy"],
                exit_criteria=["Validation milestone exit criteria planned"],
            ),
            ImplRoadmapPhase(
                id="rp_m1",
                title="Packaging",
                horizon=ImplRoadmapHorizon.MONTH_1,
                workstream_ids=["ws_positioning"],
                milestone_ids=["ms_offer"],
                entry_criteria=["Validation in progress or planned"],
                exit_criteria=["Offer artifacts planned"],
            ),
            ImplRoadmapPhase(
                id="rp_m2",
                title="Acquisition planning",
                horizon=ImplRoadmapHorizon.MONTH_2,
                workstream_ids=["ws_acquisition"],
                entry_criteria=["Budget gate policy defined"],
                blockers=["Pending local budget gate"],
            ),
        ]

        create_body = ImplementationPlanCreate(
            marketing_strategy_id=strategy.id,
            marketing_strategy_version=strategy.version,
            title=f"Implementation Plan — {strategy.title}"[:240],
            summary=(
                "Deterministic delivery decomposition of an approved MarketingStrategy. "
                "Not a MarketingPlan; does not authorize execution, spend, or specialist tasks."
            ),
            implementation_horizon=strategy.strategic_horizon or "TBD",
            workstreams=[ws_validation, ws_positioning, ws_acq],
            milestones=[ms1, ms2],
            tasks=tasks,
            role_assignments=roles,
            dependencies=deps,
            deliverables=deliverables,
            budget_plan=budget_plan,
            budget_gates=budget_gates,
            approval_gates=approval_gates,
            conditions=conditions,
            implementation_risks=risks,
            assumptions=assumptions,
            roadmap=roadmap,
            plan_origin=ImplementationPlanOrigin.DETERMINISTIC,
            supersedes_plan_id=body.supersedes_plan_id,
        )
        return await self.create(owner_id, project_id, create_body)

    async def get(
        self, owner_id: UUID, project_id: UUID, plan_id: UUID
    ) -> ImplementationPlanTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)

    async def get_latest(
        self, owner_id: UUID, project_id: UUID
    ) -> ImplementationPlanTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._plans.latest_any(owner_id, project_id)

    async def list_plans(
        self,
        owner_id: UUID,
        project_id: UUID,
        **kwargs: Any,
    ) -> list[ImplementationPlanTable] | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._plans.list_for_project(owner_id, project_id, **kwargs)

    async def update_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        body: ImplementationPlanUpdate,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        if ImplementationPlanLifecycleStatus(row.lifecycle_status) != (
            ImplementationPlanLifecycleStatus.DRAFT
        ):
            raise InvalidStateError("immutable_plan")
        self._validate_structure(body)
        data = body.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key in ("title", "summary", "implementation_horizon") and value is not None:
                setattr(
                    row,
                    key,
                    sanitize_text(str(value)).strip()[
                        : (240 if key != "summary" else 4000)
                    ],
                )
            elif key == "budget_plan" and value is not None:
                row.budget_plan = _dump(body.budget_plan)  # type: ignore[arg-type]
            elif value is not None and key in {
                "workstreams",
                "milestones",
                "tasks",
                "role_assignments",
                "dependencies",
                "deliverables",
                "budget_gates",
                "approval_gates",
                "conditions",
                "implementation_risks",
                "assumptions",
                "roadmap",
            }:
                setattr(row, key, _dump(value))
        self._recompute_readiness(row)
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._plans.update(row)

    async def submit_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest | None,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.UNDER_REVIEW)
        row.submitted_by = actor_id
        row.submitted_at = utc_now()
        note = body.note if body else None
        self._append_review_event(
            row,
            action="submit_review",
            actor_id=actor_id,
            note=note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        async with transactional(self._session):
            return await self._plans.update(row)

    async def approve(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest | None,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.APPROVED)
        row.approved_by = actor_id
        row.approved_at = utc_now()
        note = body.note if body else None
        self._append_review_event(
            row,
            action="approve",
            actor_id=actor_id,
            note=note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        # Firewall: no MarketingPlan / specialist tasks / Campaign / Agent Run
        async with transactional(self._session):
            return await self._plans.update(row)

    async def reject(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.REJECTED)
        row.rejection_reason = sanitize_text(body.rejection_reason or body.note or "").strip()[
            :2000
        ]
        self._append_review_event(
            row,
            action="reject",
            actor_id=actor_id,
            note=body.note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        async with transactional(self._session):
            return await self._plans.update(row)

    async def return_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest | None,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.DRAFT)
        note = body.note if body else None
        self._append_review_event(
            row,
            action="return_draft",
            actor_id=actor_id,
            note=note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        async with transactional(self._session):
            return await self._plans.update(row)

    async def block(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.BLOCKED)
        row.block_reason = sanitize_text(body.block_reason or body.note or "").strip()[:2000]
        self._append_review_event(
            row,
            action="block",
            actor_id=actor_id,
            note=body.note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        async with transactional(self._session):
            return await self._plans.update(row)

    async def unblock(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest | None,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        if ImplementationPlanLifecycleStatus(row.lifecycle_status) != (
            ImplementationPlanLifecycleStatus.BLOCKED
        ):
            raise InvalidStateError("invalid_transition")
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.DRAFT)
        row.block_reason = None
        note = body.note if body else None
        self._append_review_event(
            row,
            action="unblock",
            actor_id=actor_id,
            note=note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        async with transactional(self._session):
            return await self._plans.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanReviewRequest | None,
    ) -> ImplementationPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        prev = str(row.lifecycle_status)
        self._transition(row, ImplementationPlanLifecycleStatus.ARCHIVED)
        note = body.note if body else None
        self._append_review_event(
            row,
            action="archive",
            actor_id=actor_id,
            note=note,
            previous=prev,
            new_status=str(row.lifecycle_status),
        )
        async with transactional(self._session):
            return await self._plans.update(row)

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        body: ImplementationPlanCreate,
    ) -> ImplementationPlanTable | None:
        previous = await self.get(owner_id, project_id, plan_id)
        if previous is None:
            return None
        self._transition(previous, ImplementationPlanLifecycleStatus.SUPERSEDED)
        self._append_review_event(
            previous,
            action="supersede",
            actor_id=actor_id,
            note=None,
            previous=str(previous.lifecycle_status),
            new_status=str(ImplementationPlanLifecycleStatus.SUPERSEDED),
        )
        body.supersedes_plan_id = previous.id
        async with transactional(self._session):
            await self._plans.update(previous)
        return await self.create(owner_id, project_id, body)

    async def handoff_preview(
        self, owner_id: UUID, project_id: UUID, plan_id: UUID
    ) -> ImplementationPlanHandoffPreview | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        return build_handoff_preview(
            plan_id=row.id,
            plan_version=row.version,
            readiness=row.readiness_status,
            readiness_reasons=list(row.readiness_reasons or []),
            tasks=row.tasks or [],
            role_assignments=row.role_assignments or [],
            dependencies=row.dependencies or [],
            budget_gates=row.budget_gates or [],
            approval_gates=row.approval_gates or [],
        )
