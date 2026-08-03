"""Content asset service — CRUD without LLM or graph (Phase 4.0+4.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.core.security import sanitize_payload, sanitize_text
from app.db.models.marketing import ContentAssetTable, ContentAssetVersionTable
from app.db.repositories.content_asset_versions import ContentAssetVersionRepository
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_briefs import MarketingBriefRepository
from app.db.repositories.marketing_campaigns import MarketingCampaignRepository
from app.events.outbox import EventOutboxService
from app.marketing.asset_policy import (
    assert_asset_can_be_approved,
    assert_asset_can_be_archived,
    assert_asset_can_create_revision,
    assert_asset_can_create_rollback_revision,
    assert_asset_can_submit_for_review,
    assert_asset_content_editable,
    validate_content_asset_transition,
)
from app.marketing.content_diff import build_content_asset_diff
from app.marketing.contracts import (
    ContentAssetStatus,
    ContentAssetType,
    ContentAssetVersionSource,
)
from app.marketing.plan_draft_asset_mapping import (
    metadata_plan_item_index,
    metadata_source_plan_draft_id,
    plan_item_to_asset_fields,
)
from app.marketing.plan_payload_validation import CampaignPlanContentItem
from app.services.agent_runs import AgentRunService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.services.transaction import transactional

_APPROVAL_SOURCE_HTTP_API = "http_api"
_ROLLBACK_REASON_MAX_CHARS = 256

_ASSET_UPDATE_FIELDS = frozenset(
    {
        "title",
        "body",
        "asset_metadata",
        "status",
        "brief_id",
        "campaign_id",
        "task_id",
        "agent_run_id",
    },
)

_CONTENT_VERSION_FIELDS = frozenset({"title", "body", "asset_metadata"})


class ContentAssetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ContentAssetRepository(session)
        self._versions = ContentAssetVersionRepository(session)
        self._briefs = MarketingBriefRepository(session)
        self._campaigns = MarketingCampaignRepository(session)
        self._projects = ProjectService(session)
        self._tasks = TaskService(session)
        self._agent_runs = AgentRunService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _validate_links(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        brief_id: UUID | None,
        campaign_id: UUID | None,
        task_id: UUID | None,
        agent_run_id: UUID | None,
    ) -> bool:
        if brief_id is not None:
            brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
            if brief is None:
                return False

        if campaign_id is not None:
            campaign = await self._campaigns.get_by_id_for_project(
                campaign_id,
                owner_id,
                project_id,
            )
            if campaign is None:
                return False
            if getattr(campaign.status, "value", str(campaign.status)) == "archived":
                raise InvalidStateError("Archived campaign cannot be used")

        if task_id is not None:
            task = await self._tasks.get_by_id(task_id)
            if task is None or task.project_id != project_id:
                return False

        if agent_run_id is not None:
            run = await self._agent_runs.get_run(owner_id, agent_run_id)
            if run is None or run.project_id != project_id:
                return False

        return True

    def _content_snapshot_changed(
        self,
        row: ContentAssetTable,
        filtered: dict[str, Any],
    ) -> bool:
        current_metadata = row.asset_metadata or {}
        return (
            ("title" in filtered and filtered["title"] != row.title)
            or ("body" in filtered and filtered["body"] != row.body)
            or (
                "asset_metadata" in filtered
                and filtered["asset_metadata"] != current_metadata
            )
        )

    async def _append_version(
        self,
        row: ContentAssetTable,
        *,
        title: str,
        body: str,
        metadata: dict[str, Any],
        version_number: int,
        created_by_source: ContentAssetVersionSource,
        created_by_agent_run_id: UUID | None,
    ) -> ContentAssetVersionTable:
        version_row = ContentAssetVersionTable(
            owner_id=row.owner_id,
            project_id=row.project_id,
            asset_id=row.id,
            version_number=version_number,
            title=title,
            body=body,
            version_metadata=metadata,
            created_by_source=created_by_source,
            created_by_agent_run_id=created_by_agent_run_id,
        )
        return await self._versions.create_version(version_row)

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        asset_type: ContentAssetType,
        title: str,
        body: str = "",
        metadata: dict[str, Any] | None = None,
        status: ContentAssetStatus = ContentAssetStatus.DRAFT,
        brief_id: UUID | None = None,
        campaign_id: UUID | None = None,
        task_id: UUID | None = None,
        agent_run_id: UUID | None = None,
        source_marketing_plan_id: UUID | None = None,
        source_execution_run_id: UUID | None = None,
        source_specialist_output_id: UUID | None = None,
        source_specialist_type: str | None = None,
        created_by_source: ContentAssetVersionSource = ContentAssetVersionSource.HTTP_API,
        created_by_agent_run_id: UUID | None = None,
    ) -> ContentAssetTable | None:
        if status != ContentAssetStatus.DRAFT:
            raise InvalidStateError("Content assets can only be created in draft status")

        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if not await self._validate_links(
            owner_id,
            project_id,
            brief_id=brief_id,
            campaign_id=campaign_id,
            task_id=task_id,
            agent_run_id=agent_run_id,
        ):
            return None

        asset_metadata = metadata or {}
        version_agent_run_id = created_by_agent_run_id
        if (
            created_by_source == ContentAssetVersionSource.AGENT_TOOL
            and version_agent_run_id is None
        ):
            version_agent_run_id = agent_run_id

        row = ContentAssetTable(
            owner_id=owner_id,
            project_id=project_id,
            brief_id=brief_id,
            campaign_id=campaign_id,
            task_id=task_id,
            agent_run_id=agent_run_id,
            asset_type=asset_type,
            title=title,
            body=body,
            asset_metadata=asset_metadata,
            status=status,
            current_version_number=1,
            approved_version_number=None,
            source_marketing_plan_id=source_marketing_plan_id,
            source_execution_run_id=source_execution_run_id,
            source_specialist_output_id=source_specialist_output_id,
            source_specialist_type=source_specialist_type,
        )
        async with transactional(self._session):
            created = await self._repo.create(row)
            await self._append_version(
                created,
                title=title,
                body=body,
                metadata=asset_metadata,
                version_number=1,
                created_by_source=created_by_source,
                created_by_agent_run_id=version_agent_run_id,
            )
            return created

    async def list_drafts_for_plan_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        draft_id: UUID,
    ) -> list[ContentAssetTable]:
        rows = await self._repo.list_by_campaign(
            owner_id,
            project_id,
            campaign_id,
            limit=500,
        )
        draft_key = str(draft_id)
        matched = [
            row
            for row in rows
            if metadata_source_plan_draft_id(row.asset_metadata) == draft_key
        ]
        return sorted(
            matched,
            key=lambda row: metadata_plan_item_index(row.asset_metadata) or 0,
        )

    async def create_drafts_from_plan_items_in_session(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        campaign_id: UUID,
        brief_id: UUID | None,
        draft_id: UUID,
        content_items: list[CampaignPlanContentItem],
    ) -> list[ContentAssetTable]:
        """Create draft assets within the caller's transaction (no commit)."""
        created_rows: list[ContentAssetTable] = []
        for index, item in enumerate(content_items):
            fields = plan_item_to_asset_fields(
                draft_id=draft_id,
                item=item,
                plan_item_index=index,
            )
            row = ContentAssetTable(
                owner_id=owner_id,
                project_id=project_id,
                brief_id=brief_id,
                campaign_id=campaign_id,
                task_id=None,
                agent_run_id=None,
                asset_type=fields["asset_type"],
                title=fields["title"],
                body=fields["body"],
                asset_metadata=fields["metadata"],
                status=ContentAssetStatus.DRAFT,
                current_version_number=1,
                approved_version_number=None,
            )
            created = await self._repo.create(row)
            await self._append_version(
                created,
                title=fields["title"],
                body=fields["body"],
                metadata=fields["metadata"],
                version_number=1,
                created_by_source=ContentAssetVersionSource.HTTP_API,
                created_by_agent_run_id=None,
            )
            created_rows.append(created)
        return created_rows

    async def create_drafts_from_plan_items(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        campaign_id: UUID,
        brief_id: UUID | None,
        draft_id: UUID,
        content_items: list[CampaignPlanContentItem],
    ) -> list[ContentAssetTable] | None:
        """Create draft assets for each plan content item in a single transaction."""
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if not await self._validate_links(
            owner_id,
            project_id,
            brief_id=brief_id,
            campaign_id=campaign_id,
            task_id=None,
            agent_run_id=None,
        ):
            return None

        async with transactional(self._session):
            return await self.create_drafts_from_plan_items_in_session(
                owner_id,
                project_id,
                campaign_id=campaign_id,
                brief_id=brief_id,
                draft_id=draft_id,
                content_items=content_items,
            )

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> ContentAssetTable | None:
        return await self._repo.get_by_id_for_owner(asset_id, owner_id, project_id)

    def _with_agent_version_metadata(
        self,
        metadata: dict[str, Any],
        *,
        created_by_agent_run_id: UUID | None,
    ) -> dict[str, Any]:
        merged = dict(metadata)
        if created_by_agent_run_id is not None:
            merged["source_agent_run_id"] = str(created_by_agent_run_id)
        return merged

    async def create_revision_from_approved(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_asset_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_by_source: ContentAssetVersionSource = ContentAssetVersionSource.HTTP_API,
        created_by_agent_run_id: UUID | None = None,
    ) -> ContentAssetTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        source = await self.get(owner_id, project_id, source_asset_id)
        if source is None:
            return None

        assert_asset_can_create_revision(source)
        approved_version_number = source.approved_version_number
        assert approved_version_number is not None

        approved_version = await self._versions.get_version(
            source_asset_id,
            approved_version_number,
            owner_id,
            project_id,
        )
        if approved_version is None:
            raise InvalidStateError(
                "Approved version snapshot not found for content asset",
            )

        next_revision = await self._repo.max_revision_number_for_source(
            source_asset_id,
            owner_id,
            project_id,
        ) + 1

        revision_created_at = datetime.now(UTC).isoformat()
        merged_metadata = dict(approved_version.version_metadata or {})
        if metadata is not None:
            merged_metadata = {**merged_metadata, **metadata}
        merged_metadata["revision"] = {
            "source_asset_id": str(source.id),
            "source_version_number": approved_version_number,
            "created_at": revision_created_at,
        }
        merged_metadata = self._with_agent_version_metadata(
            merged_metadata,
            created_by_agent_run_id=created_by_agent_run_id,
        )

        final_title = title if title is not None else approved_version.title
        final_body = body if body is not None else approved_version.body

        row = ContentAssetTable(
            owner_id=owner_id,
            project_id=project_id,
            brief_id=source.brief_id,
            task_id=None,
            agent_run_id=None,
            asset_type=source.asset_type,
            title=final_title,
            body=final_body,
            asset_metadata=merged_metadata,
            status=ContentAssetStatus.DRAFT,
            current_version_number=1,
            approved_version_number=None,
            source_asset_id=source.id,
            source_version_number=approved_version_number,
            revision_number=next_revision,
        )

        async with transactional(self._session):
            created = await self._repo.create(row)
            version_agent_run_id = created_by_agent_run_id
            if (
                created_by_source == ContentAssetVersionSource.AGENT_TOOL
                and version_agent_run_id is None
            ):
                version_agent_run_id = None
            await self._append_version(
                created,
                title=final_title,
                body=final_body,
                metadata=merged_metadata,
                version_number=1,
                created_by_source=created_by_source,
                created_by_agent_run_id=version_agent_run_id,
            )
            return created

    async def apply_agent_content_revision(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        *,
        body: str,
        title: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
        created_by_agent_run_id: UUID | None = None,
    ) -> ContentAssetTable | None:
        row = await self.get(owner_id, project_id, asset_id)
        if row is None:
            return None

        if row.status == ContentAssetStatus.ARCHIVED:
            raise InvalidStateError("Archived content assets cannot create revisions")

        patch = metadata_patch or {}

        if row.status == ContentAssetStatus.DRAFT:
            merged_metadata = {**(row.asset_metadata or {}), **patch}
            merged_metadata = self._with_agent_version_metadata(
                merged_metadata,
                created_by_agent_run_id=created_by_agent_run_id,
            )
            updates: dict[str, Any] = {
                "body": body,
                "metadata": merged_metadata,
            }
            if title is not None:
                updates["title"] = title
            return await self.update(
                owner_id,
                project_id,
                asset_id,
                updates,
                created_by_source=ContentAssetVersionSource.AGENT_TOOL,
                created_by_agent_run_id=created_by_agent_run_id,
            )

        if row.status == ContentAssetStatus.REVIEW:
            raise InvalidStateError(
                "Content assets in review cannot be revised; approve or archive first",
            )

        if row.status == ContentAssetStatus.APPROVED:
            merged_metadata = dict(patch)
            return await self.create_revision_from_approved(
                owner_id,
                project_id,
                asset_id,
                title=title,
                body=body,
                metadata=merged_metadata or None,
                created_by_source=ContentAssetVersionSource.AGENT_TOOL,
                created_by_agent_run_id=created_by_agent_run_id,
            )

        raise InvalidStateError("Only draft or approved content assets can be revised")

    async def create_manual_revision(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        *,
        title: str,
        body: str,
        metadata_patch: dict[str, Any] | None = None,
    ) -> ContentAssetTable | None:
        """Human HTTP revision of draft content — new version row, same asset id."""
        row = await self.get(owner_id, project_id, asset_id)
        if row is None:
            return None

        if row.status == ContentAssetStatus.ARCHIVED:
            raise InvalidStateError("Archived content assets cannot be edited")
        if row.status != ContentAssetStatus.DRAFT:
            raise InvalidStateError(
                "Manual in-place revisions require draft status; "
                "use create-revision for approved assets",
            )

        patch = sanitize_payload(metadata_patch or {}) or {}
        merged_metadata = {**(row.asset_metadata or {}), **patch}

        return await self.update(
            owner_id,
            project_id,
            asset_id,
            {
                "title": sanitize_text(title)[:512],
                "body": body,
                "metadata": merged_metadata,
            },
            created_by_source=ContentAssetVersionSource.HTTP_API,
        )

    def _sanitize_rollback_reason(self, reason: str | None) -> str | None:
        if reason is None:
            return None
        cleaned = sanitize_text(reason).strip()
        if not cleaned:
            return None
        return cleaned[:_ROLLBACK_REASON_MAX_CHARS]

    async def create_rollback_revision(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_asset_id: UUID,
        source_version_number: int,
        *,
        reason: str | None = None,
    ) -> ContentAssetTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        source = await self.get(owner_id, project_id, source_asset_id)
        if source is None:
            return None

        source_version = await self._versions.get_version(
            source_asset_id,
            source_version_number,
            owner_id,
            project_id,
        )
        if source_version is None:
            return None

        assert_asset_can_create_rollback_revision(source, source_version_number)

        next_revision = await self._repo.max_revision_number_for_source(
            source_asset_id,
            owner_id,
            project_id,
        ) + 1

        rollback_created_at = datetime.now(UTC).isoformat()
        merged_metadata = dict(source_version.version_metadata or {})
        rollback_reason = self._sanitize_rollback_reason(reason)
        merged_metadata["rollback"] = {
            "source_asset_id": str(source.id),
            "source_version_number": source_version_number,
            "reason": rollback_reason,
            "created_at": rollback_created_at,
        }

        final_title = source_version.title
        final_body = source_version.body

        row = ContentAssetTable(
            owner_id=owner_id,
            project_id=project_id,
            brief_id=source.brief_id,
            task_id=None,
            agent_run_id=None,
            asset_type=source.asset_type,
            title=final_title,
            body=final_body,
            asset_metadata=merged_metadata,
            status=ContentAssetStatus.DRAFT,
            current_version_number=1,
            approved_version_number=None,
            source_asset_id=source.id,
            source_version_number=source_version_number,
            revision_number=next_revision,
        )

        async with transactional(self._session):
            created = await self._repo.create(row)
            await self._append_version(
                created,
                title=final_title,
                body=final_body,
                metadata=merged_metadata,
                version_number=1,
                created_by_source=ContentAssetVersionSource.HTTP_API,
                created_by_agent_run_id=None,
            )

        await self._emit_content_asset_rollback_revision_created(
            owner_id=owner_id,
            project_id=project_id,
            source=source,
            revision=created,
            source_version_number=source_version_number,
            created_at=rollback_created_at,
        )
        return created

    async def list_versions(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> list[ContentAssetVersionTable] | None:
        if await self.get(owner_id, project_id, asset_id) is None:
            return None
        return await self._versions.list_versions(asset_id, owner_id, project_id)

    async def get_version(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        version_number: int,
    ) -> ContentAssetVersionTable | None:
        if await self.get(owner_id, project_id, asset_id) is None:
            return None
        return await self._versions.get_version(
            asset_id,
            version_number,
            owner_id,
            project_id,
        )

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[ContentAssetTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_by_project(
            owner_id,
            project_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def list_by_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[ContentAssetTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if brief is None:
            return None
        return await self._repo.list_by_brief(
            owner_id,
            project_id,
            brief_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def list_by_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[ContentAssetTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        campaign = await self._campaigns.get_by_id_for_project(campaign_id, owner_id, project_id)
        if campaign is None:
            return None
        return await self._repo.list_by_campaign(
            owner_id,
            project_id,
            campaign_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        updates: dict[str, Any],
        *,
        created_by_source: ContentAssetVersionSource = ContentAssetVersionSource.HTTP_API,
        created_by_agent_run_id: UUID | None = None,
    ) -> ContentAssetTable | None:
        row = await self.get(owner_id, project_id, asset_id)
        if row is None:
            return None

        filtered: dict[str, Any] = {}
        for key, value in updates.items():
            if key == "metadata":
                filtered["asset_metadata"] = value
            elif key in _ASSET_UPDATE_FIELDS:
                filtered[key] = value

        if "status" in filtered:
            validate_content_asset_transition(row.status, filtered["status"])

        content_change_requested = any(key in filtered for key in _CONTENT_VERSION_FIELDS)
        if content_change_requested:
            assert_asset_content_editable(row)

        link_keys = {
            "brief_id": filtered.get("brief_id", row.brief_id),
            "campaign_id": filtered.get("campaign_id", getattr(row, "campaign_id", None)),
            "task_id": filtered.get("task_id", row.task_id),
            "agent_run_id": filtered.get("agent_run_id", row.agent_run_id),
        }
        link_fields_changed = any(
            key in filtered for key in ("brief_id", "campaign_id", "task_id", "agent_run_id")
        )
        if link_fields_changed and not await self._validate_links(
            owner_id,
            project_id,
            brief_id=link_keys["brief_id"],
            campaign_id=link_keys["campaign_id"],
            task_id=link_keys["task_id"],
            agent_run_id=link_keys["agent_run_id"],
        ):
            return None

        if not filtered:
            return row

        content_changed = self._content_snapshot_changed(row, filtered)
        next_title = filtered.get("title", row.title)
        next_body = filtered.get("body", row.body)
        next_metadata = filtered.get("asset_metadata", row.asset_metadata or {})

        async with transactional(self._session):
            if content_changed:
                next_version = row.current_version_number + 1
                await self._append_version(
                    row,
                    title=next_title,
                    body=next_body,
                    metadata=dict(next_metadata),
                    version_number=next_version,
                    created_by_source=created_by_source,
                    created_by_agent_run_id=created_by_agent_run_id,
                )
                row.current_version_number = next_version
                row.title = next_title
                row.body = next_body
                row.asset_metadata = dict(next_metadata)

            for key in ("brief_id", "campaign_id", "task_id", "agent_run_id"):
                if key in filtered:
                    setattr(row, key, filtered[key])

            if "status" in filtered:
                next_status = filtered["status"]
                row.status = next_status
                if next_status == ContentAssetStatus.REVIEW:
                    row.submitted_for_review_at = utc_now()
                if next_status == ContentAssetStatus.APPROVED:
                    row.approved_version_number = row.current_version_number
                    approved_at = utc_now()
                    row.approved_at = approved_at
                    metadata = dict(row.asset_metadata or {})
                    metadata["approval"] = {
                        "approved_at": approved_at.isoformat(),
                        "approved_by_owner_id": str(owner_id),
                        "source": _APPROVAL_SOURCE_HTTP_API,
                    }
                    row.asset_metadata = metadata

            return await self._repo.update(row)

    async def submit_for_review_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> ContentAssetTable | None:
        row = await self.get(owner_id, project_id, asset_id)
        if row is None:
            return None

        assert_asset_can_submit_for_review(row)
        validate_content_asset_transition(row.status, ContentAssetStatus.REVIEW)
        row.status = ContentAssetStatus.REVIEW
        row.submitted_for_review_at = utc_now()

        async with transactional(self._session):
            return await self._repo.update(row)

    async def approve_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> ContentAssetTable | None:
        row = await self.get(owner_id, project_id, asset_id)
        if row is None:
            return None

        assert_asset_can_be_approved(row)
        validate_content_asset_transition(row.status, ContentAssetStatus.APPROVED)
        approved_at = utc_now()
        metadata = dict(row.asset_metadata or {})
        metadata["approval"] = {
            "approved_at": approved_at.isoformat(),
            "approved_by_owner_id": str(owner_id),
            "source": _APPROVAL_SOURCE_HTTP_API,
        }
        row.asset_metadata = metadata
        row.status = ContentAssetStatus.APPROVED
        row.approved_version_number = row.current_version_number
        row.approved_at = approved_at

        async with transactional(self._session):
            updated = await self._repo.update(row)

        await self._emit_content_asset_approved(
            owner_id=owner_id,
            project_id=project_id,
            row=updated,
            approved_at=approved_at.isoformat(),
        )
        return updated

    async def archive_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> ContentAssetTable | None:
        row = await self.get(owner_id, project_id, asset_id)
        if row is None:
            return None

        assert_asset_can_be_archived(row)
        validate_content_asset_transition(row.status, ContentAssetStatus.ARCHIVED)
        archived_at = datetime.now(UTC).isoformat()
        row.status = ContentAssetStatus.ARCHIVED

        async with transactional(self._session):
            updated = await self._repo.update(row)

        await self._emit_content_asset_archived(
            owner_id=owner_id,
            project_id=project_id,
            row=updated,
            archived_at=archived_at,
        )
        return updated

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> ContentAssetTable | None:
        return await self.archive_asset(owner_id, project_id, asset_id)

    async def _emit_content_asset_rollback_revision_created(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        source: ContentAssetTable,
        revision: ContentAssetTable,
        source_version_number: int,
        created_at: str,
    ) -> None:
        await EventOutboxService(self._session).append_content_asset_rollback_revision_created(
            owner_id=owner_id,
            project_id=project_id,
            source_asset_id=source.id,
            source_version_number=source_version_number,
            revision_asset_id=revision.id,
            revision_number=revision.revision_number or 0,
            created_at=created_at,
        )

    async def _emit_content_asset_approved(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        row: ContentAssetTable,
        approved_at: str,
    ) -> None:
        await EventOutboxService(self._session).append_content_asset_approved(
            owner_id=owner_id,
            project_id=project_id,
            asset_id=row.id,
            brief_id=row.brief_id,
            asset_type=row.asset_type.value,
            title=row.title,
            approved_at=approved_at,
        )

    def _snapshot_from_asset(self, row: ContentAssetTable) -> dict[str, Any]:
        return {
            "title": row.title,
            "body": row.body,
            "metadata": dict(row.asset_metadata or {}),
        }

    def _snapshot_from_version(self, row: ContentAssetVersionTable) -> dict[str, Any]:
        return {
            "title": row.title,
            "body": row.body,
            "metadata": dict(row.version_metadata or {}),
        }

    def _diff_side_from_asset(
        self,
        row: ContentAssetTable,
        *,
        version_number: int | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        return {
            "asset_id": row.id,
            "version_number": version_number,
            "title": title if title is not None else row.title,
            "status": row.status,
            "type": row.asset_type,
        }

    def _build_diff_response(
        self,
        *,
        old_snapshot: dict[str, Any],
        new_snapshot: dict[str, Any],
        from_side: dict[str, Any],
        to_side: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "from": from_side,
            "to": to_side,
            "diff": build_content_asset_diff(old_snapshot, new_snapshot),
        }

    async def diff_versions(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any] | None:
        asset = await self.get(owner_id, project_id, asset_id)
        if asset is None:
            return None

        from_row = await self._versions.get_version(
            asset_id,
            from_version,
            owner_id,
            project_id,
        )
        to_row = await self._versions.get_version(
            asset_id,
            to_version,
            owner_id,
            project_id,
        )
        if from_row is None or to_row is None:
            return None

        return self._build_diff_response(
            old_snapshot=self._snapshot_from_version(from_row),
            new_snapshot=self._snapshot_from_version(to_row),
            from_side=self._diff_side_from_asset(
                asset,
                version_number=from_version,
                title=from_row.title,
            ),
            to_side=self._diff_side_from_asset(
                asset,
                version_number=to_version,
                title=to_row.title,
            ),
        )

    async def diff_assets(
        self,
        owner_id: UUID,
        project_id: UUID,
        from_asset_id: UUID,
        to_asset_id: UUID,
    ) -> dict[str, Any] | None:
        from_asset = await self.get(owner_id, project_id, from_asset_id)
        to_asset = await self.get(owner_id, project_id, to_asset_id)
        if from_asset is None or to_asset is None:
            return None

        return self._build_diff_response(
            old_snapshot=self._snapshot_from_asset(from_asset),
            new_snapshot=self._snapshot_from_asset(to_asset),
            from_side=self._diff_side_from_asset(
                from_asset,
                version_number=from_asset.current_version_number,
            ),
            to_side=self._diff_side_from_asset(
                to_asset,
                version_number=to_asset.current_version_number,
            ),
        )

    async def diff_revision(
        self,
        owner_id: UUID,
        project_id: UUID,
        revision_asset_id: UUID,
    ) -> dict[str, Any] | None:
        revision = await self.get(owner_id, project_id, revision_asset_id)
        if revision is None:
            return None

        if revision.source_asset_id is None or revision.source_version_number is None:
            raise InvalidStateError("Content asset is not a revision")

        source = await self.get(owner_id, project_id, revision.source_asset_id)
        if source is None:
            return None

        source_version = await self._versions.get_version(
            revision.source_asset_id,
            revision.source_version_number,
            owner_id,
            project_id,
        )
        if source_version is None:
            return None

        return self._build_diff_response(
            old_snapshot=self._snapshot_from_version(source_version),
            new_snapshot=self._snapshot_from_asset(revision),
            from_side=self._diff_side_from_asset(
                source,
                version_number=revision.source_version_number,
                title=source_version.title,
            ),
            to_side=self._diff_side_from_asset(
                revision,
                version_number=revision.current_version_number,
            ),
        )

    async def _emit_content_asset_archived(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        row: ContentAssetTable,
        archived_at: str,
    ) -> None:
        await EventOutboxService(self._session).append_content_asset_archived(
            owner_id=owner_id,
            project_id=project_id,
            asset_id=row.id,
            brief_id=row.brief_id,
            asset_type=row.asset_type.value,
            title=row.title,
            archived_at=archived_at,
        )
