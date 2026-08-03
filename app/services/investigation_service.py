"""Investigation service (Commercial MVP P0.2).

No Agent Run / LLM / Source / Evidence / Verdict / Strategy side effects.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.investigation import InvestigationTable
from app.db.repositories.investigations import InvestigationRepository
from app.db.repositories.project_briefs import ProjectBriefRepository
from app.domain.investigation_lifecycle import (
    assert_transition,
    compute_readiness,
    default_stages,
)
from app.schemas.contracts import (
    InvestigationCreateRequest,
    InvestigationStageId,
    InvestigationStageState,
    InvestigationStageStatus,
    InvestigationStageUpdateRequest,
    InvestigationStatus,
    InvestigationUpdateRequest,
    ProjectBriefStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_META_KEYS_MAX = 32
_META_VALUE_MAX = 500


def _sanitize_meta(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned = sanitize_payload(raw) or {}
    out: dict[str, Any] = {}
    for i, (key, value) in enumerate(cleaned.items()):
        if i >= _META_KEYS_MAX:
            break
        k = sanitize_text(str(key)).strip()[:64]
        if not k:
            continue
        if isinstance(value, str):
            out[k] = sanitize_text(value).strip()[:_META_VALUE_MAX]
        elif isinstance(value, (int, float, bool)) or value is None:
            out[k] = value
        else:
            out[k] = sanitize_text(str(value)).strip()[:_META_VALUE_MAX]
    return out


class InvestigationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._investigations = InvestigationRepository(session)
        self._briefs = ProjectBriefRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _stages_from_row(self, row: InvestigationTable) -> list[InvestigationStageState]:
        return [
            InvestigationStageState.model_validate(item) for item in (row.stages or [])
        ]

    def _apply_readiness(self, row: InvestigationTable) -> None:
        status = InvestigationStatus(row.status)
        stages = self._stages_from_row(row)
        readiness, reasons = compute_readiness(status=status, stages=stages)
        row.readiness_status = readiness
        row.readiness_reasons = reasons

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        request: InvestigationCreateRequest,
    ) -> InvestigationTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        brief = await self._briefs.get_by_id_for_owner(
            request.project_brief_id,
            owner_id,
            project_id,
        )
        if brief is None:
            raise InvalidStateError("brief_not_found")
        if brief.status != ProjectBriefStatus.SUBMITTED:
            raise InvalidStateError("brief_not_submitted")
        if brief.version != request.project_brief_version:
            raise InvalidStateError("brief_version_mismatch")
        if brief.input_fingerprint != request.input_fingerprint:
            raise InvalidStateError("fingerprint_mismatch")

        active = await self._investigations.get_active(owner_id, project_id)
        if active is not None:
            raise InvalidStateError("active_investigation_exists")

        stages = default_stages()
        version = await self._investigations.max_version(owner_id, project_id) + 1
        from app.schemas.contracts import InvestigationReadinessStatus

        row = InvestigationTable(
            owner_id=owner_id,
            project_id=project_id,
            project_brief_id=brief.id,
            project_brief_version=brief.version,
            input_fingerprint=brief.input_fingerprint,
            version=version,
            status=InvestigationStatus.DRAFT,
            current_stage=InvestigationStageId.PROJECT_CONTEXT,
            stages=[s.model_dump(mode="json") for s in stages],
            readiness_status=InvestigationReadinessStatus.NOT_READY,
            readiness_reasons=[],
            metadata_json={"source_evidence": "unavailable_until_p0_3_p0_4"},
        )
        self._apply_readiness(row)

        async with transactional(self._session):
            return await self._investigations.create(row)

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        request: InvestigationUpdateRequest,
    ) -> InvestigationTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )
        if row is None:
            return None
        if row.status in (
            InvestigationStatus.COMPLETED,
            InvestigationStatus.SUPERSEDED,
            InvestigationStatus.CANCELLED,
        ):
            raise InvalidStateError("investigation_immutable")

        if request.current_stage is not None:
            row.current_stage = request.current_stage
        if request.readiness_status is not None:
            row.readiness_status = request.readiness_status
        if request.readiness_reasons is not None:
            row.readiness_reasons = [
                sanitize_text(r).strip()[:500]
                for r in request.readiness_reasons
                if str(r).strip()
            ][:50]
        if request.blocked_reason is not None:
            row.blocked_reason = sanitize_text(request.blocked_reason).strip()[:2000] or None
        if request.metadata is not None:
            row.metadata_json = _sanitize_meta(request.metadata)
        row.updated_at = utc_now()
        self._apply_readiness(row)
        async with transactional(self._session):
            return await self._investigations.update(row)

    async def update_stage(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        stage: InvestigationStageId,
        request: InvestigationStageUpdateRequest,
    ) -> InvestigationTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )
        if row is None:
            return None
        if row.status in (
            InvestigationStatus.COMPLETED,
            InvestigationStatus.SUPERSEDED,
            InvestigationStatus.CANCELLED,
        ):
            raise InvalidStateError("investigation_immutable")

        stages = self._stages_from_row(row)
        found = False
        for item in stages:
            if item.stage_id == stage:
                item.status = request.status
                if request.blocked_reason is not None:
                    item.blocked_reason = (
                        sanitize_text(request.blocked_reason).strip()[:2000] or None
                    )
                found = True
                break
        if not found:
            raise InvalidStateError("investigation_stage_not_found")
        row.stages = [s.model_dump(mode="json") for s in stages]
        row.current_stage = stage
        row.updated_at = utc_now()
        self._apply_readiness(row)
        async with transactional(self._session):
            return await self._investigations.update(row)

    async def _transition(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        target: InvestigationStatus,
        *,
        blocked_reason: str | None = None,
        clear_blocked: bool = False,
    ) -> InvestigationTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )
        if row is None:
            return None
        current = InvestigationStatus(row.status)
        assert_transition(current, target)

        if target == InvestigationStatus.ACTIVE:
            active = await self._investigations.get_active(owner_id, project_id)
            if active is not None and active.id != row.id:
                raise InvalidStateError("active_investigation_exists")
            if row.started_at is None:
                row.started_at = utc_now()

        if target == InvestigationStatus.COMPLETED:
            row.completed_at = utc_now()

        if target == InvestigationStatus.BLOCKED:
            row.blocked_reason = (
                sanitize_text(blocked_reason or row.blocked_reason or "blocked").strip()[
                    :2000
                ]
            )
        elif clear_blocked or target in (
            InvestigationStatus.READY,
            InvestigationStatus.ACTIVE,
        ):
            row.blocked_reason = None

        row.status = target
        row.updated_at = utc_now()
        self._apply_readiness(row)
        async with transactional(self._session):
            return await self._investigations.update(row)

    async def mark_ready(self, owner_id: UUID, project_id: UUID, investigation_id: UUID):
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.READY,
            clear_blocked=True,
        )

    async def start(self, owner_id: UUID, project_id: UUID, investigation_id: UUID):
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.ACTIVE,
            clear_blocked=True,
        )

    async def block(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        *,
        reason: str | None = None,
    ):
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.BLOCKED,
            blocked_reason=reason,
        )

    async def resume(self, owner_id: UUID, project_id: UUID, investigation_id: UUID):
        """blocked → ready (lifecycle only)."""
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.READY,
            clear_blocked=True,
        )

    async def submit_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ):
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.UNDER_REVIEW,
        )

    async def complete(self, owner_id: UUID, project_id: UUID, investigation_id: UUID):
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.COMPLETED,
        )

    async def cancel(self, owner_id: UUID, project_id: UUID, investigation_id: UUID):
        return await self._transition(
            owner_id,
            project_id,
            investigation_id,
            InvestigationStatus.CANCELLED,
        )

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        request: InvestigationCreateRequest,
    ) -> InvestigationTable | None:
        """Create a new Investigation version; mark prior completed as superseded."""
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        source = await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )
        if source is None:
            return None
        source_status = InvestigationStatus(source.status)
        if source_status not in (
            InvestigationStatus.COMPLETED,
            InvestigationStatus.SUPERSEDED,
        ):
            # Allow supersede from completed primarily; cancel active first via cancel.
            if source_status == InvestigationStatus.ACTIVE:
                raise InvalidStateError("active_investigation_exists")
            raise InvalidStateError("investigation_invalid_transition")

        active = await self._investigations.get_active(owner_id, project_id)
        if active is not None:
            raise InvalidStateError("active_investigation_exists")

        brief = await self._briefs.get_by_id_for_owner(
            request.project_brief_id,
            owner_id,
            project_id,
        )
        if brief is None:
            raise InvalidStateError("brief_not_found")
        if brief.status != ProjectBriefStatus.SUBMITTED:
            raise InvalidStateError("brief_not_submitted")
        if brief.version != request.project_brief_version:
            raise InvalidStateError("brief_version_mismatch")
        if brief.input_fingerprint != request.input_fingerprint:
            raise InvalidStateError("fingerprint_mismatch")

        stages = default_stages()
        version = await self._investigations.max_version(owner_id, project_id) + 1
        from app.schemas.contracts import InvestigationReadinessStatus

        row = InvestigationTable(
            owner_id=owner_id,
            project_id=project_id,
            project_brief_id=brief.id,
            project_brief_version=brief.version,
            input_fingerprint=brief.input_fingerprint,
            version=version,
            status=InvestigationStatus.DRAFT,
            current_stage=InvestigationStageId.PROJECT_CONTEXT,
            stages=[s.model_dump(mode="json") for s in stages],
            readiness_status=InvestigationReadinessStatus.NOT_READY,
            readiness_reasons=[],
            supersedes_investigation_id=source.id,
            metadata_json={"source_evidence": "unavailable_until_p0_3_p0_4"},
        )
        self._apply_readiness(row)

        async with transactional(self._session):
            if source_status == InvestigationStatus.COMPLETED:
                source.status = InvestigationStatus.SUPERSEDED
                source.updated_at = utc_now()
                await self._investigations.update(source)
            return await self._investigations.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> InvestigationTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )

    async def list_investigations(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: InvestigationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InvestigationTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._investigations.list_for_project(
            owner_id,
            project_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def latest(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> InvestigationTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._investigations.get_latest_prefer_live(owner_id, project_id)

    @staticmethod
    def creates_agent_run() -> bool:
        return False

    @staticmethod
    def creates_llm_request() -> bool:
        return False

    @staticmethod
    def creates_source() -> bool:
        return False

    @staticmethod
    def creates_evidence() -> bool:
        return False

    @staticmethod
    def creates_verdict() -> bool:
        return False

    @staticmethod
    def creates_strategy() -> bool:
        return False
