"""Marketing skill run orchestration (Phase AI.234)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.db.base import utc_now
from app.db.models.marketing_skill_run import MarketingSkillRunTable
from app.db.repositories.marketing_skill_runs import MarketingSkillRunRepository
from app.marketing.skills.permissions import assert_safe_skill_input, assert_skill_enabled
from app.marketing.skills.registry import get_marketing_skill_registry
from app.schemas.contracts import MarketingSkillRunStatus, MarketingSkillType
from app.services.campaign_skill_context_service import CampaignSkillContextService
from app.services.marketing_skill_audit import log_marketing_skill_run
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class MarketingSkillRunService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = MarketingSkillRunRepository(session)
        self._projects = ProjectService(session)
        self._registry = get_marketing_skill_registry()

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def _parse_campaign_id(
        payload: dict[str, Any],
        campaign_id: UUID | None,
    ) -> UUID | None:
        if campaign_id is not None:
            return campaign_id
        raw = payload.get("campaign_id")
        return UUID(str(raw)) if raw else None

    async def create_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        skill_type: MarketingSkillType,
        input_payload: dict[str, Any],
        *,
        campaign_id: UUID | None = None,
    ) -> MarketingSkillRunTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        assert_skill_enabled(skill_type)
        safe_input = assert_safe_skill_input(input_payload)
        resolved_campaign_id = self._parse_campaign_id(safe_input, campaign_id)

        row = MarketingSkillRunTable(
            owner_id=owner_id,
            project_id=project_id,
            campaign_id=resolved_campaign_id,
            skill_type=skill_type,
            input_payload=safe_input,
            status=MarketingSkillRunStatus.QUEUED,
        )
        async with transactional(self._session):
            row = await self._runs.create(row)

        log_marketing_skill_run(
            run_id=str(row.id),
            project_id=str(project_id),
            skill_type=skill_type,
            status=MarketingSkillRunStatus.QUEUED,
        )
        return await self._execute_run(row)

    async def _execute_run(self, row: MarketingSkillRunTable) -> MarketingSkillRunTable:
        row.status = MarketingSkillRunStatus.RUNNING
        row.started_at = utc_now()
        async with transactional(self._session):
            row = await self._runs.update(row)

        log_marketing_skill_run(
            run_id=str(row.id),
            project_id=str(row.project_id),
            skill_type=row.skill_type,
            status=MarketingSkillRunStatus.RUNNING,
        )

        try:
            skill = self._registry.get(row.skill_type)
            output, metadata, used_tool_ids = await skill.executor(
                self._session,
                row.owner_id,
                row.project_id,
                dict(row.input_payload or {}),
            )
            row.output_payload = sanitize_payload(output) or {}
            row.safe_metadata = sanitize_payload(metadata) or {}
            row.used_tool_call_ids = [str(item) for item in used_tool_ids]
            row.status = MarketingSkillRunStatus.SUCCEEDED
            row.error = None
        except InvalidStateError as exc:
            row.status = MarketingSkillRunStatus.FAILED
            row.error = str(exc)[:512]
            row.safe_metadata = {"provider": "mock_skill"}
        except Exception as exc:
            row.status = MarketingSkillRunStatus.FAILED
            row.error = str(exc)[:512]
            row.safe_metadata = {"provider": "mock_skill"}

        row.finished_at = utc_now()
        if row.status == MarketingSkillRunStatus.SUCCEEDED and row.campaign_id is not None:
            await CampaignSkillContextService(self._session).apply_successful_run(row)

        async with transactional(self._session):
            row = await self._runs.update(row)

        log_marketing_skill_run(
            run_id=str(row.id),
            project_id=str(row.project_id),
            skill_type=row.skill_type,
            status=row.status,
            safe_metadata=dict(row.safe_metadata or {}),
            used_tool_call_ids=list(row.used_tool_call_ids or []),
            error=row.error,
        )
        return row

    async def get_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> MarketingSkillRunTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._runs.get_by_id_for_owner(run_id, owner_id, project_id)

    async def list_runs(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        campaign_id: UUID | None = None,
        skill_type: MarketingSkillType | None = None,
        limit: int = 50,
    ) -> list[MarketingSkillRunTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._runs.list_for_project(
            owner_id,
            project_id,
            campaign_id=campaign_id,
            skill_type=skill_type,
            limit=limit,
        )

    def list_skill_definitions(self):
        return self._registry.list_definitions()
