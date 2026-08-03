"""Publication package job service — dry-run + reliability (Phase AI.62–AI.68)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.marketing.contracts import PublicationPackageStatus
from app.publishing.contracts import PublishingChannelStatus
from app.publishing_foundation.contracts import (
    PublicationPackageJobStatus,
    PublishingAuditEventType,
)
from app.core.config import get_settings
from app.publishing.providers.contracts import PublishingExecutionInput, PublishingProviderType
from app.publishing.providers.dry_run_provider import get_dry_run_provider
from app.publishing.providers.registry import get_provider, resolve_provider_type_for_channel
from app.publishing_foundation.job_idempotency import (
    build_idempotency_fingerprint,
    hash_idempotency_key,
    normalize_publication_job_idempotency_key,
)
from app.publishing_foundation.payload_snapshot import build_package_payload_snapshot
from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata
from app.publishing_foundation.snapshot_hash import (
    compute_snapshot_hash,
    verify_snapshot_integrity,
)
from app.services.projects_service import ProjectService
from app.services.publishing_audit_service import PublishingAuditService
from app.services.transaction import transactional

_FOUNDATION_CHANNEL_TYPES = frozenset({"telegram", "instagram", "linkedin", "blog"})
_REPLAYABLE_STATUSES = frozenset(
    {
        PublicationPackageJobStatus.FAILED,
        PublicationPackageJobStatus.CANCELLED,
    },
)
_SNAPSHOT_TAMPERED = "snapshot_tampered"


class PublicationPackageJobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = PublicationPackageJobRepository(session)
        self._packages = PublicationPackageRepository(session)
        self._channels = PublishingChannelRepository(session)
        self._projects = ProjectService(session)
        self._audit = PublishingAuditService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _assert_package_approved(self, package: object) -> None:
        status = getattr(package, "status", None)
        if status != PublicationPackageStatus.APPROVED:
            raise InvalidStateError(
                "Only approved publication packages can create publish jobs",
            )

    def _assert_channel_active(self, channel: object) -> None:
        status = getattr(channel, "status", None)
        channel_type = getattr(getattr(channel, "channel_type", None), "value", None)
        if channel_type not in _FOUNDATION_CHANNEL_TYPES:
            raise InvalidStateError("Channel type is not supported for foundation publishing")
        if status != PublishingChannelStatus.ACTIVE:
            raise InvalidStateError(
                f"Only active publishing channels can be used (status={status})",
            )

    def _build_fingerprint(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
        channel_id: UUID,
    ) -> str:
        return build_idempotency_fingerprint(
            owner_id=owner_id,
            project_id=project_id,
            package_id=package_id,
            channel_id=channel_id,
        )

    def _assert_snapshot_integrity(self, row: PublicationPackageJobTable) -> None:
        snapshot = dict(row.payload_snapshot or {})
        if not verify_snapshot_integrity(snapshot, row.snapshot_hash):
            raise InvalidStateError(_SNAPSHOT_TAMPERED)

    async def _fail_snapshot_tampered(
        self,
        row: PublicationPackageJobTable,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> PublicationPackageJobTable:
        row.status = PublicationPackageJobStatus.FAILED
        row.error = sanitize_publishing_metadata({"error_code": _SNAPSHOT_TAMPERED})
        row.finished_at = utc_now()
        async with transactional(self._session):
            failed = await self._jobs.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_FAILED,
                status="failed",
                channel_id=failed.channel_id,
                publication_package_job_id=failed.id,
                safe_metadata={"error_code": _SNAPSHOT_TAMPERED},
            )
            return failed

    async def get_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        return await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)

    async def list_jobs(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        publication_package_id: UUID | None = None,
        limit: int = 100,
    ) -> list[PublicationPackageJobTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._jobs.list_by_project(
            owner_id,
            project_id,
            publication_package_id=publication_package_id,
            limit=limit,
        )

    async def create_from_approved_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
        channel_id: UUID,
        *,
        idempotency_key: str | None = None,
    ) -> tuple[PublicationPackageJobTable | None, bool]:
        """Returns (job, created). created=False when idempotent replay of create."""
        if not await self._ensure_project_owned(owner_id, project_id):
            return None, False

        from app.services.beta_limits_service import BetaLimitsService

        await BetaLimitsService(self._session).assert_can_create_publication_job(
            owner_id,
            project_id,
        )

        package = await self._packages.get_by_id_for_owner(
            package_id,
            owner_id,
            project_id,
        )
        if package is None:
            return None, False

        channel = await self._channels.get_for_owner(
            channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if channel is None:
            return None, False

        self._assert_package_approved(package)
        self._assert_channel_active(channel)

        fingerprint = self._build_fingerprint(
            owner_id,
            project_id,
            package_id,
            channel_id,
        )
        normalized_key = normalize_publication_job_idempotency_key(idempotency_key)
        if normalized_key is not None:
            key_hash = hash_idempotency_key(normalized_key)
            existing = await self._jobs.get_by_idempotency_key_hash(
                owner_id,
                project_id,
                key_hash,
            )
            if existing is not None:
                if existing.idempotency_fingerprint != fingerprint:
                    raise InvalidStateError("idempotency_fingerprint_conflict")
                return existing, False

        active = await self._jobs.get_active_for_package_channel(
            owner_id,
            project_id,
            package_id,
            channel_id,
        )
        if active is not None:
            raise InvalidStateError(
                "An active publication job already exists for this package and channel",
            )

        snapshot = build_package_payload_snapshot(package)
        row = PublicationPackageJobTable(
            owner_id=owner_id,
            project_id=project_id,
            publication_package_id=package_id,
            channel_id=channel_id,
            status=PublicationPackageJobStatus.QUEUED,
            payload_snapshot=snapshot,
            snapshot_hash=compute_snapshot_hash(snapshot),
            idempotency_key_hash=(
                hash_idempotency_key(normalized_key) if normalized_key else None
            ),
            idempotency_fingerprint=fingerprint if normalized_key else None,
        )
        async with transactional(self._session):
            created = await self._jobs.create(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_CREATED,
                status="ok",
                channel_id=channel_id,
                publication_package_job_id=created.id,
                safe_metadata={
                    "publication_package_id": str(package_id),
                    "channel_type": channel.channel_type.value,
                    "idempotent": normalized_key is not None,
                },
            )
            return created, True

    async def replay_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        source = await self.get_job(owner_id, project_id, job_id)
        if source is None:
            return None
        if source.status not in _REPLAYABLE_STATUSES:
            raise InvalidStateError(
                f"Cannot replay job in status {source.status.value}",
            )

        active = await self._jobs.get_active_for_package_channel(
            owner_id,
            project_id,
            source.publication_package_id,
            source.channel_id,
        )
        if active is not None:
            raise InvalidStateError(
                "An active publication job already exists for this package and channel",
            )

        snapshot = dict(source.payload_snapshot or {})
        row = PublicationPackageJobTable(
            owner_id=owner_id,
            project_id=project_id,
            publication_package_id=source.publication_package_id,
            channel_id=source.channel_id,
            status=PublicationPackageJobStatus.QUEUED,
            payload_snapshot=snapshot,
            snapshot_hash=source.snapshot_hash,
            replay_of_job_id=source.id,
        )
        async with transactional(self._session):
            created = await self._jobs.create(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_REPLAYED,
                status="ok",
                channel_id=created.channel_id,
                publication_package_job_id=created.id,
                safe_metadata={"replay_of_job_id": str(source.id)},
            )
            return created

    async def start_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status != PublicationPackageJobStatus.QUEUED:
            raise InvalidStateError(
                f"Cannot start job in status {row.status.value}",
            )
        try:
            self._assert_snapshot_integrity(row)
        except InvalidStateError as exc:
            if str(exc) == _SNAPSHOT_TAMPERED:
                return await self._fail_snapshot_tampered(
                    row,
                    owner_id=owner_id,
                    project_id=project_id,
                )
            raise

        row.status = PublicationPackageJobStatus.RUNNING
        row.started_at = utc_now()
        async with transactional(self._session):
            updated = await self._jobs.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_STARTED,
                status="ok",
                channel_id=updated.channel_id,
                publication_package_job_id=updated.id,
                safe_metadata={"job_status": updated.status.value},
            )
            return updated

    async def complete_dry_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status == PublicationPackageJobStatus.QUEUED:
            row = await self.start_job(owner_id, project_id, job_id)
            if row is None:
                return None
            if row.status == PublicationPackageJobStatus.FAILED:
                return row
        if row.status != PublicationPackageJobStatus.RUNNING:
            raise InvalidStateError(
                f"Cannot complete dry-run in status {row.status.value}",
            )

        try:
            self._assert_snapshot_integrity(row)
        except InvalidStateError as exc:
            if str(exc) == _SNAPSHOT_TAMPERED:
                return await self._fail_snapshot_tampered(
                    row,
                    owner_id=owner_id,
                    project_id=project_id,
                )
            raise

        channel = await self._channels.get_for_owner(
            row.channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if channel is None:
            return None

        execution = await self._run_provider(
            row,
            channel,
            provider_type=PublishingProviderType.DRY_RUN,
            owner_id=owner_id,
            project_id=project_id,
        )
        if not execution.success:
            row.status = PublicationPackageJobStatus.FAILED
            row.error = sanitize_publishing_metadata(
                {
                    "error_code": execution.error_code,
                    "message": execution.error_message,
                    "provider": "dry_run",
                },
            )
            row.finished_at = utc_now()
            async with transactional(self._session):
                failed = await self._jobs.update(row)
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=PublishingAuditEventType.JOB_FAILED,
                    status="failed",
                    channel_id=failed.channel_id,
                    publication_package_job_id=failed.id,
                    safe_metadata={
                        "provider": "dry_run",
                        "error_code": execution.error_code,
                    },
                )
                return failed

        row.status = PublicationPackageJobStatus.DRY_RUN_SUCCEEDED
        row.result_metadata = sanitize_publishing_metadata(execution.result_metadata)
        row.error = None
        row.finished_at = utc_now()
        async with transactional(self._session):
            updated = await self._jobs.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_DRY_RUN_SUCCEEDED,
                status="ok",
                channel_id=updated.channel_id,
                publication_package_job_id=updated.id,
                safe_metadata=dict(updated.result_metadata or {}),
            )
            return updated

    async def _run_provider(
        self,
        row: PublicationPackageJobTable,
        channel: object,
        *,
        provider_type: PublishingProviderType,
        owner_id: UUID,
        project_id: UUID,
    ):
        provider = get_provider(provider_type, settings=get_settings())
        channel_type = getattr(getattr(channel, "channel_type", None), "value", "")
        execution_input = PublishingExecutionInput(
            job_id=row.id,
            owner_id=owner_id,
            project_id=project_id,
            publication_package_id=row.publication_package_id,
            channel_id=row.channel_id,
            channel_type=channel_type,
            payload_snapshot=dict(row.payload_snapshot or {}),
            channel_config=dict(getattr(channel, "channel_config", None) or {}),
        )
        return await provider.publish(
            row,
            channel,  # type: ignore[arg-type]
            dict(row.payload_snapshot or {}),
            execution_input=execution_input,
        )

    async def execute_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        """Real publish — Telegram only when explicitly enabled."""
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None

        if row.status not in (
            PublicationPackageJobStatus.QUEUED,
            PublicationPackageJobStatus.RUNNING,
        ):
            raise InvalidStateError(
                f"Cannot execute job in status {row.status.value}",
            )

        channel = await self._channels.get_for_owner(
            row.channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if channel is None:
            return None

        try:
            provider_type = resolve_provider_type_for_channel(channel.channel_type.value)
        except InvalidStateError:
            raise

        if row.status == PublicationPackageJobStatus.QUEUED:
            row = await self.start_job(owner_id, project_id, job_id)
            if row is None:
                return None
            if row.status == PublicationPackageJobStatus.FAILED:
                return row

        if row.status != PublicationPackageJobStatus.RUNNING:
            raise InvalidStateError(
                f"Cannot execute job in status {row.status.value}",
            )

        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=PublishingAuditEventType.JOB_REAL_EXECUTE_REQUESTED,
            status="ok",
            channel_id=row.channel_id,
            publication_package_job_id=row.id,
            safe_metadata={
                "job_id": str(row.id),
                "channel_type": channel.channel_type.value,
                "provider": provider_type.value,
            },
        )

        execution = await self._run_provider(
            row,
            channel,
            provider_type=provider_type,
            owner_id=owner_id,
            project_id=project_id,
        )

        if execution.success:
            row.status = PublicationPackageJobStatus.SUCCEEDED
            row.result_metadata = sanitize_publishing_metadata(execution.result_metadata)
            row.error = None
            row.finished_at = utc_now()
            async with transactional(self._session):
                updated = await self._jobs.update(row)
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=PublishingAuditEventType.JOB_SUCCEEDED,
                    status="ok",
                    channel_id=updated.channel_id,
                    publication_package_job_id=updated.id,
                    safe_metadata={
                        "job_id": str(updated.id),
                        "channel_type": channel.channel_type.value,
                        "provider": provider_type.value,
                        "status": updated.status.value,
                        "latency_ms": execution.latency_ms,
                    },
                )
                return updated

        row.status = PublicationPackageJobStatus.FAILED
        row.error = sanitize_publishing_metadata(
            {
                "error_code": execution.error_code,
                "message": execution.error_message,
                "provider": provider_type.value,
            },
        )
        row.finished_at = utc_now()
        async with transactional(self._session):
            failed = await self._jobs.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_FAILED,
                status="failed",
                channel_id=failed.channel_id,
                publication_package_job_id=failed.id,
                safe_metadata={
                    "job_id": str(failed.id),
                    "channel_type": channel.channel_type.value,
                    "provider": provider_type.value,
                    "error_code": execution.error_code,
                    "latency_ms": execution.latency_ms,
                },
            )
            return failed

    async def execute_dry_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        """Start (if needed) and complete dry-run in one step."""
        row = await self.get_job(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status == PublicationPackageJobStatus.QUEUED:
            started = await self.start_job(owner_id, project_id, job_id)
            if started is None:
                return None
            if started.status == PublicationPackageJobStatus.FAILED:
                return started
        return await self.complete_dry_run(owner_id, project_id, job_id)
