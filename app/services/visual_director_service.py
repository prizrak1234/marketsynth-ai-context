"""Visual Director service — Image Golden Path (PRODUCT-CD-RUNTIME-02)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.visual_director import (
    ImageAssetTable,
    ImageAssetVersionTable,
    VisualInputSnapshotTable,
    VisualRequestTable,
    VisualRunCandidateTable,
    VisualRunTable,
)
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.visual_director import (
    ImageAssetRepository,
    VisualInputSnapshotRepository,
    VisualRequestRepository,
    VisualRunCandidateRepository,
    VisualRunRepository,
)
from app.schemas.contracts import (
    ImageAssetStatus,
    VisualDirectorApproveRequest,
    VisualDirectorCandidateRead,
    VisualDirectorGenerateRequest,
    VisualDirectorWorkspaceState,
    VisualRequestCreate,
    VisualRequestRead,
    VisualRequestUpdate,
    VisualRunRead,
    VisualRunStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional
from app.services.visual_director_image_adapter import (
    VisualDirectorImageAdapter,
    resolve_storage_path,
)

_ACTIVE = frozenset({VisualRunStatus.QUEUED, VisualRunStatus.RUNNING})


def _refs_to_str_list(raw: Any) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for item in raw:
        out.append(str(item))
    return out


def _refs_to_uuid_list(raw: Any) -> list[UUID]:
    if not raw:
        return []
    out: list[UUID] = []
    for item in raw:
        try:
            out.append(UUID(str(item)))
        except (ValueError, TypeError):
            continue
    return out


def _request_to_read(row: VisualRequestTable) -> VisualRequestRead:
    return VisualRequestRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        version=row.version,
        context_source=row.context_source,
        title=row.title,
        objective=row.objective,
        scene_description=row.scene_description,
        subject=row.subject,
        style=row.style,
        audience=row.audience,
        mood=row.mood,
        aspect_ratio=row.aspect_ratio,
        visual_format=row.visual_format,
        requested_variants=row.requested_variants,
        text_overlay=row.text_overlay,
        must_include=row.must_include,
        must_avoid=row.must_avoid,
        related_text_asset_id=row.related_text_asset_id,
        reference_asset_ids=_refs_to_uuid_list(row.reference_asset_ids),
        language=row.language,
        current_run_id=row.current_run_id,
        approved_asset_id=row.approved_asset_id,
        approved_version_number=row.approved_version_number,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _run_to_read(row: VisualRunTable) -> VisualRunRead:
    return VisualRunRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        visual_request_id=row.visual_request_id,
        visual_request_version=row.visual_request_version,
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


def _snapshot_payload(row: VisualRequestTable) -> dict[str, Any]:
    return {
        "visual_request_id": str(row.id),
        "visual_request_version": row.version,
        "context_source": row.context_source.value
        if hasattr(row.context_source, "value")
        else str(row.context_source),
        "title": row.title,
        "objective": row.objective,
        "scene_description": row.scene_description,
        "subject": row.subject,
        "style": row.style,
        "audience": row.audience,
        "mood": row.mood,
        "aspect_ratio": row.aspect_ratio.value
        if hasattr(row.aspect_ratio, "value")
        else str(row.aspect_ratio),
        "visual_format": row.visual_format.value
        if hasattr(row.visual_format, "value")
        else str(row.visual_format),
        "text_overlay": row.text_overlay,
        "must_include": row.must_include,
        "must_avoid": row.must_avoid,
        "related_text_asset_id": str(row.related_text_asset_id)
        if row.related_text_asset_id
        else None,
        "reference_asset_ids": _refs_to_str_list(row.reference_asset_ids),
        "language": row.language,
        "requested_variants": row.requested_variants,
    }


class VisualDirectorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._requests = VisualRequestRepository(session)
        self._snapshots = VisualInputSnapshotRepository(session)
        self._runs = VisualRunRepository(session)
        self._candidates = VisualRunCandidateRepository(session)
        self._images = ImageAssetRepository(session)
        self._text_assets = ContentAssetRepository(session)
        self._projects = ProjectService(session)
        self._adapter = VisualDirectorImageAdapter()
        self._settings = get_settings()

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _validate_related_text(
        self,
        owner_id: UUID,
        project_id: UUID,
        related_text_asset_id: UUID | None,
    ) -> None:
        if related_text_asset_id is None:
            return
        asset = await self._text_assets.get_by_id_for_owner(
            related_text_asset_id, owner_id, project_id
        )
        if asset is None:
            raise InvalidStateError("related_text_asset_not_found")

    async def _validate_reference_assets(
        self,
        owner_id: UUID,
        project_id: UUID,
        reference_asset_ids: list[UUID],
    ) -> None:
        for ref_id in reference_asset_ids:
            asset = await self._images.get_by_id_for_owner(ref_id, owner_id, project_id)
            if asset is None:
                raise InvalidStateError("reference_asset_not_found")

    async def create_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: VisualRequestCreate,
    ) -> VisualRequestRead | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        cleaned = sanitize_payload(body.model_dump(mode="json")) or {}
        await self._validate_related_text(owner_id, project_id, body.related_text_asset_id)
        await self._validate_reference_assets(
            owner_id, project_id, list(body.reference_asset_ids or [])
        )
        version = await self._requests.next_version(project_id)
        row = VisualRequestTable(
            owner_id=owner_id,
            project_id=project_id,
            version=version,
            context_source=body.context_source,
            title=sanitize_text(str(cleaned.get("title") or body.title)),
            objective=sanitize_text(str(cleaned.get("objective") or body.objective)),
            scene_description=sanitize_text(
                str(cleaned.get("scene_description") or body.scene_description)
            ),
            subject=sanitize_text(str(cleaned.get("subject") or body.subject)),
            style=sanitize_text(str(cleaned.get("style") or body.style)),
            audience=sanitize_text(str(cleaned.get("audience") or body.audience)),
            mood=sanitize_text(str(cleaned.get("mood") or body.mood)),
            aspect_ratio=body.aspect_ratio,
            visual_format=body.visual_format,
            requested_variants=int(
                cleaned.get("requested_variants") or body.requested_variants
            ),
            text_overlay=sanitize_text(
                str(cleaned.get("text_overlay") or body.text_overlay or "")
            ),
            must_include=sanitize_text(
                str(cleaned.get("must_include") or body.must_include or "")
            ),
            must_avoid=sanitize_text(
                str(cleaned.get("must_avoid") or body.must_avoid or "")
            ),
            related_text_asset_id=body.related_text_asset_id,
            reference_asset_ids=[str(x) for x in (body.reference_asset_ids or [])],
            language=sanitize_text(str(cleaned.get("language") or body.language)),
        )
        async with transactional(self._session):
            created = await self._requests.create(row)
        return _request_to_read(created)

    async def update_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        body: VisualRequestUpdate,
    ) -> VisualRequestRead | None:
        row = await self._requests.get_by_id_for_owner(request_id, owner_id, project_id)
        if row is None:
            return None
        if row.approved_asset_id is not None:
            raise InvalidStateError(
                "Cannot edit request fields after approval; create a new request"
            )
        active = await self._runs.get_active_for_request(request_id, owner_id, project_id)
        if active is not None:
            raise InvalidStateError("Cannot edit request while a VisualRun is active")

        data = body.model_dump(exclude_unset=True, mode="json")
        cleaned = sanitize_payload(data) or {}
        for field in (
            "title",
            "objective",
            "scene_description",
            "subject",
            "style",
            "audience",
            "mood",
            "text_overlay",
            "must_include",
            "must_avoid",
            "language",
        ):
            if field in cleaned and cleaned[field] is not None:
                setattr(row, field, sanitize_text(str(cleaned[field])))
        if "requested_variants" in cleaned and cleaned["requested_variants"] is not None:
            row.requested_variants = int(cleaned["requested_variants"])
        if "aspect_ratio" in data and data["aspect_ratio"] is not None:
            row.aspect_ratio = body.aspect_ratio  # type: ignore[assignment]
        if "related_text_asset_id" in data:
            await self._validate_related_text(
                owner_id, project_id, body.related_text_asset_id
            )
            row.related_text_asset_id = body.related_text_asset_id
        if "reference_asset_ids" in data and body.reference_asset_ids is not None:
            await self._validate_reference_assets(
                owner_id, project_id, list(body.reference_asset_ids)
            )
            row.reference_asset_ids = [str(x) for x in body.reference_asset_ids]

        row.version = row.version + 1
        async with transactional(self._session):
            updated = await self._requests.update(row)
        return _request_to_read(updated)

    async def get_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
    ) -> VisualRequestRead | None:
        row = await self._requests.get_by_id_for_owner(request_id, owner_id, project_id)
        return _request_to_read(row) if row else None

    async def list_requests(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[VisualRequestRead]:
        if not await self._ensure_project(owner_id, project_id):
            return []
        rows = await self._requests.list_for_project(owner_id, project_id)
        return [_request_to_read(r) for r in rows]

    async def generate(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        body: VisualDirectorGenerateRequest | None = None,
    ) -> VisualRunRead | None:
        row = await self._requests.get_by_id_for_owner(request_id, owner_id, project_id)
        if row is None:
            return None
        if row.approved_asset_id is not None:
            raise InvalidStateError(
                "Cannot generate after approval; create a new VisualRequest"
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

        snapshot = VisualInputSnapshotTable(
            owner_id=owner_id,
            project_id=project_id,
            visual_request_id=row.id,
            visual_request_version=row.version,
            payload=_snapshot_payload(row),
        )

        async with transactional(self._session):
            snap = await self._snapshots.create(snapshot)
            run = VisualRunTable(
                owner_id=owner_id,
                project_id=project_id,
                visual_request_id=row.id,
                visual_request_version=row.version,
                snapshot_id=snap.id,
                status=VisualRunStatus.RUNNING,
                attempt=1,
                idempotency_key=idem,
            )
            created_run = await self._runs.create(run)
            row.current_run_id = created_run.id
            await self._requests.update(row)

        async def _fail_run(error_code: str, error_message: str) -> VisualRunRead:
            async with transactional(self._session):
                created_run.status = VisualRunStatus.FAILED
                created_run.error_code = error_code
                created_run.error_message = error_message[:2000]
                created_run.completed_at = utc_now()
                await self._runs.update(created_run)
            return _run_to_read(created_run)

        try:
            generated = await self._adapter.generate_candidates(
                snapshot_payload=snap.payload,
                visual_request_id=str(row.id),
                visual_request_version=row.version,
                snapshot_id=str(snap.id),
                requested_variants=row.requested_variants,
            )

            for idx, cand in enumerate(generated):
                asset_id = uuid4()
                content_path = resolve_storage_path(
                    settings=self._settings,
                    owner_id=owner_id,
                    project_id=project_id,
                    asset_id=asset_id,
                    version=1,
                    mime_type=cand.mime_type,
                )
                path = Path(content_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(cand.image_bytes)

                meta = {
                    "visual_director": True,
                    "visual_request_id": str(row.id),
                    "visual_request_version": row.version,
                    "visual_run_id": str(created_run.id),
                    "snapshot_id": str(snap.id),
                    "candidate_index": idx + 1,
                    "generation": cand.metadata,
                    "provider": cand.provider,
                    "model": cand.model,
                    "safety_result": cand.safety_result,
                    # Skill lineage outside sanitize_generation_metadata allowlist
                    "skill_id": (cand.metadata or {}).get("skill_id")
                    or "marketsynth.visual_generation",
                    "skill_version": (cand.metadata or {}).get("skill_version")
                    or "1.0.0",
                }
                asset = ImageAssetTable(
                    id=asset_id,
                    owner_id=owner_id,
                    project_id=project_id,
                    title=sanitize_text(cand.title),
                    status=ImageAssetStatus.DRAFT,
                    current_version_number=1,
                    mime_type=cand.mime_type,
                    width=cand.width,
                    height=cand.height,
                    content_path=content_path,
                    checksum=cand.checksum,
                    file_size_bytes=len(cand.image_bytes),
                    asset_metadata=meta,
                )
                version_row = ImageAssetVersionTable(
                    image_asset_id=asset_id,
                    version_number=1,
                    mime_type=cand.mime_type,
                    width=cand.width,
                    height=cand.height,
                    content_path=content_path,
                    checksum=cand.checksum,
                    file_size_bytes=len(cand.image_bytes),
                    asset_metadata=dict(meta),
                    created_by=owner_id,
                )
                async with transactional(self._session):
                    await self._images.create(asset)
                    await self._images.create_version(version_row)
                    await self._candidates.create(
                        VisualRunCandidateTable(
                            owner_id=owner_id,
                            project_id=project_id,
                            visual_request_id=row.id,
                            visual_request_version=row.version,
                            visual_run_id=created_run.id,
                            image_asset_id=asset_id,
                            candidate_index=idx + 1,
                            rejected=False,
                        )
                    )

            async with transactional(self._session):
                created_run.status = VisualRunStatus.SUCCEEDED
                created_run.provider = generated[0].provider if generated else None
                created_run.model = generated[0].model if generated else None
                created_run.completed_at = utc_now()
                await self._runs.update(created_run)

            try:
                from app.product_skills.runtime_service import ProductSkillRuntimeService
                from app.schemas.contracts import ProductSkillRunCreate

                skill_rt = ProductSkillRuntimeService(self._session)
                await skill_rt.execute(
                    owner_id,
                    project_id,
                    ProductSkillRunCreate(
                        skill_id="marketsynth.visual_generation",
                        trigger="social_post_image",
                        input_type="visual_request",
                        input_ref={
                            "visual_request_id": str(row.id),
                            "visual_run_id": str(created_run.id),
                        },
                        idempotency_key=f"cd-visual-{created_run.id}",
                        explicit=True,
                    ),
                )
            except Exception:  # noqa: BLE001
                pass
        except InvalidStateError as exc:
            detail = str(exc)
            code = "provider_failure"
            if detail.startswith("provider_config_error"):
                code = "provider_config_error"
            elif detail.startswith("policy_rejected"):
                code = "policy_rejected"
            elif detail.startswith("unsupported_aspect"):
                code = "unsupported_aspect_ratio"
            return await _fail_run(
                code, detail.split(":", 1)[0] if ":" in detail else detail
            )
        except Exception:  # noqa: BLE001
            return await _fail_run(
                "generation_failure",
                "Image generation failed unexpectedly",
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
    ) -> VisualDirectorCandidateRead | None:
        link = await self._candidates.get_by_asset(asset_id, owner_id, project_id)
        if link is None or link.visual_request_id != request_id:
            return None
        link.rejected = True
        async with transactional(self._session):
            await self._candidates.update(link)
        asset = await self._images.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None
        request = await self._requests.get_by_id_for_owner(
            request_id, owner_id, project_id
        )
        return self._candidate_read(
            link, asset, request_version=request.version if request else None
        )

    async def approve_candidate(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID,
        asset_id: UUID,
        body: VisualDirectorApproveRequest | None = None,
    ) -> VisualDirectorCandidateRead | None:
        link = await self._candidates.get_by_asset(asset_id, owner_id, project_id)
        if link is None or link.visual_request_id != request_id:
            return None
        if link.rejected:
            raise InvalidStateError("Rejected candidate cannot be approved")
        request = await self._requests.get_by_id_for_owner(
            request_id, owner_id, project_id
        )
        if request is None:
            return None
        if (
            request.approved_asset_id is not None
            and request.approved_asset_id != asset_id
        ):
            raise InvalidStateError(
                "VisualRequest already has an approved ImageAsset; create a new request"
            )

        asset = await self._images.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None

        if link.visual_request_version != request.version:
            raise InvalidStateError(
                "Candidate is stale after VisualRequest revision; regenerate first"
            )

        if (request.text_overlay or "").strip() and not (
            body and body.confirm_text_overlay
        ):
            raise InvalidStateError("text_overlay_confirmation_required")

        if asset.status == ImageAssetStatus.APPROVED:
            raise InvalidStateError("ImageAsset already approved")

        meta = dict(asset.asset_metadata or {})
        approval = dict(meta.get("approval") or {})
        approval.update(
            {
                "type": "visual_approval",
                "visual_request_id": str(request_id),
                "visual_request_version": request.version,
                "visual_run_id": str(link.visual_run_id),
                "asset_version": asset.current_version_number,
                "note": sanitize_text(body.note) if body and body.note else None,
                "text_overlay_confirmed": bool(
                    body and body.confirm_text_overlay
                ),
            }
        )
        meta["approval"] = approval
        asset.asset_metadata = meta
        asset.status = ImageAssetStatus.APPROVED
        asset.approved_version_number = asset.current_version_number

        async with transactional(self._session):
            await self._images.update(asset)
            request.approved_asset_id = asset.id
            request.approved_version_number = asset.approved_version_number
            await self._requests.update(request)

        return self._candidate_read(link, asset, request_version=request.version)

    async def resolve_content_path(
        self,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
    ) -> tuple[str, str] | None:
        asset = await self._images.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None or not asset.content_path:
            return None
        path = Path(asset.content_path)
        if not path.is_file():
            return None
        return str(path), asset.mime_type or "image/png"

    async def workspace_state(
        self,
        owner_id: UUID,
        project_id: UUID,
        request_id: UUID | None = None,
    ) -> VisualDirectorWorkspaceState:
        if not await self._ensure_project(owner_id, project_id):
            return VisualDirectorWorkspaceState(next_action="forbidden")

        if request_id is not None:
            request_row = await self._requests.get_by_id_for_owner(
                request_id, owner_id, project_id
            )
        else:
            request_row = await self._requests.latest_for_project(owner_id, project_id)

        if request_row is None:
            return VisualDirectorWorkspaceState(next_action="create_request")

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
        if active is not None:
            candidate_rows = await self._candidates.list_for_run(
                active.id, owner_id, project_id
            )

        candidates: list[VisualDirectorCandidateRead] = []
        for link in candidate_rows:
            asset = await self._images.get_by_id_for_owner(
                link.image_asset_id, owner_id, project_id
            )
            if asset is not None:
                candidates.append(
                    self._candidate_read(
                        link, asset, request_version=request_row.version
                    )
                )

        next_action = "generate"
        if active is not None and active.status in _ACTIVE:
            next_action = "wait_generation"
        elif active is not None and active.status == VisualRunStatus.FAILED:
            next_action = "generate"
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
                f"cd-visual-{active.id}",
            )
            if (
                skill_run is not None
                and skill_run.status == ProductSkillRunStatus.SUCCEEDED
            ):
                applied_skill_id = skill_run.skill_id
                applied_skill_version = skill_run.skill_version

        related_preview = None
        if request_row.related_text_asset_id:
            text_asset = await self._text_assets.get_by_id_for_owner(
                request_row.related_text_asset_id, owner_id, project_id
            )
            if text_asset is not None:
                related_preview = (text_asset.body or text_asset.title or "")[:500]

        return VisualDirectorWorkspaceState(
            request=_request_to_read(request_row),
            active_run=_run_to_read(active) if active else None,
            candidates=candidates,
            approved_asset_id=request_row.approved_asset_id,
            approved_version_number=request_row.approved_version_number,
            next_action=next_action,
            applied_skill_id=applied_skill_id,
            applied_skill_version=applied_skill_version,
            related_text_preview=related_preview,
        )

    def _candidate_read(
        self,
        link: VisualRunCandidateTable,
        asset: ImageAssetTable,
        *,
        request_version: int | None,
    ) -> VisualDirectorCandidateRead:
        meta = dict(asset.asset_metadata or {})
        # Public safe metadata only
        generation = dict(meta.get("generation") or {})
        for key in list(generation.keys()):
            if "url" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                generation.pop(key, None)
        stale = (
            request_version is not None
            and link.visual_request_version != request_version
        )
        return VisualDirectorCandidateRead(
            asset_id=asset.id,
            visual_run_id=link.visual_run_id,
            visual_request_id=link.visual_request_id,
            visual_request_version=link.visual_request_version,
            candidate_index=link.candidate_index,
            title=asset.title,
            status=asset.status.value
            if hasattr(asset.status, "value")
            else str(asset.status),
            current_version_number=asset.current_version_number,
            approved_version_number=asset.approved_version_number,
            rejected=link.rejected,
            stale=stale,
            mime_type=asset.mime_type,
            width=asset.width,
            height=asset.height,
            checksum=asset.checksum,
            content_url=(
                f"/projects/{asset.project_id}/visual-director/candidates/"
                f"{asset.id}/content"
            ),
            safe_metadata={
                "provider": meta.get("provider"),
                "model": meta.get("model"),
                "skill_id": meta.get("skill_id") or generation.get("skill_id"),
                "skill_version": meta.get("skill_version")
                or generation.get("skill_version"),
                "adapter": generation.get("adapter") or "visual_director_image",
                "safety_result": meta.get("safety_result"),
            },
        )
