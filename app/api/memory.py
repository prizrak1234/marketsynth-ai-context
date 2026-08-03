"""Memory items CRUD API — technical system memory, not agent reasoning."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_memory_owner
from app.api.deps import get_session
from app.api.mappers import memory_to_contract
from app.db.models.memory import MemoryItemTable
from app.db.models.user import UserTable
from app.schemas.contracts import MemoryItem, MemoryLayer
from app.schemas.crud import MemoryItemCreate, MemoryItemCreateRequest, MemoryItemUpdate
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryItem, status_code=status.HTTP_201_CREATED)
async def create_memory_item(
    body: MemoryItemCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MemoryItem:
    if body.project_id is not None:
        project = await ProjectService(session).get_by_id(body.project_id)
        if project is None or project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

    service = MemoryService(session)
    created = await service.create(
        MemoryItemCreate(
            user_id=current_user.id,
            project_id=body.project_id,
            layer=body.layer,
            key=body.key,
            content=body.content,
            metadata=body.metadata,
            expires_at=body.expires_at,
        ),
    )
    return memory_to_contract(created)


@router.get("", response_model=list[MemoryItem])
async def list_memory_items(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    project_id: UUID | None = Query(default=None),
    agent_id: UUID | None = Query(
        default=None,
        description="Filter by tasks.agent_id → matching project_id on memory rows",
    ),
    layer: MemoryLayer | None = Query(default=None),
    limit: int = 100,
) -> list[MemoryItem]:
    if project_id is not None:
        project = await ProjectService(session).get_by_id(project_id)
        if project is None or project.owner_id != current_user.id:
            return []

    service = MemoryService(session)
    rows = await service.list(
        user_id=current_user.id,
        project_id=project_id,
        agent_id=agent_id,
        layer=layer,
        limit=limit,
    )
    return [memory_to_contract(row) for row in rows]


@router.get("/{memory_item_id}", response_model=MemoryItem)
async def get_memory_item(
    memory: MemoryItemTable = Depends(require_memory_owner),
) -> MemoryItem:
    return memory_to_contract(memory)


@router.patch("/{memory_item_id}", response_model=MemoryItem)
async def update_memory_item(
    body: MemoryItemUpdate,
    session: AsyncSession = Depends(get_session),
    memory: MemoryItemTable = Depends(require_memory_owner),
) -> MemoryItem:
    service = MemoryService(session)
    updated = await service.update(memory.id, body)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory item not found",
        )
    return memory_to_contract(updated)


@router.delete("/{memory_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_item(
    session: AsyncSession = Depends(get_session),
    memory: MemoryItemTable = Depends(require_memory_owner),
) -> None:
    service = MemoryService(session)
    deleted = await service.delete(memory.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory item not found",
        )
