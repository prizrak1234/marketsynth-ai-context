"""Execute campaign actions via existing services (Phase AI.169–AI.170)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.db.base import utc_now
from app.domain.campaign_skill_input import (
    SKILL_ACTION_TO_TYPE,
    build_campaign_skill_input,
)
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.marketing.scenario_wizard_content import create_content_asset_from_wizard_output
from app.publishing.contracts import PublishingChannelStatus
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
    PublishingDispatchMode,
    PublishingFoundationChannelType,
)
from app.schemas.contracts import (
    CampaignActionResult,
    CampaignActionResultStatus,
    CampaignActionType,
    CampaignControlCenter,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSkillRunStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
    ScenarioWizardRunStatus,
)
from app.schemas.publishing_foundation import PublishingFoundationChannelCreateRequest
from app.services.campaign_action_idempotency import (
    build_state_fingerprint,
    hash_idempotency_key,
    lookup_replay,
    store_replay,
)
from app.services.campaign_control_center_service import (
    CampaignArtifacts,
    CampaignControlCenterService,
)
from app.services.campaign_layer_service import CampaignLayerService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_plan_service import MarketingPlanService
from app.services.marketing_skill_run_service import MarketingSkillRunService
from app.services.marketing_specialist_output_service import MarketingSpecialistOutputService
from app.services.media_brief_service import MediaBriefService
from app.services.publication_package_job_service import PublicationPackageJobService
from app.services.publication_package_service import PublicationPackageService
from app.services.publishing_foundation_channel_service import PublishingFoundationChannelService
from app.services.publishing_schedule_service import PublishingScheduleService
from app.services.scenario_wizard_service import ScenarioWizardService
from app.services.specialist_execution_service import SpecialistExecutionService
from app.services.transaction import transactional

_PIPELINE = MarketingPipelineExecutionService.pipeline_order()
_CONTENT_SPECIALISTS = (
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_WIZARD_CHANNEL_NAME = "Scenario Wizard Telegram Dry-Run"
_REAL_DISPATCH_FORBIDDEN = "Real Telegram publish is forbidden from campaign actions"


@dataclass
class _ExecutionOutcome:
    message: str
    status: CampaignActionResultStatus = CampaignActionResultStatus.SUCCEEDED
    created_resource_type: str | None = None
    created_resource_id: UUID | None = None
    updated_resource_type: str | None = None
    updated_resource_id: UUID | None = None


class CampaignActionExecutorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._control = CampaignControlCenterService(session)
        self._layer = CampaignLayerService(session)
        self._wizard = ScenarioWizardService(session)
        self._plans = MarketingPlanService(session)
        self._runs = MarketingPlanExecutionService(session)
        self._specialists = SpecialistExecutionService(session)
        self._outputs = MarketingSpecialistOutputService(session)
        self._assets = ContentAssetService(session)
        self._briefs = MediaBriefService(session)
        self._packages = PublicationPackageService(session)
        self._jobs = PublicationPackageJobService(session)
        self._channels = PublishingFoundationChannelService(session)
        self._schedule = PublishingScheduleService(session)
        self._skill_runs = MarketingSkillRunService(session)

    async def _load_brief_for_campaign(self, artifacts: CampaignArtifacts):
        return await self._control._load_brief_for_campaign(
            artifacts.campaign.owner_id,
            artifacts.campaign.project_id,
            artifacts.campaign,
        )

    async def execute(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        action_type: CampaignActionType,
        *,
        idempotency_key: str | None = None,
        include_snapshot: bool = True,
    ) -> CampaignActionResult | None:
        center_before = await self._control.get_control_center(owner_id, project_id, campaign_id)
        if center_before is None:
            return None

        artifacts = await self._control._load_artifacts(owner_id, project_id, campaign_id)
        if artifacts is None:
            return None

        fingerprint = self._state_fingerprint(artifacts, center_before)
        key_hash = hash_idempotency_key(idempotency_key)
        campaign_row = artifacts.campaign

        if key_hash is not None:
            metadata = dict(campaign_row.campaign_metadata or {})
            try:
                cached = lookup_replay(
                    metadata,
                    key_hash=key_hash,
                    state_fingerprint=fingerprint,
                )
            except ValueError as exc:
                raise InvalidStateError("idempotency_state_conflict") from exc
            if cached is not None:
                if include_snapshot:
                    snapshot = await self._control.get_control_center(
                        owner_id,
                        project_id,
                        campaign_id,
                    )
                    return cached.model_copy(update={"control_center_snapshot": snapshot})
                return cached

        allowed = {item.type: item for item in center_before.available_actions if item.enabled}
        action_def = allowed.get(action_type)
        if action_def is None:
            raise InvalidStateError(
                f"Action {action_type.value} is not available for the current campaign state",
            )

        outcome = await self._dispatch(owner_id, project_id, campaign_id, action_type, artifacts)

        center_after = await self._control.get_control_center(owner_id, project_id, campaign_id)
        if center_after is None:
            raise InvalidStateError("Campaign state unavailable after action")

        result = CampaignActionResult(
            status=outcome.status,
            message=outcome.message,
            action_type=action_type,
            created_resource_type=outcome.created_resource_type,
            created_resource_id=outcome.created_resource_id,
            updated_resource_type=outcome.updated_resource_type,
            updated_resource_id=outcome.updated_resource_id,
            next_action_after=center_after.next_action,
            control_center_snapshot=center_after if include_snapshot else None,
        )

        if key_hash is not None:
            async with transactional(self._session):
                row = await self._layer.get(owner_id, project_id, campaign_id)
                if row is None:
                    raise InvalidStateError("Campaign not found after action")
                row.campaign_metadata = sanitize_payload(
                    store_replay(
                        dict(row.campaign_metadata or {}),
                        key_hash=key_hash,
                        state_fingerprint=fingerprint,
                        result=result,
                    ),
                ) or {}
                row.updated_at = utc_now()
                await self._layer._campaigns.update(row)

        return result

    @staticmethod
    def _state_fingerprint(
        artifacts: CampaignArtifacts,
        center: CampaignControlCenter,
    ) -> str:
        wizard = artifacts.latest_wizard
        plan = artifacts.latest_plan
        run = artifacts.latest_run
        asset = artifacts.latest_asset
        brief = artifacts.latest_brief
        package = artifacts.latest_package
        job = artifacts.latest_job
        parts = [
            str(artifacts.campaign.id),
            str(artifacts.campaign.updated_at),
            center.next_action.action_type.value,
            wizard.status.value if wizard else "",
            wizard.current_step if wizard else "",
            plan.status.value if plan else "",
            str(plan.id) if plan else "",
            run.status.value if run else "",
            str(run.id) if run else "",
            asset.status.value if asset else "",
            brief.status.value if brief else "",
            package.status.value if package else "",
            job.status.value if job else "",
            job.schedule_status.value if job and job.schedule_status else "",
        ]
        return build_state_fingerprint(parts)

    async def _ensure_dry_run_channel(self, owner_id: UUID, project_id: UUID) -> UUID:
        from app.db.repositories.publishing_channels import PublishingChannelRepository

        channels = await PublishingChannelRepository(self._session).list_for_project(
            project_id,
            owner_id=owner_id,
            include_archived=True,
        )
        channel = next(
            (item for item in (channels or []) if item.name == _WIZARD_CHANNEL_NAME),
            None,
        )
        if channel is not None and channel.status == PublishingChannelStatus.ACTIVE:
            return channel.id

        created = await self._channels.create(
            owner_id,
            project_id,
            PublishingFoundationChannelCreateRequest(
                name=_WIZARD_CHANNEL_NAME,
                channel_type=PublishingFoundationChannelType.TELEGRAM,
                status="active",
                config_metadata={"chat_id": "-100111222333", "campaign_action_dry_run": True},
            ),
        )
        if created is None:
            raise InvalidStateError("Failed to create dry-run publishing channel")
        return created.id

    async def _dispatch(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        action_type: CampaignActionType,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        if action_type == CampaignActionType.START_WIZARD:
            return await self._start_wizard(owner_id, project_id, campaign_id, artifacts)
        if action_type == CampaignActionType.ADVANCE_WIZARD:
            return await self._advance_wizard(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.APPROVE_PLAN:
            return await self._approve_plan(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.START_EXECUTION:
            return await self._start_execution(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.EXECUTE_NEXT_SPECIALIST:
            return await self._execute_next_specialist(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.APPROVE_COPYWRITER_OUTPUT:
            return await self._approve_copywriter_output(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.CREATE_CONTENT_ASSET:
            return await self._create_content_asset(owner_id, project_id, campaign_id, artifacts)
        if action_type == CampaignActionType.SUBMIT_ASSET_REVIEW:
            return await self._submit_asset(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.APPROVE_ASSET:
            return await self._approve_asset(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.CREATE_MEDIA_BRIEF:
            return await self._create_media_brief(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.SUBMIT_MEDIA_BRIEF_REVIEW:
            return await self._submit_media_brief(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.APPROVE_MEDIA_BRIEF:
            return await self._approve_media_brief(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.CREATE_PUBLICATION_PACKAGE:
            return await self._create_publication_package(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.SUBMIT_PACKAGE_REVIEW:
            return await self._submit_package(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.APPROVE_PACKAGE:
            return await self._approve_package(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.CREATE_PUBLICATION_JOB:
            return await self._create_publication_job(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.SCHEDULE_JOB:
            return await self._schedule_job(owner_id, project_id, artifacts)
        if action_type == CampaignActionType.DRY_RUN_DISPATCH:
            return await self._dry_run_dispatch(owner_id, project_id, artifacts)
        if action_type.value in SKILL_ACTION_TO_TYPE:
            return await self._run_skill(
                owner_id,
                project_id,
                campaign_id,
                action_type,
                artifacts,
            )
        raise InvalidStateError(f"Unsupported campaign action: {action_type.value}")

    async def _start_wizard(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        campaign = artifacts.campaign
        if not campaign.scenario_id:
            raise InvalidStateError("Campaign has no scenario_id")
        wizard = artifacts.latest_wizard
        if wizard is not None and wizard.status in {
            ScenarioWizardRunStatus.DRAFT,
            ScenarioWizardRunStatus.RUNNING,
            ScenarioWizardRunStatus.PAUSED,
        }:
            return _ExecutionOutcome(
                message="Wizard run already active",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="scenario_wizard_run",
                updated_resource_id=wizard.id,
            )
        row = await self._wizard.create_run(
            owner_id,
            project_id,
            campaign.scenario_id,
            source_campaign_id=campaign_id,
        )
        if row is None:
            raise InvalidStateError("Failed to start scenario wizard")
        return _ExecutionOutcome(
            message="Scenario wizard started",
            created_resource_type="scenario_wizard_run",
            created_resource_id=row.id,
        )

    async def _advance_wizard(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        wizard = artifacts.latest_wizard
        if wizard is None:
            raise InvalidStateError("No wizard run linked to campaign")
        if wizard.status in {
            ScenarioWizardRunStatus.SUCCEEDED,
            ScenarioWizardRunStatus.FAILED,
            ScenarioWizardRunStatus.CANCELLED,
        }:
            return _ExecutionOutcome(
                message=f"Wizard already {wizard.status.value}",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="scenario_wizard_run",
                updated_resource_id=wizard.id,
            )
        row = await self._wizard.advance(owner_id, project_id, wizard.id)
        if row is None:
            raise InvalidStateError("Wizard run not found")
        return _ExecutionOutcome(
            message=f"Wizard advanced to step {row.current_step}",
            updated_resource_type="scenario_wizard_run",
            updated_resource_id=row.id,
        )

    async def _approve_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        plan = artifacts.latest_plan
        if plan is None:
            raise InvalidStateError("No marketing plan linked to campaign")
        if plan.status == MarketingPlanStatus.APPROVED:
            return _ExecutionOutcome(
                message="Plan already approved",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="marketing_plan",
                updated_resource_id=plan.id,
            )
        approved = await self._plans.approve(owner_id, project_id, plan.id)
        if approved is None:
            raise InvalidStateError("Failed to approve marketing plan")
        return _ExecutionOutcome(
            message="Marketing plan approved",
            updated_resource_type="marketing_plan",
            updated_resource_id=approved.id,
        )

    async def _start_execution(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        plan = artifacts.latest_plan
        if plan is None or plan.status != MarketingPlanStatus.APPROVED:
            raise InvalidStateError("Approved marketing plan required")
        run = artifacts.latest_run
        if run is not None:
            if run.status == MarketingPlanExecutionStatus.RUNNING:
                return _ExecutionOutcome(
                    message="Execution run already started",
                    status=CampaignActionResultStatus.ALREADY_APPLIED,
                    updated_resource_type="marketing_plan_execution_run",
                    updated_resource_id=run.id,
                )
            started = await self._runs.start(owner_id, project_id, run.id)
            if started is None:
                raise InvalidStateError("Failed to start execution run")
            return _ExecutionOutcome(
                message="Execution run started",
                updated_resource_type="marketing_plan_execution_run",
                updated_resource_id=started.id,
            )
        created = await self._runs.create_from_approved_plan(owner_id, project_id, plan.id)
        if created is None:
            raise InvalidStateError("Failed to create execution run")
        started = await self._runs.start(owner_id, project_id, created.id)
        if started is None:
            raise InvalidStateError("Failed to start execution run")
        return _ExecutionOutcome(
            message="Execution run created and started",
            created_resource_type="marketing_plan_execution_run",
            created_resource_id=started.id,
        )

    async def _execute_next_specialist(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        run = artifacts.latest_run
        if run is None:
            raise InvalidStateError("No execution run linked to campaign")
        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
        for index, snapshot in enumerate(snapshots):
            if snapshot.status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED:
                continue
            if snapshot.specialist not in _PIPELINE:
                continue
            try:
                result = await self._specialists.execute_task_specialist(
                    owner_id,
                    project_id,
                    run.id,
                    index,
                )
            except InvalidStateError:
                continue
            if result is None:
                raise InvalidStateError("Failed to execute specialist task")
            return _ExecutionOutcome(
                message=f"Executed {result.specialist.value}",
                updated_resource_type="marketing_plan_execution_run",
                updated_resource_id=run.id,
                created_resource_type="marketing_specialist_output",
                created_resource_id=result.specialist_output_id,
            )
        raise InvalidStateError("No pending specialist tasks")

    async def _approve_copywriter_output(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        output = artifacts.content_outputs[0] if artifacts.content_outputs else None
        if output is None:
            raise InvalidStateError("No copywriter output linked to campaign")
        if output.status == MarketingSpecialistOutputStatus.APPROVED:
            return _ExecutionOutcome(
                message="Copywriter output already approved",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="marketing_specialist_output",
                updated_resource_id=output.id,
            )
        approved = await self._outputs.approve(owner_id, project_id, output.id)
        if approved is None:
            raise InvalidStateError("Failed to approve copywriter output")
        return _ExecutionOutcome(
            message="Copywriter output approved",
            updated_resource_type="marketing_specialist_output",
            updated_resource_id=approved.id,
        )

    async def _create_content_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        output = artifacts.content_outputs[0] if artifacts.content_outputs else None
        run = artifacts.latest_run
        plan = artifacts.latest_plan
        if output is None or run is None:
            raise InvalidStateError("Approved copywriter output and execution run required")
        if output.status != MarketingSpecialistOutputStatus.APPROVED:
            raise InvalidStateError("Copywriter output must be approved")

        if output.specialist == MarketingSpecialistType.COPYWRITER:
            asset = await self._outputs.create_content_asset_from_copywriter(
                owner_id,
                project_id,
                output.id,
            )
        else:
            asset = await create_content_asset_from_wizard_output(
                self._session,
                owner_id,
                project_id,
                output_id=output.id,
                specialist=output.specialist,
                status=output.status.value,
                output_type=output.output_type,
                title=output.title,
                content=output.content,
                structured_data=dict(output.structured_data) if output.structured_data else None,
                marketing_plan_id=plan.id if plan else None,
                execution_run_id=run.id,
                wizard_run_id=artifacts.latest_wizard.id if artifacts.latest_wizard else None,
            )
        if asset is None:
            raise InvalidStateError("Failed to create content asset")

        metadata = CampaignLayerService.tag_context(asset.asset_metadata, campaign_id)
        asset.asset_metadata = metadata
        async with transactional(self._session):
            asset = await self._layer._assets.update(asset)

        return _ExecutionOutcome(
            message="Content asset created",
            created_resource_type="content_asset",
            created_resource_id=asset.id,
        )

    async def _submit_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        asset = artifacts.latest_asset
        if asset is None:
            raise InvalidStateError("No content asset linked to campaign")
        if asset.status == ContentAssetStatus.REVIEW:
            return _ExecutionOutcome(
                message="Asset already in review",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="content_asset",
                updated_resource_id=asset.id,
            )
        await self._assets.submit_for_review_asset(owner_id, project_id, asset.id)
        return _ExecutionOutcome(
            message="Content asset submitted for review",
            updated_resource_type="content_asset",
            updated_resource_id=asset.id,
        )

    async def _approve_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        asset = artifacts.latest_asset
        if asset is None:
            raise InvalidStateError("No content asset linked to campaign")
        if asset.status == ContentAssetStatus.APPROVED:
            return _ExecutionOutcome(
                message="Asset already approved",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="content_asset",
                updated_resource_id=asset.id,
            )
        approved = await self._assets.approve_asset(owner_id, project_id, asset.id)
        if approved is None:
            raise InvalidStateError("Failed to approve content asset")
        return _ExecutionOutcome(
            message="Content asset approved",
            updated_resource_type="content_asset",
            updated_resource_id=approved.id,
        )

    async def _create_media_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        asset = artifacts.latest_asset
        if asset is None or asset.status != ContentAssetStatus.APPROVED:
            raise InvalidStateError("Approved content asset required")
        brief = await self._briefs.create_from_approved_content_asset(
            owner_id,
            project_id,
            asset.id,
        )
        if brief is None:
            raise InvalidStateError("Failed to create media brief")
        return _ExecutionOutcome(
            message="Media brief created",
            created_resource_type="media_brief",
            created_resource_id=brief.id,
        )

    async def _submit_media_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        brief = artifacts.latest_brief
        if brief is None:
            raise InvalidStateError("No media brief linked to campaign")
        if brief.status == MediaBriefStatus.REVIEW:
            return _ExecutionOutcome(
                message="Media brief already in review",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="media_brief",
                updated_resource_id=brief.id,
            )
        updated = await self._briefs.submit_for_review(owner_id, project_id, brief.id)
        if updated is None:
            raise InvalidStateError("Failed to submit media brief")
        return _ExecutionOutcome(
            message="Media brief submitted for review",
            updated_resource_type="media_brief",
            updated_resource_id=updated.id,
        )

    async def _approve_media_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        brief = artifacts.latest_brief
        if brief is None:
            raise InvalidStateError("No media brief linked to campaign")
        if brief.status == MediaBriefStatus.APPROVED:
            return _ExecutionOutcome(
                message="Media brief already approved",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="media_brief",
                updated_resource_id=brief.id,
            )
        approved = await self._briefs.approve_brief(owner_id, project_id, brief.id)
        if approved is None:
            raise InvalidStateError("Failed to approve media brief")
        return _ExecutionOutcome(
            message="Media brief approved",
            updated_resource_type="media_brief",
            updated_resource_id=approved.id,
        )

    async def _create_publication_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        asset = artifacts.latest_asset
        if asset is None or asset.status != ContentAssetStatus.APPROVED:
            raise InvalidStateError("Approved content asset required")
        package = await self._packages.create_from_approved_asset(
            owner_id,
            project_id,
            asset.id,
            channel="telegram",
        )
        if package is None:
            raise InvalidStateError("Failed to create publication package")
        return _ExecutionOutcome(
            message="Publication package created",
            created_resource_type="publication_package",
            created_resource_id=package.id,
        )

    async def _submit_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        package = artifacts.latest_package
        if package is None:
            raise InvalidStateError("No publication package linked to campaign")
        if package.status == PublicationPackageStatus.REVIEW:
            return _ExecutionOutcome(
                message="Package already in review",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="publication_package",
                updated_resource_id=package.id,
            )
        await self._packages.submit_for_review(owner_id, project_id, package.id)
        return _ExecutionOutcome(
            message="Publication package submitted for review",
            updated_resource_type="publication_package",
            updated_resource_id=package.id,
        )

    async def _approve_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        package = artifacts.latest_package
        if package is None:
            raise InvalidStateError("No publication package linked to campaign")
        if package.status == PublicationPackageStatus.APPROVED:
            return _ExecutionOutcome(
                message="Package already approved",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="publication_package",
                updated_resource_id=package.id,
            )
        approved = await self._packages.approve_package(owner_id, project_id, package.id)
        if approved is None:
            raise InvalidStateError("Failed to approve publication package")
        return _ExecutionOutcome(
            message="Publication package approved",
            updated_resource_type="publication_package",
            updated_resource_id=approved.id,
        )

    async def _create_publication_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        package = artifacts.latest_package
        if package is None or package.status != PublicationPackageStatus.APPROVED:
            raise InvalidStateError("Approved publication package required")
        if artifacts.latest_job is not None:
            job = artifacts.latest_job
            return _ExecutionOutcome(
                message="Publication job already exists",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="publication_package_job",
                updated_resource_id=job.id,
            )
        channel_id = await self._ensure_dry_run_channel(owner_id, project_id)
        job, _created = await self._jobs.create_from_approved_package(
            owner_id,
            project_id,
            package.id,
            channel_id,
        )
        if job is None:
            raise InvalidStateError("Failed to create publication job")
        return _ExecutionOutcome(
            message="Dry-run publication job created (queued)",
            created_resource_type="publication_package_job",
            created_resource_id=job.id,
        )

    async def _schedule_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        job = artifacts.latest_job
        if job is None:
            raise InvalidStateError("No publication job linked to campaign")
        if job.schedule_status == PublicationPackageJobScheduleStatus.SCHEDULED:
            return _ExecutionOutcome(
                message="Job already scheduled",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="publication_package_job",
                updated_resource_id=job.id,
            )
        scheduled_for = datetime.now(UTC) + timedelta(hours=1)
        row = await self._schedule.schedule_job(
            owner_id,
            project_id,
            job.id,
            scheduled_for=scheduled_for,
        )
        if row is None:
            raise InvalidStateError("Failed to schedule publication job")
        return _ExecutionOutcome(
            message="Publication job scheduled",
            updated_resource_type="publication_package_job",
            updated_resource_id=row.id,
        )

    async def _dry_run_dispatch(
        self,
        owner_id: UUID,
        project_id: UUID,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        job = artifacts.latest_job
        if job is None:
            raise InvalidStateError("No publication job linked to campaign")
        if job.status == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED:
            return _ExecutionOutcome(
                message="Dry-run already completed",
                status=CampaignActionResultStatus.ALREADY_APPLIED,
                updated_resource_type="publication_package_job",
                updated_resource_id=job.id,
            )

        row = await self._schedule.dispatch_due_job(
            owner_id,
            project_id,
            job.id,
            mode=PublishingDispatchMode.DRY_RUN,
        )
        if row is None:
            await self._schedule.mark_due(owner_id, project_id, job.id)
            row = await self._schedule.dispatch_due_job(
                owner_id,
                project_id,
                job.id,
                mode=PublishingDispatchMode.DRY_RUN,
            )
        if row is None:
            raise InvalidStateError("Failed to dispatch dry-run job")

        return _ExecutionOutcome(
            message="Dry-run dispatch completed",
            updated_resource_type="publication_package_job",
            updated_resource_id=row.id,
        )

    async def _run_skill(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        action_type: CampaignActionType,
        artifacts: CampaignArtifacts,
    ) -> _ExecutionOutcome:
        skill_type = SKILL_ACTION_TO_TYPE[action_type.value]
        brief = await self._load_brief_for_campaign(artifacts)
        input_payload = build_campaign_skill_input(
            artifacts.campaign,
            skill_type,
            brief=brief,
            create_tool_call=False,
        )
        run = await self._skill_runs.create_run(
            owner_id,
            project_id,
            skill_type,
            input_payload,
            campaign_id=campaign_id,
        )
        if run is None:
            raise InvalidStateError("Failed to create marketing skill run")
        if run.status != MarketingSkillRunStatus.SUCCEEDED:
            raise InvalidStateError(run.error or f"Skill run {skill_type.value} failed")
        return _ExecutionOutcome(
            message=f"Skill {skill_type.value} completed",
            created_resource_type="marketing_skill_run",
            created_resource_id=run.id,
        )

    @staticmethod
    def assert_not_real_dispatch(mode: PublishingDispatchMode) -> None:
        if mode == PublishingDispatchMode.REAL:
            raise InvalidStateError(_REAL_DISPATCH_FORBIDDEN)
