"""LLM request/response logging service — no provider calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateResourceError, InvalidStateError
from app.db.models.llm import LLMRequestTable, LLMResponseTable
from app.db.repositories.llm_requests import LLMRequestRepository, LLMResponseRepository
from app.schemas.contracts import LLMProvider, LLMRequestStatus
from app.services.agent_runs import AgentRunService
from app.services.transaction import transactional


@dataclass(frozen=True)
class LLMRequestWithResponse:
    request: LLMRequestTable
    response: LLMResponseTable | None = None


class LLMRequestService:
    TERMINAL_STATUSES = frozenset(
        {
            LLMRequestStatus.FAILED,
            LLMRequestStatus.CANCELLED,
            LLMRequestStatus.SUCCEEDED,
        },
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._requests = LLMRequestRepository(session)
        self._responses = LLMResponseRepository(session)
        self._agent_runs = AgentRunService(session)

    async def _get_owned_run(self, owner_id: UUID, agent_run_id: UUID):
        return await self._agent_runs.get_run(owner_id, agent_run_id)

    async def create_request(
        self,
        owner_id: UUID,
        *,
        agent_run_id: UUID,
        provider: LLMProvider,
        model: str,
        input_payload: dict[str, Any],
        prompt_metadata: dict[str, Any],
        request_metadata: dict[str, Any],
        task_id: UUID | None = None,
    ) -> LLMRequestTable | None:
        run = await self._get_owned_run(owner_id, agent_run_id)
        if run is None:
            return None

        if task_id is not None and run.task_id is not None and task_id != run.task_id:
            return None
        if task_id is not None and run.task_id is None:
            return None

        row = LLMRequestTable(
            owner_id=owner_id,
            project_id=run.project_id,
            agent_id=run.agent_id,
            agent_run_id=run.id,
            task_id=task_id or run.task_id,
            provider=provider,
            model=model,
            input_payload=input_payload,
            prompt_metadata=prompt_metadata,
            request_metadata=request_metadata,
            status=LLMRequestStatus.QUEUED,
        )
        async with transactional(self._session):
            return await self._requests.create(row)

    async def get_request(self, owner_id: UUID, request_id: UUID) -> LLMRequestTable | None:
        return await self._requests.get_by_id_for_owner(request_id, owner_id)

    async def get_request_with_response(
        self,
        owner_id: UUID,
        request_id: UUID,
    ) -> LLMRequestWithResponse | None:
        request = await self.get_request(owner_id, request_id)
        if request is None:
            return None
        response = await self._responses.get_by_request_id(request.id)
        return LLMRequestWithResponse(request=request, response=response)

    async def list_requests(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
        agent_id: UUID | None = None,
        agent_run_id: UUID | None = None,
        task_id: UUID | None = None,
        status: LLMRequestStatus | None = None,
        provider: LLMProvider | None = None,
        model: str | None = None,
        limit: int = 100,
    ) -> list[LLMRequestTable]:
        return await self._requests.list_by_owner(
            owner_id,
            project_id=project_id,
            agent_id=agent_id,
            agent_run_id=agent_run_id,
            task_id=task_id,
            status=status,
            provider=provider,
            model=model,
            limit=limit,
        )

    async def _get_request_for_update(
        self,
        owner_id: UUID,
        request_id: UUID,
    ) -> LLMRequestTable | None:
        return await self._requests.get_by_id_for_owner(request_id, owner_id)

    def _ensure_can_mutate(self, request: LLMRequestTable) -> None:
        if request.status in self.TERMINAL_STATUSES:
            raise InvalidStateError(f"LLM request is already {request.status}")

    async def _ensure_no_response(self, request_id: UUID) -> None:
        if await self._responses.get_by_request_id(request_id) is not None:
            raise DuplicateResourceError("LLM response already exists for this request")

    async def mark_running(self, owner_id: UUID, request_id: UUID) -> LLMRequestTable | None:
        row = await self._get_request_for_update(owner_id, request_id)
        if row is None:
            return None
        self._ensure_can_mutate(row)
        async with transactional(self._session):
            return await self._requests.set_running(row)

    async def mark_succeeded(
        self,
        owner_id: UUID,
        request_id: UUID,
        *,
        output_payload: dict[str, Any],
        raw_response: dict[str, Any],
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost_estimate: float | None,
        latency_ms: int | None,
        response_metadata: dict[str, Any],
        request_metadata_update: dict[str, Any] | None = None,
    ) -> LLMRequestWithResponse | None:
        row = await self._get_request_for_update(owner_id, request_id)
        if row is None:
            return None
        self._ensure_can_mutate(row)
        await self._ensure_no_response(row.id)

        response_row = LLMResponseTable(
            llm_request_id=row.id,
            output_payload=output_payload,
            raw_response=raw_response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_estimate=cost_estimate,
            latency_ms=latency_ms,
            response_metadata=response_metadata,
        )
        async with transactional(self._session):
            if request_metadata_update:
                row.request_metadata = {**row.request_metadata, **request_metadata_update}
            updated = await self._requests.set_succeeded(row)
            response = await self._responses.attach_response(response_row)
        return LLMRequestWithResponse(request=updated, response=response)

    async def mark_failed(
        self,
        owner_id: UUID,
        request_id: UUID,
        error: str,
        *,
        request_metadata: dict[str, Any] | None = None,
    ) -> LLMRequestTable | None:
        row = await self._get_request_for_update(owner_id, request_id)
        if row is None:
            return None
        self._ensure_can_mutate(row)
        async with transactional(self._session):
            if request_metadata:
                row.request_metadata = {**row.request_metadata, **request_metadata}
            return await self._requests.set_failed(row, error)

    async def mark_cancelled(self, owner_id: UUID, request_id: UUID) -> LLMRequestTable | None:
        row = await self._get_request_for_update(owner_id, request_id)
        if row is None:
            return None
        self._ensure_can_mutate(row)
        async with transactional(self._session):
            return await self._requests.set_cancelled(row)

    async def attach_response(
        self,
        owner_id: UUID,
        request_id: UUID,
        response: LLMResponseTable,
    ) -> LLMRequestWithResponse | None:
        row = await self._get_request_for_update(owner_id, request_id)
        if row is None:
            return None
        if row.status in {LLMRequestStatus.FAILED, LLMRequestStatus.CANCELLED}:
            raise InvalidStateError("Cannot attach response to failed or cancelled request")
        await self._ensure_no_response(row.id)

        response.llm_request_id = row.id
        async with transactional(self._session):
            updated = await self._requests.set_succeeded(row)
            created = await self._responses.attach_response(response)
        return LLMRequestWithResponse(request=updated, response=created)
