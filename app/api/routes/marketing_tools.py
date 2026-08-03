"""Marketing data tool call API (Phase AI.223)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import marketing_tool_call_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import MarketingToolCall, MarketingToolType
from app.services.marketing_tool_call_service import MarketingToolCallService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-tools",
    tags=["marketing-tools"],
)


class MarketingToolCallCreateRequest(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)


def _invalid_state_http(exc: InvalidStateError) -> HTTPException:
    code = str(exc)
    if code == "marketing_data_tools_disabled":
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Marketing data tools are disabled",
        )
    if code == "marketing_tool_forbidden_input_key":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Input payload contains forbidden secret-like keys",
        )
    if code == "marketing_tool_invalid_input":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid tool input payload",
        )
    raise exc


@router.post(
    "/{tool_type}/calls",
    response_model=MarketingToolCall,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketing_tool_call(
    tool_type: MarketingToolType,
    body: MarketingToolCallCreateRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> MarketingToolCall:
    service = MarketingToolCallService(session)
    try:
        row = await service.create_call(
            user.id,
            project_id,
            tool_type,
            body.input_payload,
        )
    except InvalidStateError as exc:
        raise _invalid_state_http(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return marketing_tool_call_to_contract(row)


@router.get("/calls", response_model=list[MarketingToolCall])
async def list_marketing_tool_calls(
    project_id: UUID,
    tool_type: MarketingToolType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[MarketingToolCall]:
    service = MarketingToolCallService(session)
    rows = await service.list_calls(
        user.id,
        project_id,
        tool_type=tool_type,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_tool_call_to_contract(row) for row in rows]


@router.get("/calls/{call_id}", response_model=MarketingToolCall)
async def get_marketing_tool_call(
    call_id: UUID,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> MarketingToolCall:
    service = MarketingToolCallService(session)
    row = await service.get_call(user.id, project_id, call_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool call not found")
    return marketing_tool_call_to_contract(row)
