"""Phase 1B.1 — commercial research orchestration pipeline."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.commercial_research.brief_from_request import (
    brief_content_from_text_update,
    brief_content_from_user_request,
)
from app.commercial_research.preflight import build_preflight_result
from app.commercial_research.quote import build_quote
from app.commercial_research.request_hash import compute_commercial_research_request_hash
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError, OwnershipError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.commercial_research_run import CommercialResearchRunTable
from app.db.models.investigation import InvestigationTable
from app.db.models.project_brief import ProjectBriefTable
from app.db.repositories.commercial_research_runs import CommercialResearchRunRepository
from app.db.repositories.investigations import InvestigationRepository
from app.db.repositories.project_briefs import ProjectBriefRepository
from app.domain.project_brief_fingerprint import compute_project_brief_fingerprint
from app.research_source_collection.readiness import collection_readiness
from app.schemas.contracts import (
    CommercialResearchApproval,
    CommercialResearchApprovalStatus,
    CommercialResearchApproveResponse,
    CommercialResearchBootstrapResponse,
    CommercialResearchEstimatedScope,
    CommercialResearchExecuteResponse,
    CommercialResearchPreflightResponse,
    CommercialResearchQuote,
    CommercialResearchQuoteResponse,
    CommercialResearchRun,
    CommercialResearchRunStatus,
    CommercialResearchStageId,
    CommercialResearchStatusCommercial,
    CommercialResearchStatusResponse,
    InvestigationCreateRequest,
    InvestigationStatus,
    ProjectBriefUpdateRequest,
)
from app.schemas.crud import ProjectCreate
from app.services.investigation_service import InvestigationService
from app.services.project_brief_service import ProjectBriefService, sanitize_brief_content
from app.services.projects_service import ProjectService
from app.services.transaction import transactional
from app.services.user_requests_service import UserRequestService

_STAGE_LABELS_RU: dict[CommercialResearchStageId, str] = {
    CommercialResearchStageId.BOOTSTRAP: "Подготовка",
    CommercialResearchStageId.PREFLIGHT: "Проверка готовности",
    CommercialResearchStageId.QUOTE: "Оценка стоимости",
    CommercialResearchStageId.APPROVAL: "Подтверждение",
    CommercialResearchStageId.SOURCE_COLLECTION: "Сбор источников",
    CommercialResearchStageId.SOURCE_VALIDATION: "Проверка источников",
    CommercialResearchStageId.EVIDENCE_EXTRACTION: "Извлечение доказательств",
    CommercialResearchStageId.FINDINGS: "Выводы",
    CommercialResearchStageId.VERDICT: "Вердикт",
    CommercialResearchStageId.COMPLETED: "Завершено",
}

_STATUS_LABELS_RU: dict[CommercialResearchRunStatus, str] = {
    CommercialResearchRunStatus.DRAFT: "Черновик",
    CommercialResearchRunStatus.PREFLIGHT_READY: "Готов к оценке",
    CommercialResearchRunStatus.QUOTE_READY: "Оценка готова",
    CommercialResearchRunStatus.AWAITING_APPROVAL: "Ожидает подтверждения",
    CommercialResearchRunStatus.QUEUED: "В очереди",
    CommercialResearchRunStatus.RUNNING: "Выполняется",
    CommercialResearchRunStatus.SUCCEEDED: "Завершено",
    CommercialResearchRunStatus.FAILED: "Ошибка",
    CommercialResearchRunStatus.CANCELLED: "Отменено",
    CommercialResearchRunStatus.OUTCOME_UNKNOWN: "Результат неизвестен",
}

_APPROVAL_LABELS_RU: dict[CommercialResearchApprovalStatus, str] = {
    CommercialResearchApprovalStatus.PENDING: "Ожидает",
    CommercialResearchApprovalStatus.APPROVED: "Подтверждено",
    CommercialResearchApprovalStatus.REJECTED: "Отклонено",
    CommercialResearchApprovalStatus.EXPIRED: "Истекло",
    CommercialResearchApprovalStatus.INVALIDATED: "Недействительно",
}


class CommercialResearchPipelineService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._runs = CommercialResearchRunRepository(session)
        self._briefs = ProjectBriefRepository(session)
        self._investigations = InvestigationRepository(session)
        self._projects = ProjectService(session)
        self._brief_service = ProjectBriefService(session)
        self._investigation_service = InvestigationService(session)
        self._user_requests = UserRequestService(session)

    def _completed_stages(self, row: CommercialResearchRunTable) -> list[CommercialResearchStageId]:
        return [CommercialResearchStageId(s) for s in (row.completed_stages or [])]

    def _mark_stage_complete(
        self,
        row: CommercialResearchRunTable,
        stage: CommercialResearchStageId,
    ) -> None:
        stages = self._completed_stages(row)
        if stage not in stages:
            stages.append(stage)
            row.completed_stages = [s.value for s in stages]
            flag_modified(row, "completed_stages")

    def _progress_for_stages(self, stages: list[CommercialResearchStageId]) -> int:
        phase1 = {
            CommercialResearchStageId.BOOTSTRAP,
            CommercialResearchStageId.PREFLIGHT,
            CommercialResearchStageId.QUOTE,
            CommercialResearchStageId.APPROVAL,
        }
        done = sum(1 for s in stages if s in phase1)
        return min(100, int(done / len(phase1) * 100))

    def _row_to_contract(self, row: CommercialResearchRunTable) -> CommercialResearchRun:
        quote_id = None
        if row.quote_json:
            quote_id = UUID(str(row.quote_json.get("quote_id")))
        approval_id = None
        if row.approval_json:
            approval_id = UUID(str(row.approval_json.get("approval_id")))
        return CommercialResearchRun(
            id=row.id,
            tenant_id=row.owner_id,
            owner_id=row.owner_id,
            user_request_id=row.user_request_id,
            project_id=row.project_id,
            project_brief_id=row.project_brief_id,
            project_brief_version=row.project_brief_version,
            investigation_id=row.investigation_id,
            status=CommercialResearchRunStatus(row.status),
            current_stage=CommercialResearchStageId(row.current_stage),
            completed_stages=self._completed_stages(row),
            progress_pct=row.progress_pct,
            request_hash=row.request_hash,
            run_version=row.run_version,
            idempotency_key=row.idempotency_key,
            quote_id=quote_id,
            approval_id=approval_id,
            provider_operation_id=row.provider_operation_id,
            error_code=row.error_code,
            safe_error_message=row.safe_error_message,
            outcome_unknown=row.outcome_unknown,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            updated_at=row.updated_at,
        )

    def _parse_quote(self, row: CommercialResearchRunTable) -> CommercialResearchQuote | None:
        if not row.quote_json:
            return None
        return CommercialResearchQuote.model_validate(row.quote_json)

    def _parse_approval(self, row: CommercialResearchRunTable) -> CommercialResearchApproval | None:
        if not row.approval_json:
            return None
        return CommercialResearchApproval.model_validate(row.approval_json)

    async def _load_user_request(self, owner_id: UUID, user_request_id: UUID):
        row = await self._user_requests.get_for_owner(owner_id, user_request_id)
        if row is None:
            raise NotFoundError("user_request_not_found")
        return row

    async def _ensure_brief_for_request(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        text: str,
        title: str,
        locale: str,
    ) -> ProjectBriefTable:
        content = brief_content_from_user_request(text=text, title=title, locale=locale)
        fingerprint = compute_project_brief_fingerprint(
            sanitize_brief_content(content.model_validate(content.model_dump()))
        )
        submitted = await self._briefs.find_submitted_by_fingerprint(
            owner_id,
            project_id,
            fingerprint,
        )
        if submitted is not None:
            return submitted

        open_draft = await self._briefs.get_open_draft(owner_id, project_id)
        if open_draft is not None:
            merged = brief_content_from_text_update(text=text, title=title, locale=locale)
            await self._brief_service.update_draft(
                owner_id,
                project_id,
                open_draft.id,
                ProjectBriefUpdateRequest.model_validate(merged.model_dump()),
            )
            submitted_row = await self._brief_service.submit(owner_id, project_id, open_draft.id)
            if submitted_row is None:
                raise InvalidStateError("brief_submit_failed")
            return submitted_row

        latest_submitted = await self._briefs.get_latest_submitted(owner_id, project_id)
        if latest_submitted is not None:
            new_draft = await self._brief_service.supersede(
                owner_id,
                project_id,
                latest_submitted.id,
                content,
            )
            if new_draft is None:
                raise InvalidStateError("brief_supersede_failed")
            submitted_row = await self._brief_service.submit(owner_id, project_id, new_draft.id)
            if submitted_row is None:
                raise InvalidStateError("brief_submit_failed")
            return submitted_row

        created = await self._brief_service.create_draft(owner_id, project_id, content)
        if created is None:
            raise InvalidStateError("brief_create_failed")
        submitted_row = await self._brief_service.submit(owner_id, project_id, created.id)
        if submitted_row is None:
            raise InvalidStateError("brief_submit_failed")
        return submitted_row

    async def _ensure_investigation(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief: ProjectBriefTable,
    ) -> InvestigationTable:
        existing = await self._investigations.get_by_brief_version(
            owner_id,
            project_id,
            brief.id,
            brief.version,
        )
        if existing is not None:
            return existing

        from app.db.repositories.business_idea_validation_runs import (
            BusinessIdeaValidationRunRepository,
        )

        active_biv = await BusinessIdeaValidationRunRepository(self._session).get_active_for_project(
            owner_id,
            project_id,
        )
        if active_biv is not None:
            linked = await self._investigations.get_by_id_for_owner(
                active_biv.investigation_id,
                owner_id,
                project_id,
            )
            if linked is not None:
                return linked

        active = await self._investigations.get_active(owner_id, project_id)
        if active is not None:
            now = utc_now()
            active.status = InvestigationStatus.SUPERSEDED
            active.updated_at = now
            await self._investigations.update(active)

        created = await self._investigation_service.create(
            owner_id,
            project_id,
            InvestigationCreateRequest(
                project_brief_id=brief.id,
                project_brief_version=brief.version,
                input_fingerprint=brief.input_fingerprint,
            ),
        )
        if created is None:
            raise InvalidStateError("investigation_create_failed")
        return created

    async def bootstrap(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        *,
        idempotency_key: str | None = None,
    ) -> CommercialResearchBootstrapResponse:
        user_request = await self._load_user_request(owner_id, user_request_id)
        if idempotency_key:
            by_key = await self._runs.get_by_idempotency_key(owner_id, idempotency_key)
            if by_key is not None:
                return CommercialResearchBootstrapResponse(
                    run=self._row_to_contract(by_key),
                    lineage_reused=True,
                )

        project_id = user_request.project_id
        if project_id is None:
            name = sanitize_text(user_request.title or user_request.text[:80]).strip() or "Проект"
            project = await self._projects.create(
                ProjectCreate(owner_id=owner_id, name=name[:255]),
            )
            project_id = project.id
            user_request.project_id = project_id
            user_request.updated_at = utc_now()
            async with transactional(self._session):
                self._session.add(user_request)
                await self._session.flush()

        brief = await self._ensure_brief_for_request(
            owner_id,
            project_id,
            text=user_request.text,
            title=user_request.title,
            locale="ru",
        )
        request_hash = compute_commercial_research_request_hash(
            user_request_id=user_request_id,
            normalized_text=user_request.normalized_text or user_request.text,
            route_category=str(user_request.route_category.value),
            project_brief_fingerprint=brief.input_fingerprint,
            project_brief_version=brief.version,
        )

        existing = await self._runs.get_by_request_hash(owner_id, user_request_id, request_hash)
        if existing is not None:
            return CommercialResearchBootstrapResponse(
                run=self._row_to_contract(existing),
                lineage_reused=True,
            )

        investigation = await self._ensure_investigation(owner_id, project_id, brief)
        run_version = await self._runs.max_run_version(owner_id, user_request_id) + 1
        now = utc_now()
        row = CommercialResearchRunTable(
            owner_id=owner_id,
            user_request_id=user_request_id,
            project_id=project_id,
            project_brief_id=brief.id,
            project_brief_version=brief.version,
            investigation_id=investigation.id,
            status=CommercialResearchRunStatus.DRAFT,
            current_stage=CommercialResearchStageId.BOOTSTRAP,
            completed_stages=[CommercialResearchStageId.BOOTSTRAP.value],
            progress_pct=25,
            request_hash=request_hash,
            run_version=run_version,
            idempotency_key=idempotency_key,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        async with transactional(self._session):
            created = await self._runs.create(row)
        return CommercialResearchBootstrapResponse(
            run=self._row_to_contract(created),
            lineage_reused=False,
        )

    async def _get_run_for_owner(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> CommercialResearchRunTable:
        row = await self._runs.get_for_user_request(owner_id, user_request_id)
        if row is None:
            raise InvalidStateError("commercial_research_run_not_found")
        if row.user_request_id != user_request_id:
            raise OwnershipError("commercial_research_run_not_owned")
        return row

    async def preflight(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        *,
        idempotency_key: str | None = None,
    ) -> CommercialResearchPreflightResponse:
        bootstrap = await self.bootstrap(owner_id, user_request_id, idempotency_key=idempotency_key)
        row = await self._runs.get_by_id(bootstrap.run.id)
        if row is None:
            raise InvalidStateError("commercial_research_run_not_found")

        user_request = await self._load_user_request(owner_id, user_request_id)
        commercial, developer = build_preflight_result(
            settings=self._settings,
            query_text=user_request.text,
        )
        row.preflight_json = {
            "commercial": commercial.model_dump(mode="json"),
            "developer": developer,
        }
        self._mark_stage_complete(row, CommercialResearchStageId.PREFLIGHT)
        row.current_stage = CommercialResearchStageId.PREFLIGHT
        row.status = CommercialResearchRunStatus.PREFLIGHT_READY
        row.progress_pct = self._progress_for_stages(self._completed_stages(row))
        row.updated_at = utc_now()
        flag_modified(row, "preflight_json")
        async with transactional(self._session):
            await self._runs.update(row)

        return CommercialResearchPreflightResponse(
            run_id=row.id,
            status=CommercialResearchRunStatus.PREFLIGHT_READY,
            commercial=commercial,
            developer=developer,
        )

    async def quote(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> CommercialResearchQuoteResponse:
        row = await self._get_run_for_owner(owner_id, user_request_id)
        if row.status not in (
            CommercialResearchRunStatus.PREFLIGHT_READY,
            CommercialResearchRunStatus.QUOTE_READY,
            CommercialResearchRunStatus.AWAITING_APPROVAL,
        ):
            raise InvalidStateError("preflight_required")

        preflight_commercial = (row.preflight_json or {}).get("commercial") or {}
        if not preflight_commercial.get("ready"):
            raise InvalidStateError("preflight_not_ready")

        scope_raw = preflight_commercial.get("estimated_scope") or {}
        scope = CommercialResearchEstimatedScope.model_validate(scope_raw)
        quote_obj, commercial, developer = build_quote(
            tenant_id=owner_id,
            request_hash=row.request_hash,
            scope=scope,
            settings=self._settings,
        )
        row.quote_json = quote_obj.model_dump(mode="json")
        row.approval_json = None
        self._mark_stage_complete(row, CommercialResearchStageId.QUOTE)
        row.current_stage = CommercialResearchStageId.QUOTE
        row.status = CommercialResearchRunStatus.QUOTE_READY
        row.progress_pct = self._progress_for_stages(self._completed_stages(row))
        row.updated_at = utc_now()
        flag_modified(row, "quote_json")
        flag_modified(row, "approval_json")
        async with transactional(self._session):
            await self._runs.update(row)

        return CommercialResearchQuoteResponse(
            run_id=row.id,
            quote_id=quote_obj.quote_id,
            status=CommercialResearchRunStatus.QUOTE_READY,
            commercial=commercial,
            developer=developer,
        )

    def _invalidate_approval(self, row: CommercialResearchRunTable, reason: str) -> None:
        approval = self._parse_approval(row)
        if approval is None:
            return
        approval.status = CommercialResearchApprovalStatus.INVALIDATED
        dumped = approval.model_dump(mode="json")
        dumped["invalidation_reason"] = reason
        row.approval_json = dumped
        flag_modified(row, "approval_json")

    async def approve(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        *,
        quote_id: UUID,
        owner_confirmed: bool,
    ) -> CommercialResearchApproveResponse:
        if not owner_confirmed:
            raise InvalidStateError("owner_confirmation_required")

        row = await self._get_run_for_owner(owner_id, user_request_id)
        quote = self._parse_quote(row)
        if quote is None:
            raise InvalidStateError("quote_required")
        if quote.quote_id != quote_id:
            raise InvalidStateError("quote_mismatch")
        if quote.request_hash != row.request_hash:
            raise InvalidStateError("quote_request_hash_mismatch")
        if quote.expires_at < utc_now():
            raise InvalidStateError("quote_expired")

        now = utc_now()
        approval = CommercialResearchApproval(
            approval_id=uuid4(),
            status=CommercialResearchApprovalStatus.APPROVED,
            tenant_id=owner_id,
            owner_id=owner_id,
            user_request_id=user_request_id,
            project_id=row.project_id,
            project_brief_id=row.project_brief_id,
            project_brief_version=row.project_brief_version,
            investigation_id=row.investigation_id,
            research_run_id=row.id,
            request_hash=row.request_hash,
            quote_id=quote.quote_id,
            owner_confirmed=True,
            approved_at=now,
            expires_at=quote.expires_at,
        )
        row.approval_json = approval.model_dump(mode="json")
        self._mark_stage_complete(row, CommercialResearchStageId.APPROVAL)
        row.current_stage = CommercialResearchStageId.APPROVAL
        row.status = CommercialResearchRunStatus.AWAITING_APPROVAL
        row.progress_pct = self._progress_for_stages(self._completed_stages(row))
        row.updated_at = now
        flag_modified(row, "approval_json")
        async with transactional(self._session):
            await self._runs.update(row)

        return CommercialResearchApproveResponse(
            run_id=row.id,
            approval_id=approval.approval_id,
            status=CommercialResearchRunStatus.AWAITING_APPROVAL,
            approval_status=CommercialResearchApprovalStatus.APPROVED,
            expires_at=approval.expires_at,
        )

    async def execute(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        *,
        idempotency_key: str,
        owner_confirmed: bool,
    ) -> CommercialResearchExecuteResponse:
        if not idempotency_key.strip():
            raise InvalidStateError("idempotency_key_required")
        if not owner_confirmed:
            raise InvalidStateError("owner_confirmation_required")

        row = await self._get_run_for_owner(owner_id, user_request_id)
        if row.status == CommercialResearchRunStatus.OUTCOME_UNKNOWN or row.outcome_unknown:
            raise InvalidStateError("outcome_unknown_no_blind_retry")
        if row.retry_blocked:
            raise InvalidStateError("retry_not_allowed")

        approval = self._parse_approval(row)
        if approval is None:
            raise InvalidStateError("approval_required")
        if approval.status != CommercialResearchApprovalStatus.APPROVED:
            raise InvalidStateError("approval_invalid")
        if approval.request_hash != row.request_hash:
            raise InvalidStateError("approval_request_hash_mismatch")
        quote = self._parse_quote(row)
        if quote is None or approval.quote_id != quote.quote_id:
            raise InvalidStateError("approval_quote_mismatch")
        if approval.expires_at < utc_now() or quote.expires_at < utc_now():
            raise InvalidStateError("approval_expired")

        raise InvalidStateError("execution_not_enabled_in_phase_1b_1")

    async def status(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        *,
        include_developer: bool = False,
    ) -> CommercialResearchStatusResponse:
        row = await self._get_run_for_owner(owner_id, user_request_id)
        return self._status_from_row(row, include_developer=include_developer)

    def _status_from_row(
        self,
        row: CommercialResearchRunTable,
        *,
        include_developer: bool,
    ) -> CommercialResearchStatusResponse:
        quote = self._parse_quote(row)
        approval = self._parse_approval(row)
        completed = self._completed_stages(row)
        blocking: str | None = None
        preflight = (row.preflight_json or {}).get("commercial") or {}
        if not preflight.get("ready") and preflight.get("blocking_reasons"):
            blocking = str((preflight.get("blocking_reasons") or ["not_ready"])[0])

        quote_summary = None
        if quote is not None:
            quote_summary = (
                f"≈ {quote.estimated_cost_min}–{quote.estimated_cost_max} {quote.currency}"
            )

        approval_label = None
        if approval is not None:
            if approval.expires_at < utc_now():
                approval_label = _APPROVAL_LABELS_RU[CommercialResearchApprovalStatus.EXPIRED]
            else:
                approval_label = _APPROVAL_LABELS_RU[approval.status]

        retryable = (
            row.status
            in (
                CommercialResearchRunStatus.PREFLIGHT_READY,
                CommercialResearchRunStatus.QUOTE_READY,
                CommercialResearchRunStatus.FAILED,
            )
            and not row.outcome_unknown
            and not row.retry_blocked
        )

        commercial = CommercialResearchStatusCommercial(
            status_label=_STATUS_LABELS_RU[CommercialResearchRunStatus(row.status)],
            stage_label=_STAGE_LABELS_RU[CommercialResearchStageId(row.current_stage)],
            completed_stage_labels=[
                _STAGE_LABELS_RU[s] for s in completed if s in _STAGE_LABELS_RU
            ],
            blocking_reason=blocking,
            quote_summary=quote_summary,
            approval_status_label=approval_label,
            retryable=retryable,
            outcome_unknown=row.outcome_unknown,
            research_not_executed=True,
        )

        developer: dict[str, Any] | None = None
        if include_developer:
            readiness = collection_readiness(self._settings)
            developer = {
                "run_id": str(row.id),
                "request_hash": row.request_hash,
                "run_version": row.run_version,
                "status": row.status,
                "current_stage": row.current_stage,
                "completed_stages": row.completed_stages,
                "quote_id": str(quote.quote_id) if quote else None,
                "approval_id": str(approval.approval_id) if approval else None,
                "readiness_status": readiness.get("status"),
                "secrets_exposed": False,
            }

        return CommercialResearchStatusResponse(
            run_id=row.id,
            user_request_id=row.user_request_id,
            project_id=row.project_id,
            investigation_id=row.investigation_id,
            status=CommercialResearchRunStatus(row.status),
            current_stage=CommercialResearchStageId(row.current_stage),
            commercial=commercial,
            developer=developer,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def mark_outcome_unknown(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> CommercialResearchRunTable:
        """Test/helper hook for outcome_unknown contract (Phase 1B.1)."""
        row = await self._get_run_for_owner(owner_id, user_request_id)
        row.status = CommercialResearchRunStatus.OUTCOME_UNKNOWN
        row.outcome_unknown = True
        row.retry_blocked = True
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._runs.update(row)
