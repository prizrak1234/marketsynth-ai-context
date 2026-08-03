"""Repository layer CRUD tests."""

from __future__ import annotations

import pytest
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.db.repositories.memory_repo import MemoryRepository
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import MemoryLayer
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_repository_crud(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    created = await repo.create(UserTable(telegram_id=99, email="a@b.co"))
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.telegram_id == 99

    by_tg = await repo.get_by_telegram_id(99)
    assert by_tg is not None

    users = await repo.list(limit=10)
    assert len(users) >= 1

    created.display_name = "Updated"
    await repo.update(created)
    await repo.delete(created)
    assert await repo.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_project_repository_list_by_owner(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    user = await user_repo.create(UserTable(telegram_id=1))

    project_repo = ProjectRepository(db_session)
    project = await project_repo.create(
        ProjectTable(owner_id=user.id, name="Demo", description="x"),
    )
    projects = await project_repo.list_by_owner(user.id)
    assert len(projects) == 1
    assert projects[0].id == project.id


@pytest.mark.asyncio
async def test_memory_repository_list_by_layer(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    user = await user_repo.create(UserTable(telegram_id=2))

    memory_repo = MemoryRepository(db_session)
    from app.db.models.memory import MemoryItemTable

    await memory_repo.create(
        MemoryItemTable(
            user_id=user.id,
            layer=MemoryLayer.L1_SESSION,
            key="session:1",
            content="state",
        ),
    )
    items = await memory_repo.list_by_user(user.id, layer=MemoryLayer.L1_SESSION)
    assert len(items) == 1
    assert items[0].key == "session:1"
