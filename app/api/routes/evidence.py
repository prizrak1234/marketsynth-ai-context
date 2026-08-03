"""Evidence API (Commercial MVP P0.4) — claims only, no Business Verdict."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import evidence_source_link_to_contract, evidence_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    Evidence,
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceCreateRequest,
    EvidenceInvestigationArea,
    EvidenceLifecycleStatus,
    EvidenceMateriality,
    EvidenceReviewNoteRequest,
    EvidenceSourceLink,
    EvidenceSourceLinkInput,
    EvidenceSummary,
    EvidenceSupersedeRequest,
    EvidenceType,
    EvidenceUpdateRequest,
)
from app.services.evidence_service import EvidenceService

router = APIRouter(
    prefix="/projects/{project_id}/investigations/{investigation_id}/evidence",
    tags=["evidence"],
)


def _map_conflict(exc: InvalidStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=Evidence, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    investigation_id: UUID,
    body: EvidenceCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    service = EvidenceService(session)
    try:
        row = await service.create(current_user.id, project.id, investigation_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    packed = await service.get(current_user.id, project.id, investigation_id, row.id)
    assert packed is not None
    return evidence_to_contract(packed[0], packed[1])


@router.get("", response_model=list[Evidence])
async def list_evidence(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    lifecycle_status: EvidenceLifecycleStatus | None = Query(default=None),
    assessment_state: EvidenceAssessmentState | None = Query(default=None),
    confidence_level: EvidenceConfidenceLevel | None = Query(default=None),
    materiality: EvidenceMateriality | None = Query(default=None),
    evidence_type: EvidenceType | None = Query(default=None),
    investigation_area: EvidenceInvestigationArea | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Evidence]:
    service = EvidenceService(session)
    rows = await service.list_evidence(
        current_user.id,
        project.id,
        investigation_id,
        lifecycle_status=lifecycle_status,
        assessment_state=assessment_state,
        confidence_level=confidence_level,
        materiality=materiality,
        evidence_type=evidence_type,
        investigation_area=investigation_area,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return [evidence_to_contract(row, links) for row, links in rows]


@router.get("/summary", response_model=EvidenceSummary)
async def evidence_summary(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> EvidenceSummary:
    service = EvidenceService(session)
    summary = await service.summary(current_user.id, project.id, investigation_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return summary


@router.get("/{evidence_id}", response_model=Evidence)
async def get_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    service = EvidenceService(session)
    packed = await service.get(
        current_user.id, project.id, investigation_id, evidence_id
    )
    if packed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence_to_contract(packed[0], packed[1])


@router.patch("/{evidence_id}", response_model=Evidence)
async def update_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    service = EvidenceService(session)
    try:
        row = await service.update(
            current_user.id, project.id, investigation_id, evidence_id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    packed = await service.get(current_user.id, project.id, investigation_id, evidence_id)
    assert packed is not None
    return evidence_to_contract(packed[0], packed[1])


async def _action(
    *,
    investigation_id: UUID,
    evidence_id: UUID,
    project: ProjectTable,
    session: AsyncSession,
    current_user: UserTable,
    method_name: str,
    body: EvidenceReviewNoteRequest | None = None,
) -> Evidence:
    service = EvidenceService(session)
    method = getattr(service, method_name)
    try:
        if body is None:
            row = await method(current_user.id, project.id, investigation_id, evidence_id)
        else:
            row = await method(
                current_user.id, project.id, investigation_id, evidence_id, body
            )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    packed = await service.get(current_user.id, project.id, investigation_id, evidence_id)
    assert packed is not None
    return evidence_to_contract(packed[0], packed[1])


@router.post("/{evidence_id}/submit-review", response_model=Evidence)
async def submit_evidence_review(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceReviewNoteRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    return await _action(
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        project=project,
        session=session,
        current_user=current_user,
        method_name="submit_review",
        body=body,
    )


@router.post("/{evidence_id}/accept", response_model=Evidence)
async def accept_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceReviewNoteRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    return await _action(
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        project=project,
        session=session,
        current_user=current_user,
        method_name="accept",
        body=body,
    )


@router.post("/{evidence_id}/reject", response_model=Evidence)
async def reject_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceReviewNoteRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    return await _action(
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        project=project,
        session=session,
        current_user=current_user,
        method_name="reject",
        body=body,
    )


@router.post("/{evidence_id}/mark-conflicting", response_model=Evidence)
async def mark_evidence_conflicting(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceReviewNoteRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    return await _action(
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        project=project,
        session=session,
        current_user=current_user,
        method_name="mark_conflicting",
        body=body,
    )


@router.post("/{evidence_id}/mark-outdated", response_model=Evidence)
async def mark_evidence_outdated(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceReviewNoteRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    return await _action(
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        project=project,
        session=session,
        current_user=current_user,
        method_name="mark_outdated",
        body=body,
    )


@router.post("/{evidence_id}/archive", response_model=Evidence)
async def archive_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceReviewNoteRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    return await _action(
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        project=project,
        session=session,
        current_user=current_user,
        method_name="archive",
        body=body,
    )


@router.post(
    "/{evidence_id}/supersede",
    response_model=Evidence,
    status_code=status.HTTP_201_CREATED,
)
async def supersede_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    body: EvidenceSupersedeRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Evidence:
    service = EvidenceService(session)
    try:
        row = await service.supersede(
            current_user.id, project.id, investigation_id, evidence_id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    packed = await service.get(current_user.id, project.id, investigation_id, row.id)
    assert packed is not None
    return evidence_to_contract(packed[0], packed[1])


@router.post(
    "/{evidence_id}/sources/{source_id}",
    response_model=EvidenceSourceLink,
    status_code=status.HTTP_201_CREATED,
)
async def attach_evidence_source(
    investigation_id: UUID,
    evidence_id: UUID,
    source_id: UUID,
    body: EvidenceSourceLinkInput,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> EvidenceSourceLink:
    service = EvidenceService(session)
    try:
        link = await service.attach_source(
            current_user.id,
            project.id,
            investigation_id,
            evidence_id,
            source_id,
            body,
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return evidence_source_link_to_contract(link)
