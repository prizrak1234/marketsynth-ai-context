"""Campaign workflow layer — recommendations and run creation (Phase AI.259–AI.261)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.domain.campaign_workflow_recommendation_engine import (
    CampaignWorkflowRecommendationInput,
    build_campaign_workflow_suggestions,
)
from app.domain.campaign_workflow_step_mapper import (
    CampaignWorkflowStepMapper,
    completed_skill_types_from_runs,
)
from app.marketing.workflows.registry import get_workflow_template, list_workflow_templates
from app.db.models.campaign_workflow_run import CampaignWorkflowRunTable
from app.db.repositories.campaign_workflow_runs import CampaignWorkflowRunRepository
from app.schemas.contracts import (
    BusinessIntent,
    CampaignBriefFields,
    CampaignWorkflowRun,
    CampaignWorkflowRunStatus,
    CampaignWorkflowRunSummary,
    CampaignWorkflowSuggestion,
    CampaignWorkflowTemplate,
)
from app.services.campaign_control_center_service import CampaignControlCenterService
from app.services.campaign_skill_context_service import CampaignSkillContextService
from app.services.campaign_supervisor_service import CampaignSupervisorService
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class CampaignWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = CampaignWorkflowRunRepository(session)
        self._control = CampaignControlCenterService(session)
        self._supervisor = CampaignSupervisorService(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def _parse_intent(campaign_metadata: dict) -> BusinessIntent | None:
        raw = campaign_metadata.get("source_business_intent")
        if not isinstance(raw, dict) or not raw.get("goal"):
            return None
        return BusinessIntent(
            goal=str(raw.get("goal") or "promo"),
            industry=raw.get("industry"),
            business_type=raw.get("business_type"),
            campaign_type=raw.get("campaign_type"),
            confidence=float(raw.get("confidence") or 0.0),
            recommended_scenario=raw.get("recommended_scenario"),
        )

    @staticmethod
    def _parse_brief(campaign_metadata: dict) -> CampaignBriefFields | None:
        raw = campaign_metadata.get("brief_fields")
        if not isinstance(raw, dict):
            return None
        try:
            return CampaignBriefFields.model_validate(raw)
        except Exception:
            return None

    async def list_templates(self) -> list[CampaignWorkflowTemplate]:
        return list_workflow_templates()

    async def recommend(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> list[CampaignWorkflowSuggestion]:
        if not await self._ensure_project_owned(owner_id, project_id):
            return []
        input_data = await self._build_recommendation_input(owner_id, project_id, campaign_id)
        if input_data is None:
            return []
        return build_campaign_workflow_suggestions(input_data)

    async def _build_recommendation_input(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignWorkflowRecommendationInput | None:
        artifacts = await self._control._load_artifacts(owner_id, project_id, campaign_id)
        if artifacts is None:
            return None

        metadata = dict(artifacts.campaign.campaign_metadata or {})
        supervisor_report = await self._supervisor.get_report(
            owner_id,
            project_id,
            campaign_id,
            audit=False,
        )
        runs = await self._runs.list_for_campaign(owner_id, project_id, campaign_id)
        active_template_ids = {
            row.template_id
            for row in runs
            if row.status
            in {CampaignWorkflowRunStatus.DRAFT, CampaignWorkflowRunStatus.ACTIVE}
        }

        latest_asset = artifacts.latest_asset
        latest_brief = artifacts.latest_brief
        latest_package = artifacts.latest_package
        has_content_asset = latest_asset is not None
        has_media_brief = latest_brief is not None
        has_publication_package = latest_package is not None

        completed = completed_skill_types_from_runs(artifacts.skill_runs)

        return CampaignWorkflowRecommendationInput(
            scenario_id=artifacts.campaign.scenario_id,
            intent=self._parse_intent(metadata),
            brief=self._parse_brief(metadata),
            skill_context=CampaignSkillContextService.skill_context_from_campaign(
                artifacts.campaign,
            ),
            completed_skill_types=completed,
            supervisor_findings=list(supervisor_report.findings) if supervisor_report else [],
            supervisor_missing_inputs=list(supervisor_report.missing_inputs)
            if supervisor_report
            else [],
            has_content_asset=has_content_asset,
            has_media_brief=has_media_brief,
            has_publication_package=has_publication_package,
            active_template_ids=active_template_ids,
        )

    async def create_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        template_id: str,
    ) -> CampaignWorkflowRun | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        template = get_workflow_template(template_id)
        if template is None:
            raise InvalidStateError(f"Unknown workflow template: {template_id}")

        campaign = await self._control._layer.get(owner_id, project_id, campaign_id)
        if campaign is None:
            return None

        duplicate = await self._runs.has_non_archived_for_template(
            owner_id,
            project_id,
            campaign_id,
            template_id,
        )
        status = CampaignWorkflowRunStatus.DRAFT if duplicate else CampaignWorkflowRunStatus.ACTIVE

        row = CampaignWorkflowRunTable(
            owner_id=owner_id,
            project_id=project_id,
            campaign_id=campaign_id,
            template_id=template_id,
            status=status,
            current_step_index=0,
            step_results={},
        )
        async with transactional(self._session):
            row = await self._runs.create(row)
        return campaign_workflow_run_to_contract(row)

    async def get_active_run_summary(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignWorkflowRunSummary | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        row = await self._runs.find_active_for_campaign(owner_id, project_id, campaign_id)
        if row is None:
            return None
        return await self._build_run_summary(owner_id, project_id, campaign_id, row)

    async def _build_run_summary(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        row: CampaignWorkflowRunTable,
    ) -> CampaignWorkflowRunSummary | None:
        template = get_workflow_template(row.template_id)
        if template is None:
            return None

        artifacts = await self._control._load_artifacts(owner_id, project_id, campaign_id)
        if artifacts is None:
            return None

        skill_context = CampaignSkillContextService.skill_context_from_campaign(
            artifacts.campaign,
        )
        context_keys = {
            key
            for key in ("segment_summary", "offer_summary", "demand_summary", "analytics_summary")
            if skill_context is not None and getattr(skill_context, key, None)
        }
        completed = completed_skill_types_from_runs(artifacts.skill_runs)

        steps = CampaignWorkflowStepMapper.build_step_views(
            template,
            current_step_index=row.current_step_index,
            run_status=CampaignWorkflowRunStatus(row.status),
            step_results=dict(row.step_results or {}),
            completed_skill_types=completed,
            skill_context_keys=context_keys,
            has_content_asset=artifacts.latest_asset is not None,
            has_media_brief=artifacts.latest_brief is not None,
            has_publication_package=artifacts.latest_package is not None,
        )

        return CampaignWorkflowRunSummary(
            run=campaign_workflow_run_to_contract(row),
            template_name=template.name,
            template_goal=template.goal,
            steps=steps,
            progress_percent=CampaignWorkflowStepMapper.progress_percent(steps),
        )


def campaign_workflow_run_to_contract(row: CampaignWorkflowRunTable) -> CampaignWorkflowRun:
    return CampaignWorkflowRun(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        campaign_id=row.campaign_id,
        template_id=row.template_id,
        status=CampaignWorkflowRunStatus(row.status),
        current_step_index=row.current_step_index,
        step_results=dict(row.step_results or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
