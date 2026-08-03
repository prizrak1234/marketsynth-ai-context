"""Content assets API (Phase 4.0)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import content_asset_to_contract, content_asset_version_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.contracts import (
    ContentAsset,
    ContentAssetDiffResponse,
    ContentAssetVersion,
)
from app.marketing.strategy_contracts import (
    MarketingStrategyDraftQuality,
    resolve_strategy_draft_quality,
)
from app.schemas.contracts import (
    CreateMediaBriefFromAssetResponse,
    CreatePublicationPackageFromAssetResponse,
)
from app.schemas.marketing import (
    ContentAssetCreateRequest,
    ContentAssetCreateRevisionRequest,
    ContentAssetManualRevisionRequest,
    ContentAssetRollbackRequest,
    ContentAssetUpdateRequest,
    CreateMediaBriefRequest,
    CreatePublicationPackageRequest,
)
from app.services.media_brief_service import MediaBriefService
from app.services.publication_package_service import PublicationPackageService
from app.services.content_asset_service import ContentAssetService

router = APIRouter(
    prefix="/projects/{project_id}/content-assets",
    tags=["content-assets"],
)


@router.post("", response_model=ContentAsset, status_code=status.HTTP_201_CREATED)
async def create_content_asset(
    body: ContentAssetCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        created = await service.create(
            current_user.id,
            project.id,
            asset_type=body.type,
            title=body.title,
            body=body.body,
            metadata=body.metadata,
            status=body.status,
            brief_id=body.brief_id,
            campaign_id=body.campaign_id,
            task_id=body.task_id,
            agent_run_id=body.agent_run_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or linked resource not found",
        )
    return content_asset_to_contract(created)


@router.get("", response_model=list[ContentAsset])
async def list_content_assets(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    brief_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ContentAsset]:
    service = ContentAssetService(session)
    if brief_id is not None:
        rows = await service.list_by_brief(
            current_user.id,
            project.id,
            brief_id,
            include_archived=include_archived,
            limit=limit,
        )
    else:
        rows = await service.list_by_project(
            current_user.id,
            project.id,
            include_archived=include_archived,
            limit=limit,
        )
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project, brief, or linked resource not found",
        )
    return [content_asset_to_contract(row) for row in rows]


@router.get("/diff", response_model=ContentAssetDiffResponse)
async def diff_content_assets(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    from_asset_id: UUID = Query(..., alias="from_asset_id"),
    to_asset_id: UUID = Query(..., alias="to_asset_id"),
) -> ContentAssetDiffResponse:
    service = ContentAssetService(session)
    result = await service.diff_assets(
        current_user.id,
        project.id,
        from_asset_id,
        to_asset_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both content assets not found",
        )
    return ContentAssetDiffResponse.model_validate(result)


@router.get("/{asset_id}/quality", response_model=MarketingStrategyDraftQuality)
async def get_content_asset_quality(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategyDraftQuality:
    service = ContentAssetService(session)
    row = await service.get(current_user.id, project.id, asset_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return resolve_strategy_draft_quality(
        body=row.body or "",
        metadata=row.asset_metadata,
    )


@router.get("/{asset_id}", response_model=ContentAsset)
async def get_content_asset(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    row = await service.get(current_user.id, project.id, asset_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(row)


@router.get("/{asset_id}/versions", response_model=list[ContentAssetVersion])
async def list_content_asset_versions(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[ContentAssetVersion]:
    service = ContentAssetService(session)
    versions = await service.list_versions(current_user.id, project.id, asset_id)
    if versions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return [content_asset_version_to_contract(row) for row in versions]


@router.get("/{asset_id}/versions/diff", response_model=ContentAssetDiffResponse)
async def diff_content_asset_versions(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
) -> ContentAssetDiffResponse:
    service = ContentAssetService(session)
    result = await service.diff_versions(
        current_user.id,
        project.id,
        asset_id,
        from_version,
        to_version,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content asset or version not found",
        )
    return ContentAssetDiffResponse.model_validate(result)


@router.get("/{asset_id}/versions/{version_number}", response_model=ContentAssetVersion)
async def get_content_asset_version(
    asset_id: UUID,
    version_number: int,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAssetVersion:
    service = ContentAssetService(session)
    version = await service.get_version(
        current_user.id,
        project.id,
        asset_id,
        version_number,
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content asset or version not found",
        )
    return content_asset_version_to_contract(version)


@router.get("/{asset_id}/revision-diff", response_model=ContentAssetDiffResponse)
async def diff_content_asset_revision(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAssetDiffResponse:
    service = ContentAssetService(session)
    try:
        result = await service.diff_revision(current_user.id, project.id, asset_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return ContentAssetDiffResponse.model_validate(result)


@router.patch("/{asset_id}", response_model=ContentAsset)
async def update_content_asset(
    asset_id: UUID,
    body: ContentAssetUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        updated = await service.update(
            current_user.id,
            project.id,
            asset_id,
            body.model_dump(exclude_unset=True),
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content asset or linked resource not found",
        )
    return content_asset_to_contract(updated)


@router.post(
    "/{asset_id}/rollback-to-version",
    response_model=ContentAsset,
    status_code=status.HTTP_201_CREATED,
)
async def rollback_content_asset_to_version(
    asset_id: UUID,
    body: ContentAssetRollbackRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        revision = await service.create_rollback_revision(
            current_user.id,
            project.id,
            asset_id,
            body.version_number,
            reason=body.reason,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content asset or version not found",
        )
    return content_asset_to_contract(revision)


@router.post("/{asset_id}/revisions", response_model=ContentAsset)
async def create_manual_content_asset_revision(
    asset_id: UUID,
    body: ContentAssetManualRevisionRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        updated = await service.create_manual_revision(
            current_user.id,
            project.id,
            asset_id,
            title=body.title,
            body=body.body,
            metadata_patch=body.metadata_patch,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(updated)


@router.post(
    "/{asset_id}/create-revision",
    response_model=ContentAsset,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_asset_revision(
    asset_id: UUID,
    body: ContentAssetCreateRevisionRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        revision = await service.create_revision_from_approved(
            current_user.id,
            project.id,
            asset_id,
            title=body.title,
            body=body.body,
            metadata=body.metadata,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(revision)


@router.post("/{asset_id}/submit-review", response_model=ContentAsset)
async def submit_content_asset_for_review(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        updated = await service.submit_for_review_asset(
            current_user.id,
            project.id,
            asset_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(updated)


@router.post("/{asset_id}/approve", response_model=ContentAsset)
async def approve_content_asset(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        approved = await service.approve_asset(current_user.id, project.id, asset_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if approved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(approved)


@router.post("/{asset_id}/archive", response_model=ContentAsset)
async def archive_content_asset_post(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        archived = await service.archive_asset(current_user.id, project.id, asset_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if archived is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(archived)


@router.post(
    "/{asset_id}/create-media-brief",
    response_model=CreateMediaBriefFromAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_media_brief_from_content_asset(
    asset_id: UUID,
    body: CreateMediaBriefRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CreateMediaBriefFromAssetResponse:
    service = MediaBriefService(session)
    try:
        brief = await service.create_from_approved_content_asset(
            current_user.id,
            project.id,
            asset_id,
            title=body.title,
            goal=body.goal,
            target_audience=body.target_audience,
            platform=body.platform,
            creative_direction=body.creative_direction,
            visual_style=body.visual_style,
            composition=body.composition,
            text_overlay=body.text_overlay,
            references=body.references,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    status_value = brief.status.value if hasattr(brief.status, "value") else str(brief.status)
    return CreateMediaBriefFromAssetResponse(
        content_asset_id=asset_id,
        media_brief_id=brief.id,
        media_brief_status=status_value,
    )


@router.post(
    "/{asset_id}/create-publication-package",
    response_model=CreatePublicationPackageFromAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_publication_package_from_asset(
    asset_id: UUID,
    body: CreatePublicationPackageRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CreatePublicationPackageFromAssetResponse:
    service = PublicationPackageService(session)
    try:
        package = await service.create_from_approved_asset(
            current_user.id,
            project.id,
            asset_id,
            channel=body.channel,
            title=body.title,
            body=body.body,
            cta=body.cta,
            metadata=body.metadata,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    channel_value = package.channel.value if hasattr(package.channel, "value") else str(package.channel)
    status_value = package.status.value if hasattr(package.status, "value") else str(package.status)
    return CreatePublicationPackageFromAssetResponse(
        content_asset_id=asset_id,
        publication_package_id=package.id,
        publication_package_status=status_value,
        channel=channel_value,
    )


@router.delete("/{asset_id}", response_model=ContentAsset)
async def archive_content_asset(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentAsset:
    service = ContentAssetService(session)
    try:
        archived = await service.archive_asset(current_user.id, project.id, asset_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if archived is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")
    return content_asset_to_contract(archived)
