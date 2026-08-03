"""KG.2 — Knowledge Governance Operator API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.security import sanitize_payload
from app.db.models.knowledge_governance import BenchmarkCaseTable, BenchmarkDatasetTable
from app.db.models.user import UserTable
from app.knowledge_governance.benchmark_runner import ensure_drilling_benchmark_seeded, run_benchmark
from app.knowledge_governance.lifecycle import LifecycleError
from app.knowledge_governance.operator import KnowledgeGovernanceOperator
from app.schemas.contracts import KnowledgeDomain

router = APIRouter(prefix="/knowledge-governance", tags=["knowledge-governance"])


class CandidateCreateBody(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=200_000)
    source_uri: str = Field(min_length=1, max_length=1000)
    domain: KnowledgeDomain = KnowledgeDomain.OPERATIONS
    language: str = Field(default="ru", max_length=16)
    source_hash: str | None = Field(default=None, max_length=128)
    citation_required: bool = True


class AssignOwnerBody(BaseModel):
    owner_user_id: UUID
    reviewer_user_id: UUID | None = None


class ReviewBody(BaseModel):
    decision: str = Field(max_length=32)
    rationale: str | None = Field(default=None, max_length=4000)
    next_review_days: int = Field(default=90, ge=7, le=730)


class PublishBody(BaseModel):
    expected_lock_version: int | None = None


class SupersedeBody(BaseModel):
    new_content: str = Field(min_length=1, max_length=200_000)
    new_version: str = Field(min_length=1, max_length=32)
    source_uri: str | None = Field(default=None, max_length=1000)


def _http_lifecycle(exc: LifecycleError) -> HTTPException:
    code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail={"code": exc.code, "message": exc.message})


@router.get("/candidates")
async def list_candidates(
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    rows = await op.list_objects(tenant_owner_id=current_user.id, status="draft")
    return {"candidates": rows, "count": len(rows)}


@router.post("/candidates", status_code=status.HTTP_201_CREATED)
async def create_candidate(
    body: CandidateCreateBody,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    clean = sanitize_payload(
        {
            "code": body.code,
            "title": body.title,
            "content": body.content,
            "source_uri": body.source_uri,
        }
    )
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.create_candidate(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            code=str(clean.get("code") or body.code),
            title=str(clean.get("title") or body.title),
            content=str(clean.get("content") or body.content),
            source_uri=str(clean.get("source_uri") or body.source_uri),
            domain=body.domain,
            language=body.language,
            source_hash=body.source_hash,
            citation_required=body.citation_required,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.get("/objects")
async def list_objects(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    rows = await op.list_objects(tenant_owner_id=current_user.id, status=status_filter)
    return {"objects": rows, "count": len(rows)}


@router.get("/objects/{object_id}")
async def get_object(
    object_id: UUID,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.get_object_detail(
            tenant_owner_id=current_user.id, object_id=object_id
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/objects/{object_id}/assign-owner")
async def assign_owner(
    object_id: UUID,
    body: AssignOwnerBody,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.assign_owner(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            object_id=object_id,
            owner_user_id=body.owner_user_id,
            reviewer_user_id=body.reviewer_user_id,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/versions/{version_id}/review")
async def review_version(
    version_id: UUID,
    body: ReviewBody,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    rationale = None
    if body.rationale:
        rationale = str(sanitize_payload({"r": body.rationale}).get("r") or body.rationale)
    try:
        return await op.review_version(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            version_id=version_id,
            decision=body.decision,
            rationale=rationale,
            next_review_days=body.next_review_days,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/versions/{version_id}/validate")
async def validate_version(
    version_id: UUID,
    body: ReviewBody | None = None,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Human validation step — approve review → validated (no auto-publish)."""
    op = KnowledgeGovernanceOperator(session)
    decision = (body.decision if body else "approve") or "approve"
    try:
        return await op.review_version(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            version_id=version_id,
            decision=decision,
            rationale=body.rationale if body else "validated",
            next_review_days=body.next_review_days if body else 90,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/versions/{version_id}/publish")
async def publish_version(
    version_id: UUID,
    body: PublishBody | None = None,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.publish_version(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            version_id=version_id,
            expected_lock_version=body.expected_lock_version if body else None,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/versions/{version_id}/deprecate")
async def deprecate_version(
    version_id: UUID,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.deprecate_version(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            version_id=version_id,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/versions/{version_id}/supersede")
async def supersede_version(
    version_id: UUID,
    body: SupersedeBody,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    clean = sanitize_payload({"content": body.new_content, "uri": body.source_uri or ""})
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.supersede_version(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            version_id=version_id,
            new_content=str(clean.get("content") or body.new_content),
            new_version=body.new_version,
            source_uri=(str(clean.get("uri")) or None) if body.source_uri else None,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.post("/versions/{version_id}/archive")
async def archive_version(
    version_id: UUID,
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    try:
        return await op.archive_version(
            tenant_owner_id=current_user.id,
            actor_user_id=current_user.id,
            version_id=version_id,
        )
    except LifecycleError as exc:
        raise _http_lifecycle(exc) from exc


@router.get("/freshness")
async def freshness_scan(
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    op = KnowledgeGovernanceOperator(session)
    rows = await op.scan_freshness(tenant_owner_id=current_user.id)
    return {"checks": rows, "count": len(rows)}


@router.get("/benchmarks")
async def list_benchmarks(
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    _ = current_user
    await ensure_drilling_benchmark_seeded(session)
    result = await session.execute(select(BenchmarkDatasetTable))
    datasets = result.scalars().all()
    out: list[dict[str, Any]] = []
    for ds in datasets:
        cases = await session.execute(
            select(BenchmarkCaseTable).where(BenchmarkCaseTable.dataset_id == ds.id)
        )
        case_rows = cases.scalars().all()
        out.append(
            {
                "id": str(ds.id),
                "name": ds.name,
                "version": ds.version,
                "domain": ds.domain,
                "case_count": len(case_rows),
            }
        )
    return {"datasets": out, "count": len(out)}


@router.post("/benchmarks/drilling_operations/run")
async def run_drilling_benchmark(
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Deterministic governance checks — no external LLM."""
    return await run_benchmark(
        session, tenant_owner_id=current_user.id, domain="drilling_operations"
    )
