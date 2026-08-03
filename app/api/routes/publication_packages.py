"""Publication packages API — draft packages only, no send (Phase AI.43)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    publication_package_job_to_contract,
    publication_package_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.contracts import PublicationPackage
from app.publishing_foundation.contracts import PublicationPackageJob
from app.services.publication_package_job_service import PublicationPackageJobService
from app.services.publication_package_service import PublicationPackageService

router = APIRouter(
    prefix="/projects/{project_id}/publication-packages",
    tags=["publication-packages"],
)


@router.get("", response_model=list[PublicationPackage])
async def list_publication_packages(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    content_asset_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublicationPackage]:
    service = PublicationPackageService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        content_asset_id=content_asset_id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [publication_package_to_contract(row) for row in rows]


@router.get("/{package_id}", response_model=PublicationPackage)
async def get_publication_package(
    package_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackage:
    service = PublicationPackageService(session)
    row = await service.get(current_user.id, project.id, package_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package not found",
        )
    return publication_package_to_contract(row)


@router.post("/{package_id}/submit-review", response_model=PublicationPackage)
async def submit_publication_package_for_review(
    package_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackage:
    service = PublicationPackageService(session)
    try:
        updated = await service.submit_for_review(
            current_user.id,
            project.id,
            package_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package not found",
        )
    return publication_package_to_contract(updated)


@router.post("/{package_id}/approve", response_model=PublicationPackage)
async def approve_publication_package(
    package_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackage:
    service = PublicationPackageService(session)
    try:
        updated = await service.approve_package(
            current_user.id,
            project.id,
            package_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package not found",
        )
    return publication_package_to_contract(updated)


@router.post("/{package_id}/archive", response_model=PublicationPackage)
async def archive_publication_package(
    package_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackage:
    service = PublicationPackageService(session)
    try:
        updated = await service.archive_package(
            current_user.id,
            project.id,
            package_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package not found",
        )
    return publication_package_to_contract(updated)


@router.post(
    "/{package_id}/publication-jobs",
    response_model=PublicationPackageJob,
    status_code=status.HTTP_201_CREATED,
)
async def create_publication_package_job(
    package_id: UUID,
    response: Response,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    channel_id: UUID = Query(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    try:
        row, created = await service.create_from_approved_package(
            current_user.id,
            project.id,
            package_id,
            channel_id,
            idempotency_key=idempotency_key,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package or channel not found",
        )
    if not created:
        response.status_code = status.HTTP_200_OK
    return publication_package_job_to_contract(row)
