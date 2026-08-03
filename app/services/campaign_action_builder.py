"""Build explicit campaign actions from control center state (Phase AI.168)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.campaign_skill_input import SKILL_TYPE_TO_ACTION
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)
from app.schemas.contracts import (
    CampaignAction,
    CampaignActionType,
    CampaignHealthStatus,
    CampaignNextAction,
    CampaignNextActionType,
    CampaignResourceIds,
    CampaignSkillSuggestion,
    MarketingPlanExecutionStatus,
    MarketingPlanStatus,
    MarketingSpecialistOutputStatus,
    ScenarioWizardRunStatus,
)
from app.services.campaign_control_center_service import CampaignArtifacts

_CONFIRM_ACTIONS = frozenset(
    {
        CampaignActionType.APPROVE_PLAN,
        CampaignActionType.APPROVE_COPYWRITER_OUTPUT,
        CampaignActionType.APPROVE_ASSET,
        CampaignActionType.APPROVE_MEDIA_BRIEF,
        CampaignActionType.APPROVE_PACKAGE,
        CampaignActionType.SCHEDULE_JOB,
        CampaignActionType.DRY_RUN_DISPATCH,
    },
)

_WIZARD_RUNNING = frozenset(
    {
        ScenarioWizardRunStatus.DRAFT,
        ScenarioWizardRunStatus.RUNNING,
        ScenarioWizardRunStatus.PAUSED,
    },
)


def _action(
    action_type: CampaignActionType,
    *,
    label: str,
    enabled: bool = True,
    disabled_reason: str | None = None,
    target_resource_type: str | None = None,
    target_resource_id: UUID | None = None,
    safe_payload: dict[str, Any] | None = None,
) -> CampaignAction:
    return CampaignAction(
        type=action_type,
        label=label,
        enabled=enabled,
        disabled_reason=disabled_reason,
        target_resource_type=target_resource_type,
        target_resource_id=target_resource_id,
        confirmation_required=action_type in _CONFIRM_ACTIONS,
        safe_payload=safe_payload or {},
    )


def _wizard_blocks_non_advance(artifacts: CampaignArtifacts) -> bool:
    wizard = artifacts.latest_wizard
    return wizard is not None and wizard.status in _WIZARD_RUNNING


def _resolve_primary_type(
    next_action: CampaignNextAction,
    artifacts: CampaignArtifacts,
) -> CampaignActionType | None:
    mapping = {
        CampaignNextActionType.START_WIZARD: CampaignActionType.START_WIZARD,
        CampaignNextActionType.ADVANCE_WIZARD: CampaignActionType.ADVANCE_WIZARD,
        CampaignNextActionType.APPROVE_PLAN: CampaignActionType.APPROVE_PLAN,
        CampaignNextActionType.START_EXECUTION: CampaignActionType.START_EXECUTION,
        CampaignNextActionType.EXECUTE_NEXT_SPECIALIST: CampaignActionType.EXECUTE_NEXT_SPECIALIST,
        CampaignNextActionType.APPROVE_COPYWRITER_OUTPUT: CampaignActionType.APPROVE_COPYWRITER_OUTPUT,
        CampaignNextActionType.CREATE_CONTENT_ASSET: CampaignActionType.CREATE_CONTENT_ASSET,
        CampaignNextActionType.CREATE_MEDIA_BRIEF: CampaignActionType.CREATE_MEDIA_BRIEF,
        CampaignNextActionType.CREATE_PUBLICATION_PACKAGE: CampaignActionType.CREATE_PUBLICATION_PACKAGE,
    }
    action_type = mapping.get(next_action.action_type)
    if next_action.action_type == CampaignNextActionType.APPROVE_ASSET:
        asset = artifacts.latest_asset
        if asset is not None and asset.status == ContentAssetStatus.DRAFT:
            return CampaignActionType.SUBMIT_ASSET_REVIEW
        return CampaignActionType.APPROVE_ASSET
    if next_action.action_type == CampaignNextActionType.APPROVE_MEDIA_BRIEF:
        brief = artifacts.latest_brief
        if brief is not None and brief.status == MediaBriefStatus.DRAFT:
            return CampaignActionType.SUBMIT_MEDIA_BRIEF_REVIEW
        return CampaignActionType.APPROVE_MEDIA_BRIEF
    if next_action.action_type == CampaignNextActionType.CREATE_PUBLICATION_PACKAGE:
        package = artifacts.latest_package
        if package is None:
            return CampaignActionType.CREATE_PUBLICATION_PACKAGE
        if package.status == PublicationPackageStatus.DRAFT:
            return CampaignActionType.SUBMIT_PACKAGE_REVIEW
        if package.status == PublicationPackageStatus.REVIEW:
            return CampaignActionType.APPROVE_PACKAGE
        return CampaignActionType.CREATE_PUBLICATION_PACKAGE
    if next_action.action_type == CampaignNextActionType.SCHEDULE_OR_DRY_RUN:
        job = artifacts.latest_job
        if job is None:
            return CampaignActionType.CREATE_PUBLICATION_JOB
        if job.schedule_status == PublicationPackageJobScheduleStatus.UNSCHEDULED:
            return CampaignActionType.SCHEDULE_JOB
        return CampaignActionType.DRY_RUN_DISPATCH
    return action_type


def build_campaign_actions(
    artifacts: CampaignArtifacts,
    next_action: CampaignNextAction,
    resource_ids: CampaignResourceIds,
    *,
    health_status: CampaignHealthStatus,
    skill_suggestions: list[CampaignSkillSuggestion] | None = None,
) -> tuple[CampaignAction | None, list[CampaignAction]]:
    actions: list[CampaignAction] = []
    wizard = artifacts.latest_wizard
    plan = artifacts.latest_plan
    run = artifacts.latest_run
    content_output = artifacts.content_outputs[0] if artifacts.content_outputs else None
    asset = artifacts.latest_asset
    brief = artifacts.latest_brief
    package = artifacts.latest_package
    job = artifacts.latest_job
    campaign = artifacts.campaign
    wizard_active = _wizard_blocks_non_advance(artifacts)

    def add(action: CampaignAction) -> None:
        if wizard_active and action.type != CampaignActionType.ADVANCE_WIZARD:
            actions.append(
                _action(
                    action.type,
                    label=action.label,
                    enabled=False,
                    disabled_reason="Finish the active wizard with Advance wizard first.",
                    target_resource_type=action.target_resource_type,
                    target_resource_id=action.target_resource_id,
                    safe_payload=action.safe_payload,
                ),
            )
            return
        actions.append(action)

    if campaign.scenario_id and (wizard is None or wizard.status in {
        ScenarioWizardRunStatus.SUCCEEDED,
        ScenarioWizardRunStatus.FAILED,
        ScenarioWizardRunStatus.CANCELLED,
    }):
        add(
            _action(
                CampaignActionType.START_WIZARD,
                label="Start scenario wizard",
                enabled=health_status != CampaignHealthStatus.FAILED and bool(campaign.scenario_id),
                disabled_reason=None if campaign.scenario_id else "Attach a scenario first.",
                target_resource_type="campaign",
                target_resource_id=campaign.id,
            ),
        )

    if wizard is not None and wizard.status in _WIZARD_RUNNING:
        add(
            _action(
                CampaignActionType.ADVANCE_WIZARD,
                label="Advance wizard step",
                enabled=True,
                target_resource_type="scenario_wizard_run",
                target_resource_id=wizard.id,
                safe_payload={"current_step": wizard.current_step},
            ),
        )

    if plan is not None and plan.status == MarketingPlanStatus.DRAFT:
        add(
            _action(
                CampaignActionType.APPROVE_PLAN,
                label="Approve marketing plan",
                enabled=not wizard_active,
                disabled_reason="Use wizard or wait until wizard completes." if wizard_active else None,
                target_resource_type="marketing_plan",
                target_resource_id=plan.id,
            ),
        )

    if plan is not None and plan.status == MarketingPlanStatus.APPROVED and run is None:
        add(
            _action(
                CampaignActionType.START_EXECUTION,
                label="Start execution run",
                enabled=not wizard_active,
                target_resource_type="marketing_plan",
                target_resource_id=plan.id,
            ),
        )

    if run is not None and run.status in {
        MarketingPlanExecutionStatus.RUNNING,
        MarketingPlanExecutionStatus.QUEUED,
    }:
        add(
            _action(
                CampaignActionType.EXECUTE_NEXT_SPECIALIST,
                label="Execute next specialist",
                enabled=not wizard_active,
                target_resource_type="marketing_plan_execution_run",
                target_resource_id=run.id,
            ),
        )

    if content_output is not None and content_output.status != MarketingSpecialistOutputStatus.APPROVED:
        add(
            _action(
                CampaignActionType.APPROVE_COPYWRITER_OUTPUT,
                label="Approve copywriter output",
                enabled=not wizard_active,
                target_resource_type="marketing_specialist_output",
                target_resource_id=content_output.id,
            ),
        )

    if content_output is not None and content_output.status == MarketingSpecialistOutputStatus.APPROVED and asset is None:
        add(
            _action(
                CampaignActionType.CREATE_CONTENT_ASSET,
                label="Create content asset",
                enabled=not wizard_active,
                target_resource_type="marketing_specialist_output",
                target_resource_id=content_output.id,
            ),
        )

    if asset is not None and asset.status == ContentAssetStatus.DRAFT:
        add(
            _action(
                CampaignActionType.SUBMIT_ASSET_REVIEW,
                label="Submit asset for review",
                enabled=not wizard_active,
                target_resource_type="content_asset",
                target_resource_id=asset.id,
            ),
        )

    if asset is not None and asset.status == ContentAssetStatus.REVIEW:
        add(
            _action(
                CampaignActionType.APPROVE_ASSET,
                label="Approve content asset",
                enabled=not wizard_active,
                target_resource_type="content_asset",
                target_resource_id=asset.id,
            ),
        )

    if asset is not None and asset.status == ContentAssetStatus.APPROVED and brief is None:
        add(
            _action(
                CampaignActionType.CREATE_MEDIA_BRIEF,
                label="Create media brief",
                enabled=not wizard_active,
                target_resource_type="content_asset",
                target_resource_id=asset.id,
            ),
        )

    if brief is not None and brief.status == MediaBriefStatus.DRAFT:
        add(
            _action(
                CampaignActionType.SUBMIT_MEDIA_BRIEF_REVIEW,
                label="Submit media brief for review",
                enabled=not wizard_active,
                target_resource_type="media_brief",
                target_resource_id=brief.id,
            ),
        )

    if brief is not None and brief.status == MediaBriefStatus.REVIEW:
        add(
            _action(
                CampaignActionType.APPROVE_MEDIA_BRIEF,
                label="Approve media brief",
                enabled=not wizard_active,
                target_resource_type="media_brief",
                target_resource_id=brief.id,
            ),
        )

    if asset is not None and asset.status == ContentAssetStatus.APPROVED and package is None:
        add(
            _action(
                CampaignActionType.CREATE_PUBLICATION_PACKAGE,
                label="Create publication package",
                enabled=not wizard_active,
                target_resource_type="content_asset",
                target_resource_id=asset.id,
                safe_payload={"channel": "telegram"},
            ),
        )

    if package is not None and package.status == PublicationPackageStatus.DRAFT:
        add(
            _action(
                CampaignActionType.SUBMIT_PACKAGE_REVIEW,
                label="Submit package for review",
                enabled=not wizard_active,
                target_resource_type="publication_package",
                target_resource_id=package.id,
            ),
        )

    if package is not None and package.status == PublicationPackageStatus.REVIEW:
        add(
            _action(
                CampaignActionType.APPROVE_PACKAGE,
                label="Approve publication package",
                enabled=not wizard_active,
                target_resource_type="publication_package",
                target_resource_id=package.id,
            ),
        )

    if package is not None and package.status == PublicationPackageStatus.APPROVED and job is None:
        add(
            _action(
                CampaignActionType.CREATE_PUBLICATION_JOB,
                label="Create dry-run publication job",
                enabled=not wizard_active,
                target_resource_type="publication_package",
                target_resource_id=package.id,
            ),
        )

    if job is not None and job.status == PublicationPackageJobStatus.QUEUED:
        if job.schedule_status == PublicationPackageJobScheduleStatus.UNSCHEDULED:
            add(
                _action(
                    CampaignActionType.SCHEDULE_JOB,
                    label="Schedule publication job",
                    enabled=not wizard_active,
                    target_resource_type="publication_package_job",
                    target_resource_id=job.id,
                ),
            )
        add(
            _action(
                CampaignActionType.DRY_RUN_DISPATCH,
                label="Dispatch dry-run",
                enabled=not wizard_active
                and job.schedule_status
                in {
                    PublicationPackageJobScheduleStatus.SCHEDULED,
                    PublicationPackageJobScheduleStatus.DUE,
                },
                disabled_reason="Schedule the job before dry-run dispatch."
                if job.schedule_status == PublicationPackageJobScheduleStatus.UNSCHEDULED
                else None,
                target_resource_type="publication_package_job",
                target_resource_id=job.id,
            ),
        )

    for suggestion in skill_suggestions or []:
        action_type = SKILL_TYPE_TO_ACTION.get(suggestion.skill_type)
        if action_type is None:
            continue
        add(
            _action(
                action_type,
                label=suggestion.label or suggestion.skill_type.value.replace("_", " "),
                enabled=not wizard_active,
                disabled_reason="Finish the active wizard with Advance wizard first."
                if wizard_active
                else None,
                target_resource_type="campaign",
                target_resource_id=campaign.id,
                safe_payload={
                    "skill_type": suggestion.skill_type.value,
                    "expected_output": suggestion.expected_output,
                },
            ),
        )

    primary_type = _resolve_primary_type(next_action, artifacts)
    primary: CampaignAction | None = None
    if primary_type is not None:
        for candidate in actions:
            if candidate.type == primary_type:
                primary = candidate
                break
        if primary is None:
            primary = _action(
                primary_type,
                label=next_action.label,
                enabled=False,
                disabled_reason=next_action.safe_description,
            )

    return primary, actions
