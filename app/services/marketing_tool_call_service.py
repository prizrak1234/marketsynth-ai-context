"""Marketing data tool call orchestration (Phase AI.223)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.db.base import utc_now
from app.db.models.marketing_tool_call import MarketingToolCallTable
from app.db.repositories.marketing_tool_calls import MarketingToolCallRepository
from app.marketing.data_tools.permissions import (
    assert_safe_input_payload,
    assert_tool_enabled,
)
from app.marketing.data_tools.registry import get_marketing_tool_registry
from app.schemas.contracts import MarketingToolCallStatus, MarketingToolType
from app.services.marketing_tool_audit import log_marketing_tool_call
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class MarketingToolCallService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._calls = MarketingToolCallRepository(session)
        self._projects = ProjectService(session)
        self._registry = get_marketing_tool_registry()

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def create_call(
        self,
        owner_id: UUID,
        project_id: UUID,
        tool_type: MarketingToolType,
        input_payload: dict[str, Any],
    ) -> MarketingToolCallTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        assert_tool_enabled(tool_type)
        safe_input = assert_safe_input_payload(input_payload)

        row = MarketingToolCallTable(
            owner_id=owner_id,
            project_id=project_id,
            tool_type=tool_type,
            input_payload=safe_input,
            status=MarketingToolCallStatus.QUEUED,
        )
        async with transactional(self._session):
            row = await self._calls.create(row)

        log_marketing_tool_call(
            call_id=str(row.id),
            project_id=str(project_id),
            tool_type=tool_type,
            status=MarketingToolCallStatus.QUEUED,
        )

        return await self._execute_call(row)

    async def _execute_call(self, row: MarketingToolCallTable) -> MarketingToolCallTable:
        row.status = MarketingToolCallStatus.RUNNING
        row.started_at = utc_now()
        async with transactional(self._session):
            row = await self._calls.update(row)

        log_marketing_tool_call(
            call_id=str(row.id),
            project_id=str(row.project_id),
            tool_type=row.tool_type,
            status=MarketingToolCallStatus.RUNNING,
        )

        try:
            handler = self._registry.get(row.tool_type)
            output, metadata = await handler(dict(row.input_payload or {}))
            row.output_payload = sanitize_payload(output) or {}
            row.safe_metadata = sanitize_payload(metadata) or {}
            row.status = MarketingToolCallStatus.SUCCEEDED
            row.error = None
        except InvalidStateError as exc:
            row.status = MarketingToolCallStatus.FAILED
            row.error = str(exc)[:512]
            row.safe_metadata = {"external_call": False}
        except Exception as exc:
            row.status = MarketingToolCallStatus.FAILED
            row.error = sanitize_payload(str(exc)) if isinstance(str(exc), str) else "tool_failed"
            if isinstance(row.error, str) and len(row.error) > 512:
                row.error = row.error[:512]
            row.safe_metadata = {"external_call": False}

        row.finished_at = utc_now()
        async with transactional(self._session):
            row = await self._calls.update(row)

        log_marketing_tool_call(
            call_id=str(row.id),
            project_id=str(row.project_id),
            tool_type=row.tool_type,
            status=row.status,
            safe_metadata=dict(row.safe_metadata or {}),
            error=row.error,
        )
        return row

    async def get_call(
        self,
        owner_id: UUID,
        project_id: UUID,
        call_id: UUID,
    ) -> MarketingToolCallTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._calls.get_by_id_for_owner(call_id, owner_id, project_id)

    async def list_calls(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        tool_type: MarketingToolType | None = None,
        limit: int = 50,
    ) -> list[MarketingToolCallTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._calls.list_for_project(
            owner_id,
            project_id,
            tool_type=tool_type,
            limit=limit,
        )
