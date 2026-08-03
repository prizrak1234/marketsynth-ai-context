"""Campaign supervisor — read-only quality report (Phase AI.249)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.campaign_supervisor_engine import (
    CampaignSupervisorInput,
    build_campaign_supervisor_report,
)
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.schemas.contracts import (
    BusinessIntent,
    CampaignSupervisorReport,
    CampaignSupervisorSeverity,
    MarketingSkillRunStatus,
    MarketingSpecialistType,
)
from app.services.campaign_control_center_service import CampaignControlCenterService
from app.services.campaign_skill_context_service import CampaignSkillContextService
from app.services.campaign_supervisor_audit import log_campaign_supervisor_report
from app.services.projects_service import ProjectService

_CONTENT_SPECIALISTS = (
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_TOP_FINDINGS_LIMIT = 5


class CampaignSupervisorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._control = CampaignControlCenterService(session)
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
    def _has_website_channel(brief) -> bool:
        if brief is None:
            return False
        channels = [str(item).lower() for item in (brief.channels or [])]
        return any(token in channel for channel in channels for token in ("web", "site", "сайт"))

    async def build_input(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignSupervisorInput | None:
        artifacts = await self._control._load_artifacts(owner_id, project_id, campaign_id)
        if artifacts is None:
            return None

        resource_ids = self._control._resource_ids(artifacts)
        next_action, health_status, _blocking = self._control._resolve_next_action(
            artifacts,
            resource_ids,
        )
        brief = await self._control._load_brief_for_campaign(
            owner_id,
            project_id,
            artifacts.campaign,
        )
        metadata = artifacts.campaign.campaign_metadata or {}
        intent = self._parse_intent(metadata)
        skill_context = CampaignSkillContextService.skill_context_from_campaign(artifacts.campaign)
        completed = {
            run.skill_type
            for run in artifacts.skill_runs
            if run.status == MarketingSkillRunStatus.SUCCEEDED
        }
        content_output = next(
            (output for output in artifacts.content_outputs if output.specialist in _CONTENT_SPECIALISTS),
            None,
        )
        asset = artifacts.latest_asset
        brief_row = artifacts.latest_brief
        package = artifacts.latest_package
        job = artifacts.latest_job

        return CampaignSupervisorInput(
            campaign_id=campaign_id,
            campaign_status=artifacts.campaign.status,
            scenario_id=artifacts.campaign.scenario_id,
            intent=intent,
            brief=brief,
            skill_context=skill_context,
            completed_skill_types=completed,
            next_action_type=next_action.action_type,
            health_status=health_status,
            has_copywriter_output=content_output is not None,
            copywriter_output_id=content_output.id if content_output else None,
            has_content_asset=asset is not None,
            content_asset_approved=asset is not None and asset.status == ContentAssetStatus.APPROVED,
            content_asset_id=asset.id if asset else None,
            has_media_brief=brief_row is not None,
            media_brief_approved=brief_row is not None and brief_row.status == MediaBriefStatus.APPROVED,
            media_brief_id=brief_row.id if brief_row else None,
            has_media_asset=bool(artifacts.media_assets),
            has_publication_package=package is not None,
            publication_package_approved=package is not None
            and package.status == PublicationPackageStatus.APPROVED,
            publication_package_id=package.id if package else None,
            has_publication_job=job is not None,
            publication_job_failed=job is not None and job.status == PublicationPackageJobStatus.FAILED,
            publication_job_id=job.id if job else None,
            has_website_channel=self._has_website_channel(brief),
        )

    async def get_report(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        audit: bool = True,
    ) -> CampaignSupervisorReport | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        supervisor_input = await self.build_input(owner_id, project_id, campaign_id)
        if supervisor_input is None:
            return None

        report = build_campaign_supervisor_report(supervisor_input)
        if audit:
            log_campaign_supervisor_report(
                campaign_id=str(campaign_id),
                project_id=str(project_id),
                report=report,
            )
        return report

    @staticmethod
    def summarize_for_control_center(
        report: CampaignSupervisorReport,
        *,
        top_limit: int = _TOP_FINDINGS_LIMIT,
    ) -> dict:
        critical_count = sum(
            1
            for item in report.findings
            if item.severity == CampaignSupervisorSeverity.CRITICAL
        )
        return {
            "supervisor_health_score": report.health_score,
            "supervisor_findings_count": len(report.findings),
            "critical_findings_count": critical_count,
            "top_findings": report.findings[:top_limit],
        }
