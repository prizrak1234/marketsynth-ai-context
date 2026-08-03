"""Build compact workflow summaries for orchestrator parent runs (Phase 5.7)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.graphs.handoff import is_handoff_child_run
from app.schemas.workflow_summary import (
    AgentRunWorkflowSummary,
    WorkflowAssetSummary,
    WorkflowChildRunSummary,
)
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService
from app.services.content_asset_service import ContentAssetService


def _metadata_purpose(metadata: dict[str, Any] | None) -> str | None:
    if not isinstance(metadata, dict):
        return None
    purpose = metadata.get("purpose")
    return str(purpose) if purpose is not None else None


def _quality_score(metadata: dict[str, Any] | None) -> float | None:
    if not isinstance(metadata, dict):
        return None
    quality = metadata.get("quality")
    if not isinstance(quality, dict):
        return None
    score = quality.get("score")
    if isinstance(score, (int, float)):
        return float(score)
    return None


def _asset_summary(row: Any) -> WorkflowAssetSummary:
    metadata = dict(row.asset_metadata or {})
    meta_source = metadata.get("source_asset_id")
    source_id: UUID | None = None
    if meta_source is not None:
        try:
            source_id = UUID(str(meta_source))
        except ValueError:
            source_id = None
    if source_id is None and row.source_asset_id is not None:
        source_id = row.source_asset_id
    return WorkflowAssetSummary(
        id=row.id,
        title=row.title,
        type=row.asset_type.value if hasattr(row.asset_type, "value") else str(row.asset_type),
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        agent_run_id=row.agent_run_id,
        source_asset_id=source_id,
        metadata_purpose=_metadata_purpose(metadata),
        quality_score=_quality_score(metadata),
    )


def _is_asset_related(
    row: Any,
    *,
    run_ids: set[UUID],
    related_asset_ids: set[UUID],
) -> bool:
    if row.agent_run_id in run_ids:
        return True
    if row.id in related_asset_ids:
        return True
    if row.source_asset_id in related_asset_ids:
        return True
    metadata = dict(row.asset_metadata or {})
    meta_source = metadata.get("source_asset_id")
    if meta_source is not None:
        try:
            if UUID(str(meta_source)) in related_asset_ids:
                return True
        except ValueError:
            pass
    return False


class AgentRunWorkflowSummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = AgentRunService(session)
        self._agents = AgentService(session)
        self._assets = ContentAssetService(session)

    async def get_summary(
        self,
        owner_id: UUID,
        parent_run_id: UUID,
    ) -> AgentRunWorkflowSummary | None:
        parent = await self._runs.get_run(owner_id, parent_run_id)
        if parent is None:
            return None

        handoff = {}
        if isinstance(parent.output_payload, dict):
            raw_handoff = parent.output_payload.get("handoff")
            if isinstance(raw_handoff, dict):
                handoff = dict(raw_handoff)

        child_run_rows = await self._collect_child_runs(owner_id, parent)
        run_ids: set[UUID] = {parent.id}
        for child in child_run_rows:
            run_ids.add(child.id)

        project_assets = await self._assets.list_by_project(
            owner_id,
            parent.project_id,
            include_archived=False,
            limit=500,
        )
        if project_assets is None:
            project_assets = []

        seed_ids = {row.id for row in project_assets if row.agent_run_id in run_ids}
        related_assets = [
            _asset_summary(row)
            for row in project_assets
            if _is_asset_related(row, run_ids=run_ids, related_asset_ids=seed_ids)
        ]

        child_summaries: list[WorkflowChildRunSummary] = []
        for child in child_run_rows:
            agent = await self._agents.get_agent(child.agent_id, owner_id)
            agent_type = agent.type.value if agent is not None else "unknown"
            child_assets = [
                summary
                for summary in related_assets
                if summary.agent_run_id == child.id
            ]
            child_summaries.append(
                WorkflowChildRunSummary(
                    id=child.id,
                    agent_type=agent_type,
                    status=child.status.value,
                    created_assets=child_assets,
                ),
            )

        return AgentRunWorkflowSummary(
            parent_run_id=parent.id,
            status=parent.status.value,
            handoff=handoff,
            child_runs=child_summaries,
            related_assets=related_assets,
        )

    async def _collect_child_runs(
        self,
        owner_id: UUID,
        parent: AgentRunTable,
    ) -> list[AgentRunTable]:
        parent_str = str(parent.id)
        children: list[AgentRunTable] = []
        seen: set[UUID] = set()

        handoff_child_id: UUID | None = None
        if isinstance(parent.output_payload, dict):
            handoff = parent.output_payload.get("handoff")
            if isinstance(handoff, dict):
                raw_child = handoff.get("child_run_id")
                if isinstance(raw_child, str) and raw_child.strip():
                    try:
                        handoff_child_id = UUID(raw_child.strip())
                    except ValueError:
                        handoff_child_id = None

        if handoff_child_id is not None:
            row = await self._runs.get_run(owner_id, handoff_child_id)
            if row is not None:
                children.append(row)
                seen.add(row.id)

        project_runs = await self._runs.list_runs(
            owner_id,
            project_id=parent.project_id,
            limit=500,
        )
        for row in project_runs:
            if row.id in seen:
                continue
            metadata = dict(row.run_metadata or {})
            if not is_handoff_child_run(metadata):
                continue
            if metadata.get("parent_agent_run_id") == parent_str:
                children.append(row)
                seen.add(row.id)

        return children
