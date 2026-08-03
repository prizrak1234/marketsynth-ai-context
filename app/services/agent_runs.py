"""Agent run logging service — no LLM execution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.db.repositories.agent_runs import AgentRunRepository
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.task_repo import TaskRepository
from app.executors.run_replay_policy import (
    build_replay_metadata,
    normalize_replay_reason,
    validate_replay_source_run,
)
from app.agents.run_depth import MAX_AGENT_RUN_DEPTH, compute_agent_run_depth
from app.schemas.contracts import AgentRunStatus, AgentStatus, AgentType
from app.services.agents import AgentService
from app.services.transaction import transactional


class AgentRunService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AgentRunRepository(session)
        self._tasks = TaskRepository(session)
        self._projects = ProjectRepository(session)
        self._agents = AgentService(session)

    async def _get_owned_agent(self, agent_id: UUID, owner_id: UUID):
        agent = await self._agents.get_agent(agent_id, owner_id)
        if agent is None or agent.status == AgentStatus.ARCHIVED:
            return None
        return agent

    async def _get_owned_task(self, task_id: UUID, owner_id: UUID, project_id: UUID):
        task = await self._tasks.get_by_id(task_id)
        if task is None:
            return None
        project = await self._projects.get_by_id(task.project_id)
        if project is None or project.owner_id != owner_id:
            return None
        if task.project_id != project_id:
            return None
        return task

    async def _validate_parent_agent_run(
        self,
        owner_id: UUID,
        parent_agent_run_id: UUID,
        *,
        project_id: UUID,
    ) -> AgentRunTable:
        parent = await self._repo.get_by_id_for_owner(parent_agent_run_id, owner_id)
        if parent is None:
            raise NotFoundError("Parent agent run not found")
        if parent.project_id != project_id:
            raise InvalidStateError("Parent agent run belongs to a different project")
        parent_depth = await compute_agent_run_depth(self._session, parent, owner_id)
        if parent_depth >= MAX_AGENT_RUN_DEPTH:
            raise InvalidStateError("Maximum agent run depth exceeded")
        parent_agent = await self.get_executable_agent(parent.agent_id, owner_id)
        if parent_agent.type in (AgentType.PROGRAMMER, AgentType.MEDIA):
            raise InvalidStateError(f"{parent_agent.type.value} runs cannot spawn child runs")
        return parent

    async def create_run(
        self,
        owner_id: UUID,
        *,
        agent_id: UUID,
        task_id: UUID | None,
        input_payload: dict[str, Any],
        metadata: dict[str, Any],
        parent_agent_run_id: UUID | None = None,
    ) -> AgentRunTable | None:
        agent = await self._get_owned_agent(agent_id, owner_id)
        if agent is None:
            return None

        if task_id is not None:
            task = await self._get_owned_task(task_id, owner_id, agent.project_id)
            if task is None:
                return None

        if parent_agent_run_id is not None:
            await self._validate_parent_agent_run(
                owner_id,
                parent_agent_run_id,
                project_id=agent.project_id,
            )

        row = AgentRunTable(
            owner_id=owner_id,
            project_id=agent.project_id,
            task_id=task_id,
            agent_id=agent_id,
            parent_agent_run_id=parent_agent_run_id,
            status=AgentRunStatus.QUEUED,
            input_payload=input_payload,
            run_metadata=metadata,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def get_run(self, owner_id: UUID, run_id: UUID) -> AgentRunTable | None:
        return await self._repo.get_by_id_for_owner(run_id, owner_id)

    async def count_children(self, parent_run_id: UUID, owner_id: UUID) -> int:
        return await self._repo.count_children_by_parent(owner_id, parent_run_id)

    async def list_runs(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
        agent_id: UUID | None = None,
        task_id: UUID | None = None,
        status: AgentRunStatus | None = None,
        limit: int = 100,
    ) -> list[AgentRunTable]:
        return await self._repo.list_by_owner(
            owner_id,
            project_id=project_id,
            agent_id=agent_id,
            task_id=task_id,
            status=status,
            limit=limit,
        )

    async def _get_run_for_update(self, owner_id: UUID, run_id: UUID) -> AgentRunTable | None:
        return await self._repo.get_by_id_for_owner(run_id, owner_id)

    async def validate_agent_for_execution(self, agent_id: UUID, owner_id: UUID) -> None:
        await self.get_executable_agent(agent_id, owner_id)

    async def get_executable_agent(self, agent_id: UUID, owner_id: UUID):
        agent = await self._agents.get_agent(agent_id, owner_id)
        if agent is None:
            raise NotFoundError("Agent not found")
        if agent.status == AgentStatus.ARCHIVED:
            raise InvalidStateError("Agent is archived")
        return agent

    async def claim_queued_run(self, owner_id: UUID, run_id: UUID) -> AgentRunTable | None:
        async with transactional(self._session):
            return await self._repo.claim_queued_run(run_id, owner_id)

    async def mark_running(self, owner_id: UUID, run_id: UUID) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.set_running(row)

    async def patch_output_payload(
        self,
        owner_id: UUID,
        run_id: UUID,
        output_payload: dict[str, Any],
    ) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.set_output_payload(row, output_payload)

    async def mark_succeeded(
        self,
        owner_id: UUID,
        run_id: UUID,
        output_payload: dict[str, Any],
    ) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.set_succeeded(row, output_payload)

    async def mark_failed(
        self,
        owner_id: UUID,
        run_id: UUID,
        error: str,
    ) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.set_failed(row, error)

    async def mark_cancelled(self, owner_id: UUID, run_id: UUID) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.set_cancelled(row)

    async def patch_run_metadata(
        self,
        owner_id: UUID,
        run_id: UUID,
        metadata: dict[str, Any],
    ) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.set_run_metadata(row, metadata)

    async def replay_failed_run(
        self,
        owner_id: UUID,
        source_run_id: UUID,
        *,
        replay_reason: str | None = None,
    ) -> AgentRunTable:
        source = await self.get_run(owner_id, source_run_id)
        if source is None:
            raise NotFoundError("Agent run not found")

        agent = await self._agents.get_agent(source.agent_id, owner_id)
        validate_replay_source_run(source, agent)

        project = await self._projects.get_by_id(source.project_id)
        if project is None or project.owner_id != owner_id:
            raise NotFoundError("Project not found")

        if source.task_id is not None:
            task = await self._get_owned_task(source.task_id, owner_id, source.project_id)
            if task is None:
                raise NotFoundError("Task not found")

        reason = normalize_replay_reason(replay_reason)
        metadata = build_replay_metadata(source, replay_reason=reason)

        row = AgentRunTable(
            owner_id=owner_id,
            project_id=source.project_id,
            task_id=source.task_id,
            agent_id=source.agent_id,
            status=AgentRunStatus.QUEUED,
            input_payload=dict(source.input_payload or {}),
            run_metadata=metadata,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def requeue_for_handoff_retry(self, owner_id: UUID, run_id: UUID) -> AgentRunTable | None:
        row = await self._get_run_for_update(owner_id, run_id)
        if row is None:
            return None
        if row.status not in (AgentRunStatus.FAILED, AgentRunStatus.QUEUED):
            return None
        async with transactional(self._session):
            return await self._repo.reset_to_queued(row)
