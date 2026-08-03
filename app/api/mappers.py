"""Map SQLModel rows to Pydantic contracts for API responses."""

from __future__ import annotations

from uuid import UUID

from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.agent_run import AgentRunTable
from app.db.models.campaign import CampaignTable
from app.db.models.campaign_plan_drafts import CampaignPlanDraftTable
from app.db.models.event_outbox import EventOutboxTable
from app.db.models.llm import LLMRequestTable, LLMResponseTable
from app.db.models.marketing import (
    ContentAssetTable,
    ContentAssetVersionTable,
    MarketingBriefTable,
    PublicationPackageTable,
)
from app.db.models.media import (
    MediaAssetTable,
    MediaBriefTable,
    MediaGenerationJobTable,
)
from app.db.models.marketing_plan import MarketingPlanTable, MarketingPlanVersionTable
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.db.models.marketing_specialist_output import (
    MarketingSpecialistOutputTable,
    MarketingSpecialistOutputVersionTable,
)
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.marketing_funnels import (
    FunnelStepAssetLinkTable,
    MarketingFunnelStepTable,
    MarketingFunnelTable,
)
from app.db.models.marketing_skill_run import MarketingSkillRunTable
from app.db.models.marketing_tool_call import MarketingToolCallTable
from app.db.models.project import ProjectTable
from app.db.models.project_brief import ProjectBriefTable
from app.db.models.investigation import InvestigationTable
from app.db.models.source import InvestigationSourceLinkTable, SourceTable
from app.db.models.evidence import EvidenceSourceLinkTable, InvestigationEvidenceTable
from app.db.models.business_verdict import (
    BusinessVerdictEvidenceLinkTable,
    BusinessVerdictEvidenceSnapshotTable,
    BusinessVerdictTable,
)
from app.db.models.marketing_strategy import MarketingStrategyTable
from app.db.models.implementation_plan import ImplementationPlanTable
from app.db.models.project_webhook import ProjectWebhookTable
from app.db.models.publication_delivery_log import PublicationDeliveryLogTable
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.scenario_wizard_run import ScenarioWizardRunTable
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.db.models.task import TaskTable
from app.db.models.beta_feedback_report import BetaFeedbackReportTable
from app.db.models.user import UserTable
from app.db.models.webhook_delivery_log import WebhookDeliveryLogTable
from app.db.repositories.funnel_step_asset_links import FunnelStepAssetLinkRow
from app.executors.engine_resolver import ExecutionEngine
from app.marketing.contracts import (
    CampaignPlanDraft,
    ContentAsset,
    ContentAssetVersion,
    MarketingBrief,
    MarketingCampaign,
    PublicationPackage,
)
from app.marketing.media_contracts import MediaAsset, MediaBrief
from app.media_generation.contracts import MediaGenerationJob
from app.marketing.funnel_contracts import (
    FunnelStepAssetLink,
    FunnelStepLinkedAsset,
    MarketingFunnel,
    MarketingFunnelStep,
)
from app.publishing.contracts import (
    PublicationDeliveryLog,
    PublicationJob,
    PublishingChannel,
)
from app.publishing_foundation.contracts import (
    PublicationPackageJob,
    PublicationPackageJobScheduleStatus,
    PublishingFoundationChannel,
)
from app.beta.safe_feedback_context import sanitize_feedback_context
from app.schemas.contracts import (
    AgentChatMessage,
    BetaFeedbackReport,
    AgentChatSession,
    Agent,
    AgentCapability,
    AgentRun,
    Campaign,
    CampaignStatus,
    EventOutbox,
    LLMRequest,
    LLMResponse,
    MarketingExecutionMode,
    MarketingPlan,
    MarketingPlanExecutionRun,
    MarketingPlanExecutionStatus,
    MarketingPlanStatus,
    MarketingPlanVersion,
    MarketingSpecialistOutput,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistOutputVersion,
    MarketingSpecialistType,
    MarketingSkillRun,
    MarketingSkillRunStatus,
    MarketingSkillType,
    MarketingToolCall,
    MarketingToolCallStatus,
    MarketingToolType,
    MemoryItem,
    Project,
    ProjectBrief,
    ProjectBriefReadinessStatus,
    ProjectBriefStatus,
    Investigation,
    InvestigationReadinessStatus,
    InvestigationStageId,
    InvestigationStageState,
    InvestigationStatus,
    InvestigationSourceLink,
    InvestigationSourceLinkStatus,
    Source,
    SourceCapability,
    SourceFreshnessStatus,
    SourceProvenanceType,
    SourceReliabilityLevel,
    SourceStatus,
    SourceType,
    Evidence,
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceInvestigationArea,
    EvidenceLifecycleStatus,
    EvidenceLocatorType,
    EvidenceMateriality,
    EvidencePreparedByType,
    EvidenceSourceLink,
    EvidenceSourceStance,
    EvidenceType,
    BusinessVerdict,
    BusinessVerdictConfidenceLevel,
    BusinessVerdictEvidenceLink,
    BusinessVerdictEvidenceRole,
    BusinessVerdictEvidenceSnapshot,
    BusinessVerdictLifecycleStatus,
    BusinessVerdictPreparedByType,
    BusinessVerdictStrategyEligibility,
    VerdictAssumption,
    VerdictChangeTrigger,
    VerdictCondition,
    VerdictCriticalRisk,
    VerdictFinding,
    VerdictKind,
    VerdictReadinessStatus,
    MarketingStrategy as MarketingStrategyContract,
    MarketingStrategyLifecycleStatus,
    MarketingStrategyOrigin,
    MarketingStrategyReadinessStatus,
    StrategyHandoffStatus,
    StrategyPositioning,
    StrategyBudgetPolicy,
    StrategyObjective,
    StrategyAudienceSegment,
    StrategyOffer,
    StrategyChannelItem,
    StrategyFunnelStage,
    StrategyAssetItem,
    StrategyMetric,
    StrategyVerdictConditionLink,
    StrategyStrategicRisk,
    StrategyPlanningAssumption,
    ImplementationPlan as ImplementationPlanContract,
    ImplementationPlanLifecycleStatus,
    ImplementationPlanOrigin,
    ImplementationPlanReadinessStatus,
    ImplWorkstream,
    ImplMilestone,
    ImplTask,
    ImplRoleAssignment,
    ImplDependency,
    ImplDeliverable,
    ImplBudgetPlan,
    ImplBudgetGate,
    ImplApprovalGate,
    ImplConditionRef,
    ImplRisk,
    ImplAssumption,
    ImplRoadmapPhase,
    ScenarioWizardRun,
    ScenarioWizardRunStatus,
    Task,
    User,
    WebhookDeliveryLog,
)
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_plan_service import MarketingPlanService
from app.services.scenario_wizard_service import ScenarioWizardService
from app.schemas.crud import AgentRunExecuteResponse, ProjectWebhookRead


def user_to_contract(row: UserTable) -> User:
    return User(
        id=row.id,
        telegram_id=row.telegram_id,
        email=row.email,
        display_name=row.display_name,
        role=row.role,
        is_active=row.is_active,
        beta_access_status=row.beta_access_status,
        beta_notes=row.beta_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def project_to_contract(row: ProjectTable) -> Project:
    return Project(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
        config=dict(row.config or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def project_brief_to_contract(row: ProjectBriefTable) -> ProjectBrief:
    return ProjectBrief(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        version=row.version,
        status=ProjectBriefStatus(row.status),
        language=row.language,
        project_basics=row.project_basics,
        product=row.product,
        market=row.market,
        audience=row.audience,
        economics=row.economics,
        materials_summary=row.materials_summary,
        assumptions=list(row.assumptions or []),
        missing_data=list(row.missing_data or []),
        readiness_status=ProjectBriefReadinessStatus(row.readiness_status),
        readiness_reasons=list(row.readiness_reasons or []),
        input_fingerprint=row.input_fingerprint,
        supersedes_brief_id=row.supersedes_brief_id,
        submitted_at=row.submitted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def investigation_to_contract(row: InvestigationTable) -> Investigation:
    return Investigation(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        project_brief_id=row.project_brief_id,
        project_brief_version=row.project_brief_version,
        input_fingerprint=row.input_fingerprint,
        version=row.version,
        status=InvestigationStatus(row.status),
        current_stage=InvestigationStageId(row.current_stage),
        stages=[
            InvestigationStageState.model_validate(item) for item in (row.stages or [])
        ],
        readiness_status=InvestigationReadinessStatus(row.readiness_status),
        readiness_reasons=list(row.readiness_reasons or []),
        started_at=row.started_at,
        completed_at=row.completed_at,
        blocked_reason=row.blocked_reason,
        supersedes_investigation_id=row.supersedes_investigation_id,
        metadata=dict(row.metadata_json or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def source_to_contract(row: SourceTable) -> Source:
    return Source(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        source_type=SourceType(row.source_type),
        provenance_type=SourceProvenanceType(row.provenance_type),
        title=row.title,
        origin=row.origin or "",
        url=row.url,
        domain=row.domain,
        publisher=row.publisher,
        language=row.language,
        country=row.country,
        published_at=row.published_at,
        captured_at=row.captured_at,
        accessed_at=row.accessed_at,
        freshness_status=SourceFreshnessStatus(row.freshness_status),
        reliability_level=SourceReliabilityLevel(row.reliability_level),
        status=SourceStatus(row.status),
        fingerprint=row.fingerprint,
        content_hash=row.content_hash,
        etag=row.etag,
        version=row.version,
        supersedes_source_id=row.supersedes_source_id,
        license_type=row.license_type,
        capabilities=[
            SourceCapability(item) for item in (row.capabilities or [])
        ],
        reusable_within_project=bool(row.reusable_within_project),
        metadata=dict(row.metadata_json or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def investigation_source_link_to_contract(
    row: InvestigationSourceLinkTable,
) -> InvestigationSourceLink:
    return InvestigationSourceLink(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        investigation_id=row.investigation_id,
        source_id=row.source_id,
        purpose=row.purpose,
        investigation_area=row.investigation_area,
        notes=row.notes,
        status=InvestigationSourceLinkStatus(row.status),
        added_by=row.added_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def evidence_source_link_to_contract(row: EvidenceSourceLinkTable) -> EvidenceSourceLink:
    return EvidenceSourceLink(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        investigation_id=row.investigation_id,
        evidence_id=row.evidence_id,
        source_id=row.source_id,
        stance=EvidenceSourceStance(row.stance),
        locator_type=EvidenceLocatorType(row.locator_type),
        locator_value=row.locator_value,
        excerpt=row.excerpt,
        excerpt_hash=row.excerpt_hash,
        note=row.note,
        added_by=row.added_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def evidence_to_contract(
    row: InvestigationEvidenceTable,
    links: list[EvidenceSourceLinkTable] | None = None,
) -> Evidence:
    return Evidence(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        investigation_id=row.investigation_id,
        claim=row.claim,
        evidence_type=EvidenceType(row.evidence_type),
        investigation_area=EvidenceInvestigationArea(row.investigation_area),
        lifecycle_status=EvidenceLifecycleStatus(row.lifecycle_status),
        assessment_state=EvidenceAssessmentState(row.assessment_state),
        confidence_level=EvidenceConfidenceLevel(row.confidence_level),
        materiality=EvidenceMateriality(row.materiality),
        review_note=row.review_note,
        why_it_matters=row.why_it_matters,
        recommended_source_type=row.recommended_source_type,
        prepared_by_type=EvidencePreparedByType(row.prepared_by_type),
        prepared_by_reference=row.prepared_by_reference,
        version=row.version,
        input_fingerprint=row.input_fingerprint,
        supersedes_evidence_id=row.supersedes_evidence_id,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
        source_links=[
            evidence_source_link_to_contract(link) for link in (links or [])
        ],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def business_verdict_snapshot_to_contract(
    row: BusinessVerdictEvidenceSnapshotTable,
) -> BusinessVerdictEvidenceSnapshot:
    from uuid import UUID as _UUID

    evidence_ids = []
    for raw in row.evidence_ids or []:
        evidence_ids.append(raw if isinstance(raw, _UUID) else _UUID(str(raw)))
    evidence_versions: dict[str, int] = {
        str(k): int(v) for k, v in (row.evidence_versions or {}).items()
    }
    return BusinessVerdictEvidenceSnapshot(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        investigation_id=row.investigation_id,
        snapshot_hash=row.snapshot_hash,
        evidence_ids=evidence_ids,
        evidence_versions=evidence_versions,
        accepted_evidence_count=row.accepted_evidence_count,
        missing_critical_count=row.missing_critical_count,
        conflicting_critical_count=row.conflicting_critical_count,
        outdated_critical_count=row.outdated_critical_count,
        area_coverage={str(k): int(v) for k, v in (row.area_coverage or {}).items()},
        readiness_status=VerdictReadinessStatus(row.readiness_status),
        verdict_readiness_contribution=row.verdict_readiness_contribution,
        created_at=row.created_at,
    )


def business_verdict_link_to_contract(
    row: BusinessVerdictEvidenceLinkTable,
) -> BusinessVerdictEvidenceLink:
    return BusinessVerdictEvidenceLink(
        id=row.id,
        verdict_id=row.verdict_id,
        evidence_id=row.evidence_id,
        evidence_version=row.evidence_version,
        role=BusinessVerdictEvidenceRole(row.role),
        decision_criterion=row.decision_criterion,
        materiality_at_snapshot=EvidenceMateriality(row.materiality_at_snapshot),
        assessment_state_at_snapshot=EvidenceAssessmentState(
            row.assessment_state_at_snapshot
        ),
        confidence_at_snapshot=EvidenceConfidenceLevel(row.confidence_at_snapshot),
        note=row.note,
        owner_id=row.owner_id,
        project_id=row.project_id,
        created_at=row.created_at,
    )


def business_verdict_to_contract(
    row: BusinessVerdictTable,
    *,
    links: list[BusinessVerdictEvidenceLinkTable] | None = None,
    snapshot: BusinessVerdictEvidenceSnapshotTable | None = None,
    strategy_eligibility: BusinessVerdictStrategyEligibility | None = None,
) -> BusinessVerdict:
    from app.domain.business_verdict_engine import compute_strategy_eligibility

    eligibility = strategy_eligibility or compute_strategy_eligibility(
        verdict_type=VerdictKind(row.verdict_type),
        lifecycle_status=BusinessVerdictLifecycleStatus(row.lifecycle_status),
        conditions=row.conditions or [],
    )
    return BusinessVerdict(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        investigation_id=row.investigation_id,
        investigation_version=row.investigation_version,
        project_brief_id=row.project_brief_id,
        project_brief_version=row.project_brief_version,
        version=row.version,
        verdict_type=VerdictKind(row.verdict_type),
        lifecycle_status=BusinessVerdictLifecycleStatus(row.lifecycle_status),
        confidence_level=BusinessVerdictConfidenceLevel(row.confidence_level),
        evidence_snapshot_id=row.evidence_snapshot_id,
        evidence_snapshot_hash=row.evidence_snapshot_hash,
        executive_conclusion=row.executive_conclusion,
        executive_rationale=row.executive_rationale,
        primary_business_implication=row.primary_business_implication,
        recommended_next_action=row.recommended_next_action,
        supporting_evidence_summary=row.supporting_evidence_summary,
        counter_evidence_summary=row.counter_evidence_summary,
        conditions=[VerdictCondition.model_validate(x) for x in (row.conditions or [])],
        critical_risks=[
            VerdictCriticalRisk.model_validate(x) for x in (row.critical_risks or [])
        ],
        assumptions=[
            VerdictAssumption.model_validate(x) for x in (row.assumptions or [])
        ],
        change_triggers=[
            VerdictChangeTrigger.model_validate(x) for x in (row.change_triggers or [])
        ],
        findings=[VerdictFinding.model_validate(x) for x in (row.findings or [])],
        readiness_snapshot=VerdictReadinessStatus(row.readiness_snapshot),
        prepared_by_type=BusinessVerdictPreparedByType(row.prepared_by_type),
        prepared_by_reference=row.prepared_by_reference,
        submitted_by=row.submitted_by,
        submitted_at=row.submitted_at,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        rejection_reason=row.rejection_reason,
        supersedes_verdict_id=row.supersedes_verdict_id,
        strategy_eligibility=eligibility,
        evidence_links=[
            business_verdict_link_to_contract(link) for link in (links or [])
        ],
        evidence_snapshot=(
            business_verdict_snapshot_to_contract(snapshot) if snapshot else None
        ),
        creates_strategy=False,
        creates_execution_approval=False,
        creates_publication_approval=False,
        creates_agent_run=False,
        is_execution_approval=False,
        is_readiness=False,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_strategy_to_contract(row: MarketingStrategyTable) -> MarketingStrategyContract:
    from uuid import UUID as _UUID

    plan_ids = []
    for raw in row.related_marketing_plan_ids or []:
        plan_ids.append(raw if isinstance(raw, _UUID) else _UUID(str(raw)))
    return MarketingStrategyContract(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        business_verdict_id=row.business_verdict_id,
        business_verdict_version=row.business_verdict_version,
        business_verdict_type=VerdictKind(row.business_verdict_type),
        evidence_snapshot_id=row.evidence_snapshot_id,
        evidence_snapshot_hash=row.evidence_snapshot_hash,
        version=row.version,
        lifecycle_status=MarketingStrategyLifecycleStatus(row.lifecycle_status),
        strategy_origin=MarketingStrategyOrigin(row.strategy_origin),
        title=row.title,
        executive_summary=row.executive_summary,
        primary_business_objective=row.primary_business_objective,
        strategic_horizon=row.strategic_horizon,
        objectives=[StrategyObjective.model_validate(x) for x in (row.objectives or [])],
        audience_segments=[
            StrategyAudienceSegment.model_validate(x) for x in (row.audience_segments or [])
        ],
        positioning=StrategyPositioning.model_validate(row.positioning or {}),
        offers=[StrategyOffer.model_validate(x) for x in (row.offers or [])],
        channel_strategy=[
            StrategyChannelItem.model_validate(x) for x in (row.channel_strategy or [])
        ],
        funnel=[StrategyFunnelStage.model_validate(x) for x in (row.funnel or [])],
        asset_plan=[StrategyAssetItem.model_validate(x) for x in (row.asset_plan or [])],
        budget_policy=StrategyBudgetPolicy.model_validate(row.budget_policy or {}),
        metrics=[StrategyMetric.model_validate(x) for x in (row.metrics or [])],
        verdict_conditions=[
            StrategyVerdictConditionLink.model_validate(x)
            for x in (row.verdict_conditions or [])
        ],
        strategic_risks=[
            StrategyStrategicRisk.model_validate(x) for x in (row.strategic_risks or [])
        ],
        assumptions=[
            StrategyPlanningAssumption.model_validate(x) for x in (row.assumptions or [])
        ],
        execution_constraints=[str(x) for x in (row.execution_constraints or [])],
        readiness_status=MarketingStrategyReadinessStatus(row.readiness_status),
        submitted_by=row.submitted_by,
        submitted_at=row.submitted_at,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        rejection_reason=row.rejection_reason,
        supersedes_strategy_id=row.supersedes_strategy_id,
        related_marketing_plan_ids=plan_ids,
        handoff_status=StrategyHandoffStatus(row.handoff_status),
        creates_marketing_plan=False,
        creates_campaign=False,
        creates_execution_approval=False,
        creates_publication_approval=False,
        creates_agent_run=False,
        is_marketing_plan=False,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def implementation_plan_to_contract(row: ImplementationPlanTable) -> ImplementationPlanContract:
    return ImplementationPlanContract(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        marketing_strategy_id=row.marketing_strategy_id,
        marketing_strategy_version=row.marketing_strategy_version,
        business_verdict_id=row.business_verdict_id,
        business_verdict_version=row.business_verdict_version,
        evidence_snapshot_id=row.evidence_snapshot_id,
        evidence_snapshot_hash=row.evidence_snapshot_hash,
        version=row.version,
        lifecycle_status=ImplementationPlanLifecycleStatus(row.lifecycle_status),
        plan_origin=ImplementationPlanOrigin(row.plan_origin),
        title=row.title,
        summary=row.summary,
        implementation_horizon=row.implementation_horizon,
        workstreams=[ImplWorkstream.model_validate(x) for x in (row.workstreams or [])],
        milestones=[ImplMilestone.model_validate(x) for x in (row.milestones or [])],
        tasks=[ImplTask.model_validate(x) for x in (row.tasks or [])],
        role_assignments=[
            ImplRoleAssignment.model_validate(x) for x in (row.role_assignments or [])
        ],
        dependencies=[ImplDependency.model_validate(x) for x in (row.dependencies or [])],
        deliverables=[ImplDeliverable.model_validate(x) for x in (row.deliverables or [])],
        budget_plan=ImplBudgetPlan.model_validate(row.budget_plan or {}),
        budget_gates=[ImplBudgetGate.model_validate(x) for x in (row.budget_gates or [])],
        approval_gates=[
            ImplApprovalGate.model_validate(x) for x in (row.approval_gates or [])
        ],
        conditions=[ImplConditionRef.model_validate(x) for x in (row.conditions or [])],
        implementation_risks=[
            ImplRisk.model_validate(x) for x in (row.implementation_risks or [])
        ],
        assumptions=[ImplAssumption.model_validate(x) for x in (row.assumptions or [])],
        roadmap=[ImplRoadmapPhase.model_validate(x) for x in (row.roadmap or [])],
        readiness_status=ImplementationPlanReadinessStatus(row.readiness_status),
        readiness_reasons=[str(x) for x in (row.readiness_reasons or [])],
        submitted_by=row.submitted_by,
        submitted_at=row.submitted_at,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        rejection_reason=row.rejection_reason,
        block_reason=row.block_reason,
        supersedes_plan_id=row.supersedes_plan_id,
        creates_marketing_plan=False,
        creates_specialist_tasks=False,
        creates_campaign=False,
        creates_execution_approval=False,
        creates_publication_approval=False,
        creates_agent_run=False,
        is_marketing_plan=False,
        budget_gates_authorize_spend=False,
        approval_gates_are_local_only=True,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def agent_to_contract(row: AgentTable) -> Agent:
    return Agent(
        id=row.id,
        project_id=row.project_id,
        owner_id=row.owner_id,
        type=row.type,
        name=row.name,
        description=row.description,
        status=row.status,
        config=row.config,
        capabilities=[AgentCapability.model_validate(item) for item in row.capabilities],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def agent_run_to_contract(row: AgentRunTable) -> AgentRun:
    return AgentRun(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        task_id=row.task_id,
        agent_id=row.agent_id,
        parent_agent_run_id=row.parent_agent_run_id,
        status=row.status,
        input_payload=row.input_payload,
        output_payload=row.output_payload,
        error=row.error,
        metadata=row.run_metadata,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def agent_run_execute_response(
    row: AgentRunTable,
    execution_engine: ExecutionEngine,
) -> AgentRunExecuteResponse:
    return AgentRunExecuteResponse(
        **agent_run_to_contract(row).model_dump(),
        execution_engine=execution_engine,
    )


def task_to_contract(row: TaskTable) -> Task:
    return Task(
        id=row.id,
        project_id=row.project_id,
        agent_id=row.agent_id,
        title=row.title,
        status=row.status,
        input_payload=row.input_payload,
        output_payload=row.output_payload,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def memory_to_contract(row: MemoryItemTable) -> MemoryItem:
    return MemoryItem(
        id=row.id,
        user_id=row.user_id,
        project_id=row.project_id,
        layer=row.layer,
        key=row.key,
        content=row.content,
        metadata=row.item_metadata,
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


def llm_request_to_contract(row: LLMRequestTable) -> LLMRequest:
    return LLMRequest(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        agent_id=row.agent_id,
        agent_run_id=row.agent_run_id,
        task_id=row.task_id,
        provider=row.provider,
        model=row.model,
        input_payload=row.input_payload,
        prompt_metadata=row.prompt_metadata,
        request_metadata=row.request_metadata,
        status=row.status,
        error=row.error,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def llm_response_to_contract(row: LLMResponseTable) -> LLMResponse:
    return LLMResponse(
        id=row.id,
        llm_request_id=row.llm_request_id,
        output_payload=row.output_payload,
        raw_response=row.raw_response,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        total_tokens=row.total_tokens,
        cost_estimate=row.cost_estimate,
        latency_ms=row.latency_ms,
        response_metadata=row.response_metadata,
        created_at=row.created_at,
    )


def webhook_delivery_log_to_contract(row: WebhookDeliveryLogTable) -> WebhookDeliveryLog:
    return WebhookDeliveryLog(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        webhook_id=row.webhook_id,
        event_outbox_id=row.event_outbox_id,
        event_type=row.event_type,
        target_url_preview=row.target_url_preview,
        status=row.status,
        http_status_code=row.http_status_code,
        attempt_number=row.attempt_number,
        duration_ms=row.duration_ms,
        error_code=row.error_code,
        error_message=row.error_message,
        response_preview=row.response_preview,
        created_at=row.created_at,
    )


def project_webhook_to_read(row: ProjectWebhookTable) -> ProjectWebhookRead:
    return ProjectWebhookRead(
        id=row.id,
        project_id=row.project_id,
        url=row.url,
        subscribed_event_types=list(row.subscribed_event_types or []),
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_brief_to_contract(row: MarketingBriefTable) -> MarketingBrief:
    return MarketingBrief(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        title=row.title,
        product_description=row.product_description,
        target_audience=row.target_audience,
        offer=row.offer,
        goals=list(row.goals or []),
        constraints=dict(row.constraints or {}),
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def content_asset_to_contract(row: ContentAssetTable) -> ContentAsset:
    return ContentAsset(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        brief_id=row.brief_id,
        campaign_id=getattr(row, "campaign_id", None),
        task_id=row.task_id,
        agent_run_id=row.agent_run_id,
        type=row.asset_type,
        title=row.title,
        body=row.body,
        metadata=dict(row.asset_metadata or {}),
        status=row.status,
        current_version_number=row.current_version_number,
        approved_version_number=row.approved_version_number,
        source_asset_id=row.source_asset_id,
        source_version_number=row.source_version_number,
        revision_number=row.revision_number,
        source_marketing_plan_id=getattr(row, "source_marketing_plan_id", None),
        source_execution_run_id=getattr(row, "source_execution_run_id", None),
        source_specialist_output_id=getattr(row, "source_specialist_output_id", None),
        source_specialist_type=getattr(row, "source_specialist_type", None),
        submitted_for_review_at=getattr(row, "submitted_for_review_at", None),
        approved_at=getattr(row, "approved_at", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def publication_package_to_contract(row: PublicationPackageTable) -> PublicationPackage:
    return PublicationPackage(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        content_asset_id=row.content_asset_id,
        source_content_asset_id=row.source_content_asset_id,
        channel=row.channel,
        title=row.title,
        body=row.body,
        cta=row.cta,
        metadata=dict(row.package_metadata or {}),
        status=row.status,
        submitted_for_review_at=getattr(row, "submitted_for_review_at", None),
        approved_at=getattr(row, "approved_at", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def media_brief_to_contract(row: MediaBriefTable) -> MediaBrief:
    return MediaBrief(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        content_asset_id=row.content_asset_id,
        source_content_asset_id=row.source_content_asset_id,
        status=row.status,
        title=row.title,
        goal=row.goal,
        target_audience=row.target_audience,
        platform=row.platform,
        creative_direction=row.creative_direction,
        visual_style=row.visual_style,
        composition=row.composition,
        text_overlay=row.text_overlay,
        references=list(row.references or []),
        submitted_for_review_at=row.submitted_for_review_at,
        approved_at=row.approved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def media_asset_to_contract(row: MediaAssetTable) -> MediaAsset:
    return MediaAsset(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        media_brief_id=row.media_brief_id,
        source_media_brief_id=row.source_media_brief_id,
        media_type=row.media_type,
        status=row.status,
        generation_provider=row.generation_provider,
        generation_metadata=dict(row.generation_metadata or {}),
        source_generation_job_id=getattr(row, "source_generation_job_id", None),
        provider=getattr(row, "provider", None),
        provider_asset_ref=getattr(row, "provider_asset_ref", None),
        storage_uri=getattr(row, "storage_uri", None),
        mime_type=getattr(row, "mime_type", None),
        width=getattr(row, "width", None),
        height=getattr(row, "height", None),
        current_version_number=getattr(row, "current_version_number", 1),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def media_generation_job_to_contract(row: MediaGenerationJobTable) -> MediaGenerationJob:
    return MediaGenerationJob(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        media_brief_id=row.media_brief_id,
        media_asset_id=row.media_asset_id,
        provider=row.provider,
        media_type=row.media_type,
        prompt=row.prompt,
        status=row.status,
        result_metadata=dict(row.result_metadata or {}),
        error=row.error,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def campaign_to_contract(row: CampaignTable) -> Campaign:
    return Campaign(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        name=row.name,
        goal=row.goal,
        scenario_id=row.scenario_id,
        status=CampaignStatus(row.status),
        metadata=dict(row.campaign_metadata or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_tool_call_to_contract(row: MarketingToolCallTable) -> MarketingToolCall:
    return MarketingToolCall(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        tool_type=MarketingToolType(row.tool_type),
        input_payload=dict(row.input_payload or {}),
        output_payload=dict(row.output_payload) if row.output_payload else None,
        status=MarketingToolCallStatus(row.status),
        safe_metadata=dict(row.safe_metadata or {}),
        error=row.error,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def marketing_skill_run_to_contract(row: MarketingSkillRunTable) -> MarketingSkillRun:
    used_tool_call_ids: list[UUID] = []
    for value in row.used_tool_call_ids or []:
        try:
            used_tool_call_ids.append(UUID(str(value)))
        except ValueError:
            continue
    return MarketingSkillRun(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        campaign_id=row.campaign_id,
        skill_type=MarketingSkillType(row.skill_type),
        input_payload=dict(row.input_payload or {}),
        output_payload=dict(row.output_payload) if row.output_payload else None,
        status=MarketingSkillRunStatus(row.status),
        used_tool_call_ids=used_tool_call_ids,
        safe_metadata=dict(row.safe_metadata or {}),
        error=row.error,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def marketing_campaign_to_contract(row: MarketingCampaignTable) -> MarketingCampaign:
    return MarketingCampaign(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        brief_id=row.brief_id,
        title=row.title,
        description=row.description,
        status=row.status,
        start_at=row.start_at,
        end_at=row.end_at,
        campaign_metadata=dict(row.campaign_metadata or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def campaign_plan_draft_to_contract(row: CampaignPlanDraftTable) -> CampaignPlanDraft:
    return CampaignPlanDraft(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        campaign_id=row.campaign_id,
        source_agent_run_id=row.source_agent_run_id,
        title=row.title,
        plan_payload=dict(row.plan_payload or {}),
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_funnel_to_contract(row: MarketingFunnelTable) -> MarketingFunnel:
    return MarketingFunnel(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        brief_id=row.brief_id,
        title=row.title,
        description=row.description,
        status=row.status,
        metadata=dict(row.funnel_metadata or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_funnel_step_to_contract(row: MarketingFunnelStepTable) -> MarketingFunnelStep:
    return MarketingFunnelStep(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        funnel_id=row.funnel_id,
        step_type=row.step_type,
        title=row.title,
        description=row.description,
        position=row.position,
        status=row.status,
        metadata=dict(row.step_metadata or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def funnel_step_asset_link_to_contract(row: FunnelStepAssetLinkTable) -> FunnelStepAssetLink:
    return FunnelStepAssetLink(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        funnel_id=row.funnel_id,
        step_id=row.step_id,
        asset_id=row.asset_id,
        role=row.role,
        created_at=row.created_at,
    )


def funnel_step_linked_asset_to_contract(row: FunnelStepAssetLinkRow) -> FunnelStepLinkedAsset:
    return FunnelStepLinkedAsset(
        link_id=row.link_id,
        asset_id=row.asset_id,
        role=row.role,
        asset_title=row.asset_title,
        asset_type=row.asset_type,
        asset_status=row.asset_status,
        created_at=row.created_at,
    )


def content_asset_version_to_contract(row: ContentAssetVersionTable) -> ContentAssetVersion:
    return ContentAssetVersion(
        version_number=row.version_number,
        title=row.title,
        body=row.body,
        metadata=dict(row.version_metadata or {}),
        created_by_source=row.created_by_source,
        created_at=row.created_at,
    )


def publishing_channel_to_contract(row: PublishingChannelTable) -> PublishingChannel:
    return PublishingChannel(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        name=row.name,
        type=row.channel_type,
        status=row.status,
        config_preview=dict(row.config_preview or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def publication_job_to_contract(row: PublicationJobTable) -> PublicationJob:
    return PublicationJob(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        asset_id=row.asset_id,
        asset_version_number=row.asset_version_number,
        channel_id=row.channel_id,
        campaign_id=getattr(row, "campaign_id", None),
        status=row.status,
        attempts=row.attempts,
        payload_preview=dict(row.payload_preview or {}),
        error=row.error,
        created_at=row.created_at,
        scheduled_at=row.scheduled_at,
        queued_at=row.queued_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def publishing_foundation_channel_to_contract(
    row: PublishingChannelTable,
) -> PublishingFoundationChannel:
    from app.publishing_foundation.contracts import (
        PublishingFoundationChannelStatus,
        PublishingFoundationChannelType,
    )

    return PublishingFoundationChannel(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        channel_type=PublishingFoundationChannelType(row.channel_type.value),
        name=row.name,
        status=PublishingFoundationChannelStatus(row.status.value),
        config_metadata=dict(row.channel_config or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def publication_package_job_to_contract(
    row: PublicationPackageJobTable,
) -> PublicationPackageJob:
    return PublicationPackageJob(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        publication_package_id=row.publication_package_id,
        channel_id=row.channel_id,
        status=row.status,
        payload_snapshot=dict(row.payload_snapshot or {}),
        snapshot_hash=getattr(row, "snapshot_hash", None),
        result_metadata=dict(row.result_metadata or {}),
        error=dict(row.error) if row.error else None,
        replay_of_job_id=getattr(row, "replay_of_job_id", None),
        scheduled_for=getattr(row, "scheduled_for", None),
        schedule_status=getattr(
            row,
            "schedule_status",
            PublicationPackageJobScheduleStatus.UNSCHEDULED,
        ),
        dispatch_attempts=getattr(row, "dispatch_attempts", 0),
        last_dispatch_error=(
            dict(row.last_dispatch_error) if getattr(row, "last_dispatch_error", None) else None
        ),
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def publication_delivery_log_to_contract(
    row: PublicationDeliveryLogTable,
) -> PublicationDeliveryLog:
    return PublicationDeliveryLog(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        publication_job_id=row.publication_job_id,
        channel_id=row.channel_id,
        channel_type=row.channel_type,
        status=row.status,
        attempt_number=row.attempt_number,
        duration_ms=row.duration_ms,
        error_code=row.error_code,
        error_message=row.error_message,
        response_preview=row.response_preview,
        created_at=row.created_at,
    )


def event_outbox_to_contract(row: EventOutboxTable) -> EventOutbox:
    return EventOutbox(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        event_type=row.event_type,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        payload=row.payload,
        status=row.status,
        attempts=row.attempts,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def agent_chat_session_to_contract(row: AgentChatSessionTable) -> AgentChatSession:
    return AgentChatSession(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        agent_id=row.agent_id,
        entrypoint=row.entrypoint,
        domain=row.domain,
        title=row.title,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def agent_chat_message_to_contract(
    row: AgentChatMessageTable,
    *,
    blocks: list[ChatAssistantMessageBlock] | None = None,
) -> AgentChatMessage:
    from app.schemas.contracts import ChatAssistantMessageBlock

    resolved_blocks: list[ChatAssistantMessageBlock] = []
    if blocks is not None:
        resolved_blocks = list(blocks)
    return AgentChatMessage(
        id=row.id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        metadata=row.message_metadata or {},
        agent_run_id=row.agent_run_id,
        created_at=row.created_at,
        blocks=resolved_blocks,
    )


def marketing_plan_to_contract(row: MarketingPlanTable) -> MarketingPlan:
    return MarketingPlan(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        source_run_id=row.source_run_id,
        source_session_id=row.source_session_id,
        source_scenario_id=row.source_scenario_id,
        source_scenario_name=row.source_scenario_name,
        title=row.title,
        goal=row.goal,
        project_context=dict(row.project_context or {}),
        specialist_tasks=MarketingPlanService.specialist_tasks_for_row(row),
        execution_mode=MarketingExecutionMode(row.execution_mode),
        status=MarketingPlanStatus(row.status),
        current_version_number=row.current_version_number,
        approved_version_number=row.approved_version_number,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_plan_version_to_contract(
    row: MarketingPlanVersionTable,
) -> MarketingPlanVersion:
    return MarketingPlanVersion(
        id=row.id,
        marketing_plan_id=row.marketing_plan_id,
        version_number=row.version_number,
        goal=row.goal,
        project_context=dict(row.project_context or {}),
        specialist_tasks=MarketingPlanService.specialist_tasks_for_version(row),
        execution_mode=MarketingExecutionMode(row.execution_mode),
        created_at=row.created_at,
        created_by_run_id=row.created_by_run_id,
    )


def marketing_specialist_output_to_contract(
    row: MarketingSpecialistOutputTable,
) -> MarketingSpecialistOutput:
    return MarketingSpecialistOutput(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        marketing_plan_id=row.marketing_plan_id,
        execution_run_id=row.execution_run_id,
        task_index=row.task_index,
        specialist=MarketingSpecialistType(row.specialist),
        title=row.title,
        output_type=row.output_type,
        content=row.content,
        structured_data=dict(row.structured_data) if row.structured_data else None,
        status=MarketingSpecialistOutputStatus(row.status),
        current_version_number=row.current_version_number,
        approved_version_number=row.approved_version_number,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_specialist_output_version_to_contract(
    row: MarketingSpecialistOutputVersionTable,
) -> MarketingSpecialistOutputVersion:
    return MarketingSpecialistOutputVersion(
        id=row.id,
        specialist_output_id=row.specialist_output_id,
        version_number=row.version_number,
        title=row.title,
        output_type=row.output_type,
        content=row.content,
        structured_data=dict(row.structured_data) if row.structured_data else None,
        created_at=row.created_at,
        created_by_run_id=row.created_by_run_id,
    )


def beta_feedback_report_to_contract(row: BetaFeedbackReportTable) -> BetaFeedbackReport:
    raw_context = row.safe_context if isinstance(row.safe_context, dict) else None
    return BetaFeedbackReport(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        source=row.source,
        severity=row.severity,
        status=row.status,
        title=row.title,
        description=row.description,
        safe_context=sanitize_feedback_context(raw_context),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def marketing_plan_execution_run_to_contract(
    row: MarketingPlanExecutionRunTable,
) -> MarketingPlanExecutionRun:
    return MarketingPlanExecutionRun(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        marketing_plan_id=row.marketing_plan_id,
        marketing_plan_version_number=row.marketing_plan_version_number,
        status=MarketingPlanExecutionStatus(row.status),
        task_snapshots=MarketingPlanExecutionService.task_snapshots_for_row(row),
        result_summary=dict(row.result_summary) if row.result_summary else None,
        error=dict(row.error) if row.error else None,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def scenario_wizard_run_to_contract(row: ScenarioWizardRunTable) -> ScenarioWizardRun:
    return ScenarioWizardRun(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        scenario_id=row.scenario_id,
        scenario_name=row.scenario_name,
        source_campaign_id=row.source_campaign_id,
        status=ScenarioWizardRunStatus(row.status),
        current_step=row.current_step,
        step_results=ScenarioWizardService.step_results_for_row(row),
        failure_reason=row.failure_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
        finished_at=row.finished_at,
    )
