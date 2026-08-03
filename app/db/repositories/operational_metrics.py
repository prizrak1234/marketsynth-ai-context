"""Aggregated operational metrics queries (Phase 3.11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.db.models.event_outbox import EventOutboxTable
from app.db.models.webhook_delivery_log import WebhookDeliveryLogTable
from app.executors.execution_metadata import get_execution_engine_from_run
from app.graphs.handoff import is_handoff_child_run
from app.graphs.handoff_worker_state import get_handoff_worker_state
from app.schemas.contracts import AgentRunStatus, EventOutboxStatus, WebhookDeliveryLogStatus

METRICS_WINDOW_HOURS = 24
METRICS_WINDOW_LABEL = "24h"


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def metrics_window_start(*, now: datetime | None = None) -> datetime:
    anchor = now or utc_now()
    return anchor - timedelta(hours=METRICS_WINDOW_HOURS)


class OperationalMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_agent_runs_by_status(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> dict[str, int]:
        statement = (
            select(AgentRunTable.status, func.count())
            .where(
                AgentRunTable.owner_id == owner_id,
                AgentRunTable.created_at >= since,
            )
            .group_by(AgentRunTable.status)
        )
        if project_id is not None:
            statement = statement.where(AgentRunTable.project_id == project_id)
        result = await self._session.execute(statement)
        counts = {status.value: 0 for status in AgentRunStatus}
        for status, count in result.all():
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def count_outbox_by_status(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> dict[str, int]:
        statement = (
            select(EventOutboxTable.status, func.count())
            .where(
                EventOutboxTable.owner_id == owner_id,
                EventOutboxTable.created_at >= since,
            )
            .group_by(EventOutboxTable.status)
        )
        if project_id is not None:
            statement = statement.where(EventOutboxTable.project_id == project_id)
        result = await self._session.execute(statement)
        counts = {status.value: 0 for status in EventOutboxStatus}
        for status, count in result.all():
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def count_webhook_delivery_by_status(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> dict[str, int]:
        statement = (
            select(WebhookDeliveryLogTable.status, func.count())
            .where(
                WebhookDeliveryLogTable.owner_id == owner_id,
                WebhookDeliveryLogTable.created_at >= since,
            )
            .group_by(WebhookDeliveryLogTable.status)
        )
        if project_id is not None:
            statement = statement.where(WebhookDeliveryLogTable.project_id == project_id)
        result = await self._session.execute(statement)
        counts = {status.value: 0 for status in WebhookDeliveryLogStatus}
        for status, count in result.all():
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def webhook_duration_stats(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> tuple[float | None, int | None]:
        statement = select(
            func.avg(WebhookDeliveryLogTable.duration_ms),
            func.max(WebhookDeliveryLogTable.duration_ms),
        ).where(
            WebhookDeliveryLogTable.owner_id == owner_id,
            WebhookDeliveryLogTable.created_at >= since,
            WebhookDeliveryLogTable.duration_ms.is_not(None),
        )
        if project_id is not None:
            statement = statement.where(WebhookDeliveryLogTable.project_id == project_id)
        result = await self._session.execute(statement)
        avg_ms, max_ms = result.one()
        avg_value = round(float(avg_ms), 2) if avg_ms is not None else None
        max_value = int(max_ms) if max_ms is not None else None
        return avg_value, max_value

    async def failed_webhook_counts_by_webhook(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> dict[str, int]:
        statement = (
            select(WebhookDeliveryLogTable.webhook_id, func.count())
            .where(
                WebhookDeliveryLogTable.owner_id == owner_id,
                WebhookDeliveryLogTable.created_at >= since,
                WebhookDeliveryLogTable.status == WebhookDeliveryLogStatus.FAILED,
                WebhookDeliveryLogTable.webhook_id.is_not(None),
            )
            .group_by(WebhookDeliveryLogTable.webhook_id)
        )
        if project_id is not None:
            statement = statement.where(WebhookDeliveryLogTable.project_id == project_id)
        result = await self._session.execute(statement)
        return {str(webhook_id): int(count) for webhook_id, count in result.all()}

    async def oldest_pending_outbox_age_seconds(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> int | None:
        statement = (
            select(EventOutboxTable.created_at)
            .where(
                EventOutboxTable.owner_id == owner_id,
                EventOutboxTable.status == EventOutboxStatus.PENDING,
            )
            .order_by(EventOutboxTable.created_at.asc())
            .limit(1)
        )
        if project_id is not None:
            statement = statement.where(EventOutboxTable.project_id == project_id)
        result = await self._session.execute(statement)
        created_at = result.scalar_one_or_none()
        if created_at is None:
            return None
        return max(0, int((utc_now() - _coerce_utc(created_at)).total_seconds()))

    async def count_pending_outbox_global(self) -> int:
        statement = select(func.count()).where(
            EventOutboxTable.status == EventOutboxStatus.PENDING,
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def list_agent_runs_for_handoff_metrics(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> list[AgentRunTable]:
        statement = select(AgentRunTable).where(
            AgentRunTable.owner_id == owner_id,
            AgentRunTable.created_at >= since,
        )
        if project_id is not None:
            statement = statement.where(AgentRunTable.project_id == project_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    def summarize_handoff_and_graph_runs(
        runs: list[AgentRunTable],
    ) -> tuple[dict[str, int], dict[str, int], int | None]:
        handoff: dict[str, int] = {
            "queued": 0,
            "failed": 0,
            "dead_lettered": 0,
        }
        graph: dict[str, int] = {
            "succeeded": 0,
            "failed": 0,
        }
        oldest_queued_at: datetime | None = None

        for run in runs:
            metadata = dict(run.run_metadata or {})
            if is_handoff_child_run(metadata):
                if run.status == AgentRunStatus.QUEUED:
                    handoff["queued"] += 1
                    if oldest_queued_at is None or run.created_at < oldest_queued_at:
                        oldest_queued_at = run.created_at
                elif run.status == AgentRunStatus.FAILED:
                    handoff["failed"] += 1
                worker = get_handoff_worker_state(metadata)
                if worker.get("dead_lettered"):
                    handoff["dead_lettered"] += 1
                continue

            output = dict(run.output_payload or {})
            engine = output.get("execution_engine") or metadata.get("execution_engine")
            if engine != "langgraph":
                continue
            if run.status == AgentRunStatus.SUCCEEDED:
                graph["succeeded"] += 1
            elif run.status == AgentRunStatus.FAILED:
                graph["failed"] += 1

        oldest_age: int | None = None
        if oldest_queued_at is not None:
            oldest_age = max(0, int((utc_now() - _coerce_utc(oldest_queued_at)).total_seconds()))
        return handoff, graph, oldest_age

    @staticmethod
    def summarize_execution_engine_metrics(
        runs: list[AgentRunTable],
    ) -> dict[str, Any]:
        by_engine: dict[str, dict[str, int]] = {
            "classic": {"succeeded": 0, "failed": 0, "total": 0},
            "langgraph": {"succeeded": 0, "failed": 0, "total": 0},
            "unknown": {"succeeded": 0, "failed": 0, "total": 0},
        }

        for run in runs:
            metadata = dict(run.run_metadata or {})
            if is_handoff_child_run(metadata):
                continue

            engine = get_execution_engine_from_run(run) or "unknown"
            if engine not in by_engine:
                engine = "unknown"
            bucket = by_engine[engine]
            bucket["total"] += 1
            if run.status == AgentRunStatus.SUCCEEDED:
                bucket["succeeded"] += 1
            elif run.status == AgentRunStatus.FAILED:
                bucket["failed"] += 1

        def _success_rate(engine_key: str) -> float | None:
            bucket = by_engine[engine_key]
            total = bucket["total"]
            if total == 0:
                return None
            return round(bucket["succeeded"] / total, 4)

        return {
            "agent_runs_by_execution_engine": {
                "classic": by_engine["classic"],
                "langgraph": by_engine["langgraph"],
            },
            "graph_vs_classic_success_rate": {
                "classic": _success_rate("classic"),
                "langgraph": _success_rate("langgraph"),
            },
            "graph_vs_classic_failed_count": {
                "classic": by_engine["classic"]["failed"],
                "langgraph": by_engine["langgraph"]["failed"],
            },
        }

    @staticmethod
    def summarize_replay_metrics(runs: list[AgentRunTable]) -> dict[str, Any]:
        replayed_runs_count = 0
        failed_runs_replayed_count = 0
        replay_source_status_counts: dict[str, int] = {}

        for run in runs:
            metadata = dict(run.run_metadata or {})
            replay = metadata.get("replay")
            if not isinstance(replay, dict):
                continue
            source_run_id = replay.get("source_run_id")
            if not isinstance(source_run_id, str) or not source_run_id.strip():
                continue

            replayed_runs_count += 1
            source_status = replay.get("source_status")
            if isinstance(source_status, str) and source_status.strip():
                key = source_status.strip()
                replay_source_status_counts[key] = replay_source_status_counts.get(key, 0) + 1
                if key == AgentRunStatus.FAILED.value:
                    failed_runs_replayed_count += 1

        return {
            "replayed_runs_count": replayed_runs_count,
            "failed_runs_replayed_count": failed_runs_replayed_count,
            "replay_source_status_counts": replay_source_status_counts,
        }
