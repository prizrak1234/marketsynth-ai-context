"""BusinessVerdict API (Commercial MVP P0.5).

Commercial viability decision — not execution/publication approval, not Strategy.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    business_verdict_snapshot_to_contract,
    business_verdict_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    BusinessVerdict,
    BusinessVerdictConfidenceLevel,
    BusinessVerdictCreate,
    BusinessVerdictEvidenceSnapshot,
    BusinessVerdictLifecycleStatus,
    BusinessVerdictReviewRequest,
    BusinessVerdictUpdate,
    VerdictKind,
)
from app.services.business_verdict_service import BusinessVerdictService

investigation_router = APIRouter(
    prefix="/projects/{project_id}/investigations/{investigation_id}/business-verdicts",
    tags=["business-verdicts"],
)

router = APIRouter(
    prefix="/projects/{project_id}/business-verdicts",
    tags=["business-verdicts"],
)


def _map_conflict(exc: InvalidStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


async def _pack(
    service: BusinessVerdictService,
    owner_id: UUID,
    project_id: UUID,
    row,
) -> BusinessVerdict:
    links = await service.list_links(owner_id, project_id, row.id)
    snap = await service.get_snapshot(owner_id, project_id, row.id)
    return business_verdict_to_contract(
        row,
        links=links,
        snapshot=snap,
        strategy_eligibility=service.strategy_eligibility_for(row),
    )


@investigation_router.post("", response_model=BusinessVerdict, status_code=status.HTTP_201_CREATED)
async def create_business_verdict(
    investigation_id: UUID,
    body: BusinessVerdictCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.create(current_user.id, project.id, investigation_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@investigation_router.post(
    "/build-draft",
    response_model=BusinessVerdict,
    status_code=status.HTTP_201_CREATED,
)
async def build_deterministic_draft(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.build_deterministic_draft(
            current_user.id, project.id, investigation_id
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.get("", response_model=list[BusinessVerdict])
async def list_business_verdicts(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    verdict_type: VerdictKind | None = Query(default=None),
    lifecycle_status: BusinessVerdictLifecycleStatus | None = Query(default=None),
    confidence_level: BusinessVerdictConfidenceLevel | None = Query(default=None),
    investigation_id: UUID | None = Query(default=None),
    version: int | None = Query(default=None, ge=1),
    prepared_from: datetime | None = Query(default=None),
    prepared_to: datetime | None = Query(default=None),
    approved_from: datetime | None = Query(default=None),
    approved_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[BusinessVerdict]:
    service = BusinessVerdictService(session)
    rows = await service.list_verdicts(
        current_user.id,
        project.id,
        verdict_type=verdict_type,
        lifecycle_status=lifecycle_status,
        confidence_level=confidence_level,
        investigation_id=investigation_id,
        version=version,
        prepared_from=prepared_from,
        prepared_to=prepared_to,
        approved_from=approved_from,
        approved_to=approved_to,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return [await _pack(service, current_user.id, project.id, row) for row in rows]


@router.get("/latest", response_model=BusinessVerdict)
async def get_latest_business_verdict(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    row = await service.get_latest(current_user.id, project.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.get("/{verdict_id}", response_model=BusinessVerdict)
async def get_business_verdict(
    verdict_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    row = await service.get(current_user.id, project.id, verdict_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.patch("/{verdict_id}", response_model=BusinessVerdict)
async def patch_business_verdict(
    verdict_id: UUID,
    body: BusinessVerdictUpdate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.update_draft(current_user.id, project.id, verdict_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.get("/{verdict_id}/evidence-snapshot", response_model=BusinessVerdictEvidenceSnapshot)
async def get_verdict_evidence_snapshot(
    verdict_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdictEvidenceSnapshot:
    service = BusinessVerdictService(session)
    snap = await service.get_snapshot(current_user.id, project.id, verdict_id)
    if snap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return business_verdict_snapshot_to_contract(snap)


@router.post("/{verdict_id}/submit-review", response_model=BusinessVerdict)
async def submit_business_verdict_review(
    verdict_id: UUID,
    body: BusinessVerdictReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.submit_review(
            current_user.id, project.id, verdict_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.post("/{verdict_id}/approve", response_model=BusinessVerdict)
async def approve_business_verdict(
    verdict_id: UUID,
    body: BusinessVerdictReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.approve(
            current_user.id, project.id, verdict_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.post("/{verdict_id}/reject", response_model=BusinessVerdict)
async def reject_business_verdict(
    verdict_id: UUID,
    body: BusinessVerdictReviewRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.reject(
            current_user.id, project.id, verdict_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.post("/{verdict_id}/return-draft", response_model=BusinessVerdict)
async def return_business_verdict_draft(
    verdict_id: UUID,
    body: BusinessVerdictReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.return_draft(
            current_user.id, project.id, verdict_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.post("/{verdict_id}/archive", response_model=BusinessVerdict)
async def archive_business_verdict(
    verdict_id: UUID,
    body: BusinessVerdictReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.archive(
            current_user.id, project.id, verdict_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.post("/{verdict_id}/supersede", response_model=BusinessVerdict, status_code=status.HTTP_201_CREATED)
async def supersede_business_verdict(
    verdict_id: UUID,
    body: BusinessVerdictCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    service = BusinessVerdictService(session)
    try:
        row = await service.supersede(
            current_user.id, project.id, verdict_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)


@router.post("/{verdict_id}/build-draft", response_model=BusinessVerdict, status_code=status.HTTP_201_CREATED)
async def rebuild_draft_from_verdict_context(
    verdict_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessVerdict:
    """Create a new deterministic draft for the same Investigation (explicit action)."""
    service = BusinessVerdictService(session)
    existing = await service.get(current_user.id, project.id, verdict_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        row = await service.build_deterministic_draft(
            current_user.id, project.id, existing.investigation_id
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await _pack(service, current_user.id, project.id, row)
