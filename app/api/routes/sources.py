"""Source API (Commercial MVP P0.3) — provenance only, no fetch/Evidence."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    investigation_source_link_to_contract,
    source_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    InvestigationSourceItem,
    InvestigationSourceLink,
    InvestigationSourceLinkCreateRequest,
    InvestigationSourceLinkStatus,
    InvestigationSourceLinkUpdateRequest,
    Source,
    SourceArchiveRequest,
    SourceCreateRequest,
    SourceFreshnessStatus,
    SourceProvenanceType,
    SourceReliabilityLevel,
    SourceReliabilityReviewRequest,
    SourceSnapshot,
    SourceStatus,
    SourceSupersedeRequest,
    SourceType,
)
from app.services.source_service import SourceService

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["sources"])
investigation_sources_router = APIRouter(
    prefix="/projects/{project_id}/investigations/{investigation_id}/sources",
    tags=["investigation-sources"],
)


def _map_conflict(exc: InvalidStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=Source, status_code=status.HTTP_201_CREATED)
async def register_source(
    body: SourceCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Source:
    service = SourceService(session)
    try:
        row = await service.register(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return source_to_contract(row)


@router.get("", response_model=list[Source])
async def list_sources(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    source_type: SourceType | None = Query(default=None),
    provenance_type: SourceProvenanceType | None = Query(default=None),
    freshness_status: SourceFreshnessStatus | None = Query(default=None),
    reliability_level: SourceReliabilityLevel | None = Query(default=None),
    status_filter: SourceStatus | None = Query(default=None, alias="status"),
    publisher: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Source]:
    service = SourceService(session)
    rows = await service.list_sources(
        current_user.id,
        project.id,
        source_type=source_type,
        provenance_type=provenance_type,
        freshness_status=freshness_status,
        reliability_level=reliability_level,
        status=status_filter,
        publisher=publisher,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [source_to_contract(row) for row in rows]


@router.get("/{source_id}", response_model=Source)
async def get_source(
    source_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Source:
    service = SourceService(session)
    row = await service.get(current_user.id, project.id, source_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source_to_contract(row)


@router.get("/{source_id}/versions", response_model=list[Source])
async def list_source_versions(
    source_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[Source]:
    service = SourceService(session)
    rows = await service.list_versions(current_user.id, project.id, source_id)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return [source_to_contract(row) for row in rows]


@router.get("/{source_id}/snapshot", response_model=SourceSnapshot)
async def get_source_snapshot(
    source_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> SourceSnapshot:
    service = SourceService(session)
    snap = await service.snapshot(current_user.id, project.id, source_id)
    if snap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return snap


@router.post("/{source_id}/supersede", response_model=Source, status_code=status.HTTP_201_CREATED)
async def supersede_source(
    source_id: UUID,
    body: SourceSupersedeRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Source:
    service = SourceService(session)
    try:
        row = await service.supersede(current_user.id, project.id, source_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source_to_contract(row)


@router.post("/{source_id}/archive", response_model=Source)
async def archive_source(
    source_id: UUID,
    body: SourceArchiveRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Source:
    service = SourceService(session)
    try:
        row = await service.archive(current_user.id, project.id, source_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source_to_contract(row)


@router.post("/{source_id}/review-reliability", response_model=Source)
async def review_source_reliability(
    source_id: UUID,
    body: SourceReliabilityReviewRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Source:
    service = SourceService(session)
    try:
        row = await service.review_reliability(current_user.id, project.id, source_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source_to_contract(row)


@investigation_sources_router.post(
    "/{source_id}",
    response_model=InvestigationSourceLink,
    status_code=status.HTTP_201_CREATED,
)
async def attach_source_to_investigation(
    investigation_id: UUID,
    source_id: UUID,
    body: InvestigationSourceLinkCreateRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> InvestigationSourceLink:
    service = SourceService(session)
    try:
        link = await service.attach(
            current_user.id,
            project.id,
            investigation_id,
            source_id,
            body,
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return investigation_source_link_to_contract(link)


@investigation_sources_router.get("", response_model=list[InvestigationSourceItem])
async def list_investigation_sources(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: InvestigationSourceLinkStatus | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[InvestigationSourceItem]:
    service = SourceService(session)
    rows = await service.list_investigation_sources(
        current_user.id,
        project.id,
        investigation_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return [
        InvestigationSourceItem(
            link=investigation_source_link_to_contract(link),
            source=source_to_contract(source),
        )
        for link, source in rows
    ]


@investigation_sources_router.patch(
    "/{source_id}",
    response_model=InvestigationSourceLink,
)
async def update_investigation_source_link(
    investigation_id: UUID,
    source_id: UUID,
    body: InvestigationSourceLinkUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> InvestigationSourceLink:
    service = SourceService(session)
    link = await service.update_link(
        current_user.id,
        project.id,
        investigation_id,
        source_id,
        body,
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return investigation_source_link_to_contract(link)


@investigation_sources_router.delete(
    "/{source_id}",
    response_model=InvestigationSourceLink,
)
async def detach_investigation_source_link(
    investigation_id: UUID,
    source_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> InvestigationSourceLink:
    """Soft-detach (excluded). Does not delete Source history."""
    service = SourceService(session)
    link = await service.detach_link(
        current_user.id,
        project.id,
        investigation_id,
        source_id,
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return investigation_source_link_to_contract(link)
