"""Global operations health snapshot (Phase 3.11)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.config_sanity import validate_runtime_config
from app.core.redis import check_redis_connection
from app.db.repositories.operational_metrics import OperationalMetricsRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.session import check_database_connection
from app.queues.handoff_queue_metrics import count_known_queue_owners
from app.schemas.operational_metrics import OperationsHealthResponse


async def gather_operations_health(session: AsyncSession) -> OperationsHealthResponse:
    settings = get_settings()
    db_ok = await check_database_connection()
    redis_ok = await check_redis_connection()

    pending_outbox = 0
    pending_publication_jobs = 0
    known_owners = 0
    if db_ok:
        repo = OperationalMetricsRepository(session)
        pending_outbox = await repo.count_pending_outbox_global()
        pending_publication_jobs = await PublicationJobRepository(session).count_pending_global()
    if redis_ok:
        try:
            known_owners = await count_known_queue_owners()
        except Exception:
            known_owners = 0

    config_warnings = validate_runtime_config(
        settings,
        redis_available=redis_ok if redis_ok else False,
        database_available=db_ok if db_ok else False,
    )
    compact_warnings = [warning.compact() for warning in config_warnings]

    overall = "ok" if db_ok and redis_ok else "degraded"
    return OperationsHealthResponse(
        status=overall,
        app="ok",
        database="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
        handoff_scheduler_enabled=settings.graph_handoff_scheduler_enabled,
        outbox_dispatcher_enabled=settings.event_outbox_dispatcher_enabled,
        publication_worker_enabled=settings.publication_worker_enabled,
        graph_version=settings.graph_version,
        pending_outbox_count=pending_outbox,
        pending_publication_jobs_count=pending_publication_jobs,
        handoff_queue_known_owners_count=known_owners,
        config_warnings_count=len(compact_warnings),
        config_warnings=compact_warnings,
    )
