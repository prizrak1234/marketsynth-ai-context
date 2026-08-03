"""MarketingStrategy service (Commercial MVP P0.6).

Durable GTM strategy from approved GO/CONDITIONAL_GO BusinessVerdict.
Never creates MarketingPlan, Campaign, Agent Run, or execution approvals.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.marketing_strategy import MarketingStrategyTable
from app.db.repositories.business_verdicts import BusinessVerdictRepository
from app.db.repositories.marketing_strategies import MarketingStrategyRepository
from app.domain.marketing_strategy_engine import (
    assert_verdict_allows_strategy,
    compute_strategy_readiness,
    copy_verdict_conditions,
    validate_channel_mix,
    validate_offers_prices,
    validate_positioning,
)
from app.schemas.contracts import (
    BusinessVerdictLifecycleStatus,
    MarketingStrategyBuildDraftRequest,
    MarketingStrategyCreate,
    MarketingStrategyLifecycleStatus,
    MarketingStrategyOrigin,
    MarketingStrategyReadinessStatus,
    MarketingStrategyReviewRequest,
    MarketingStrategyUpdate,
    StrategyAssumptionPlanningStatus,
    StrategyAudienceSegment,
    StrategyBudgetLine,
    StrategyBudgetPolicy,
    StrategyChannelItem,
    StrategyChannelStatus,
    StrategyFunnelStage,
    StrategyHandoffStatus,
    StrategyMarketType,
    StrategyMetric,
    StrategyObjective,
    StrategyObjectivePriority,
    StrategyObjectiveStatus,
    StrategyOffer,
    StrategyOfferType,
    StrategyPlanningAssumption,
    StrategyPositioning,
    StrategyPriceMode,
    StrategySegmentPriority,
    StrategySegmentValidationStatus,
    StrategyStrategicRisk,
    StrategyVerdictConditionLink,
    VerdictKind,
    VerdictRiskProbability,
    VerdictRiskSeverity,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_LIFECYCLE: dict[
    MarketingStrategyLifecycleStatus, frozenset[MarketingStrategyLifecycleStatus]
] = {
    MarketingStrategyLifecycleStatus.DRAFT: frozenset(
        {
            MarketingStrategyLifecycleStatus.UNDER_REVIEW,
            MarketingStrategyLifecycleStatus.ARCHIVED,
            MarketingStrategyLifecycleStatus.SUPERSEDED,
        }
    ),
    MarketingStrategyLifecycleStatus.UNDER_REVIEW: frozenset(
        {
            MarketingStrategyLifecycleStatus.DRAFT,
            MarketingStrategyLifecycleStatus.APPROVED,
            MarketingStrategyLifecycleStatus.REJECTED,
            MarketingStrategyLifecycleStatus.SUPERSEDED,
        }
    ),
    MarketingStrategyLifecycleStatus.APPROVED: frozenset(
        {
            MarketingStrategyLifecycleStatus.SUPERSEDED,
            MarketingStrategyLifecycleStatus.ARCHIVED,
        }
    ),
    MarketingStrategyLifecycleStatus.REJECTED: frozenset(
        {
            MarketingStrategyLifecycleStatus.ARCHIVED,
            MarketingStrategyLifecycleStatus.SUPERSEDED,
        }
    ),
    MarketingStrategyLifecycleStatus.SUPERSEDED: frozenset(),
    MarketingStrategyLifecycleStatus.ARCHIVED: frozenset(),
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


class MarketingStrategyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._strategies = MarketingStrategyRepository(session)
        self._verdicts = BusinessVerdictRepository(session)

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _transition(
        self,
        row: MarketingStrategyTable,
        target: MarketingStrategyLifecycleStatus,
    ) -> None:
        current = MarketingStrategyLifecycleStatus(row.lifecycle_status)
        if target not in _LIFECYCLE.get(current, frozenset()):
            raise InvalidStateError("invalid_transition")
        if current == MarketingStrategyLifecycleStatus.APPROVED and target not in (
            MarketingStrategyLifecycleStatus.SUPERSEDED,
            MarketingStrategyLifecycleStatus.ARCHIVED,
        ):
            raise InvalidStateError("immutable_strategy")
        row.lifecycle_status = target
        row.updated_at = utc_now()

    def _append_review_event(
        self,
        row: MarketingStrategyTable,
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
                "business_verdict_id": str(row.business_verdict_id),
                "business_verdict_version": row.business_verdict_version,
                "evidence_snapshot_hash": row.evidence_snapshot_hash,
                "at": utc_now().isoformat(),
            }
        )
        meta["review_events"] = events
        meta["creates_marketing_plan"] = False
        meta["creates_campaign"] = False
        meta["creates_execution_approval"] = False
        meta["creates_agent_run"] = False
        row.metadata_json = meta

    def _validate_sections(self, body: MarketingStrategyCreate | MarketingStrategyUpdate) -> None:
        positioning = getattr(body, "positioning", None)
        if positioning is not None:
            validate_positioning(positioning)
        offers = getattr(body, "offers", None)
        if offers is not None:
            validate_offers_prices(list(offers))
        channels = getattr(body, "channel_strategy", None)
        if channels is not None:
            validate_channel_mix(list(channels))

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: MarketingStrategyCreate,
    ) -> MarketingStrategyTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        verdict = await self._verdicts.get_by_id_for_owner(
            body.business_verdict_id, owner_id, project_id
        )
        if verdict is None:
            raise InvalidStateError("verdict_not_found")
        if int(verdict.version) != int(body.business_verdict_version):
            raise InvalidStateError("verdict_version_mismatch")
        if BusinessVerdictLifecycleStatus(verdict.lifecycle_status) == (
            BusinessVerdictLifecycleStatus.SUPERSEDED
        ):
            raise InvalidStateError("verdict_superseded")
        assert_verdict_allows_strategy(verdict)

        conditions = list(body.verdict_conditions)
        if VerdictKind(verdict.verdict_type) == VerdictKind.CONDITIONAL_GO:
            # Preserve Verdict condition authority — merge references
            copied = copy_verdict_conditions(verdict.conditions or [])
            by_id = {c.verdict_condition_id: c for c in copied}
            for c in conditions:
                by_id[c.verdict_condition_id] = c
            conditions = list(by_id.values())
            if not conditions and (verdict.conditions or []):
                conditions = copied

        self._validate_sections(body)
        readiness = compute_strategy_readiness(
            verdict_type=VerdictKind(verdict.verdict_type),
            objectives=list(body.objectives),
            segments=list(body.audience_segments),
            positioning=body.positioning,
            offers=list(body.offers),
            channels=list(body.channel_strategy),
            metrics=list(body.metrics),
            verdict_conditions=conditions,
            assumptions=list(body.assumptions),
        )

        version = await self._strategies.next_version(owner_id, project_id)
        row = MarketingStrategyTable(
            owner_id=owner_id,
            project_id=project_id,
            business_verdict_id=verdict.id,
            business_verdict_version=verdict.version,
            business_verdict_type=VerdictKind(verdict.verdict_type),
            evidence_snapshot_id=verdict.evidence_snapshot_id,
            evidence_snapshot_hash=verdict.evidence_snapshot_hash,
            version=version,
            lifecycle_status=MarketingStrategyLifecycleStatus.DRAFT,
            strategy_origin=body.strategy_origin,
            title=sanitize_text(body.title).strip()[:240],
            executive_summary=sanitize_text(body.executive_summary).strip()[:4000],
            primary_business_objective=sanitize_text(
                body.primary_business_objective
            ).strip()[:2000],
            strategic_horizon=sanitize_text(body.strategic_horizon).strip()[:240],
            objectives=_dump(list(body.objectives)),
            audience_segments=_dump(list(body.audience_segments)),
            positioning=_dump(body.positioning),
            offers=_dump(list(body.offers)),
            channel_strategy=_dump(list(body.channel_strategy)),
            funnel=_dump(list(body.funnel)),
            asset_plan=_dump(list(body.asset_plan)),
            budget_policy=_dump(body.budget_policy),
            metrics=_dump(list(body.metrics)),
            verdict_conditions=_dump(conditions),
            strategic_risks=_dump(list(body.strategic_risks)),
            assumptions=_dump(list(body.assumptions)),
            execution_constraints=[
                sanitize_text(x).strip()[:500] for x in body.execution_constraints
            ],
            readiness_status=readiness,
            supersedes_strategy_id=body.supersedes_strategy_id,
            related_marketing_plan_ids=[],
            handoff_status=StrategyHandoffStatus.NOT_STARTED,
            metadata_json={
                "creates_marketing_plan": False,
                "creates_campaign": False,
                "creates_execution_approval": False,
                "creates_publication_approval": False,
                "creates_agent_run": False,
                "review_events": [],
            },
        )
        async with transactional(self._session):
            return await self._strategies.create(row)

    async def build_deterministic_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: MarketingStrategyBuildDraftRequest,
    ) -> MarketingStrategyTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        verdict = await self._verdicts.get_by_id_for_owner(
            body.business_verdict_id, owner_id, project_id
        )
        if verdict is None:
            raise InvalidStateError("verdict_not_found")
        assert_verdict_allows_strategy(verdict)
        is_cond = VerdictKind(verdict.verdict_type) == VerdictKind.CONDITIONAL_GO
        conditions = copy_verdict_conditions(verdict.conditions or [])
        segment = StrategyAudienceSegment(
            id="seg_primary",
            name="Primary audience (hypothesis from Verdict)",
            market_type=StrategyMarketType.UNKNOWN,
            problem="Confirmed commercial problem space from approved Verdict",
            desired_outcome="Measurable go-to-market traction under Verdict constraints",
            evidence_strength=verdict.confidence_level,
            priority=StrategySegmentPriority.PRIMARY,
            validation_status=(
                StrategySegmentValidationStatus.EVIDENCE_SUPPORTED_HYPOTHESIS
                if is_cond
                else StrategySegmentValidationStatus.CONFIRMED
            ),
        )
        positioning = StrategyPositioning(
            target_customer=segment.name,
            category="Local / professional service go-to-market",
            core_problem=segment.problem,
            alternative_used_today="Status-quo channels without evidence-backed offer packaging",
            primary_differentiation=(
                "Offer framed by approved Evidence Snapshot and Verdict constraints, "
                "not slogan claims"
            ),
            proof=verdict.supporting_evidence_summary,
            reason_to_believe=verdict.executive_rationale[:500],
            key_message=verdict.executive_conclusion[:500],
            positioning_risks=["Generic brand wording rejected by validation"],
        )
        offer = StrategyOffer(
            id="offer_core",
            offer_type=StrategyOfferType.VALIDATION if is_cond else StrategyOfferType.CORE,
            name="Core / validation offer",
            target_segment_id=segment.id,
            customer_problem=segment.problem,
            promised_outcome=segment.desired_outcome,
            price_model=StrategyPriceMode.UNKNOWN if is_cond else StrategyPriceMode.RANGE,
            price_value_or_range=None if is_cond else "Requires pricing Evidence before exact",
            validation_status=segment.validation_status,
            call_to_action="Book consultation / request proposal",
        )
        channels = [
            StrategyChannelItem(
                channel="content",
                role="Demand education",
                funnel_stage="interest",
                target_segment_ids=[segment.id],
                status=StrategyChannelStatus.RECOMMENDED,
                evidence_basis="Verdict supporting Evidence",
            ),
            StrategyChannelItem(
                channel="direct_sales",
                role="Qualification conversations",
                funnel_stage="qualification",
                target_segment_ids=[segment.id],
                status=StrategyChannelStatus.TEST if is_cond else StrategyChannelStatus.RECOMMENDED,
            ),
            StrategyChannelItem(
                channel="paid_search",
                role="Acquisition test",
                funnel_stage="awareness",
                target_segment_ids=[segment.id],
                status=StrategyChannelStatus.CONDITIONAL if is_cond else StrategyChannelStatus.TEST,
                risk="Budget unvalidated",
            ),
        ]
        objectives = [
            StrategyObjective(
                id="obj_1",
                title="Validate or acquire first qualified demand",
                business_outcome=verdict.primary_business_implication[:500],
                marketing_outcome="Pipeline of qualified conversations",
                priority=StrategyObjectivePriority.CRITICAL,
                timeframe="30-90 days",
                success_metric="Qualified conversations / validated price signals",
                linked_verdict_criterion=verdict.verdict_type,
                status=StrategyObjectiveStatus.PROPOSED,
            )
        ]
        funnel = [
            StrategyFunnelStage(
                stage="awareness",
                customer_action="Discovers offer category",
                business_action="Publish evidence-aligned content",
                channel="content",
                metric="Reach quality",
                linked_objective_ids=["obj_1"],
            ),
            StrategyFunnelStage(
                stage="conversion",
                customer_action="Requests consult / proposal",
                business_action="Qualify and close validation offer",
                channel="direct_sales",
                metric="Qualified requests",
                linked_objective_ids=["obj_1"],
            ),
        ]
        metrics = [
            StrategyMetric(
                id="met_1",
                name="Qualified lead conversations",
                category="validation" if is_cond else "marketing",
                purpose="Decide continue / pivot based on demand quality",
                decision_threshold="Minimum viable conversation volume in horizon",
                action_if_missed="Reopen Verdict / Investigation path",
                linked_objective_ids=["obj_1"],
            )
        ]
        create = MarketingStrategyCreate(
            business_verdict_id=verdict.id,
            business_verdict_version=verdict.version,
            title=f"GTM Strategy · Verdict v{verdict.version}",
            executive_summary=(
                f"Deterministic draft from approved {verdict.verdict_type} Verdict. "
                f"Evidence snapshot {verdict.evidence_snapshot_hash[:12]}…. "
                "MarketingStrategy ≠ MarketingPlan; no execution authorization."
            ),
            primary_business_objective=verdict.primary_business_implication[:2000],
            strategic_horizon="90 days",
            objectives=objectives,
            audience_segments=[segment],
            positioning=positioning,
            offers=[offer],
            channel_strategy=channels,
            funnel=funnel,
            asset_plan=[],
            budget_policy=StrategyBudgetPolicy(
                acquisition_testing=StrategyBudgetLine(
                    category="acquisition_testing",
                    amount_mode=StrategyPriceMode.UNKNOWN,
                    rationale="Test budget TBD — no guaranteed ROI",
                    requires_approval=True,
                ),
                no_guaranteed_roi=True,
                notes="Budget policy only — not budget approval",
            ),
            metrics=metrics,
            verdict_conditions=conditions,
            strategic_risks=[
                StrategyStrategicRisk(
                    id="risk_1",
                    title="Condition / Evidence drift",
                    probability=VerdictRiskProbability.MEDIUM,
                    severity=VerdictRiskSeverity.HIGH if is_cond else VerdictRiskSeverity.MEDIUM,
                    business_impact="Commercial loss if conditions ignored",
                    strategy_impact="Planning readiness remains conditional/blocked",
                    mitigation="Keep Verdict conditions authoritative",
                )
            ],
            assumptions=[
                StrategyPlanningAssumption(
                    id="asm_1",
                    statement="Approved Verdict remains valid for this planning horizon",
                    confidence=verdict.confidence_level,
                    impact_if_false="Strategy must be superseded after new Verdict",
                    status=StrategyAssumptionPlanningStatus.ACCEPTED_FOR_PLANNING,
                )
            ],
            execution_constraints=[
                "No Campaign creation",
                "No MarketingPlan auto-create",
                "No execution/publication approval",
            ],
            strategy_origin=MarketingStrategyOrigin.DETERMINISTIC,
            supersedes_strategy_id=body.supersedes_strategy_id,
        )
        return await self.create(owner_id, project_id, create)

    async def list_strategies(
        self, owner_id: UUID, project_id: UUID, **filters: Any
    ) -> list[MarketingStrategyTable] | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._strategies.list_for_project(owner_id, project_id, **filters)

    async def get(
        self, owner_id: UUID, project_id: UUID, strategy_id: UUID
    ) -> MarketingStrategyTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._strategies.get_by_id_for_owner(strategy_id, owner_id, project_id)

    async def get_latest(
        self, owner_id: UUID, project_id: UUID
    ) -> MarketingStrategyTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        approved = await self._strategies.latest_approved(owner_id, project_id)
        if approved is not None:
            return approved
        return await self._strategies.latest_any(owner_id, project_id)

    async def update_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        body: MarketingStrategyUpdate,
    ) -> MarketingStrategyTable | None:
        row = await self.get(owner_id, project_id, strategy_id)
        if row is None:
            return None
        if MarketingStrategyLifecycleStatus(row.lifecycle_status) != (
            MarketingStrategyLifecycleStatus.DRAFT
        ):
            raise InvalidStateError("immutable_strategy")
        self._validate_sections(body)
        if body.title is not None:
            row.title = sanitize_text(body.title).strip()[:240]
        if body.executive_summary is not None:
            row.executive_summary = sanitize_text(body.executive_summary).strip()[:4000]
        if body.primary_business_objective is not None:
            row.primary_business_objective = sanitize_text(
                body.primary_business_objective
            ).strip()[:2000]
        if body.strategic_horizon is not None:
            row.strategic_horizon = sanitize_text(body.strategic_horizon).strip()[:240]
        if body.objectives is not None:
            row.objectives = _dump(list(body.objectives))
        if body.audience_segments is not None:
            row.audience_segments = _dump(list(body.audience_segments))
        if body.positioning is not None:
            row.positioning = _dump(body.positioning)
        if body.offers is not None:
            row.offers = _dump(list(body.offers))
        if body.channel_strategy is not None:
            row.channel_strategy = _dump(list(body.channel_strategy))
        if body.funnel is not None:
            row.funnel = _dump(list(body.funnel))
        if body.asset_plan is not None:
            row.asset_plan = _dump(list(body.asset_plan))
        if body.budget_policy is not None:
            row.budget_policy = _dump(body.budget_policy)
        if body.metrics is not None:
            row.metrics = _dump(list(body.metrics))
        if body.verdict_conditions is not None:
            row.verdict_conditions = _dump(list(body.verdict_conditions))
        if body.strategic_risks is not None:
            row.strategic_risks = _dump(list(body.strategic_risks))
        if body.assumptions is not None:
            row.assumptions = _dump(list(body.assumptions))
        if body.execution_constraints is not None:
            row.execution_constraints = [
                sanitize_text(x).strip()[:500] for x in body.execution_constraints
            ]
        row.readiness_status = compute_strategy_readiness(
            verdict_type=VerdictKind(row.business_verdict_type),
            objectives=row.objectives or [],
            segments=row.audience_segments or [],
            positioning=row.positioning or {},
            offers=row.offers or [],
            channels=row.channel_strategy or [],
            metrics=row.metrics or [],
            verdict_conditions=[
                StrategyVerdictConditionLink.model_validate(x)
                for x in (row.verdict_conditions or [])
            ],
            assumptions=row.assumptions or [],
        )
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._strategies.update(row)

    async def submit_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        actor_id: UUID,
        body: MarketingStrategyReviewRequest | None = None,
    ) -> MarketingStrategyTable | None:
        row = await self.get(owner_id, project_id, strategy_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, MarketingStrategyLifecycleStatus.UNDER_REVIEW)
        row.submitted_by = actor_id
        row.submitted_at = utc_now()
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="submit_review",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=MarketingStrategyLifecycleStatus.UNDER_REVIEW.value,
        )
        async with transactional(self._session):
            return await self._strategies.update(row)

    async def approve(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        actor_id: UUID,
        body: MarketingStrategyReviewRequest | None = None,
    ) -> MarketingStrategyTable | None:
        row = await self.get(owner_id, project_id, strategy_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, MarketingStrategyLifecycleStatus.APPROVED)
        row.approved_by = actor_id
        row.approved_at = utc_now()
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="approve",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=MarketingStrategyLifecycleStatus.APPROVED.value,
        )
        async with transactional(self._session):
            return await self._strategies.update(row)

    async def reject(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        actor_id: UUID,
        body: MarketingStrategyReviewRequest,
    ) -> MarketingStrategyTable | None:
        row = await self.get(owner_id, project_id, strategy_id)
        if row is None:
            return None
        reason = sanitize_text(body.rejection_reason or body.note or "").strip()
        if not reason:
            raise InvalidStateError("invalid_transition")
        previous = str(row.lifecycle_status)
        self._transition(row, MarketingStrategyLifecycleStatus.REJECTED)
        row.rejection_reason = reason[:2000]
        self._append_review_event(
            row,
            action="reject",
            actor_id=actor_id,
            note=reason,
            previous=previous,
            new_status=MarketingStrategyLifecycleStatus.REJECTED.value,
        )
        async with transactional(self._session):
            return await self._strategies.update(row)

    async def return_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        actor_id: UUID,
        body: MarketingStrategyReviewRequest | None = None,
    ) -> MarketingStrategyTable | None:
        row = await self.get(owner_id, project_id, strategy_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, MarketingStrategyLifecycleStatus.DRAFT)
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="return_draft",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=MarketingStrategyLifecycleStatus.DRAFT.value,
        )
        async with transactional(self._session):
            return await self._strategies.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        actor_id: UUID,
        body: MarketingStrategyReviewRequest | None = None,
    ) -> MarketingStrategyTable | None:
        row = await self.get(owner_id, project_id, strategy_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, MarketingStrategyLifecycleStatus.ARCHIVED)
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="archive",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=MarketingStrategyLifecycleStatus.ARCHIVED.value,
        )
        async with transactional(self._session):
            return await self._strategies.update(row)

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        strategy_id: UUID,
        actor_id: UUID,
        body: MarketingStrategyCreate,
    ) -> MarketingStrategyTable | None:
        prev = await self.get(owner_id, project_id, strategy_id)
        if prev is None:
            return None
        create_body = body.model_copy(update={"supersedes_strategy_id": prev.id})
        new_row = await self.create(owner_id, project_id, create_body)
        if new_row is None:
            return None
        prev = await self.get(owner_id, project_id, strategy_id)
        if prev is None:
            return new_row
        previous = str(prev.lifecycle_status)
        self._transition(prev, MarketingStrategyLifecycleStatus.SUPERSEDED)
        self._append_review_event(
            prev,
            action="superseded_by",
            actor_id=actor_id,
            note=str(new_row.id),
            previous=previous,
            new_status=MarketingStrategyLifecycleStatus.SUPERSEDED.value,
        )
        async with transactional(self._session):
            await self._strategies.update(prev)
        return new_row
