"""Content production provenance helpers for tests and API (Phase AI.83)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.schemas.demo_flow import ContentProductionProvenanceResponse, ProvenanceNodeSummary
from app.schemas.contracts import MarketingSpecialistType


def _node(
    entity_id: UUID,
    *,
    status: str | None = None,
    safe_summary: str | None = None,
) -> ProvenanceNodeSummary:
    return ProvenanceNodeSummary(
        id=entity_id,
        status=status,
        safe_summary=safe_summary,
    )


async def build_content_production_provenance(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    publication_job_id: UUID,
) -> ContentProductionProvenanceResponse | None:
    jobs = PublicationPackageJobRepository(session)
    job = await jobs.get_by_id_for_owner(publication_job_id, owner_id, project_id)
    if job is None:
        return None

    packages = PublicationPackageRepository(session)
    package = await packages.get_by_id_for_owner(
        job.publication_package_id,
        owner_id,
        project_id,
    )

    asset = None
    brief = None
    media_asset = None
    copywriter = None
    run = None
    plan = None
    channel = await PublishingChannelRepository(session).get_for_owner(
        job.channel_id,
        owner_id=owner_id,
        project_id=project_id,
    )

    if package is not None:
        asset = await ContentAssetRepository(session).get_by_id_for_owner(
            package.content_asset_id,
            owner_id,
            project_id,
        )

    if asset is not None:
        if asset.source_execution_run_id is not None:
            run = await MarketingPlanExecutionRunRepository(session).get_by_id_for_owner(
                asset.source_execution_run_id,
                owner_id,
                project_id,
            )
        if asset.source_marketing_plan_id is not None:
            plan = await MarketingPlanRepository(session).get_by_id_for_owner(
                asset.source_marketing_plan_id,
                owner_id,
                project_id,
            )
        if asset.source_specialist_output_id is not None:
            copywriter = await MarketingSpecialistOutputRepository(session).get_by_id_for_owner(
                asset.source_specialist_output_id,
                owner_id,
                project_id,
            )
        briefs = await MediaBriefRepository(session).list_by_project(
            owner_id,
            project_id,
            content_asset_id=asset.id,
            limit=1,
        )
        if briefs:
            brief = briefs[0]
            media_rows = await MediaAssetRepository(session).list_by_project(
                owner_id,
                project_id,
                media_brief_id=brief.id,
                limit=1,
            )
            if media_rows:
                media_asset = media_rows[0]

    if copywriter is None and run is not None:
        outputs = await MarketingSpecialistOutputRepository(session).list_by_project(
            owner_id,
            project_id,
            execution_run_id=run.id,
            specialist=MarketingSpecialistType.COPYWRITER,
            limit=1,
        )
        if outputs:
            copywriter = outputs[0]

    return ContentProductionProvenanceResponse(
        publication_package_job_id=job.id,
        source_scenario_id=plan.source_scenario_id if plan else None,
        source_scenario_name=plan.source_scenario_name if plan else None,
        source_wizard_run_id=(
            str((plan.project_context or {}).get("wizard_run_id"))
            if plan and (plan.project_context or {}).get("wizard_run_id")
            else None
        ),
        source_campaign_id=(
            str((plan.project_context or {}).get("source_campaign_id"))
            if plan and (plan.project_context or {}).get("source_campaign_id")
            else (
                str((asset.asset_metadata or {}).get("source_campaign_id"))
                if asset and (asset.asset_metadata or {}).get("source_campaign_id")
                else None
            )
        ),
        marketing_plan=_node(
            plan.id,
            status=plan.status.value if plan else None,
            safe_summary=(plan.title[:120] if plan and plan.title else None),
        )
        if plan
        else None,
        execution_run=_node(
            run.id,
            status=run.status.value if run else None,
            safe_summary=f"run v{run.marketing_plan_version_number}" if run else None,
        )
        if run
        else None,
        copywriter_output=_node(
            copywriter.id,
            status=copywriter.status.value if copywriter else None,
            safe_summary=copywriter.title[:120] if copywriter and copywriter.title else None,
        )
        if copywriter
        else None,
        content_asset=_node(
            asset.id,
            status=asset.status.value if asset else None,
            safe_summary=asset.title[:120] if asset and asset.title else None,
        )
        if asset
        else None,
        media_brief=_node(
            brief.id,
            status=brief.status.value if brief else None,
            safe_summary=brief.title[:120] if brief and getattr(brief, "title", None) else None,
        )
        if brief
        else None,
        media_asset=_node(
            media_asset.id,
            status=media_asset.status.value if media_asset else None,
            safe_summary=media_asset.media_type.value if media_asset else None,
        )
        if media_asset
        else None,
        publication_package=_node(
            package.id,
            status=package.status.value if package else None,
            safe_summary=package.channel.value if package else None,
        )
        if package
        else None,
        publication_package_job=_node(
            job.id,
            status=job.status.value,
            safe_summary=job.schedule_status.value,
        ),
        publishing_channel=_node(
            channel.id,
            status=channel.status.value if channel else None,
            safe_summary=channel.channel_type.value if channel else None,
        )
        if channel
        else None,
    )
