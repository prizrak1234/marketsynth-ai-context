"""FastAPI auth dependencies — API key Bearer and/or browser session cookie."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.agent import AgentTable
from app.db.models.memory import MemoryItemTable
from app.db.models.project import ProjectTable
from app.db.models.task import TaskTable
from app.db.models.user import UserTable
from app.schemas.contracts import UserRole
from app.services.agents import AgentService
from app.services.auth import AuthService
from app.services.beta_access_service import BetaAccessService
from app.services.browser_session_service import BrowserSessionService
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService

log = get_logger(__name__)

# Request-state keys
AUTH_METHOD_KEY = "ms_auth_method"
AUTH_SESSION_ID_KEY = "ms_auth_session_id"


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
    ms_pilot_session: Annotated[str | None, Cookie(alias="ms_pilot_session")] = None,
) -> UserTable:
    settings = get_settings()
    cookie_name = settings.browser_session_cookie_name
    cookie_token = request.cookies.get(cookie_name) or ms_pilot_session

    # Prefer browser session cookie when present
    if cookie_token:
        browser = BrowserSessionService(session)
        result = await browser.authenticate_token(cookie_token)
        if result is None:
            log.info("unauthorized_request", reason="session_invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="session_expired",
            )
        user, browser_session = result
        request.state.ms_auth_method = "browser_session"
        request.state.ms_auth_session_id = str(browser_session.id)
        return user

    if not authorization or not authorization.lower().startswith("bearer "):
        log.info("unauthorized_request", reason="authentication_required")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )

    plain_key = authorization[7:].strip()
    if not plain_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )

    auth_service = AuthService(session)
    result = await auth_service.authenticate_api_key(plain_key)
    if result is None:
        log.info("unauthorized_request", reason="invalid_api_key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    user, _api_key = result
    request.state.ms_auth_method = "api_key"
    return user


async def require_active_user_unrestricted(
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> UserTable:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_disabled",
        )
    return current_user


async def require_active_user(
    current_user: Annotated[UserTable, Depends(require_active_user_unrestricted)],
) -> UserTable:
    BetaAccessService.enforce_mvp_access(current_user)
    return current_user


def require_role(*roles: UserRole) -> Callable[..., UserTable]:
    allowed = set(roles)

    async def _require_role(
        current_user: Annotated[UserTable, Depends(require_active_user)],
    ) -> UserTable:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _require_role


async def require_project_owner(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(require_active_user)],
) -> ProjectTable:
    project = await ProjectService(session).get_by_id(project_id)
    if project is None or project.owner_id != current_user.id:
        log.info(
            "forbidden_or_hidden_resource_access",
            resource="project",
            project_id=str(project_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def require_task_owner(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(require_active_user)],
) -> TaskTable:
    task = await TaskService(session).get_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    project = await ProjectService(session).get_by_id(task.project_id)
    if project is None or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


async def require_memory_owner(
    memory_item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(require_active_user)],
) -> MemoryItemTable:
    memory = await MemoryService(session).get_by_id(memory_item_id)
    if memory is None or memory.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory item not found",
        )

    if memory.project_id is not None:
        project = await ProjectService(session).get_by_id(memory.project_id)
        if project is None or project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory item not found",
            )

    return memory


async def require_agent_owner(
    agent_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(require_active_user)],
) -> AgentTable:
    agent = await AgentService(session).get_agent(agent_id, current_user.id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent
