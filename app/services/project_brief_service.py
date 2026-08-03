"""ProjectBrief service (Commercial MVP P0.1).

No Investigation / Agent Run / Verdict / Strategy / execution side effects.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateResourceError, InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.project_brief import ProjectBriefTable
from app.db.repositories.project_briefs import ProjectBriefRepository
from app.domain.project_brief_fingerprint import compute_project_brief_fingerprint
from app.schemas.contracts import (
    ProjectBriefContent,
    ProjectBriefCreateRequest,
    ProjectBriefReadinessStatus,
    ProjectBriefStatus,
    ProjectBriefUpdateRequest,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_TEXT_MAX = 8000
_SHORT_MAX = 512


def _sanitize_str(value: str, max_len: int = _TEXT_MAX) -> str:
    return sanitize_text(value).strip()[:max_len]


def _sanitize_str_list(values: list[str], *, max_len: int = 1000) -> list[str]:
    return [_sanitize_str(item, max_len=512) for item in values if str(item).strip()][:max_len]


def sanitize_brief_content(content: ProjectBriefContent) -> ProjectBriefContent:
    raw = sanitize_payload(content.model_dump(mode="json")) or {}
    validated = ProjectBriefContent.model_validate(raw)
    # Re-apply length clamps after nested validation
    data = validated.model_dump(mode="json")
    data["language"] = _sanitize_str(str(data.get("language") or "ru"), 16) or "ru"
    data["assumptions"] = _sanitize_str_list(
        [str(x) for x in (data.get("assumptions") or [])],
    )
    data["missing_data"] = _sanitize_str_list(
        [str(x) for x in (data.get("missing_data") or [])],
    )
    data["readiness_reasons"] = _sanitize_str_list(
        [str(x) for x in (data.get("readiness_reasons") or [])],
    )
    return ProjectBriefContent.model_validate(data)


class ProjectBriefService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._briefs = ProjectBriefRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _row_from_content(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        version: int,
        content: ProjectBriefContent,
        fingerprint: str,
        status: ProjectBriefStatus = ProjectBriefStatus.DRAFT,
        supersedes_brief_id: UUID | None = None,
        submitted_at: Any = None,
    ) -> ProjectBriefTable:
        dumped = content.model_dump(mode="json")
        return ProjectBriefTable(
            owner_id=owner_id,
            project_id=project_id,
            version=version,
            status=status,
            language=content.language,
            project_basics=dumped["project_basics"],
            product=dumped["product"],
            market=dumped["market"],
            audience=dumped["audience"],
            economics=dumped["economics"],
            materials_summary=dumped["materials_summary"],
            assumptions=dumped["assumptions"],
            missing_data=dumped["missing_data"],
            readiness_status=content.readiness_status,
            readiness_reasons=dumped["readiness_reasons"],
            input_fingerprint=fingerprint,
            supersedes_brief_id=supersedes_brief_id,
            submitted_at=submitted_at,
        )

    def _apply_update(
        self,
        existing: ProjectBriefContent,
        patch: ProjectBriefUpdateRequest,
    ) -> ProjectBriefContent:
        data = existing.model_dump(mode="json")
        patch_data = patch.model_dump(mode="json", exclude_unset=True)
        for key, value in patch_data.items():
            if value is not None:
                data[key] = value
        return ProjectBriefContent.model_validate(data)

    def content_from_row(self, row: ProjectBriefTable) -> ProjectBriefContent:
        return ProjectBriefContent.model_validate(
            {
                "language": row.language,
                "project_basics": row.project_basics,
                "product": row.product,
                "market": row.market,
                "audience": row.audience,
                "economics": row.economics,
                "materials_summary": row.materials_summary,
                "assumptions": row.assumptions,
                "missing_data": row.missing_data,
                "readiness_status": row.readiness_status,
                "readiness_reasons": row.readiness_reasons,
            }
        )

    async def create_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        request: ProjectBriefCreateRequest,
    ) -> ProjectBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        open_draft = await self._briefs.get_open_draft(owner_id, project_id)
        if open_draft is not None:
            raise InvalidStateError("project_brief_draft_already_exists")

        content = sanitize_brief_content(ProjectBriefContent.model_validate(request.model_dump()))
        fingerprint = compute_project_brief_fingerprint(content)
        version = await self._briefs.max_version(owner_id, project_id) + 1
        row = self._row_from_content(
            owner_id=owner_id,
            project_id=project_id,
            version=version,
            content=content,
            fingerprint=fingerprint,
        )
        async with transactional(self._session):
            return await self._briefs.create(row)

    async def update_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        request: ProjectBriefUpdateRequest,
    ) -> ProjectBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if row is None:
            return None
        if row.status != ProjectBriefStatus.DRAFT:
            raise InvalidStateError("project_brief_submitted_immutable")

        current = self.content_from_row(row)
        merged = sanitize_brief_content(self._apply_update(current, request))
        fingerprint = compute_project_brief_fingerprint(merged)
        dumped = merged.model_dump(mode="json")
        row.language = merged.language
        row.project_basics = dumped["project_basics"]
        row.product = dumped["product"]
        row.market = dumped["market"]
        row.audience = dumped["audience"]
        row.economics = dumped["economics"]
        row.materials_summary = dumped["materials_summary"]
        row.assumptions = dumped["assumptions"]
        row.missing_data = dumped["missing_data"]
        row.readiness_status = merged.readiness_status
        row.readiness_reasons = dumped["readiness_reasons"]
        row.input_fingerprint = fingerprint
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._briefs.update(row)

    async def submit(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> ProjectBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if row is None:
            return None
        if row.status != ProjectBriefStatus.DRAFT:
            raise InvalidStateError("project_brief_invalid_transition")

        duplicate = await self._briefs.find_submitted_by_fingerprint(
            owner_id,
            project_id,
            row.input_fingerprint,
        )
        if duplicate is not None:
            raise DuplicateResourceError("project_brief_duplicate_fingerprint")

        previous = await self._briefs.get_latest_submitted(owner_id, project_id)
        now = utc_now()
        async with transactional(self._session):
            if previous is not None and previous.id != row.id:
                previous.status = ProjectBriefStatus.SUPERSEDED
                previous.updated_at = now
                await self._briefs.update(previous)
                row.supersedes_brief_id = previous.id

            row.status = ProjectBriefStatus.SUBMITTED
            row.submitted_at = now
            row.updated_at = now
            return await self._briefs.update(row)

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        request: ProjectBriefCreateRequest | None = None,
    ) -> ProjectBriefTable | None:
        """Create a new draft version from a submitted brief (or provided content)."""
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        source = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if source is None:
            return None
        if source.status not in (
            ProjectBriefStatus.SUBMITTED,
            ProjectBriefStatus.SUPERSEDED,
            ProjectBriefStatus.ARCHIVED,
        ):
            raise InvalidStateError("project_brief_invalid_transition")

        open_draft = await self._briefs.get_open_draft(owner_id, project_id)
        if open_draft is not None:
            raise InvalidStateError("project_brief_draft_already_exists")

        if request is not None:
            content = sanitize_brief_content(
                ProjectBriefContent.model_validate(request.model_dump()),
            )
        else:
            content = sanitize_brief_content(self.content_from_row(source))

        fingerprint = compute_project_brief_fingerprint(content)
        version = await self._briefs.max_version(owner_id, project_id) + 1
        row = self._row_from_content(
            owner_id=owner_id,
            project_id=project_id,
            version=version,
            content=content,
            fingerprint=fingerprint,
            supersedes_brief_id=source.id,
        )
        async with transactional(self._session):
            return await self._briefs.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> ProjectBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)

    async def list_briefs(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: ProjectBriefStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProjectBriefTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._briefs.list_for_project(
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
        *,
        prefer_submitted: bool = True,
    ) -> ProjectBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if prefer_submitted:
            submitted = await self._briefs.get_latest_submitted(owner_id, project_id)
            if submitted is not None:
                return submitted
        return await self._briefs.get_latest_any(owner_id, project_id)

    # Invariants for tests — side-effect firewall
    @staticmethod
    def creates_investigation() -> bool:
        return False

    @staticmethod
    def creates_agent_run() -> bool:
        return False

    @staticmethod
    def creates_verdict() -> bool:
        return False

    @staticmethod
    def creates_strategy() -> bool:
        return False
