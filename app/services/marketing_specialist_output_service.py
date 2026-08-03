"""Marketing specialist output artifacts (Phase AI.30) — placeholder only."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.marketing_specialist_registry import get_marketing_specialist
from app.core.exceptions import InvalidStateError
from app.db.models.marketing_specialist_output import (
    MarketingSpecialistOutputTable,
    MarketingSpecialistOutputVersionTable,
)
from app.db.repositories.marketing_plan_execution_runs import (
    MarketingPlanExecutionRunRepository,
)
from app.db.repositories.marketing_specialist_output_versions import (
    MarketingSpecialistOutputVersionRepository,
)
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.models.marketing import ContentAssetTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.marketing.contracts import ContentAssetStatus, ContentAssetVersionSource
from app.marketing.copywriter_quality_gate import validate_copywriter_content_items
from app.marketing.copywriter_asset_conversion import (
    assert_copywriter_output_eligible,
    build_content_asset_fields_from_copywriter,
    build_content_asset_fields_from_copywriter_item,
    extract_content_items,
)
from app.schemas.contracts import (
    MarketingPlanExecutionTaskSnapshot,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_PLACEHOLDER_CONTENT = "Specialist output generation is not enabled in this phase."
_PLACEHOLDER_OUTPUT_TYPE = "placeholder"
_TITLE_MAX = 512
_CONTENT_MAX = 8192

_ACTIVE_STATUSES = frozenset(
    {
        MarketingSpecialistOutputStatus.DRAFT,
        MarketingSpecialistOutputStatus.APPROVED,
    },
)


def _snapshot_at_index(
    snapshots: list[MarketingPlanExecutionTaskSnapshot],
    task_index: int,
) -> MarketingPlanExecutionTaskSnapshot:
    if task_index < 0 or task_index >= len(snapshots):
        raise InvalidStateError("Task index is out of range for this execution run")
    return snapshots[task_index]


def _default_title(specialist: MarketingSpecialistType) -> str:
    profile = get_marketing_specialist(specialist)
    return f"{profile.name} output"[:_TITLE_MAX]


def _placeholder_structured_data(
    snapshot: MarketingPlanExecutionTaskSnapshot,
) -> dict[str, Any]:
    return {
        "mode": "placeholder",
        "objective": snapshot.objective,
        "expected_output": snapshot.expected_output,
    }


class MarketingSpecialistOutputService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outputs = MarketingSpecialistOutputRepository(session)
        self._versions = MarketingSpecialistOutputVersionRepository(session)
        self._execution_runs = MarketingPlanExecutionRunRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def create_placeholder_output(
        self,
        owner_id: UUID,
        project_id: UUID,
        execution_run_id: UUID,
        task_index: int,
    ) -> MarketingSpecialistOutputTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        run = await self._execution_runs.get_by_id_for_owner(
            execution_run_id,
            owner_id,
            project_id,
        )
        if run is None:
            return None

        existing = await self._outputs.get_by_run_and_task_index(execution_run_id, task_index)
        if existing is not None:
            if existing.status in _ACTIVE_STATUSES:
                return existing
            raise InvalidStateError(
                "A specialist output for this task exists but is archived",
            )

        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
        snapshot = _snapshot_at_index(snapshots, task_index)
        title = _default_title(snapshot.specialist)
        content = _PLACEHOLDER_CONTENT
        structured = _placeholder_structured_data(snapshot)

        async with transactional(self._session):
            row = MarketingSpecialistOutputTable(
                owner_id=owner_id,
                project_id=project_id,
                marketing_plan_id=run.marketing_plan_id,
                execution_run_id=run.id,
                task_index=task_index,
                specialist=snapshot.specialist,
                title=title,
                output_type=_PLACEHOLDER_OUTPUT_TYPE,
                content=content[:_CONTENT_MAX],
                structured_data=structured,
                status=MarketingSpecialistOutputStatus.DRAFT,
                current_version_number=1,
                approved_version_number=None,
            )
            row = await self._outputs.create(row)

            version_row = MarketingSpecialistOutputVersionTable(
                specialist_output_id=row.id,
                version_number=1,
                title=row.title,
                output_type=row.output_type,
                content=row.content,
                structured_data=row.structured_data,
                created_by_run_id=execution_run_id,
            )
            await self._versions.create(version_row)
            return row

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
    ) -> MarketingSpecialistOutputTable | None:
        return await self._outputs.get_by_id_for_owner(output_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        execution_run_id: UUID | None = None,
        marketing_plan_id: UUID | None = None,
        specialist: MarketingSpecialistType | None = None,
        status: MarketingSpecialistOutputStatus | None = None,
        limit: int = 50,
    ) -> list[MarketingSpecialistOutputTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._outputs.list_by_project(
            owner_id,
            project_id,
            execution_run_id=execution_run_id,
            marketing_plan_id=marketing_plan_id,
            specialist=specialist,
            status=status,
            limit=limit,
        )

    async def approve(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
    ) -> MarketingSpecialistOutputTable | None:
        row = await self.get(owner_id, project_id, output_id)
        if row is None:
            return None
        if row.status == MarketingSpecialistOutputStatus.ARCHIVED:
            raise InvalidStateError("Archived specialist outputs cannot be approved")
        if row.status != MarketingSpecialistOutputStatus.DRAFT:
            raise InvalidStateError("Only draft specialist outputs can be approved")

        async with transactional(self._session):
            row.status = MarketingSpecialistOutputStatus.APPROVED
            row.approved_version_number = row.current_version_number
            return await self._outputs.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
    ) -> MarketingSpecialistOutputTable | None:
        row = await self.get(owner_id, project_id, output_id)
        if row is None:
            return None
        if row.status == MarketingSpecialistOutputStatus.ARCHIVED:
            return row
        if row.status not in _ACTIVE_STATUSES:
            raise InvalidStateError("Specialist output cannot be archived from this status")

        async with transactional(self._session):
            row.status = MarketingSpecialistOutputStatus.ARCHIVED
            return await self._outputs.update(row)

    async def list_versions(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
    ) -> list[MarketingSpecialistOutputVersionTable] | None:
        row = await self.get(owner_id, project_id, output_id)
        if row is None:
            return None
        return await self._versions.list_for_output(row.id)

    async def get_version(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
        version_number: int,
    ) -> MarketingSpecialistOutputVersionTable | None:
        row = await self.get(owner_id, project_id, output_id)
        if row is None:
            return None
        return await self._versions.get_version(row.id, version_number)

    async def create_content_asset_from_copywriter(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
    ) -> ContentAssetTable | None:
        """Explicit Copywriter → ContentAsset draft conversion (Phase AI.40)."""
        row = await self.get(owner_id, project_id, output_id)
        if row is None:
            return None

        assert_copywriter_output_eligible(
            specialist=row.specialist,
            status=row.status.value
            if hasattr(row.status, "value")
            else str(row.status),
            output_type=row.output_type,
        )

        assets = ContentAssetRepository(self._session)
        existing = await assets.get_by_source_specialist_output_id(
            owner_id,
            project_id,
            output_id,
        )
        if existing is not None:
            raise InvalidStateError(
                "A content asset already exists for this copywriter specialist output",
            )

        fields = build_content_asset_fields_from_copywriter(
            title=row.title,
            content=row.content,
            structured_data=dict(row.structured_data) if row.structured_data else None,
        )
        created = await ContentAssetService(self._session).create(
            owner_id,
            project_id,
            asset_type=fields["asset_type"],
            title=fields["title"],
            body=fields["body"],
            metadata=fields["metadata"],
            status=ContentAssetStatus.DRAFT,
            source_marketing_plan_id=row.marketing_plan_id,
            source_execution_run_id=row.execution_run_id,
            source_specialist_output_id=row.id,
            source_specialist_type=MarketingSpecialistType.COPYWRITER.value,
            created_by_source=ContentAssetVersionSource.HTTP_API,
        )
        if created is None:
            raise InvalidStateError("Failed to create content asset from copywriter output")
        return created

    async def create_content_assets_from_copywriter(
        self,
        owner_id: UUID,
        project_id: UUID,
        output_id: UUID,
        *,
        content_planner_output_id: UUID,
        idempotency_key: str | None = None,
        minimum_assets: int = 3,
        expected_channel: str | None = None,
    ) -> list[ContentAssetTable]:
        """Create one ContentAsset per copywriter content_item (R3.3B-LITE)."""
        row = await self.get(owner_id, project_id, output_id)
        if row is None:
            return []

        assert_copywriter_output_eligible(
            specialist=row.specialist,
            status=row.status.value
            if hasattr(row.status, "value")
            else str(row.status),
            output_type=row.output_type,
        )

        structured = dict(row.structured_data) if row.structured_data else None
        if structured and structured.get("mock"):
            raise InvalidStateError("Mock provider output cannot create commercial content assets")

        assets_repo = ContentAssetRepository(self._session)
        existing = await assets_repo.list_by_source_specialist_output_id(
            owner_id,
            project_id,
            output_id,
        )
        if existing:
            if idempotency_key and all(
                (row.asset_metadata or {}).get("content_factory_idempotency_key") == idempotency_key
                for row in existing
            ):
                return existing
            raise InvalidStateError(
                "Content assets already exist for this copywriter specialist output",
            )

        items = extract_content_items(structured)
        resolved_channel = (
            expected_channel
            or (structured or {}).get("brief_channel")
            or ""
        )
        validate_copywriter_content_items(
            items,
            expected_channel=str(resolved_channel),
            minimum_items=minimum_assets,
            require_russian=str(resolved_channel).lower() in {"", "telegram", "social", "blog"},
        )
        created_rows: list[ContentAssetTable] = []
        asset_service = ContentAssetService(self._session)
        planner_id_str = str(content_planner_output_id)

        for index, item in enumerate(items, start=1):
            fields = build_content_asset_fields_from_copywriter_item(
                item=item,
                slot_index=index,
                fallback_title=row.title,
                structured_data=structured,
                content_planner_output_id=planner_id_str,
                idempotency_key=idempotency_key,
            )
            if fields is None:
                continue

            created = await asset_service.create(
                owner_id,
                project_id,
                asset_type=fields["asset_type"],
                title=fields["title"],
                body=fields["body"],
                metadata=fields["metadata"],
                status=ContentAssetStatus.DRAFT,
                source_marketing_plan_id=row.marketing_plan_id,
                source_execution_run_id=row.execution_run_id,
                source_specialist_output_id=row.id,
                source_specialist_type=MarketingSpecialistType.COPYWRITER.value,
                created_by_source=ContentAssetVersionSource.HTTP_API,
            )
            if created is None:
                raise InvalidStateError("Failed to create content asset from copywriter output")
            created_rows.append(created)

        if len(created_rows) < minimum_assets:
            raise InvalidStateError(
                f"Copywriter output produced fewer than {minimum_assets} valid content items",
            )
        return created_rows
