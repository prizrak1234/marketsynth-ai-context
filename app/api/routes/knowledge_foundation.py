"""Knowledge Inventory + durable store API (Phase H2.1–H2.4)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.db.models.user import UserTable
from app.knowledge_foundation.admission import KNOWLEDGE_ADMISSION_RULES, required_metadata_fields
from app.knowledge_foundation.allowlists import (
    KNOWLEDGE_SOURCE_ALLOWLIST,
    KNOWLEDGE_SOURCE_BLOCKLIST_PREFIXES,
)
from app.knowledge_foundation.ingestion import (
    ingest_approved_content_pack,
    ingestion_manifest_v1,
)
from app.knowledge_foundation.inventory import filter_inventory, get_inventory_item
from app.knowledge_foundation.migration_manifest import (
    FIRST_APPROVED_PACK_IDS,
    list_manifest,
)
from app.knowledge_foundation.retrieval_adapter import (
    RETRIEVAL_POLICY_VERSION,
    KnowledgeRetrievalAdapter,
)
from app.knowledge_foundation.retrieval_policy import RETRIEVAL_ORDER
from app.knowledge_foundation.review_service import (
    KnowledgeReviewError,
    approve_knowledge_item,
    reject_knowledge_item,
)
from app.knowledge_foundation.snapshot_service import KnowledgeSnapshotService
from app.knowledge_foundation.storage_decision import (
    BULK_REPO_INGESTION_ENABLED,
    EMBEDDINGS_ENABLED,
    SELECTED_STORAGE_OPTION,
    STORAGE_DECISION_RATIONALE,
)
from app.knowledge_foundation.store import (
    KnowledgeStoreError,
    KnowledgeStoreService,
    row_to_stored,
)
from app.schemas.contracts import (
    KnowledgeApproveRequest,
    KnowledgeDomain,
    KnowledgeInventoryFilter,
    KnowledgeItem,
    KnowledgeItemStatus,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
    KnowledgeReviewRequest,
    KnowledgeSnapshot,
    KnowledgeSupersedeRequest,
    KnowledgeType,
    SpecialistSkillCode,
    StoredKnowledgeItem,
)

router = APIRouter(prefix="/knowledge-foundation", tags=["knowledge-foundation"])


@router.get("/inventory", response_model=list[KnowledgeItem])
async def list_knowledge_inventory(
    current_user: UserTable = Depends(require_active_user),
    knowledge_type: KnowledgeType | None = Query(default=None),
    domain: KnowledgeDomain | None = Query(default=None),
    status_filter: KnowledgeItemStatus | None = Query(default=None, alias="status"),
    specialist_role: str | None = Query(default=None),
    locale: str | None = Query(default=None),
) -> list[KnowledgeItem]:
    _ = current_user
    return filter_inventory(
        KnowledgeInventoryFilter(
            knowledge_type=knowledge_type,
            domain=domain,
            status=status_filter,
            specialist_role=specialist_role,
            locale=locale,
        )
    )


@router.get("/inventory/{item_id}", response_model=KnowledgeItem)
async def get_knowledge_inventory_item(
    item_id: str,
    current_user: UserTable = Depends(require_active_user),
) -> KnowledgeItem:
    _ = current_user
    item = get_inventory_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found")
    return item


@router.post("/inventory/{item_id}/approve", response_model=KnowledgeItem)
async def approve_inventory_item(
    item_id: str,
    body: KnowledgeReviewRequest | None = None,
    current_user: UserTable = Depends(require_active_user),
) -> KnowledgeItem:
    try:
        return approve_knowledge_item(
            item_id,
            reviewed_by=str(current_user.id),
            note=body.note if body else None,
        )
    except KnowledgeReviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/inventory/{item_id}/reject", response_model=KnowledgeItem)
async def reject_inventory_item(
    item_id: str,
    body: KnowledgeReviewRequest | None = None,
    current_user: UserTable = Depends(require_active_user),
) -> KnowledgeItem:
    try:
        return reject_knowledge_item(
            item_id,
            reviewed_by=str(current_user.id),
            note=body.note if body else None,
        )
    except KnowledgeReviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/items", response_model=list[StoredKnowledgeItem])
async def list_stored_knowledge(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: KnowledgeItemStatus | None = Query(default=None, alias="status"),
    locale: str | None = Query(default=None),
) -> list[StoredKnowledgeItem]:
    _ = current_user
    rows = await KnowledgeStoreService(session).list_items(
        status=status_filter,
        locale=locale,
    )
    return [row_to_stored(r) for r in rows]


@router.post("/items/ingest-content-pack", response_model=list[StoredKnowledgeItem])
async def ingest_content_pack(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[StoredKnowledgeItem]:
    rows = await ingest_approved_content_pack(
        session,
        reviewed_by=str(current_user.id),
    )
    return [row_to_stored(r) for r in rows]


@router.post("/items/{item_id}/approve", response_model=StoredKnowledgeItem)
async def approve_stored_item(
    item_id: UUID,
    body: KnowledgeApproveRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> StoredKnowledgeItem:
    try:
        row = await KnowledgeStoreService(session).approve(
            item_id,
            reviewed_by=str(current_user.id),
            rationale=body.rationale if body else None,
        )
    except KnowledgeStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return row_to_stored(row)


@router.post("/items/{item_id}/reject", response_model=StoredKnowledgeItem)
async def reject_stored_item(
    item_id: UUID,
    body: KnowledgeReviewRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> StoredKnowledgeItem:
    try:
        row = await KnowledgeStoreService(session).reject(
            item_id,
            reviewed_by=str(current_user.id),
            rationale=body.note if body else None,
        )
    except KnowledgeStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return row_to_stored(row)


@router.post("/items/{item_id}/archive", response_model=StoredKnowledgeItem)
async def archive_stored_item(
    item_id: UUID,
    body: KnowledgeReviewRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> StoredKnowledgeItem:
    try:
        row = await KnowledgeStoreService(session).archive(
            item_id,
            reviewed_by=str(current_user.id),
            rationale=body.note if body else None,
        )
    except KnowledgeStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return row_to_stored(row)


@router.post("/items/{item_id}/supersede", response_model=StoredKnowledgeItem)
async def supersede_stored_item(
    item_id: UUID,
    body: KnowledgeSupersedeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> StoredKnowledgeItem:
    try:
        row = await KnowledgeStoreService(session).supersede(
            item_id,
            content=body.content,
            version=body.version,
            reviewed_by=str(current_user.id),
            source_uri=body.source_uri,
            source_hash=body.source_hash,
            rationale=body.rationale,
            locale=body.locale,
            tags=body.tags,
        )
    except KnowledgeStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return row_to_stored(row)


@router.get("/policy")
async def get_knowledge_policy(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    return {
        "admission_rules": KNOWLEDGE_ADMISSION_RULES,
        "required_metadata_fields": list(required_metadata_fields()),
        "retrieval_order": list(RETRIEVAL_ORDER),
        "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
        "storage_option": SELECTED_STORAGE_OPTION.value,
        "storage_rationale": STORAGE_DECISION_RATIONALE,
        "embeddings_enabled": EMBEDDINGS_ENABLED,
        "bulk_repo_ingestion_enabled": BULK_REPO_INGESTION_ENABLED,
        "source_allowlist": sorted(KNOWLEDGE_SOURCE_ALLOWLIST),
        "source_blocklist_prefixes": list(KNOWLEDGE_SOURCE_BLOCKLIST_PREFIXES),
        "first_approved_pack_ids": list(FIRST_APPROVED_PACK_IDS),
        "migration_manifest": list_manifest(),
        "ingestion_manifest_v1": ingestion_manifest_v1(),
        "execution_enabled": False,
        "agent_run_enabled": False,
        "llm_enabled": False,
    }


@router.post("/retrieve", response_model=KnowledgeRetrievalResult)
async def retrieve_knowledge(
    body: KnowledgeRetrievalRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_content: bool = Query(default=False),
) -> KnowledgeRetrievalResult:
    if body.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner_mismatch")
    return await KnowledgeRetrievalAdapter(session).retrieve(
        body,
        include_content=include_content,
    )


@router.get("/retrieval-preview")
async def retrieval_preview(
    skill_code: SpecialistSkillCode = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    project_id: str | None = Query(default=None),
    locale: str = Query(default="ru"),
) -> dict:
    project_uuid = UUID(project_id) if project_id else None
    result = await KnowledgeRetrievalAdapter(session).retrieve(
        KnowledgeRetrievalRequest(
            skill_code=skill_code.value,
            owner_id=current_user.id,
            project_id=project_uuid,
            locale=locale,
        ),
        include_content=False,
    )
    return {
        "skill_code": skill_code.value,
        "hits": [item.model_dump(mode="json") for item in result.items],
        "result": result.model_dump(mode="json"),
        "embeddings_used": False,
        "similarity_as_confidence": False,
        "llm_used": False,
    }


@router.get("/snapshots/{snapshot_id}", response_model=KnowledgeSnapshot)
async def get_snapshot(
    snapshot_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> KnowledgeSnapshot:
    row = await KnowledgeSnapshotService(session).get_for_owner(current_user.id, snapshot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    return KnowledgeSnapshotService(session).to_contract(row)
