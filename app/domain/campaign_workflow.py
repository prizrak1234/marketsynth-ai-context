"""Campaign execution workflow — computed read model (Phase 13.0 / 14.2)."""



from __future__ import annotations



from dataclasses import dataclass

from uuid import UUID



from app.marketing.contracts import ContentAssetStatus

from app.schemas.contracts import (

    CampaignWorkflowRecommendedAction,

    CampaignWorkflowState,

)

from app.schemas.marketing_campaigns import CampaignWorkflowCounts





@dataclass(frozen=True)

class WorkflowAssetFacts:

    asset_id: UUID

    status: ContentAssetStatus

    current_version_number: int

    source_asset_id: UUID | None





@dataclass(frozen=True)

class CampaignWorkflowInput:

    plan_drafts_count: int

    assets: tuple[WorkflowAssetFacts, ...]

    succeeded_job_asset_ids: frozenset[UUID]

    pending_review_assets: int = 0





@dataclass(frozen=True)

class CampaignWorkflowComputation:

    workflow_state: CampaignWorkflowState

    counts: CampaignWorkflowCounts

    next_recommended_action: CampaignWorkflowRecommendedAction





def _active_assets(assets: tuple[WorkflowAssetFacts, ...]) -> list[WorkflowAssetFacts]:

    return [asset for asset in assets if asset.status != ContentAssetStatus.ARCHIVED]





def _has_revision_activity(asset: WorkflowAssetFacts) -> bool:

    return asset.current_version_number > 1 or asset.source_asset_id is not None





def _build_counts(

    *,

    plan_drafts_count: int,

    assets: tuple[WorkflowAssetFacts, ...],

    pending_review_assets: int,

) -> CampaignWorkflowCounts:

    assets_draft = sum(1 for asset in assets if asset.status == ContentAssetStatus.DRAFT)

    assets_approved = sum(

        1 for asset in assets if asset.status == ContentAssetStatus.APPROVED

    )

    assets_total = assets_draft + assets_approved

    return CampaignWorkflowCounts(

        plan_drafts=plan_drafts_count,

        assets_total=assets_total,

        assets_approved=assets_approved,

        assets_draft=assets_draft,

        pending_review_assets=pending_review_assets,

    )





def _is_completed(

    active: list[WorkflowAssetFacts],

    succeeded_job_asset_ids: frozenset[UUID],

) -> bool:

    if not active:

        return False

    active_ids = {asset.asset_id for asset in active}

    return active_ids.issubset(succeeded_job_asset_ids)





def _recommended_action_for_state(

    state: CampaignWorkflowState,

) -> CampaignWorkflowRecommendedAction:

    mapping = {

        CampaignWorkflowState.PLANNING: CampaignWorkflowRecommendedAction.CREATE_PLAN_DRAFT,

        CampaignWorkflowState.PLAN_READY: CampaignWorkflowRecommendedAction.GENERATE_ASSETS,

        CampaignWorkflowState.ASSETS_GENERATED: CampaignWorkflowRecommendedAction.REVIEW_ASSETS,

        CampaignWorkflowState.CONTENT_IN_REVISION: (

            CampaignWorkflowRecommendedAction.REVIEW_ASSETS

        ),

        CampaignWorkflowState.READY_FOR_REVIEW: (

            CampaignWorkflowRecommendedAction.HUMAN_REVIEW_REQUIRED

        ),

        CampaignWorkflowState.APPROVED_FOR_PUBLICATION: (

            CampaignWorkflowRecommendedAction.SCHEDULE_PUBLICATION

        ),

        CampaignWorkflowState.COMPLETED: CampaignWorkflowRecommendedAction.NONE,

    }

    return mapping[state]





def compute_campaign_workflow(input_data: CampaignWorkflowInput) -> CampaignWorkflowComputation:

    counts = _build_counts(

        plan_drafts_count=input_data.plan_drafts_count,

        assets=input_data.assets,

        pending_review_assets=input_data.pending_review_assets,

    )

    active = _active_assets(input_data.assets)

    has_revision = any(_has_revision_activity(asset) for asset in active)



    if _is_completed(active, input_data.succeeded_job_asset_ids):

        state = CampaignWorkflowState.COMPLETED

    elif input_data.pending_review_assets > 0:

        state = CampaignWorkflowState.READY_FOR_REVIEW

    elif counts.assets_total > 0 and counts.assets_approved == counts.assets_total:

        state = CampaignWorkflowState.APPROVED_FOR_PUBLICATION

    elif counts.assets_draft > 0 and counts.assets_approved == 0 and has_revision:

        state = CampaignWorkflowState.CONTENT_IN_REVISION

    elif counts.assets_total > 0:

        state = CampaignWorkflowState.ASSETS_GENERATED

    elif counts.plan_drafts > 0:

        state = CampaignWorkflowState.PLAN_READY

    else:

        state = CampaignWorkflowState.PLANNING



    return CampaignWorkflowComputation(

        workflow_state=state,

        counts=counts,

        next_recommended_action=_recommended_action_for_state(state),

    )


