"""LLM request/response logging API routes (debug/internal)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.api.mappers import llm_request_to_contract, llm_response_to_contract
from app.core.exceptions import DuplicateResourceError, InvalidStateError
from app.db.models.user import UserTable
from app.schemas.contracts import LLMProvider, LLMRequest, LLMRequestStatus, LLMResponse
from app.schemas.crud import (
    LLMRequestCreateRequest,
    LLMRequestFailedRequest,
    LLMRequestSucceededRequest,
)
from app.services.llm_requests import LLMRequestService

router = APIRouter(prefix="/llm-requests", tags=["llm-requests"])


class LLMRequestDetailResponse(BaseModel):
    request: LLMRequest
    response: LLMResponse | None = None


@router.post("", response_model=LLMRequest, status_code=status.HTTP_201_CREATED)
async def create_llm_request(
    body: LLMRequestCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> LLMRequest:
    service = LLMRequestService(session)
    created = await service.create_request(
        current_user.id,
        agent_run_id=body.agent_run_id,
        provider=body.provider,
        model=body.model,
        input_payload=body.input_payload,
        prompt_metadata=body.prompt_metadata,
        request_metadata=body.request_metadata,
        task_id=body.task_id,
    )
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run or task not found",
        )
    return llm_request_to_contract(created)


@router.get("", response_model=list[LLMRequest])
async def list_llm_requests(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    project_id: UUID | None = Query(default=None),
    agent_id: UUID | None = Query(default=None),
    agent_run_id: UUID | None = Query(default=None),
    task_id: UUID | None = Query(default=None),
    status: LLMRequestStatus | None = Query(default=None),
    provider: LLMProvider | None = Query(default=None),
    model: str | None = Query(default=None),
    limit: int = 100,
) -> list[LLMRequest]:
    service = LLMRequestService(session)
    rows = await service.list_requests(
        current_user.id,
        project_id=project_id,
        agent_id=agent_id,
        agent_run_id=agent_run_id,
        task_id=task_id,
        status=status,
        provider=provider,
        model=model,
        limit=limit,
    )
    return [llm_request_to_contract(row) for row in rows]


@router.get("/{request_id}", response_model=LLMRequestDetailResponse)
async def get_llm_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> LLMRequestDetailResponse:
    service = LLMRequestService(session)
    detail = await service.get_request_with_response(current_user.id, request_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM request not found")
    return LLMRequestDetailResponse(
        request=llm_request_to_contract(detail.request),
        response=llm_response_to_contract(detail.response) if detail.response else None,
    )


@router.post("/{request_id}/running", response_model=LLMRequest)
async def mark_llm_request_running(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> LLMRequest:
    service = LLMRequestService(session)
    try:
        updated = await service.mark_running(current_user.id, request_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM request not found")
    return llm_request_to_contract(updated)


@router.post("/{request_id}/succeeded", response_model=LLMRequestDetailResponse)
async def mark_llm_request_succeeded(
    request_id: UUID,
    body: LLMRequestSucceededRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> LLMRequestDetailResponse:
    service = LLMRequestService(session)
    try:
        result = await service.mark_succeeded(
            current_user.id,
            request_id,
            output_payload=body.output_payload,
            raw_response=body.raw_response,
            input_tokens=body.input_tokens,
            output_tokens=body.output_tokens,
            total_tokens=body.total_tokens,
            cost_estimate=body.cost_estimate,
            latency_ms=body.latency_ms,
            response_metadata=body.response_metadata,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None or result.response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM request not found")
    return LLMRequestDetailResponse(
        request=llm_request_to_contract(result.request),
        response=llm_response_to_contract(result.response),
    )


@router.post("/{request_id}/failed", response_model=LLMRequest)
async def mark_llm_request_failed(
    request_id: UUID,
    body: LLMRequestFailedRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> LLMRequest:
    service = LLMRequestService(session)
    try:
        updated = await service.mark_failed(current_user.id, request_id, body.error)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM request not found")
    return llm_request_to_contract(updated)


@router.post("/{request_id}/cancelled", response_model=LLMRequest)
async def mark_llm_request_cancelled(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> LLMRequest:
    service = LLMRequestService(session)
    try:
        updated = await service.mark_cancelled(current_user.id, request_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM request not found")
    return llm_request_to_contract(updated)
