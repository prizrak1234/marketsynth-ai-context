"""Operational metrics for graph, handoff, outbox, and webhooks (Phase 3.11)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.marketing_campaigns import MarketingCampaignRepository
from app.db.repositories.operational_metrics import (
    METRICS_WINDOW_LABEL,
    OperationalMetricsRepository,
    metrics_window_start,
)
from app.db.repositories.publication_delivery_logs import PublicationDeliveryLogRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.queues.handoff_queue_metrics import get_owner_redis_metrics
from app.schemas.operational_metrics import (
    OperationalMetricsRedis,
    OperationalMetricsResponse,
    ReviewQueueOperationalMetrics,
)
from app.services.review_queue_service import ReviewQueueService
from app.services.projects_service import ProjectService


class OperationalMetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._metrics = OperationalMetricsRepository(session)
        self._projects = ProjectService(session)

    async def get_project_operational_metrics(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> OperationalMetricsResponse | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        return await self._build_metrics(owner_id=owner_id, project_id=project_id)

    async def get_owner_operational_metrics(
        self,
        owner_id: UUID,
    ) -> OperationalMetricsResponse:
        return await self._build_metrics(owner_id=owner_id, project_id=None)

    async def _build_metrics(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> OperationalMetricsResponse:
        since = metrics_window_start()
        agent_runs = await self._metrics.count_agent_runs_by_status(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        outbox = await self._metrics.count_outbox_by_status(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        delivery_status = await self._metrics.count_webhook_delivery_by_status(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        avg_duration_ms, max_duration_ms = await self._metrics.webhook_duration_stats(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        failed_by_webhook = await self._metrics.failed_webhook_counts_by_webhook(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        oldest_outbox_age = await self._metrics.oldest_pending_outbox_age_seconds(
            owner_id=owner_id,
            project_id=project_id,
        )

        runs = await self._metrics.list_agent_runs_for_handoff_metrics(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        handoff_counts, graph_counts, oldest_handoff_age = (
            OperationalMetricsRepository.summarize_handoff_and_graph_runs(runs)
        )
        execution_metrics = OperationalMetricsRepository.summarize_execution_engine_metrics(
            runs,
        )
        replay_metrics = OperationalMetricsRepository.summarize_replay_metrics(runs)

        pub_jobs = PublicationJobRepository(self._session)
        pub_deliveries = PublicationDeliveryLogRepository(self._session)
        jobs_by_status = await pub_jobs.count_by_status(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        deliveries_by_status = await pub_deliveries.count_by_status(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        pub_avg_ms, pub_max_ms = await pub_deliveries.duration_stats(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        failed_by_channel = await pub_deliveries.failed_counts_by_channel(
            owner_id=owner_id,
            project_id=project_id,
            since=since,
        )
        publishing_metrics = {
            "jobs_by_status": jobs_by_status,
            "deliveries_by_status": deliveries_by_status,
            "failed_jobs_count": await pub_jobs.count_failed_jobs(
                owner_id=owner_id,
                project_id=project_id,
            ),
            "oldest_queued_job_age_seconds": await pub_jobs.oldest_queued_job_age_seconds(
                owner_id=owner_id,
                project_id=project_id,
            ),
            "avg_delivery_duration_ms": pub_avg_ms,
            "max_delivery_duration_ms": pub_max_ms,
            "failed_count_by_channel_id": failed_by_channel,
            "scheduled_jobs_count": await pub_jobs.count_scheduled_jobs(
                owner_id=owner_id,
                project_id=project_id,
            ),
            "due_scheduled_jobs_count": await pub_jobs.count_due_scheduled_jobs(
                owner_id=owner_id,
                project_id=project_id,
            ),
            "next_scheduled_publication_at": await pub_jobs.next_scheduled_publication_at(
                owner_id=owner_id,
                project_id=project_id,
            ),
            "cancelled_scheduled_jobs_24h": await pub_jobs.count_cancelled_scheduled_jobs(
                owner_id=owner_id,
                project_id=project_id,
                since=since,
            ),
        }

        campaigns = await MarketingCampaignRepository(self._session).operational_metrics_counts(
            owner_id=owner_id,
            project_id=project_id,
        )

        pending_assets = 0
        if project_id is not None:
            pending_assets = await ReviewQueueService(self._session).count_pending_assets(
                owner_id,
                project_id,
            )

        redis_raw = await get_owner_redis_metrics(owner_id)
        redis = OperationalMetricsRedis.model_validate(redis_raw)

        return OperationalMetricsResponse(
            project_id=project_id,
            window=METRICS_WINDOW_LABEL,
            agent_runs=agent_runs,
            graph_runs=graph_counts,
            handoff={
                **handoff_counts,
                "oldest_queued_age_seconds": oldest_handoff_age,
            },
            outbox={
                **outbox,
                "oldest_pending_age_seconds": oldest_outbox_age,
            },
            webhooks={
                "delivery_status": delivery_status,
                "avg_duration_ms": avg_duration_ms,
                "max_duration_ms": max_duration_ms,
                "failed_count_by_webhook_id": failed_by_webhook,
            },
            execution=execution_metrics,
            replay=replay_metrics,
            publishing=publishing_metrics,
            campaigns=campaigns,
            review_queue=ReviewQueueOperationalMetrics(pending_assets=pending_assets),
            redis=redis,
        )
