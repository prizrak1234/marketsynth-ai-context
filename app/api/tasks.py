"""Tasks CRUD API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_task_owner
from app.api.deps import get_session
from app.api.mappers import task_to_contract
from app.db.models.task import TaskTable
from app.db.models.user import UserTable
from app.schemas.contracts import Task
from app.schemas.crud import TaskCreate, TaskUpdate
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Task:
    project = await ProjectService(session).get_by_id(body.project_id)
    if project is None or project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    service = TaskService(session)
    if not await service.validate_agent_assignment(
        owner_id=current_user.id,
        project_id=body.project_id,
        agent_id=body.agent_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    created = await service.create(body)
    return task_to_contract(created)


@router.get("", response_model=list[Task])
async def list_tasks(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    project_id: UUID | None = Query(default=None),
    limit: int = 100,
) -> list[Task]:
    service = TaskService(session)
    rows = await service.list_for_user(current_user.id, project_id=project_id, limit=limit)
    return [task_to_contract(row) for row in rows]


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task: TaskTable = Depends(require_task_owner),
) -> Task:
    return task_to_contract(task)


@router.patch("/{task_id}", response_model=Task)
async def update_task(
    body: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    task: TaskTable = Depends(require_task_owner),
    current_user: UserTable = Depends(require_active_user),
) -> Task:
    service = TaskService(session)
    if body.agent_id is not None and not await service.validate_agent_assignment(
        owner_id=current_user.id,
        project_id=task.project_id,
        agent_id=body.agent_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    updated = await service.update(task.id, body)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task_to_contract(updated)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    session: AsyncSession = Depends(get_session),
    task: TaskTable = Depends(require_task_owner),
) -> None:
    service = TaskService(session)
    deleted = await service.delete(task.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
