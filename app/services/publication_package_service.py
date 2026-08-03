"""Publication package service — draft packages only, no send (Phase AI.43–AI.44)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.db.models.marketing import PublicationPackageTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.marketing.contracts import PublicationPackageStatus
from app.marketing.publication_package_policy import (
    assert_package_can_be_approved,
    assert_package_can_be_archived,
    assert_package_can_submit_for_review,
    validate_publication_package_transition,
)
from app.marketing.publication_package_conversion import (
    assert_asset_eligible_for_publication_package,
    build_publication_package_fields,
    parse_publication_channel,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class PublicationPackageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PublicationPackageRepository(session)
        self._assets = ContentAssetRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
    ) -> PublicationPackageTable | None:
        return await self._repo.get_by_id_for_owner(package_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        content_asset_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[PublicationPackageTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_by_project(
            owner_id,
            project_id,
            content_asset_id=content_asset_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def create_from_approved_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        *,
        channel: str,
        title: str | None = None,
        body: str | None = None,
        cta: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PublicationPackageTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None

        assert_asset_eligible_for_publication_package(asset)
        parsed_channel = parse_publication_channel(channel)

        existing = await self._repo.get_by_asset_and_channel(
            owner_id,
            project_id,
            asset_id,
            parsed_channel,
        )
        if existing is not None:
            raise InvalidStateError(
                f"A publication package already exists for this asset and channel "
                f"({parsed_channel.value})",
            )

        fields = build_publication_package_fields(
            asset,
            channel=parsed_channel,
            title=title,
            body=body,
            cta=cta,
            metadata=metadata,
        )

        row = PublicationPackageTable(
            owner_id=owner_id,
            project_id=project_id,
            content_asset_id=asset_id,
            source_content_asset_id=asset_id,
            channel=parsed_channel,
            title=fields["title"],
            body=fields["body"],
            cta=fields["cta"],
            package_metadata=fields["metadata"],
            status=PublicationPackageStatus.DRAFT,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def submit_for_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
    ) -> PublicationPackageTable | None:
        row = await self.get(owner_id, project_id, package_id)
        if row is None:
            return None
        assert_package_can_submit_for_review(row)
        validate_publication_package_transition(
            row.status,
            PublicationPackageStatus.REVIEW,
        )
        row.status = PublicationPackageStatus.REVIEW
        row.submitted_for_review_at = utc_now()
        async with transactional(self._session):
            return await self._repo.update(row)

    async def approve_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
    ) -> PublicationPackageTable | None:
        row = await self.get(owner_id, project_id, package_id)
        if row is None:
            return None
        assert_package_can_be_approved(row)
        validate_publication_package_transition(
            row.status,
            PublicationPackageStatus.APPROVED,
        )
        row.status = PublicationPackageStatus.APPROVED
        row.approved_at = utc_now()
        async with transactional(self._session):
            return await self._repo.update(row)

    async def archive_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
    ) -> PublicationPackageTable | None:
        row = await self.get(owner_id, project_id, package_id)
        if row is None:
            return None
        assert_package_can_be_archived(row)
        validate_publication_package_transition(
            row.status,
            PublicationPackageStatus.ARCHIVED,
        )
        row.status = PublicationPackageStatus.ARCHIVED
        async with transactional(self._session):
            return await self._repo.update(row)
