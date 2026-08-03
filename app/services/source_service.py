"""Source service (Commercial MVP P0.3).

Immutable provenance registry. No fetch, parse, Evidence, Agent Run, or LLM.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.source import InvestigationSourceLinkTable, SourceTable
from app.db.repositories.investigations import InvestigationRepository
from app.db.repositories.sources import (
    InvestigationSourceLinkRepository,
    SourceRepository,
)
from app.domain.source_fingerprint import (
    compute_source_fingerprint,
    derive_domain,
    derive_freshness,
    normalize_url,
    sanitize_source_metadata,
    to_source_snapshot,
    validate_capabilities,
)
from app.schemas.contracts import (
    InvestigationSourceLinkCreateRequest,
    InvestigationSourceLinkStatus,
    InvestigationSourceLinkUpdateRequest,
    SourceArchiveRequest,
    SourceCreateRequest,
    SourceProvenanceType,
    SourceReliabilityLevel,
    SourceReliabilityReviewRequest,
    SourceStatus,
    SourceSupersedeRequest,
    SourceType,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_STATUS_TRANSITIONS: dict[SourceStatus, frozenset[SourceStatus]] = {
    SourceStatus.REGISTERED: frozenset(
        {
            SourceStatus.AVAILABLE,
            SourceStatus.UNAVAILABLE,
            SourceStatus.REJECTED,
            SourceStatus.ARCHIVED,
            SourceStatus.SUPERSEDED,
        }
    ),
    SourceStatus.AVAILABLE: frozenset(
        {
            SourceStatus.UNAVAILABLE,
            SourceStatus.REJECTED,
            SourceStatus.ARCHIVED,
            SourceStatus.SUPERSEDED,
        }
    ),
    SourceStatus.UNAVAILABLE: frozenset(
        {
            SourceStatus.AVAILABLE,
            SourceStatus.REJECTED,
            SourceStatus.ARCHIVED,
            SourceStatus.SUPERSEDED,
        }
    ),
    SourceStatus.REJECTED: frozenset({SourceStatus.ARCHIVED}),
    SourceStatus.SUPERSEDED: frozenset(),
    SourceStatus.ARCHIVED: frozenset(),
}


class SourceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sources = SourceRepository(session)
        self._links = InvestigationSourceLinkRepository(session)
        self._investigations = InvestigationRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _build_row(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        request: SourceCreateRequest,
        version: int,
        supersedes_source_id: UUID | None,
    ) -> SourceTable:
        if request.provenance_type == SourceProvenanceType.GENERATED:
            # generated must not default to high — reliability always unverified at create
            pass
        title = sanitize_text(request.title).strip()
        if not title:
            raise InvalidStateError("invalid_provenance")
        caps = validate_capabilities(request.capabilities)
        url = normalize_url(request.url)
        domain = derive_domain(url, request.domain)
        fingerprint = compute_source_fingerprint(
            project_id=project_id,
            source_type=request.source_type,
            title=title,
            url=url,
            publisher=request.publisher,
            published_at=request.published_at,
            content_hash=request.content_hash,
        )
        freshness = derive_freshness(
            published_at=request.published_at,
            accessed_at=request.accessed_at,
            captured_at=request.captured_at,
            explicit=request.freshness_status,
        )
        meta = sanitize_source_metadata(request.metadata)
        meta["source_snapshot"] = True
        meta["fetches_external"] = False
        meta["stores_content"] = False
        meta["creates_evidence"] = False
        return SourceTable(
            owner_id=owner_id,
            project_id=project_id,
            source_type=request.source_type,
            provenance_type=request.provenance_type,
            title=title,
            origin=sanitize_text(request.origin or "").strip()[:500],
            url=url,
            domain=domain,
            publisher=(sanitize_text(request.publisher).strip()[:500] if request.publisher else None),
            language=request.language,
            country=request.country,
            published_at=request.published_at,
            captured_at=request.captured_at or utc_now(),
            accessed_at=request.accessed_at,
            freshness_status=freshness,
            reliability_level=SourceReliabilityLevel.UNVERIFIED,
            status=SourceStatus.REGISTERED,
            fingerprint=fingerprint,
            content_hash=request.content_hash,
            etag=request.etag,
            version=version,
            supersedes_source_id=supersedes_source_id,
            license_type=request.license_type,
            capabilities=[c.value for c in caps],
            reusable_within_project=True,
            metadata_json=meta,
        )

    async def register(
        self,
        owner_id: UUID,
        project_id: UUID,
        request: SourceCreateRequest,
    ) -> SourceTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        row = self._build_row(
            owner_id=owner_id,
            project_id=project_id,
            request=request,
            version=1,
            supersedes_source_id=None,
        )
        existing = await self._sources.find_live_by_fingerprint(
            owner_id,
            project_id,
            row.fingerprint,
        )
        if existing is not None:
            raise InvalidStateError("duplicate_source")

        investigation_id = request.attach_to_investigation_id
        async with transactional(self._session):
            created = await self._sources.create(row)
            if investigation_id is not None:
                await self._attach_unchecked(
                    owner_id,
                    project_id,
                    investigation_id,
                    created.id,
                    InvestigationSourceLinkCreateRequest(
                        purpose=request.link_purpose,
                        status=InvestigationSourceLinkStatus.ACCEPTED,
                    ),
                )
            return created

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
    ) -> SourceTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._sources.get_by_id_for_owner(source_id, owner_id, project_id)

    async def list_sources(
        self,
        owner_id: UUID,
        project_id: UUID,
        **filters: object,
    ) -> list[SourceTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._sources.list_for_project(owner_id, project_id, **filters)  # type: ignore[arg-type]

    async def list_versions(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
    ) -> list[SourceTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        rows = await self._sources.list_versions(owner_id, project_id, source_id)
        if not rows:
            return None
        return rows

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
        request: SourceSupersedeRequest,
    ) -> SourceTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        old = await self._sources.get_by_id_for_owner(source_id, owner_id, project_id)
        if old is None:
            return None
        if old.status in (SourceStatus.SUPERSEDED, SourceStatus.ARCHIVED):
            raise InvalidStateError("immutable_source")

        new_row = self._build_row(
            owner_id=owner_id,
            project_id=project_id,
            request=request,
            version=old.version + 1,
            supersedes_source_id=old.id,
        )
        # fingerprint may match intentionally for same identity with new content_hash
        dup = await self._sources.find_live_by_fingerprint(
            owner_id,
            project_id,
            new_row.fingerprint,
        )
        if dup is not None and dup.id != old.id:
            raise InvalidStateError("fingerprint_conflict")

        async with transactional(self._session):
            old.status = SourceStatus.SUPERSEDED
            old.updated_at = utc_now()
            await self._sources.update(old)
            return await self._sources.create(new_row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
        request: SourceArchiveRequest | None = None,
    ) -> SourceTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._sources.get_by_id_for_owner(source_id, owner_id, project_id)
        if row is None:
            return None
        self._assert_status(SourceStatus(row.status), SourceStatus.ARCHIVED)
        async with transactional(self._session):
            if request and request.reason:
                meta = dict(row.metadata_json or {})
                meta["archive_reason"] = sanitize_text(request.reason).strip()[:500]
                row.metadata_json = sanitize_source_metadata(meta)
            row.status = SourceStatus.ARCHIVED
            row.updated_at = utc_now()
            return await self._sources.update(row)

    async def review_reliability(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
        request: SourceReliabilityReviewRequest,
    ) -> SourceTable | None:
        """Audited reliability assessment without mutating identity fields."""
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._sources.get_by_id_for_owner(source_id, owner_id, project_id)
        if row is None:
            return None
        if row.status in (SourceStatus.SUPERSEDED, SourceStatus.ARCHIVED):
            raise InvalidStateError("immutable_source")
        if (
            row.provenance_type == SourceProvenanceType.GENERATED
            and request.reliability_level == SourceReliabilityLevel.HIGH
        ):
            raise InvalidStateError("invalid_provenance")

        async with transactional(self._session):
            meta = dict(row.metadata_json or {})
            history = list(meta.get("reliability_reviews") or [])
            if not isinstance(history, list):
                history = []
            history.append(
                {
                    "previous": row.reliability_level,
                    "next": request.reliability_level.value,
                    "note": sanitize_text(request.review_note or "").strip()[:500],
                    "at": utc_now().isoformat(),
                }
            )
            meta["reliability_reviews"] = history[-20:]
            row.metadata_json = sanitize_source_metadata(
                {k: v for k, v in meta.items() if k != "reliability_reviews"}
            )
            # preserve list under controlled key after sanitize
            row.metadata_json["reliability_reviews"] = history[-20:]
            row.reliability_level = request.reliability_level
            row.updated_at = utc_now()
            return await self._sources.update(row)

    async def snapshot(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
    ):
        row = await self.get(owner_id, project_id, source_id)
        if row is None:
            return None
        return to_source_snapshot(
            source_id=row.id,
            project_id=row.project_id,
            version=row.version,
            fingerprint=row.fingerprint,
            content_hash=row.content_hash,
            captured_at=row.captured_at,
            accessed_at=row.accessed_at,
            supersedes_source_id=row.supersedes_source_id,
            status=SourceStatus(row.status),
        )

    async def _attach_unchecked(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        source_id: UUID,
        request: InvestigationSourceLinkCreateRequest,
    ) -> InvestigationSourceLinkTable:
        inv = await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )
        if inv is None:
            raise InvalidStateError("investigation_not_found")
        source = await self._sources.get_by_id_for_owner(source_id, owner_id, project_id)
        if source is None:
            raise InvalidStateError("source_not_found")
        if source.project_id != project_id:
            raise InvalidStateError("cross_project_link")
        existing = await self._links.get_link(
            owner_id, project_id, investigation_id, source_id
        )
        if existing is not None:
            return existing
        link = InvestigationSourceLinkTable(
            owner_id=owner_id,
            project_id=project_id,
            investigation_id=investigation_id,
            source_id=source_id,
            purpose=request.purpose,
            investigation_area=request.investigation_area,
            notes=request.notes,
            status=request.status,
            added_by=owner_id,
        )
        return await self._links.create(link)

    async def attach(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        source_id: UUID,
        request: InvestigationSourceLinkCreateRequest | None = None,
    ) -> InvestigationSourceLinkTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        body = request or InvestigationSourceLinkCreateRequest()
        async with transactional(self._session):
            return await self._attach_unchecked(
                owner_id,
                project_id,
                investigation_id,
                source_id,
                body,
            )

    async def update_link(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        source_id: UUID,
        request: InvestigationSourceLinkUpdateRequest,
    ) -> InvestigationSourceLinkTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        link = await self._links.get_link(
            owner_id, project_id, investigation_id, source_id
        )
        if link is None:
            return None
        async with transactional(self._session):
            if request.purpose is not None:
                link.purpose = request.purpose
            if request.investigation_area is not None:
                link.investigation_area = request.investigation_area
            if request.notes is not None:
                link.notes = request.notes
            if request.status is not None:
                link.status = request.status
            link.updated_at = utc_now()
            return await self._links.update(link)

    async def detach_link(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        source_id: UUID,
    ) -> InvestigationSourceLinkTable | None:
        """Soft-detach: mark link excluded — never delete Source history."""
        return await self.update_link(
            owner_id,
            project_id,
            investigation_id,
            source_id,
            InvestigationSourceLinkUpdateRequest(
                status=InvestigationSourceLinkStatus.EXCLUDED,
            ),
        )

    async def list_investigation_sources(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        *,
        status: InvestigationSourceLinkStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[InvestigationSourceLinkTable, SourceTable]] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        inv = await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )
        if inv is None:
            return None
        links = await self._links.list_for_investigation(
            owner_id,
            project_id,
            investigation_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        out: list[tuple[InvestigationSourceLinkTable, SourceTable]] = []
        for link in links:
            source = await self._sources.get_by_id_for_owner(
                link.source_id, owner_id, project_id
            )
            if source is not None:
                out.append((link, source))
        return out

    def _assert_status(self, current: SourceStatus, target: SourceStatus) -> None:
        allowed = _STATUS_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise InvalidStateError("invalid_transition")

    @staticmethod
    def creates_agent_run() -> bool:
        return False

    @staticmethod
    def creates_llm_request() -> bool:
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

    @staticmethod
    def fetches_external() -> bool:
        return False

    @staticmethod
    def stores_file_content() -> bool:
        return False
