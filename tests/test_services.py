"""Service layer tests."""

from __future__ import annotations

import pytest
from app.db.models.user import UserTable
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session_factory
from app.schemas.contracts import MemoryLayer, TaskStatus
from app.schemas.crud import (
    MemoryItemCreate,
    ProjectCreate,
    TaskCreate,
    TaskUpdate,
    UserCreate,
)
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.services.transaction import transactional
from app.services.users_service import UserService
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_service_create_and_get(db_session: AsyncSession) -> None:
    service = UserService(db_session)
    created = await service.create(
        UserCreate(telegram_id=100, email="svc@example.com", display_name="Svc User"),
    )
    fetched = await service.get_by_id(created.id)
    assert fetched is not None
    assert fetched.telegram_id == 100
    assert fetched.email == "svc@example.com"


@pytest.mark.asyncio
async def test_project_service_create_and_list(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    owner = await user_repo.create(UserTable(telegram_id=101))

    service = ProjectService(db_session)
    created = await service.create(
        ProjectCreate(owner_id=owner.id, name="Service Project", description="demo"),
    )
    projects = await service.list(user_id=owner.id)
    assert len(projects) == 1
    assert projects[0].id == created.id
    assert projects[0].name == "Service Project"


@pytest.mark.asyncio
async def test_task_service_create_and_update(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    owner = await user_repo.create(UserTable(telegram_id=102))

    project_service = ProjectService(db_session)
    project = await project_service.create(
        ProjectCreate(owner_id=owner.id, name="Task Project"),
    )

    service = TaskService(db_session)
    created = await service.create(
        TaskCreate(project_id=project.id, title="Initial title", status=TaskStatus.PENDING),
    )
    updated = await service.update(
        created.id,
        TaskUpdate(title="Updated title", status=TaskStatus.RUNNING),
    )
    assert updated is not None
    assert updated.title == "Updated title"
    assert updated.status == TaskStatus.RUNNING


@pytest.mark.asyncio
async def test_memory_service_create_and_list(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    owner = await user_repo.create(UserTable(telegram_id=103))

    service = MemoryService(db_session)
    await service.create(
        MemoryItemCreate(
            user_id=owner.id,
            layer=MemoryLayer.L1_SESSION,
            key="svc:session",
            content="service layer state",
            metadata={"source": "test"},
        ),
    )
    items = await service.list(user_id=owner.id, layer=MemoryLayer.L1_SESSION)
    assert len(items) == 1
    assert items[0].key == "svc:session"
    assert items[0].item_metadata == {"source": "test"}


@pytest.mark.asyncio
async def test_service_create_commits(db_session: AsyncSession) -> None:
    service = UserService(db_session)
    created = await service.create(
        UserCreate(telegram_id=8888, email="persist@example.com", display_name="Persisted"),
    )

    factory = get_session_factory()
    async with factory() as verify_session:
        verify_service = UserService(verify_session)
        fetched = await verify_service.get_by_id(created.id)
        assert fetched is not None
        assert fetched.telegram_id == 8888
        assert fetched.email == "persist@example.com"


@pytest.mark.asyncio
async def test_service_rollback_on_error(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    duplicate_tg = 7777

    with pytest.raises(IntegrityError):
        async with transactional(db_session):
            await repo.create(UserTable(telegram_id=duplicate_tg, email="first@test.com"))
            await repo.create(UserTable(telegram_id=duplicate_tg, email="second@test.com"))

    factory = get_session_factory()
    async with factory() as verify_session:
        verify_repo = UserRepository(verify_session)
        assert await verify_repo.get_by_telegram_id(duplicate_tg) is None
