"""Idempotent smoke seed — demo user, project, task, and memory item."""

from __future__ import annotations

import asyncio
import sys

from app.db.repositories.user_repo import UserRepository
from app.db.session import close_db, get_engine, get_session_factory, init_db
from app.schemas.contracts import MemoryLayer, TaskStatus, UserRole
from app.schemas.crud import MemoryItemCreate, ProjectCreate, TaskCreate, UserCreate
from app.services.auth import AuthService
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.services.users_service import UserService
from sqlmodel import SQLModel

SMOKE_TELEGRAM_ID = 9_000_001
SMOKE_USER_EMAIL = "smoke@botfazer.local"
SMOKE_USER_NAME = "Smoke Demo User"
SMOKE_PROJECT_NAME = "Smoke Demo Project"
SMOKE_TASK_TITLE = "Smoke demo task"
SMOKE_MEMORY_KEY = "smoke:demo:session"
SMOKE_API_KEY_NAME = "Smoke seed key"


async def _ensure_schema() -> None:
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def run_smoke_seed() -> None:
    await _ensure_schema()
    factory = get_session_factory()

    async with factory() as session:
        user_repo = UserRepository(session)
        user_service = UserService(session)
        project_service = ProjectService(session)
        task_service = TaskService(session)
        memory_service = MemoryService(session)

        auth_service = AuthService(session)

        user = await user_repo.get_by_telegram_id(SMOKE_TELEGRAM_ID)
        if user is None:
            user = await user_service.create(
                UserCreate(
                    telegram_id=SMOKE_TELEGRAM_ID,
                    email=SMOKE_USER_EMAIL,
                    display_name=SMOKE_USER_NAME,
                    role=UserRole.OWNER,
                    is_active=True,
                ),
            )
            print(f"Created user {user.id}")
        else:
            print(f"User already exists {user.id}")

        existing_keys = await auth_service.list_api_keys(user.id)
        smoke_key = next((k for k in existing_keys if k.name == SMOKE_API_KEY_NAME), None)
        if smoke_key is None:
            created_key = await auth_service.create_api_key(user.id, SMOKE_API_KEY_NAME)
            print(f"Created API key prefix={created_key.api_key.key_prefix}")
            print(f"API key (save now): {created_key.plain_key}")
        else:
            print(f"API key already exists prefix={smoke_key.key_prefix}")

        projects = await project_service.list(user_id=user.id)
        project = next((p for p in projects if p.name == SMOKE_PROJECT_NAME), None)
        if project is None:
            project = await project_service.create(
                ProjectCreate(
                    owner_id=user.id,
                    name=SMOKE_PROJECT_NAME,
                    description="Idempotent smoke seed project",
                ),
            )
            print(f"Created project {project.id}")
        else:
            print(f"Project already exists {project.id}")

        tasks = await task_service.list(project_id=project.id)
        task = next((t for t in tasks if t.title == SMOKE_TASK_TITLE), None)
        if task is None:
            task = await task_service.create(
                TaskCreate(
                    project_id=project.id,
                    title=SMOKE_TASK_TITLE,
                    status=TaskStatus.PENDING,
                    input_payload={"source": "smoke_seed"},
                ),
            )
            print(f"Created task {task.id}")
        else:
            print(f"Task already exists {task.id}")

        memory_items = await memory_service.list(
            user_id=user.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
        )
        memory_item = next((m for m in memory_items if m.key == SMOKE_MEMORY_KEY), None)
        if memory_item is None:
            memory_item = await memory_service.create(
                MemoryItemCreate(
                    user_id=user.id,
                    project_id=project.id,
                    layer=MemoryLayer.L1_SESSION,
                    key=SMOKE_MEMORY_KEY,
                    content="Smoke seed session state",
                    metadata={"seed": True},
                ),
            )
            print(f"Created memory item {memory_item.id}")
        else:
            print(f"Memory item already exists {memory_item.id}")

    await close_db()
    print("Smoke seed complete.")


def main() -> int:
    try:
        asyncio.run(run_smoke_seed())
    except Exception as exc:
        print(f"Smoke seed failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
