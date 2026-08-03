"""Media generation orchestration — jobs only, gated providers (Phase AI.56–AI.58)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.media import MediaAssetTable, MediaAssetVersionTable, MediaGenerationJobTable
from app.db.repositories.media_asset_versions import MediaAssetVersionRepository
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.db.repositories.media_generation_jobs import MediaGenerationJobRepository
from app.marketing.media_contracts import MediaAssetStatus, MediaAssetType, MediaBriefStatus
from app.media_generation.contracts import (
    ImageGenerationInput,
    ImageGenerationResult,
    MediaGenerationJobStatus,
    MediaGenerationProvider,
)
from app.media_generation.prompt_builder import build_image_prompt_from_brief
from app.media_generation.provider_registry import assert_provider_selectable, get_image_provider
from app.media_generation.safe_metadata import sanitize_generation_metadata
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_IMAGE_MEDIA_TYPE = MediaAssetType.IMAGE.value


class MediaGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = MediaGenerationJobRepository(session)
        self._briefs = MediaBriefRepository(session)
        self._assets = MediaAssetRepository(session)
        self._versions = MediaAssetVersionRepository(session)
        self._projects = ProjectService(session)
        self._settings = get_settings()

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _parse_provider(self, provider: str) -> MediaGenerationProvider:
        cleaned = sanitize_text(provider).strip().lower()
        try:
            return MediaGenerationProvider(cleaned)
        except ValueError as exc:
            raise InvalidStateError(
                f"Unsupported media generation provider: {provider}",
            ) from exc

    def _assert_brief_eligible(self, brief: object) -> None:
        status = getattr(brief, "status", None)
        if status != MediaBriefStatus.APPROVED:
            raise InvalidStateError(
                "Only approved media briefs can start media generation",
            )

    async def get_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> MediaGenerationJobTable | None:
        return await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)

    async def list_jobs_for_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> list[MediaGenerationJobTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id) is None:
            return None
        return await self._jobs.list_by_brief(owner_id, project_id, brief_id)

    async def create_job_from_approved_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        *,
        provider: str = MediaGenerationProvider.MOCK.value,
        media_type: str = _IMAGE_MEDIA_TYPE,
    ) -> MediaGenerationJobTable | None:
        if media_type != _IMAGE_MEDIA_TYPE:
            raise InvalidStateError("Only image media_type is supported in this phase")

        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        from app.services.beta_limits_service import BetaLimitsService

        await BetaLimitsService(self._session).assert_can_create_generation_job(
            owner_id,
            project_id,
        )

        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if brief is None:
            return None

        self._assert_brief_eligible(brief)
        parsed_provider = self._parse_provider(provider)
        assert_provider_selectable(parsed_provider, self._settings)

        active = await self._jobs.get_active_for_brief(owner_id, project_id, brief_id)
        if active is not None:
            raise InvalidStateError(
                "An active media generation job already exists for this brief",
            )

        prompt = build_image_prompt_from_brief(brief)
        row = MediaGenerationJobTable(
            owner_id=owner_id,
            project_id=project_id,
            media_brief_id=brief_id,
            media_asset_id=None,
            provider=parsed_provider,
            media_type=media_type,
            prompt=prompt,
            status=MediaGenerationJobStatus.QUEUED,
            result_metadata={},
        )
        async with transactional(self._session):
            return await self._jobs.create(row)

    async def start_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> MediaGenerationJobTable | None:
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status != MediaGenerationJobStatus.QUEUED:
            raise InvalidStateError("Only queued media generation jobs can be started")
        row.status = MediaGenerationJobStatus.RUNNING
        row.started_at = datetime.now(UTC)
        async with transactional(self._session):
            return await self._jobs.update(row)

    async def complete_mock_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> MediaGenerationJobTable | None:
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.provider != MediaGenerationProvider.MOCK:
            raise InvalidStateError("complete_mock_job requires provider=mock")
        if row.status not in (
            MediaGenerationJobStatus.QUEUED,
            MediaGenerationJobStatus.RUNNING,
        ):
            raise InvalidStateError("Job is not in a completable state")
        if row.status == MediaGenerationJobStatus.QUEUED:
            row.status = MediaGenerationJobStatus.RUNNING
            row.started_at = datetime.now(UTC)
        provider = get_image_provider(MediaGenerationProvider.MOCK, self._settings)
        result = await provider.generate_image(
            ImageGenerationInput(prompt=row.prompt, size="1024x1024"),
        )
        return await self._finalize_success(owner_id, project_id, row, result)

    async def execute_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> MediaGenerationJobTable | None:
        """Run provider for a job (mock or gated OpenAI Images)."""
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status not in (
            MediaGenerationJobStatus.QUEUED,
            MediaGenerationJobStatus.RUNNING,
        ):
            raise InvalidStateError("Job is not in a runnable state")
        if row.status == MediaGenerationJobStatus.QUEUED:
            row.status = MediaGenerationJobStatus.RUNNING
            row.started_at = datetime.now(UTC)
            await self._jobs.update(row)

        provider_impl = get_image_provider(row.provider, self._settings)
        try:
            result = await provider_impl.generate_image(
                ImageGenerationInput(
                    prompt=row.prompt,
                    model=self._settings.openai_images_model
                    if row.provider == MediaGenerationProvider.OPENAI_IMAGES
                    else None,
                    size="1024x1024",
                ),
            )
        except Exception as exc:
            return await self._finalize_failure(owner_id, project_id, row, str(exc))
        return await self._finalize_success(owner_id, project_id, row, result)

    async def _finalize_success(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: MediaGenerationJobTable,
        result: ImageGenerationResult,
    ) -> MediaGenerationJobTable:
        safe_meta = sanitize_generation_metadata(result.safe_metadata)
        row.status = MediaGenerationJobStatus.SUCCEEDED
        row.finished_at = datetime.now(UTC)
        row.result_metadata = safe_meta
        row.error = None

        async with transactional(self._session):
            asset = await self._upsert_media_asset_from_generation(
                owner_id,
                project_id,
                row,
                result,
                safe_meta,
            )
            row.media_asset_id = asset.id
            updated_job = await self._jobs.update(row)
        return updated_job

    async def _finalize_failure(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: MediaGenerationJobTable,
        error_message: str,
    ) -> MediaGenerationJobTable:
        row.status = MediaGenerationJobStatus.FAILED
        row.finished_at = datetime.now(UTC)
        row.error = sanitize_text(error_message)[:1024]
        async with transactional(self._session):
            if row.media_asset_id is not None:
                asset = await self._assets.get_by_id_for_owner(
                    row.media_asset_id,
                    owner_id,
                    project_id,
                )
                if asset is not None:
                    asset.status = MediaAssetStatus.GENERATION_FAILED
                    await self._assets.update(asset)
            return await self._jobs.update(row)

    async def _upsert_media_asset_from_generation(
        self,
        owner_id: UUID,
        project_id: UUID,
        job: MediaGenerationJobTable,
        result: ImageGenerationResult,
        safe_meta: dict,
    ) -> MediaAssetTable:
        brief_id = job.media_brief_id
        existing = await self._assets.get_by_brief_and_type(
            owner_id,
            project_id,
            brief_id,
            MediaAssetType.IMAGE,
        )
        merged_metadata = {
            **safe_meta,
            "source_generation_job_id": str(job.id),
            "media_brief_id": str(brief_id),
        }

        if existing is None:
            asset = MediaAssetTable(
                owner_id=owner_id,
                project_id=project_id,
                media_brief_id=brief_id,
                source_media_brief_id=brief_id,
                media_type=MediaAssetType.IMAGE,
                status=MediaAssetStatus.DRAFT,
                generation_provider=result.provider,
                generation_metadata=merged_metadata,
                source_generation_job_id=job.id,
                provider=result.provider,
                provider_asset_ref=result.provider_asset_ref,
                storage_uri=result.storage_uri,
                mime_type=result.mime_type,
                width=result.width,
                height=result.height,
                current_version_number=1,
            )
            created = await self._assets.create(asset)
            await self._append_version(
                created,
                job_id=job.id,
                result=result,
                safe_meta=merged_metadata,
                version_number=1,
            )
            return created

        existing.status = MediaAssetStatus.DRAFT
        existing.generation_provider = result.provider
        existing.generation_metadata = merged_metadata
        existing.source_generation_job_id = job.id
        existing.provider = result.provider
        existing.provider_asset_ref = result.provider_asset_ref
        existing.storage_uri = result.storage_uri
        existing.mime_type = result.mime_type
        existing.width = result.width
        existing.height = result.height
        next_version = existing.current_version_number + 1
        existing.current_version_number = next_version
        updated = await self._assets.update(existing)
        await self._append_version(
            updated,
            job_id=job.id,
            result=result,
            safe_meta=merged_metadata,
            version_number=next_version,
        )
        return updated

    async def _append_version(
        self,
        asset: MediaAssetTable,
        *,
        job_id: UUID,
        result: ImageGenerationResult,
        safe_meta: dict,
        version_number: int,
    ) -> MediaAssetVersionTable:
        version_row = MediaAssetVersionTable(
            owner_id=asset.owner_id,
            project_id=asset.project_id,
            media_asset_id=asset.id,
            version_number=version_number,
            source_generation_job_id=job_id,
            storage_uri=result.storage_uri,
            provider_asset_ref=result.provider_asset_ref,
            version_metadata=dict(safe_meta),
        )
        return await self._versions.create(version_row)
