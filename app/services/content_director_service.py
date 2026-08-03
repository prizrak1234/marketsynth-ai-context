"""Content Director service — Text Golden Path (PRODUCT-CD-RUNTIME-01)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.content_director import (
    ContentInputSnapshotTable,
    ContentRequestTable,
    ContentRunCandidateTable,
    ContentRunTable,
)
from app.db.models.marketing import ContentAssetTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.content_director import (
    ContentInputSnapshotRepository,
    ContentRequestRepository,
    ContentRunCandidateRepository,
    ContentRunRepository,
)
from app.marketing.contracts import ContentAssetStatus, ContentAssetType
from app.schemas.contracts import (
    ContentDirectorApproveRequest,
    ContentDirectorCandidateRead,
    ContentDirectorEditRequest,
    ContentDirectorGenerateRequest,
    ContentDirectorWorkspaceState,
    ContentInputSnapshotRead,
    ContentRequestCreate,
    ContentRequestRead,
    ContentRequestUpdate,
    ContentRunRead,
    ContentRunStatus,
)
from app.services.content_asset_service import ContentAssetService
from app.services.content_director_text_adapter import ContentDirectorTextAdapter
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_ACTIVE = frozenset({ContentRunStatus.QUEUED, ContentRunStatus.RUNNING})


def _request_to_read(row: ContentRequestTable) -> ContentRequestRead:
    return ContentRequestRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        version=row.version,
        context_source=row.context_source,
        title=row.title,
        objective=row.objective,
        channel=row.channel,
        content_type=row.content_type,
        audience_description=row.audience_description,
        key_message=row.key_message,
        offer_value_proposition=row.offer_value_proposition,
        tone=row.tone,
        language=row.language,
        length=row.length,
        cta=row.cta,
        must_include=row.must_include,
        must_avoid=row.must_avoid,
        requested_variants=row.requested_variants,
        current_run_id=row.current_run_id,
        approved_asset_id=row.approved_asset_id,
        approved_version_number=row.approved_version_number,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _run_to_read(row: ContentRunTable) -> ContentRunRead:
    return ContentRunRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        content_request_id=row.content_request_id,
        content_request_version=row.content_request_version,
        snapshot_id=row.snapshot_id,
        status=row.status,
        attempt=row.attempt,
        error_code=row.error_code,
        error_message=row.error_message,
        provider=row.provider,
        model=row.model,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def _snapshot_payload(row: ContentRequestTable) -> dict[str, Any]:
    return {
        "content_request_id": str(row.id),
        "content_request_version": row.version,
        "context_source": row.context_source.value
        if hasattr(row.context_source, "value")
        else str(row.context_source),
        "title": row.title,
        "objective": row.objective,
        "channel": row.channel.value if hasattr(row.channel, "value") else str(row.channel),
        "content_type": row.content_type.value
        if hasattr(row.content_type, "value")
        else str(row.content_type),
        "audience_description": row.audience_description,
        "key_message": row.key_message,
        "offer_value_proposition": row.offer_value_proposition,
        "tone": row.tone,
        "language": row.language,
        "length": row.length,
        "cta": row.cta,
        "must_include": row.must_include,
        "must_avoid": row.must_avoid,
        "requested_variants": row.requested_variants,
    }


class ContentDirectorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._requests = ContentRequestRepository(session)
        self._snapshots = ContentInputSnapshotRepository(session)
        self._runs = ContentRunRepository(session)
        self._candidates = ContentRunCandidateRepository(session)
        self._assets = ContentAssetRepository(session)
        self._asset_service = ContentAssetService(session)
        self._projects = ProjectService(session)
        self._adapter = ContentDirectorTextAdapter()

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def create_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: ContentRequestCreate,
    ) -> ContentRequestRead | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        cleaned = sanitize_payload(body.model_dump()) or {}
        version = await self._requests.next_version(project_id)
        row = ContentRequestTable(
            owner_id=owner_id,
            project_id=project_id,
            version=version,
            context_source=body.context_source,
            title=sanitize_text(str(cleaned.get("title") or body.title)),
            objective=sanitize_text(str(cleaned.get("objective") or body.objective)),
            channel=body.channel,
            content_type=body.content_type,
            audience_description=sanitize_text(
                str(cleaned.get("audience_description") or body.audience_description)
            ),
            key_message=sanitize_text(str(cleaned.get("key_message") or body.key_message)),
            offer_value_proposition=sanitize_text(
                str(
                    cleaned.get("offer_value_proposition")
                    or body.offer_value_proposition
                    or ""
                )
            ),
            tone=sanitize_text(str(cleaned.get("tone") or body.tone)),
            language=sanitize_text(str(cleaned.get("language") or body.language)),
            length=sanitize_text(str(cleaned.get("length") or body.length)),
            cta=sanitize_text(str(cleaned.get("cta") or body.cta or "")),
            must_include=sanitize_text(
                str(cleaned.get("must_include") or body.must_include or "")
            ),
            must_avoid=sanitize_text(
                str(cleaned.get("must_avoid") or body.must_avoid or "")
            ),
            requested_variants=int(
                cleaned.get("requested_variants") or body.requested_variants
            ),
        )
        async with transactional(self._session):
            created = await self._requests.create(row)
        return _request_to_read(created)

    async def update_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        body: ContentRequestUpdate,
    ) -> ContentRequestRead | None:
        row = await self._requests.get_by_id_for_owner(request_id, owner_id, project_id)
        if row is None:
            return None
        if row.approved_asset_id is not None:
            raise InvalidStateError(
                "Cannot edit request fields after approval; create a new request version"
            )
        active = await self._runs.get_active_for_request(request_id, owner_id, project_id)
        if active is not None:
            raise InvalidStateError("Cannot edit request while a ContentRun is active")

        data = body.model_dump(exclude_unset=True)
        cleaned = sanitize_payload(data) or {}
        for field in (
            "title",
            "objective",
            "audience_description",
            "key_message",
            "offer_value_proposition",
            "tone",
            "language",
            "length",
            "cta",
            "must_include",
            "must_avoid",
        ):
            if field in cleaned and cleaned[field] is not None:
                setattr(row, field, sanitize_text(str(cleaned[field])))
        if "requested_variants" in cleaned and cleaned["requested_variants"] is not None:
            row.requested_variants = int(cleaned["requested_variants"])

        # Bump version on material edit so pins stay honest
        row.version = row.version + 1
        async with transactional(self._session):
            updated = await self._requests.update(row)
        return _request_to_read(updated)

    async def get_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
    ) -> ContentRequestRead | None:
        row = await self._requests.get_by_id_for_owner(request_id, owner_id, project_id)
        return _request_to_read(row) if row else None

    async def list_requests(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[ContentRequestRead]:
        if not await self._ensure_project(owner_id, project_id):
            return []
        rows = await self._requests.list_for_project(owner_id, project_id)
        return [_request_to_read(r) for r in rows]

    async def generate(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        body: ContentDirectorGenerateRequest | None = None,
    ) -> ContentRunRead | None:
        row = await self._requests.get_by_id_for_owner(request_id, owner_id, project_id)
        if row is None:
            return None
        if row.approved_asset_id is not None:
            raise InvalidStateError(
                "Cannot generate after approval; create a new ContentRequest"
            )

        idem = (body.idempotency_key if body else None) or None
        if idem:
            existing_idemp = await self._runs.get_by_idempotency(
                request_id, idem, owner_id, project_id
            )
            if existing_idemp is not None:
                return _run_to_read(existing_idemp)

        active = await self._runs.get_active_for_request(request_id, owner_id, project_id)
        if active is not None:
            return _run_to_read(active)

        snapshot = ContentInputSnapshotTable(
            owner_id=owner_id,
            project_id=project_id,
            content_request_id=row.id,
            content_request_version=row.version,
            payload=_snapshot_payload(row),
        )

        async with transactional(self._session):
            snap = await self._snapshots.create(snapshot)
            run = ContentRunTable(
                owner_id=owner_id,
                project_id=project_id,
                content_request_id=row.id,
                content_request_version=row.version,
                snapshot_id=snap.id,
                status=ContentRunStatus.RUNNING,
                attempt=1,
                idempotency_key=idem,
            )
            created_run = await self._runs.create(run)
            row.current_run_id = created_run.id
            await self._requests.update(row)

        async def _fail_run(error_code: str, error_message: str) -> ContentRunRead:
            async with transactional(self._session):
                created_run.status = ContentRunStatus.FAILED
                created_run.error_code = error_code
                created_run.error_message = error_message[:2000]
                created_run.completed_at = utc_now()
                await self._runs.update(created_run)
            return _run_to_read(created_run)

        try:
            generated = await self._adapter.generate_candidates(
                snapshot_payload=snap.payload,
                content_request_id=str(row.id),
                content_request_version=row.version,
                snapshot_id=str(snap.id),
                requested_variants=row.requested_variants,
            )

            for idx, cand in enumerate(generated):
                asset = await self._asset_service.create(
                    owner_id,
                    project_id,
                    asset_type=ContentAssetType.TELEGRAM_POST,
                    title=sanitize_text(cand.title),
                    body=sanitize_text(cand.body),
                    metadata={
                        "content_director": True,
                        "content_request_id": str(row.id),
                        "content_request_version": row.version,
                        "content_run_id": str(created_run.id),
                        "snapshot_id": str(snap.id),
                        "candidate_index": idx + 1,
                        "generation": cand.metadata,
                        "provider": cand.provider,
                        "model": cand.model,
                    },
                )
                if asset is None:
                    return await _fail_run(
                        "persist_failure",
                        "Failed to persist candidate asset",
                    )
                async with transactional(self._session):
                    await self._candidates.create(
                        ContentRunCandidateTable(
                            owner_id=owner_id,
                            project_id=project_id,
                            content_request_id=row.id,
                            content_request_version=row.version,
                            content_run_id=created_run.id,
                            content_asset_id=asset.id,
                            candidate_index=idx + 1,
                            rejected=False,
                        )
                    )

            async with transactional(self._session):
                created_run.status = ContentRunStatus.SUCCEEDED
                created_run.provider = generated[0].provider if generated else None
                created_run.model = generated[0].model if generated else None
                created_run.completed_at = utc_now()
                await self._runs.update(created_run)

            # Skill Runtime lineage — Copywriter participation (no second generation).
            # Workspace stamps applied_skill_* only from a succeeded SkillRun
            # with idempotency key cd-copywriter-{content_run_id}.
            try:
                from app.product_skills.runtime_service import ProductSkillRuntimeService
                from app.schemas.contracts import ProductSkillRunCreate

                skill_rt = ProductSkillRuntimeService(self._session)
                await skill_rt.execute(
                    owner_id,
                    project_id,
                    ProductSkillRunCreate(
                        skill_id="marketsynth.copywriter",
                        trigger="telegram_post",
                        input_type="content_request",
                        input_ref={
                            "content_request_id": str(row.id),
                            "content_run_id": str(created_run.id),
                        },
                        idempotency_key=f"cd-copywriter-{created_run.id}",
                        explicit=True,
                    ),
                )
            except Exception:  # noqa: BLE001 — ContentRun already succeeded; lineage is additive
                pass
        except InvalidStateError as exc:
            detail = str(exc)
            code = "provider_failure"
            if detail.startswith("provider_config_error"):
                code = "provider_config_error"
            # Customer-safe message — no raw provider exception bodies.
            return await _fail_run(code, detail.split(":", 1)[0] if ":" in detail else detail)
        except Exception:  # noqa: BLE001 — never leave RUNNING stuck
            return await _fail_run(
                "generation_failure",
                "Content generation failed unexpectedly",
            )

        refreshed = await self._runs.get_by_id_for_owner(
            created_run.id, owner_id, project_id
        )
        return _run_to_read(refreshed) if refreshed else _run_to_read(created_run)

    async def reject_candidate(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        asset_id: UUID,
    ) -> ContentDirectorCandidateRead | None:
        link = await self._candidates.get_by_asset(asset_id, owner_id, project_id)
        if link is None or link.content_request_id != request_id:
            return None
        link.rejected = True
        async with transactional(self._session):
            await self._candidates.update(link)
        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None
        return self._candidate_read(link, asset)

    async def edit_candidate(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        asset_id: UUID,
        body: ContentDirectorEditRequest,
    ) -> ContentDirectorCandidateRead | None:
        link = await self._candidates.get_by_asset(asset_id, owner_id, project_id)
        if link is None or link.content_request_id != request_id:
            return None
        request = await self._requests.get_by_id_for_owner(
            request_id, owner_id, project_id
        )
        if request is None:
            return None
        if request.approved_asset_id == asset_id:
            raise InvalidStateError(
                "Cannot edit approved asset in place; create a new ContentRequest"
            )
        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None
        if asset.status == ContentAssetStatus.APPROVED:
            raise InvalidStateError("Approved ContentAsset body is immutable")

        title = sanitize_text(body.title or asset.title)
        text_body = sanitize_text(body.body)
        updated = await self._asset_service.create_manual_revision(
            owner_id,
            project_id,
            asset_id,
            title=title,
            body=text_body,
            metadata_patch={
                "content_director_edit": True,
                "edited_from_version": asset.current_version_number,
                "actor_id": str(owner_id),
            },
        )
        if updated is None:
            return None
        return self._candidate_read(link, updated)

    async def approve_candidate(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        asset_id: UUID,
        body: ContentDirectorApproveRequest | None = None,
    ) -> ContentDirectorCandidateRead | None:
        link = await self._candidates.get_by_asset(asset_id, owner_id, project_id)
        if link is None or link.content_request_id != request_id:
            return None
        if link.rejected:
            raise InvalidStateError("Rejected candidate cannot be approved")
        request = await self._requests.get_by_id_for_owner(
            request_id, owner_id, project_id
        )
        if request is None:
            return None

        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None

        if asset.status == ContentAssetStatus.DRAFT:
            submitted = await self._asset_service.submit_for_review_asset(
                owner_id, project_id, asset_id
            )
            if submitted is None:
                return None
        approved = await self._asset_service.approve_asset(
            owner_id, project_id, asset_id
        )
        if approved is None:
            return None

        # Strengthen content_approval pin metadata
        meta = dict(approved.asset_metadata or {})
        approval = dict(meta.get("approval") or {})
        approval.update(
            {
                "type": "content_approval",
                "content_request_id": str(request_id),
                "content_request_version": request.version,
                "content_run_id": str(link.content_run_id),
                "asset_version": approved.current_version_number,
                "note": sanitize_text(body.note) if body and body.note else None,
            }
        )
        meta["approval"] = approval
        approved.asset_metadata = meta

        async with transactional(self._session):
            await self._assets.update(approved)
            request.approved_asset_id = approved.id
            request.approved_version_number = approved.approved_version_number
            await self._requests.update(request)

        return self._candidate_read(link, approved)

    async def workspace_state(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID | None = None,
    ) -> ContentDirectorWorkspaceState:
        if not await self._ensure_project(owner_id, project_id):
            return ContentDirectorWorkspaceState(next_action="forbidden")

        request_row: ContentRequestTable | None
        if request_id is not None:
            request_row = await self._requests.get_by_id_for_owner(
                request_id, owner_id, project_id
            )
        else:
            request_row = await self._requests.latest_for_project(owner_id, project_id)

        if request_row is None:
            return ContentDirectorWorkspaceState(next_action="create_request")

        active = None
        if request_row.current_run_id:
            active = await self._runs.get_by_id_for_owner(
                request_row.current_run_id, owner_id, project_id
            )
        if active is None:
            active = await self._runs.get_active_for_request(
                request_row.id, owner_id, project_id
            )

        candidate_rows = await self._candidates.list_for_request(
            request_row.id, owner_id, project_id
        )
        # Prefer latest run's candidates
        if active is not None:
            candidate_rows = await self._candidates.list_for_run(
                active.id, owner_id, project_id
            )

        candidates: list[ContentDirectorCandidateRead] = []
        for link in candidate_rows:
            asset = await self._assets.get_by_id_for_owner(
                link.content_asset_id, owner_id, project_id
            )
            if asset is not None:
                candidates.append(self._candidate_read(link, asset))

        next_action = "generate"
        if active is not None and active.status in _ACTIVE:
            next_action = "wait_generation"
        elif candidates and request_row.approved_asset_id is None:
            next_action = "review_candidates"
        elif request_row.approved_asset_id is not None:
            next_action = "approved"

        applied_skill_id = None
        applied_skill_version = None
        if active is not None and candidates:
            from app.product_skills.runtime_service import ProductSkillRuntimeService
            from app.schemas.contracts import ProductSkillRunStatus

            skill_rt = ProductSkillRuntimeService(self._session)
            skill_run = await skill_rt.get_run_by_idempotency(
                owner_id,
                project_id,
                f"cd-copywriter-{active.id}",
            )
            if (
                skill_run is not None
                and skill_run.status == ProductSkillRunStatus.SUCCEEDED
            ):
                applied_skill_id = skill_run.skill_id
                applied_skill_version = skill_run.skill_version

        return ContentDirectorWorkspaceState(
            request=_request_to_read(request_row),
            active_run=_run_to_read(active) if active else None,
            candidates=candidates,
            approved_asset_id=request_row.approved_asset_id,
            approved_version_number=request_row.approved_version_number,
            next_action=next_action,
            applied_skill_id=applied_skill_id,
            applied_skill_version=applied_skill_version,
        )

    def _candidate_read(
        self,
        link: ContentRunCandidateTable,
        asset: ContentAssetTable,
    ) -> ContentDirectorCandidateRead:
        return ContentDirectorCandidateRead(
            asset_id=asset.id,
            content_run_id=link.content_run_id,
            content_request_id=link.content_request_id,
            content_request_version=link.content_request_version,
            candidate_index=link.candidate_index,
            title=asset.title,
            body=asset.body or "",
            status=asset.status.value
            if hasattr(asset.status, "value")
            else str(asset.status),
            current_version_number=asset.current_version_number,
            approved_version_number=asset.approved_version_number,
            rejected=link.rejected,
        )
