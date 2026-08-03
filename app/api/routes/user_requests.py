"""UserRequest API — Phase H1 conversational intake + H2.5 skill context."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.db.models.user import UserTable
from app.db.models.user_request import UserRequestTable
from app.schemas.contracts import UserRequest
from app.services.user_requests_service import UserRequestService

router = APIRouter(prefix="/user-requests", tags=["user-requests"])


class UserRequestCreateBody(BaseModel):
    text: str = Field(min_length=0, max_length=8000)
    selected_scenario: str | None = Field(default=None, max_length=64)
    source: str = Field(default="home_conversation", max_length=64)
    skill_inputs: dict[str, Any] | None = None
    locale: str = Field(default="ru", max_length=16)
    client_message_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=128)
    conversation_id: UUID | None = None


class UserRequestClarifyBody(BaseModel):
    answer: str = Field(default="", max_length=4000)
    skill_inputs: dict[str, Any] | None = None
    locale: str = Field(default="ru", max_length=16)


class ContentDraftReviewBody(BaseModel):
    action: str = Field(max_length=32)
    note: str | None = Field(default=None, max_length=2000)


def _to_contract(row: UserRequestTable) -> UserRequest:
    snap_count = 0
    if row.knowledge_snapshot_id and row.knowledge_snapshot_hash:
        # Count is stored indirectly via attachment; expose approved_knowledge_count
        # from skill_inputs meta if present, else 1 when snapshot exists.
        snap_count = int((row.skill_inputs or {}).get("_approved_knowledge_count") or 0)
        if snap_count == 0 and row.execution_readiness.value == "ready_for_draft":
            snap_count = 1  # at least attached; UI may load snapshot for exact count
    return UserRequest(
        id=row.id,
        owner_id=row.owner_id,
        text=row.text,
        normalized_text=row.normalized_text,
        selected_scenario=row.selected_scenario,
        route_category=row.route_category,
        route_kind=row.route_kind,
        route_confidence=row.route_confidence,
        status=row.status,
        clarification_question=row.clarification_question,
        clarification_answer=row.clarification_answer,
        project_id=row.project_id,
        task_id=row.task_id,
        assigned_specialist=row.assigned_specialist,
        requires_project=row.requires_project,
        avoids_investigation=row.avoids_investigation,
        next_href=row.next_href,
        next_action_label=row.next_action_label,
        assistant_message=row.assistant_message,
        title=row.title,
        source=row.source,
        skill_code=row.skill_code,
        skill_version=row.skill_version,
        capability_pack_code=row.capability_pack_code,
        capability_pack_version=row.capability_pack_version,
        knowledge_snapshot_id=row.knowledge_snapshot_id,
        knowledge_snapshot_hash=row.knowledge_snapshot_hash,
        execution_readiness=row.execution_readiness,
        missing_inputs=list(row.missing_inputs or []),
        quality_profile_code=row.quality_profile_code,
        skill_inputs=dict(row.skill_inputs or {}),
        approved_knowledge_count=int(
            (row.skill_inputs or {}).get("_approved_knowledge_count") or snap_count
        ),
        generated_visual_asset_ids=[
            UUID(str(x)) if not isinstance(x, UUID) else x
            for x in (row.generated_visual_asset_ids or [])
        ],
        generation_status=row.generation_status,
        generation_warnings=list(row.generation_warnings or []),
        content_draft=row.content_draft,
        content_draft_review_status=row.content_draft_review_status,
        prompt_package_hash=row.prompt_package_hash,
        execution_provider=row.execution_provider,
        execution_model=row.execution_model,
        business_idea_validation=(row.skill_inputs or {}).get("business_idea_validation"),
        client_message_id=row.client_message_id,
        idempotency_key=row.idempotency_key,
        conversation_id=row.conversation_id,
        sequence_number=row.sequence_number,
        assistant_run_id=row.assistant_run_id,
        routing_decision_id=row.routing_decision_id,
        chat_route=row.chat_route,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=UserRequest, status_code=status.HTTP_201_CREATED)
async def create_user_request(
    body: UserRequestCreateBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> UserRequest:
    if not (body.text or "").strip() and not body.selected_scenario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_request",
        )
    service = UserRequestService(session)
    row = await service.create(
        owner_id=current_user.id,
        text=body.text,
        selected_scenario=body.selected_scenario,
        source=body.source,
        skill_inputs=body.skill_inputs,
        locale=body.locale,
        client_message_id=body.client_message_id,
        idempotency_key=body.idempotency_key,
        conversation_id=body.conversation_id,
    )
    return _to_contract(row)


@router.get("", response_model=list[UserRequest])
async def list_user_requests(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[UserRequest]:
    rows = await UserRequestService(session).list_for_owner(current_user.id, limit=limit)
    return [_to_contract(r) for r in rows]


@router.get("/{request_id}", response_model=UserRequest)
async def get_user_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> UserRequest:
    row = await UserRequestService(session).get_for_owner(current_user.id, request_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    return _to_contract(row)


@router.post("/{request_id}/clarify", response_model=UserRequest)
async def clarify_user_request(
    request_id: UUID,
    body: UserRequestClarifyBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> UserRequest:
    if not (body.answer or "").strip() and not body.skill_inputs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_clarification",
        )
    row = await UserRequestService(session).clarify(
        owner_id=current_user.id,
        request_id=request_id,
        answer=body.answer or "",
        skill_inputs=body.skill_inputs,
        locale=body.locale,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    return _to_contract(row)


@router.post("/{request_id}/content-draft/review", response_model=UserRequest)
async def review_content_draft(
    request_id: UUID,
    body: ContentDraftReviewBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> UserRequest:
    from app.schemas.contracts import ContentDraftReviewAction

    try:
        action = ContentDraftReviewAction(body.action)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_review_action",
        ) from exc
    service = UserRequestService(session)
    existing = await service.get_for_owner(current_user.id, request_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    if not existing.content_draft:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="no_draft_to_review")
    row = await service.review_content_draft(
        owner_id=current_user.id,
        request_id=request_id,
        action=action,
        note=body.note,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    return _to_contract(row)
