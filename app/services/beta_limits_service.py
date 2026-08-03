"""Beta tester soft limits (Phase AI.87)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededError
from app.db.base import ensure_naive_utc
from app.db.models.agent_chat import AgentChatSessionTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.media import MediaGenerationJobTable
from app.db.models.project import ProjectTable
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublicationJobTable
class BetaLimitsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    def _raise_limit(self, *, code: str, message: str, limit: int) -> None:
        raise RateLimitExceededError(
            error_code=code,
            safe_message=message,
            limit=limit,
        )

    async def assert_can_create_project(self, owner_id: UUID) -> None:
        if not self._settings.beta_limits_enabled:
            return
        limit = self._settings.effective_beta_limit(
            generous=self._settings.beta_max_projects_per_user,
            strict=self._settings.beta_strict_max_projects_per_user,
        )
        count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(ProjectTable).where(
                        ProjectTable.owner_id == owner_id,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        if count >= limit:
            self._raise_limit(
                code="project_limit_exceeded",
                message=f"Project limit reached ({limit} per user).",
                limit=limit,
            )

    async def assert_can_create_chat_session(self, owner_id: UUID, project_id: UUID) -> None:
        if not self._settings.beta_limits_enabled:
            return
        limit = self._settings.effective_beta_limit(
            generous=self._settings.beta_max_chat_sessions_per_project,
            strict=self._settings.beta_strict_max_chat_sessions_per_project,
        )
        count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(AgentChatSessionTable).where(
                        AgentChatSessionTable.owner_id == owner_id,
                        AgentChatSessionTable.project_id == project_id,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        if count >= limit:
            self._raise_limit(
                code="chat_session_limit_exceeded",
                message=f"Chat session limit reached ({limit} per project).",
                limit=limit,
            )

    async def assert_can_create_marketing_plan(self, owner_id: UUID, project_id: UUID) -> None:
        if not self._settings.beta_limits_enabled:
            return
        limit = self._settings.effective_beta_limit(
            generous=self._settings.beta_max_marketing_plans_per_project,
            strict=self._settings.beta_strict_max_marketing_plans_per_project,
        )
        count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(MarketingPlanTable).where(
                        MarketingPlanTable.owner_id == owner_id,
                        MarketingPlanTable.project_id == project_id,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        if count >= limit:
            self._raise_limit(
                code="marketing_plan_limit_exceeded",
                message=f"Marketing plan limit reached ({limit} per project).",
                limit=limit,
            )

    async def assert_can_create_generation_job(self, owner_id: UUID, project_id: UUID) -> None:
        if not self._settings.beta_limits_enabled:
            return
        limit = self._settings.effective_beta_limit(
            generous=self._settings.beta_max_generation_jobs_per_day,
            strict=self._settings.beta_strict_max_generation_jobs_per_day,
        )
        start = ensure_naive_utc(
            datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(MediaGenerationJobTable).where(
                        MediaGenerationJobTable.owner_id == owner_id,
                        MediaGenerationJobTable.project_id == project_id,
                        MediaGenerationJobTable.created_at >= start,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        if count >= limit:
            self._raise_limit(
                code="generation_job_daily_limit_exceeded",
                message=f"Daily media generation job limit reached ({limit}).",
                limit=limit,
            )

    async def assert_can_create_publication_job(self, owner_id: UUID, project_id: UUID) -> None:
        if not self._settings.beta_limits_enabled:
            return
        limit = self._settings.effective_beta_limit(
            generous=self._settings.beta_max_publication_jobs_per_day,
            strict=self._settings.beta_strict_max_publication_jobs_per_day,
        )
        start = ensure_naive_utc(
            datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        package_count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(PublicationPackageJobTable).where(
                        PublicationPackageJobTable.owner_id == owner_id,
                        PublicationPackageJobTable.project_id == project_id,
                        PublicationPackageJobTable.created_at >= start,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        legacy_count = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(PublicationJobTable).where(
                        PublicationJobTable.owner_id == owner_id,
                        PublicationJobTable.project_id == project_id,
                        PublicationJobTable.created_at >= start,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        if package_count + legacy_count >= limit:
            self._raise_limit(
                code="publication_job_daily_limit_exceeded",
                message=f"Daily publication job limit reached ({limit}).",
                limit=limit,
            )
