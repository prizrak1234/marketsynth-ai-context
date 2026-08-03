"""Unified agent run execution — routes to classic or LangGraph (Phase 3.13)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, ExecutorError, InvalidStateError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.executors.agent_run_executor import AgentRunExecutor
from app.executors.engine_resolver import ExecutionEngine, resolve_execution_engine
from app.executors.execution_guard import CLAIM_SOURCE_EXECUTE, prepare_agent_run_execute
from app.executors.execution_metadata import get_execution_engine_from_run, stamp_execution_on_run
from app.graphs.runner import AgentGraphRunner
from app.services.agent_runs import AgentRunService
from app.services.llm_requests import LLMRequestService
from app.services.projects_service import ProjectService


class AgentRunCoordinator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._agent_runs = AgentRunService(session)
        self._projects = ProjectService(session)
        self._llm_requests = LLMRequestService(session)

    async def execute_run(
        self,
        run_id: UUID,
        owner_id: UUID,
        *,
        request_engine: str | None = None,
        idempotency_key: str | None = None,
        settings: Settings | None = None,
    ) -> tuple[AgentRunTable, ExecutionEngine]:
        cfg = settings or get_settings()
        prepared = await prepare_agent_run_execute(
            self._agent_runs,
            owner_id,
            run_id,
            idempotency_key=idempotency_key,
        )

        run = prepared.run
        project = await self._projects.get_by_id(run.project_id)
        engine = resolve_execution_engine(
            cfg,
            project=project,
            request_override=request_engine,
        )

        if prepared.kind == "cached":
            cached_engine = get_execution_engine_from_run(run) or engine
            return run, cached_engine

        try:
            if engine == "langgraph":
                final_run = await self._execute_langgraph(run_id, owner_id, already_claimed=True)
            else:
                final_run = await self._execute_classic(run_id, owner_id, already_claimed=True)
        except (NotFoundError, InvalidStateError, ConflictError):
            await stamp_execution_on_run(
                self._agent_runs,
                owner_id,
                run_id,
                engine,
                idempotency_key=prepared.idempotency_key,
                started_at=prepared.started_at,
                claim_source=CLAIM_SOURCE_EXECUTE,
            )
            raise
        except ExecutorError:
            await stamp_execution_on_run(
                self._agent_runs,
                owner_id,
                run_id,
                engine,
                idempotency_key=prepared.idempotency_key,
                started_at=prepared.started_at,
                claim_source=CLAIM_SOURCE_EXECUTE,
            )
            raise

        finished_at = (
            final_run.finished_at.isoformat()
            if final_run.finished_at
            else None
        )
        stamped = await stamp_execution_on_run(
            self._agent_runs,
            owner_id,
            run_id,
            engine,
            idempotency_key=prepared.idempotency_key,
            started_at=prepared.started_at,
            finished_at=finished_at,
            claim_source=CLAIM_SOURCE_EXECUTE,
        )
        if stamped is not None:
            final_run = stamped
        return final_run, engine

    async def _execute_classic(
        self,
        run_id: UUID,
        owner_id: UUID,
        *,
        already_claimed: bool = False,
    ) -> AgentRunTable:
        executor = AgentRunExecutor(
            self._session,
            self._agent_runs,
            self._llm_requests,
        )
        return await executor.execute_run(run_id, owner_id, already_claimed=already_claimed)

    async def _execute_langgraph(
        self,
        run_id: UUID,
        owner_id: UUID,
        *,
        already_claimed: bool = False,
    ) -> AgentRunTable:
        runner = AgentGraphRunner(
            self._session,
            self._agent_runs,
            self._llm_requests,
        )
        return await runner.execute_run(run_id, owner_id, already_claimed=already_claimed)
