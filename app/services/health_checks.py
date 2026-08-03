"""Infrastructure health probes — no business logic."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.redis import check_redis_connection
from app.db.session import check_database_connection


@dataclass(frozen=True)
class HealthReport:
    status: str
    app: str
    database: str
    redis: str

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"


async def gather_health_report() -> HealthReport:
    db_ok = await check_database_connection()
    redis_ok = await check_redis_connection()
    overall = "ok" if db_ok and redis_ok else "degraded"
    return HealthReport(
        status=overall,
        app="ok",
        database="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
    )
