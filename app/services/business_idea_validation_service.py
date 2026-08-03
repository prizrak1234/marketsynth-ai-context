"""Business Idea Validation service — idempotent runs + UserRequest attachment."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.business_idea_validation.output_enrichment import (
    enrich_output_commercial,
    enrich_output_gap_presentation,
)
from app.business_idea_validation.partial_research_delivery import is_partial_research_output
from app.business_idea_validation.progress_persistence import PersistingBivRunProgressTracker
from app.business_idea_validation.run_observability import BivRunObservabilityRecorder
from app.business_idea_validation.skill import BusinessIdeaValidationSkill
from app.core.api_errors import _STABLE_DOMAIN_ERROR_CODES
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError, ResearchPipelineError
from app.core.logging import get_logger
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.analysis_context import AnalysisContextTable
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.repositories.business_idea_validation_runs import BusinessIdeaValidationRunRepository
from app.schemas.contracts import (
    BivPipelineStage,
    BivResearchMode,
    BivResearchTerminalState,
    BivRunObservability,
    BivRunProgress,
    BusinessIdeaValidationAsyncRunAcceptedResponse,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationProjectHydration,
    BusinessIdeaValidationProjectLatestRunSummary,
    BusinessIdeaValidationRunRequest,
    BusinessIdeaValidationRunResponse,
    BusinessIdeaValidationRunStatus,
)
from app.business_idea_validation.e2e_deterministic_fixture import E2eDeterministicFixtureService
from app.services.analysis_context_service import AnalysisContextService
from app.services.commercial_research_pipeline_service import CommercialResearchPipelineService
from app.services.transaction import transactional
from app.services.user_requests_service import UserRequestService

RESEARCH_IDEMPOTENCY_PREFIX = "biv-research-"
RERUN_IDEMPOTENCY_PREFIX = "biv-rerun-"
INTERRUPTED_ERROR_CODE = "research_execution_interrupted"

log = get_logger(__name__)


def build_research_idempotency_key(analysis_context_id: UUID, input_snapshot_hash: str) -> str:
    return f"{RESEARCH_IDEMPOTENCY_PREFIX}{analysis_context_id}-{input_snapshot_hash[:16]}"


def build_rerun_idempotency_key(analysis_context_id: UUID, input_snapshot_hash: str) -> str:
    return f"{RERUN_IDEMPOTENCY_PREFIX}{analysis_context_id}-{input_snapshot_hash[:12]}-{uuid4().hex[:10]}"


def resolve_research_mode(body: BusinessIdeaValidationRunRequest) -> BivResearchMode:
    if body.research_mode != BivResearchMode.INITIAL:
        return body.research_mode
    if body.rerun_intent or body.idempotency_key.startswith(RERUN_IDEMPOTENCY_PREFIX):
        if body.changed_fields:
            return BivResearchMode.REFINED_RERUN
        return BivResearchMode.RERUN
    return BivResearchMode.INITIAL


class BusinessIdeaValidationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._runs = BusinessIdeaValidationRunRepository(session)
        self._user_requests = UserRequestService(session)
        self._pipeline = CommercialResearchPipelineService(session, settings)
        self._analysis_contexts = AnalysisContextService(session, settings)

    def _biv_input_from_context_row(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        user_request_id: UUID,
        context_row,
        fallback_idea: str,
    ) -> BusinessIdeaValidationInput:
        fields = self._analysis_contexts.build_biv_input_from_context(context_row)
        idea = sanitize_text(fields.get("idea") or fallback_idea).strip()
        return BusinessIdeaValidationInput(
            tenant_id=owner_id,
            project_id=project_id,
            user_request_id=user_request_id,
            idea=idea,
            market=fields.get("market"),
            location=fields.get("location"),
            target_audience=fields.get("target_audience"),
            budget=fields.get("budget"),
            constraints=fields.get("constraints"),
            product_or_service=fields.get("product_or_service"),
            pricing_or_revenue_model=fields.get("pricing_or_revenue_model"),
            known_competitors=fields.get("known_competitors"),
            analysis_goal=fields.get("analysis_goal"),
            current_stage=fields.get("current_stage"),
        )

    async def _persist_partial_research_failure(
        self,
        row: BusinessIdeaValidationRunTable,
        output: BusinessIdeaValidationOutput,
        *,
        progress_tracker: PersistingBivRunProgressTracker,
        observability: BivRunObservabilityRecorder,
        context_row: AnalysisContextTable | None = None,
    ) -> BusinessIdeaValidationOutput:
        output = enrich_output_gap_presentation(output)
        error_code = output.partial_failure_code or "evidence_insufficiency"
        safe_message = (
            output.partial_safe_message
            or self._commercial_safe_message(error_code)
        )
        progress_tracker.mark_failed(safe_message=safe_message, error_code=error_code)
        now = utc_now()
        terminal_progress = progress_tracker.snapshot()
        output = output.model_copy(update={"run_progress": terminal_progress})
        row.status = BusinessIdeaValidationRunStatus.FAILED
        row.result_json = output.model_dump(mode="json")
        row.business_verdict_id = None
        row.investigation_id = output.investigation_id
        row.error_code = error_code
        row.safe_error_message = safe_message
        row.finished_at = now
        row.updated_at = now
        row.progress_json = terminal_progress.model_dump(mode="json")
        row.observability_json = observability.snapshot().model_dump(mode="json")
        async with transactional(self._session):
            await self._runs.update(row)
            if context_row is not None:
                await self._analysis_contexts.mark_rerun_ready(context_row)
        return output

    async def _enrich_output(
        self,
        output: BusinessIdeaValidationOutput,
        *,
        owner_id: UUID,
        user_request_id: UUID,
        analysis_context_id: UUID | None,
        fallback_idea: str = "",
    ) -> BusinessIdeaValidationOutput:
        inp: BusinessIdeaValidationInput | None = None
        if analysis_context_id is not None:
            ctx = await self._analysis_contexts._contexts.get_by_id(owner_id, analysis_context_id)
            if ctx is not None:
                inp = self._biv_input_from_context_row(
                    owner_id=owner_id,
                    project_id=output.project_id or ctx.project_id,
                    user_request_id=user_request_id,
                    context_row=ctx,
                    fallback_idea=fallback_idea,
                )
        return enrich_output_commercial(output, inp)

    async def _maybe_persist_enriched(
        self,
        row: BusinessIdeaValidationRunTable,
        output: BusinessIdeaValidationOutput,
    ) -> None:
        if row.result_json and row.result_json.get("customer_report"):
            return
        if output.customer_report is None:
            return
        row.result_json = output.model_dump(mode="json")
        row.updated_at = utc_now()
        async with transactional(self._session):
            await self._runs.update(row)

    async def _persist_run_progress(
        self,
        row: BusinessIdeaValidationRunTable,
        progress: BivRunProgress,
    ) -> None:
        run_id = row.id
        progress_json = progress.model_dump(mode="json")
        now = utc_now()
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as isolated:
            try:
                async with transactional(isolated):
                    db_row = await isolated.get(BusinessIdeaValidationRunTable, run_id)
                    if db_row is None:
                        return
                    db_row.progress_json = progress_json
                    db_row.updated_at = now
                    await isolated.flush()
            except Exception:
                if self._settings.app_env in {"development", "test", "pilot"}:
                    return
                raise

    async def _persist_run_observability(
        self,
        row: BusinessIdeaValidationRunTable,
        observability: BivRunObservability,
    ) -> None:
        run_id = row.id
        observability_json = observability.model_dump(mode="json")
        now = utc_now()
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as isolated:
            try:
                async with transactional(isolated):
                    db_row = await isolated.get(BusinessIdeaValidationRunTable, run_id)
                    if db_row is None:
                        return
                    db_row.observability_json = observability_json
                    db_row.updated_at = now
                    await isolated.flush()
            except Exception:
                if self._settings.app_env in {"development", "test", "pilot"}:
                    return
                raise

    def _progress_from_row(self, row: BusinessIdeaValidationRunTable) -> BivRunProgress | None:
        if not row.progress_json:
            return None
        progress = BivRunProgress.model_validate(row.progress_json)
        if row.status in {
            BusinessIdeaValidationRunStatus.SUCCEEDED,
            BusinessIdeaValidationRunStatus.FAILED,
        } and progress.state != row.status:
            progress = progress.model_copy(update={"state": row.status})
        return progress

    def _commercial_safe_message(self, error_code: str) -> str:
        return _STABLE_DOMAIN_ERROR_CODES.get(
            error_code,
            "Business idea validation failed.",
        )

    @staticmethod
    def interrupted_safe_message() -> str:
        return _STABLE_DOMAIN_ERROR_CODES.get(
            INTERRUPTED_ERROR_CODE,
            "Research was interrupted. Please retry.",
        )

    def _initial_queued_progress(
        self,
        row: BusinessIdeaValidationRunTable,
        *,
        correlation_id: str,
    ) -> BivRunProgress:
        now = row.created_at
        return BivRunProgress(
            run_id=row.id,
            state=BusinessIdeaValidationRunStatus.QUEUED,
            current_stage=BivPipelineStage.NORMALIZING_INPUT,
            completed_stages=[],
            started_at=now,
            updated_at=now,
            progress_percent=0,
            correlation_id=correlation_id,
        )

    def _to_async_accepted(
        self,
        row: BusinessIdeaValidationRunTable,
        *,
        user_request_id: UUID,
        lineage_reused: bool = False,
    ) -> BusinessIdeaValidationAsyncRunAcceptedResponse:
        return BusinessIdeaValidationAsyncRunAcceptedResponse(
            run_id=row.id,
            user_request_id=row.user_request_id,
            project_id=row.project_id,
            analysis_context_id=row.analysis_context_id,
            input_snapshot_hash=row.input_snapshot_hash or "",
            status=row.status,
            progress=self._progress_from_row(row),
            created_at=row.created_at,
            lineage_reused=lineage_reused,
        )

    async def _resolve_idempotent_enqueue(
        self,
        existing: BusinessIdeaValidationRunTable,
        body: BusinessIdeaValidationRunRequest,
        user_request_id: UUID,
    ) -> BusinessIdeaValidationAsyncRunAcceptedResponse | None:
        if (
            existing.analysis_context_id != body.analysis_context_id
            or existing.input_snapshot_hash != body.input_snapshot_hash
        ):
            raise InvalidStateError("analysis_context_stale")

        if existing.status in {
            BusinessIdeaValidationRunStatus.QUEUED,
            BusinessIdeaValidationRunStatus.RUNNING,
        }:
            return self._to_async_accepted(
                existing,
                user_request_id=user_request_id,
                lineage_reused=True,
            )

        if existing.status == BusinessIdeaValidationRunStatus.SUCCEEDED:
            return self._to_async_accepted(
                existing,
                user_request_id=user_request_id,
                lineage_reused=True,
            )

        is_rerun_key = body.idempotency_key.startswith(RERUN_IDEMPOTENCY_PREFIX)
        if existing.status == BusinessIdeaValidationRunStatus.FAILED and not is_rerun_key:
            return self._to_async_accepted(
                existing,
                user_request_id=user_request_id,
                lineage_reused=True,
            )
        return None

    async def get_run_for_owner(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        run_id: UUID,
    ) -> BusinessIdeaValidationRunResponse:
        row = await self._runs.get_by_id_for_owner(owner_id, run_id)
        if row is None or row.user_request_id != user_request_id:
            raise NotFoundError("validation_run_not_found")
        output = None
        if row.result_json:
            user_request = await self._user_requests.get_for_owner(owner_id, user_request_id)
            output = await self._enrich_output(
                BusinessIdeaValidationOutput.model_validate(row.result_json),
                owner_id=owner_id,
                user_request_id=user_request_id,
                analysis_context_id=row.analysis_context_id,
                fallback_idea=user_request.text if user_request else "",
            )
            await self._maybe_persist_enriched(row, output)
        research_mode = (
            BivResearchMode(row.research_mode)
            if row.research_mode
            else None
        )
        return BusinessIdeaValidationRunResponse(
            run_id=row.id,
            user_request_id=user_request_id,
            project_id=row.project_id,
            analysis_context_id=row.analysis_context_id,
            input_snapshot_hash=row.input_snapshot_hash,
            status=row.status,
            research_mode=research_mode,
            parent_run_id=row.parent_run_id,
            output=output,
            error_code=row.error_code,
            safe_message=row.safe_error_message,
            progress=self._progress_from_row(row),
        )

    async def get_progress_for_run(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        run_id: UUID,
    ) -> BivRunProgress:
        row = await self._runs.get_by_id_for_owner(owner_id, run_id)
        if row is None or row.user_request_id != user_request_id:
            raise NotFoundError("validation_run_not_found")
        progress = self._progress_from_row(row)
        if progress is None:
            raise NotFoundError("progress_not_found")
        return progress

    async def try_claim_queued_run(self, run_id: UUID) -> bool:
        async with transactional(self._session):
            claimed = await self._runs.claim_queued(run_id)
            if claimed is None:
                return False
            await self._session.flush()
            return True

    async def enqueue_run(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        body: BusinessIdeaValidationRunRequest,
    ) -> BusinessIdeaValidationAsyncRunAcceptedResponse:
        if not body.idempotency_key.strip():
            raise InvalidStateError("idempotency_key_required")
        if not body.analysis_context_id or not body.input_snapshot_hash:
            raise InvalidStateError("analysis_context_required")

        research_mode = resolve_research_mode(body)
        is_rerun = research_mode in {BivResearchMode.RERUN, BivResearchMode.REFINED_RERUN}
        is_initial = research_mode == BivResearchMode.INITIAL
        if is_initial and not body.idempotency_key.startswith(RESEARCH_IDEMPOTENCY_PREFIX):
            raise InvalidStateError("research_idempotency_key_required")
        if is_rerun and not body.idempotency_key.startswith(RERUN_IDEMPOTENCY_PREFIX):
            raise InvalidStateError("rerun_idempotency_key_required")

        existing = await self._runs.get_by_idempotency_key(owner_id, body.idempotency_key)
        if existing is not None:
            resolved = await self._resolve_idempotent_enqueue(
                existing,
                body,
                user_request_id,
            )
            if resolved is not None:
                return resolved

        user_request = await self._user_requests.get_for_owner(owner_id, user_request_id)
        if user_request is None:
            raise NotFoundError("user_request_not_found")

        context_row = await self._analysis_contexts.get_for_run(
            owner_id,
            body.analysis_context_id,
            body.input_snapshot_hash,
        )
        context_project_id = context_row.project_id
        if user_request.project_id is None:
            user_request.project_id = context_project_id
            user_request.updated_at = utc_now()
            async with transactional(self._session):
                self._session.add(user_request)
                await self._session.flush()
        elif user_request.project_id != context_project_id:
            raise InvalidStateError("analysis_context_stale")

        async with transactional(self._session):
            active = await self._runs.get_active_for_project_for_update(
                owner_id,
                context_project_id,
            )
            if active is not None:
                return self._to_async_accepted(
                    active,
                    user_request_id=active.user_request_id,
                    lineage_reused=True,
                )

        bootstrap = await self._pipeline.bootstrap(owner_id, user_request_id)
        project_id = bootstrap.run.project_id

        context_row = await self._analysis_contexts.assert_runnable(
            owner_id,
            project_id,
            body.analysis_context_id,
            body.input_snapshot_hash,
        )
        await self._analysis_contexts.mark_analysis_requested(context_row)

        context_fields = self._analysis_contexts.build_biv_input_from_context(context_row)
        idea = sanitize_text(body.idea or context_fields["idea"] or user_request.text).strip()
        if len(idea) < 8:
            raise InvalidStateError("idea_too_short")

        now = utc_now()
        correlation_id = uuid4().hex
        row = BusinessIdeaValidationRunTable(
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=user_request_id,
            project_id=project_id,
            investigation_id=bootstrap.run.investigation_id,
            analysis_context_id=context_row.id,
            input_snapshot_hash=body.input_snapshot_hash,
            idempotency_key=body.idempotency_key,
            status=BusinessIdeaValidationRunStatus.QUEUED,
            research_mode=research_mode.value,
            parent_run_id=body.parent_run_id,
            created_at=now,
            updated_at=now,
        )
        try:
            async with transactional(self._session):
                raced_active = await self._runs.get_active_for_project_for_update(
                    owner_id,
                    project_id,
                )
                if raced_active is not None:
                    return self._to_async_accepted(
                        raced_active,
                        user_request_id=raced_active.user_request_id,
                        lineage_reused=True,
                    )
                row = await self._runs.create(row)
                row.progress_json = self._initial_queued_progress(
                    row,
                    correlation_id=correlation_id,
                ).model_dump(mode="json")
                await self._runs.update(row)
                await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raced = await self._runs.get_by_idempotency_key(owner_id, body.idempotency_key)
            if raced is not None:
                resolved = await self._resolve_idempotent_enqueue(
                    raced,
                    body,
                    user_request_id,
                )
                if resolved is not None:
                    return resolved
            active = await self._runs.get_active_for_project(owner_id, project_id)
            if active is not None:
                return self._to_async_accepted(
                    active,
                    user_request_id=active.user_request_id,
                    lineage_reused=True,
                )
            raise InvalidStateError("idempotency_conflict") from None

        from app.workers.biv_run_dispatcher import get_biv_run_dispatcher

        await get_biv_run_dispatcher().dispatch(row.id)
        return self._to_async_accepted(row, user_request_id=user_request_id)

    async def execute_claimed_run(self, run_id: UUID) -> None:
        row = await self._runs.get_by_id(run_id)
        if row is None:
            return
        if row.status != BusinessIdeaValidationRunStatus.RUNNING:
            return

        user_request = await self._user_requests.get_for_owner(row.owner_id, row.user_request_id)
        if user_request is None:
            await self._mark_run_failed(
                run_id,
                error_code="user_request_not_found",
                safe_message=self._commercial_safe_message("user_request_not_found"),
            )
            return

        if row.analysis_context_id is None or not row.input_snapshot_hash:
            await self._mark_run_failed(
                run_id,
                error_code="analysis_context_required",
                safe_message=self._commercial_safe_message("analysis_context_required"),
            )
            return

        try:
            context_row = await self._analysis_contexts.get_for_run(
                row.owner_id,
                row.analysis_context_id,
                row.input_snapshot_hash,
            )
        except (NotFoundError, InvalidStateError) as exc:
            await self._mark_run_failed(
                run_id,
                error_code=str(exc),
                safe_message=self._commercial_safe_message(str(exc)),
            )
            return

        research_mode = (
            BivResearchMode(row.research_mode)
            if row.research_mode
            else BivResearchMode.INITIAL
        )
        context_fields = self._analysis_contexts.build_biv_input_from_context(context_row)
        skill_input = BusinessIdeaValidationInput(
            tenant_id=row.owner_id,
            project_id=row.project_id,
            user_request_id=row.user_request_id,
            idea=sanitize_text(context_fields.get("idea") or user_request.text).strip(),
            market=context_fields.get("market"),
            location=context_fields.get("location"),
            target_audience=context_fields.get("target_audience"),
            budget=context_fields.get("budget"),
            constraints=context_fields.get("constraints"),
            product_or_service=context_fields.get("product_or_service"),
            pricing_or_revenue_model=context_fields.get("pricing_or_revenue_model"),
            known_competitors=context_fields.get("known_competitors"),
            analysis_goal=context_fields.get("analysis_goal"),
            current_stage=context_fields.get("current_stage"),
        )

        correlation_id = uuid4().hex
        now = utc_now()
        progress_tracker = PersistingBivRunProgressTracker(
            run_id=row.id,
            correlation_id=correlation_id,
            started_at=now,
            on_persist=lambda snap: self._persist_run_progress(row, snap),
        )
        await self._persist_run_progress(row, progress_tracker.snapshot())

        observability = BivRunObservabilityRecorder(
            run_id=row.id,
            correlation_id=correlation_id,
            project_id=row.project_id,
            user_request_id=row.user_request_id,
            research_mode=research_mode,
            parent_run_id=row.parent_run_id,
        )
        observability.record_transition("running", stage="started")
        await self._analysis_contexts.mark_analyzing(context_row)

        fixture_svc = E2eDeterministicFixtureService(self._session, self._settings)
        e2e_outcome = await fixture_svc.resolve_for_owner(row.owner_id)
        try:
            if e2e_outcome is not None:
                from app.business_idea_validation.e2e_deterministic_adapter import (
                    execute_e2e_deterministic_run,
                )

                output = await execute_e2e_deterministic_run(
                    e2e_outcome,
                    skill_input,
                    run_id=row.id,
                    progress=progress_tracker,
                )
                # E2E adapter emits synthetic IDs; keep bootstrap investigation for FK safety.
                output = output.model_copy(update={"investigation_id": row.investigation_id})
            else:
                output = await BusinessIdeaValidationSkill(self._session, self._settings).run(
                    skill_input,
                    run_id=row.id,
                    progress=progress_tracker,
                    observability=observability,
                )
            output = output.model_copy(
                update={
                    "run_id": row.id,
                    "owner_id": row.owner_id,
                    "project_id": row.project_id,
                    "analysis_context_id": context_row.id,
                    "input_snapshot_hash": row.input_snapshot_hash,
                    "research_terminal_state": output.research_terminal_state,
                    "research_mode": research_mode,
                    "parent_run_id": row.parent_run_id,
                }
            )
            if is_partial_research_output(output):
                await self._persist_partial_research_failure(
                    row,
                    output,
                    progress_tracker=progress_tracker,
                    observability=observability,
                    context_row=context_row,
                )
                log.info(
                    "biv_run_partial_research",
                    run_id=str(row.id),
                    project_id=str(row.project_id),
                    error_code=output.partial_failure_code,
                )
                return
            output = await self._enrich_output(
                output,
                owner_id=row.owner_id,
                user_request_id=row.user_request_id,
                analysis_context_id=context_row.id,
                fallback_idea=user_request.text,
            )
            row.status = BusinessIdeaValidationRunStatus.SUCCEEDED
            row.result_json = output.model_dump(mode="json")
            if e2e_outcome is not None:
                row.business_verdict_id = None
            else:
                row.business_verdict_id = output.business_verdict_id
            row.investigation_id = output.investigation_id
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.error_code = None
            row.safe_error_message = None
            row.progress_json = (
                output.run_progress or progress_tracker.snapshot()
            ).model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")

            user_request.skill_inputs = {
                **dict(user_request.skill_inputs or {}),
                "business_idea_validation_run_id": str(row.id),
                "business_idea_validation": output.model_dump(mode="json"),
                "analysis_context_id": str(context_row.id),
                "input_snapshot_hash": row.input_snapshot_hash,
            }
            user_request.skill_code = BusinessIdeaValidationSkill.SKILL_CODE
            user_request.skill_version = BusinessIdeaValidationSkill.SKILL_VERSION
            user_request.project_id = row.project_id
            user_request.updated_at = row.finished_at
            flag_modified(user_request, "skill_inputs")

            async with transactional(self._session):
                await self._runs.update(row)
                self._session.add(user_request)
                if e2e_outcome is not None:
                    await fixture_svc.clear_for_owner(row.owner_id)
                await self._session.flush()

            await self._analysis_contexts.mark_completed(context_row)
        except ResearchPipelineError as exc:
            progress_tracker.mark_failed(
                safe_message=exc.safe_message,
                error_code=exc.failure_code,
            )
            observability.record_transition("failed", stage=exc.failure_stage)
            row.status = BusinessIdeaValidationRunStatus.FAILED
            row.error_code = exc.failure_code
            row.safe_error_message = exc.safe_message
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.progress_json = progress_tracker.snapshot().model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")
            async with transactional(self._session):
                await self._runs.update(row)
            log.info(
                "biv_run_pipeline_failed",
                run_id=str(row.id),
                project_id=str(row.project_id),
                error_code=exc.failure_code,
            )
        except InvalidStateError as exc:
            error_code = str(exc)
            safe_message = self._commercial_safe_message(error_code)
            progress_tracker.mark_failed(safe_message=safe_message, error_code=error_code)
            observability.record_transition(
                "failed",
                stage=progress_tracker.snapshot().current_stage.value,
            )
            row.status = BusinessIdeaValidationRunStatus.FAILED
            row.error_code = error_code
            row.safe_error_message = safe_message
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.progress_json = progress_tracker.snapshot().model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")
            async with transactional(self._session):
                await self._runs.update(row)
            log.warning(
                "biv_run_lifecycle_failure",
                run_id=str(row.id),
                project_id=str(row.project_id),
                error_code=error_code,
            )
        except Exception:  # noqa: BLE001
            error_code = "research_internal_error"
            safe_message = self._commercial_safe_message(error_code)
            progress_tracker.mark_failed(safe_message=safe_message, error_code=error_code)
            observability.record_transition(
                "failed",
                stage=progress_tracker.snapshot().current_stage.value,
            )
            row.status = BusinessIdeaValidationRunStatus.FAILED
            row.error_code = error_code
            row.safe_error_message = safe_message
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.progress_json = progress_tracker.snapshot().model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")
            async with transactional(self._session):
                await self._runs.update(row)
            log.exception(
                "biv_run_unhandled_failure",
                run_id=str(row.id),
                project_id=str(row.project_id),
                error_code=error_code,
            )
        finally:
            if e2e_outcome is not None:
                async with transactional(self._session):
                    await fixture_svc.clear_for_owner(row.owner_id)

    async def _mark_run_failed(
        self,
        run_id: UUID,
        *,
        error_code: str,
        safe_message: str,
    ) -> None:
        row = await self._runs.get_by_id(run_id)
        if row is None:
            return
        now = utc_now()
        row.status = BusinessIdeaValidationRunStatus.FAILED
        row.error_code = error_code
        row.safe_error_message = safe_message
        row.finished_at = now
        row.updated_at = now
        async with transactional(self._session):
            await self._runs.update(row)

    async def get_progress(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> BivRunProgress | None:
        row = await self._runs.get_latest_for_user_request(owner_id, user_request_id)
        if row is None:
            return None
        return self._progress_from_row(row)

    async def get_diagnostics(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> BivRunObservability | None:
        if self._settings.app_env not in {"development", "test", "pilot"}:
            return None
        row = await self._runs.get_latest_for_user_request(owner_id, user_request_id)
        if row is None or not row.observability_json:
            return None
        return BivRunObservability.model_validate(row.observability_json)

    async def run(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        body: BusinessIdeaValidationRunRequest,
    ) -> BusinessIdeaValidationRunResponse:
        if not body.idempotency_key.strip():
            raise InvalidStateError("idempotency_key_required")

        if not body.analysis_context_id or not body.input_snapshot_hash:
            raise InvalidStateError("analysis_context_required")

        research_mode = resolve_research_mode(body)
        is_rerun = research_mode in {BivResearchMode.RERUN, BivResearchMode.REFINED_RERUN}
        is_initial = research_mode == BivResearchMode.INITIAL
        if is_initial and not body.idempotency_key.startswith(RESEARCH_IDEMPOTENCY_PREFIX):
            raise InvalidStateError("research_idempotency_key_required")
        if is_rerun and not body.idempotency_key.startswith(RERUN_IDEMPOTENCY_PREFIX):
            raise InvalidStateError("rerun_idempotency_key_required")

        existing = await self._runs.get_by_idempotency_key(
            owner_id,
            body.idempotency_key,
        )
        if existing is not None:
            if (
                existing.analysis_context_id != body.analysis_context_id
                or existing.input_snapshot_hash != body.input_snapshot_hash
            ):
                raise InvalidStateError("analysis_context_stale")

            if existing.status in {
                BusinessIdeaValidationRunStatus.QUEUED,
                BusinessIdeaValidationRunStatus.RUNNING,
            }:
                return BusinessIdeaValidationRunResponse(
                    run_id=existing.id,
                    user_request_id=user_request_id,
                    project_id=existing.project_id,
                    analysis_context_id=existing.analysis_context_id,
                    input_snapshot_hash=existing.input_snapshot_hash,
                    status=existing.status,
                    output=None,
                    lineage_reused=False,
                    progress=self._progress_from_row(existing),
                )

            if existing.status == BusinessIdeaValidationRunStatus.SUCCEEDED and existing.result_json:
                user_request = await self._user_requests.get_for_owner(owner_id, user_request_id)
                output = await self._enrich_output(
                    BusinessIdeaValidationOutput.model_validate(existing.result_json),
                    owner_id=owner_id,
                    user_request_id=user_request_id,
                    analysis_context_id=existing.analysis_context_id,
                    fallback_idea=user_request.text if user_request else "",
                )
                await self._maybe_persist_enriched(existing, output)
                return BusinessIdeaValidationRunResponse(
                    run_id=existing.id,
                    user_request_id=user_request_id,
                    project_id=existing.project_id,
                    analysis_context_id=existing.analysis_context_id,
                    input_snapshot_hash=existing.input_snapshot_hash,
                    status=existing.status,
                    output=output,
                    lineage_reused=True,
                )

        user_request = await self._user_requests.get_for_owner(owner_id, user_request_id)
        if user_request is None:
            raise NotFoundError("user_request_not_found")

        context_row = await self._analysis_contexts.get_for_run(
            owner_id,
            body.analysis_context_id,
            body.input_snapshot_hash,
        )
        context_project_id = context_row.project_id
        if user_request.project_id is None:
            user_request.project_id = context_project_id
            user_request.updated_at = utc_now()
            async with transactional(self._session):
                self._session.add(user_request)
                await self._session.flush()
        elif user_request.project_id != context_project_id:
            raise InvalidStateError("analysis_context_stale")

        bootstrap = await self._pipeline.bootstrap(owner_id, user_request_id)
        project_id = bootstrap.run.project_id

        context_row = await self._analysis_contexts.assert_runnable(
            owner_id,
            project_id,
            body.analysis_context_id,
            body.input_snapshot_hash,
        )
        await self._analysis_contexts.mark_analysis_requested(context_row)

        context_fields = self._analysis_contexts.build_biv_input_from_context(context_row)
        skill_input = BusinessIdeaValidationInput(
            tenant_id=owner_id,
            project_id=project_id,
            user_request_id=user_request_id,
            idea=sanitize_text(body.idea or context_fields["idea"] or user_request.text).strip(),
            market=body.market or context_fields["market"],
            location=body.location or context_fields["location"],
            target_audience=body.target_audience or context_fields["target_audience"],
            budget=body.budget or context_fields["budget"],
            constraints=body.constraints or context_fields["constraints"],
            product_or_service=context_fields.get("product_or_service"),
            pricing_or_revenue_model=context_fields.get("pricing_or_revenue_model"),
            known_competitors=context_fields.get("known_competitors"),
            analysis_goal=context_fields.get("analysis_goal"),
            current_stage=context_fields.get("current_stage"),
        )
        if len(skill_input.idea) < 8:
            raise InvalidStateError("idea_too_short")

        now = utc_now()
        correlation_id = uuid4().hex
        row = BusinessIdeaValidationRunTable(
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=user_request_id,
            project_id=project_id,
            investigation_id=bootstrap.run.investigation_id,
            analysis_context_id=context_row.id,
            input_snapshot_hash=body.input_snapshot_hash,
            idempotency_key=body.idempotency_key,
            status=BusinessIdeaValidationRunStatus.RUNNING,
            research_mode=research_mode.value,
            parent_run_id=body.parent_run_id,
            created_at=now,
            updated_at=now,
        )
        async with transactional(self._session):
            row = await self._runs.create(row)

        progress_tracker = PersistingBivRunProgressTracker(
            run_id=row.id,
            correlation_id=correlation_id,
            started_at=now,
            on_persist=lambda snap: self._persist_run_progress(row, snap),
        )
        await self._persist_run_progress(row, progress_tracker.snapshot())

        observability = BivRunObservabilityRecorder(
            run_id=row.id,
            correlation_id=correlation_id,
            project_id=project_id,
            user_request_id=user_request_id,
            research_mode=research_mode,
            parent_run_id=body.parent_run_id,
        )
        observability.record_transition("running", stage="started")

        await self._analysis_contexts.mark_analyzing(context_row)

        try:
            output = await BusinessIdeaValidationSkill(self._session, self._settings).run(
                skill_input,
                run_id=row.id,
                progress=progress_tracker,
                observability=observability,
            )
            output = output.model_copy(
                update={
                    "run_id": row.id,
                    "owner_id": owner_id,
                    "project_id": project_id,
                    "analysis_context_id": context_row.id,
                    "input_snapshot_hash": body.input_snapshot_hash,
                    "research_terminal_state": output.research_terminal_state,
                    "research_mode": research_mode,
                    "parent_run_id": body.parent_run_id,
                }
            )
            if is_partial_research_output(output):
                output = await self._persist_partial_research_failure(
                    row,
                    output,
                    progress_tracker=progress_tracker,
                    observability=observability,
                    context_row=context_row,
                )
                return BusinessIdeaValidationRunResponse(
                    run_id=row.id,
                    user_request_id=user_request_id,
                    project_id=project_id,
                    analysis_context_id=context_row.id,
                    input_snapshot_hash=body.input_snapshot_hash,
                    status=row.status,
                    research_mode=research_mode,
                    parent_run_id=body.parent_run_id,
                    output=output,
                    error_code=row.error_code,
                    safe_message=row.safe_error_message,
                    progress=self._progress_from_row(row),
                )
            output = await self._enrich_output(
                output,
                owner_id=owner_id,
                user_request_id=user_request_id,
                analysis_context_id=context_row.id,
                fallback_idea=user_request.text,
            )
            row.status = BusinessIdeaValidationRunStatus.SUCCEEDED
            row.result_json = output.model_dump(mode="json")
            row.business_verdict_id = output.business_verdict_id
            row.investigation_id = output.investigation_id
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.error_code = None
            row.safe_error_message = None
            row.progress_json = (
                output.run_progress or progress_tracker.snapshot()
            ).model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")

            user_request.skill_inputs = {
                **dict(user_request.skill_inputs or {}),
                "business_idea_validation_run_id": str(row.id),
                "business_idea_validation": output.model_dump(mode="json"),
                "analysis_context_id": str(context_row.id),
                "input_snapshot_hash": body.input_snapshot_hash,
            }
            user_request.skill_code = BusinessIdeaValidationSkill.SKILL_CODE
            user_request.skill_version = BusinessIdeaValidationSkill.SKILL_VERSION
            user_request.project_id = project_id
            user_request.updated_at = row.finished_at
            flag_modified(user_request, "skill_inputs")

            async with transactional(self._session):
                await self._runs.update(row)
                self._session.add(user_request)
                await self._session.flush()

            await self._analysis_contexts.mark_completed(context_row)

            return BusinessIdeaValidationRunResponse(
                run_id=row.id,
                user_request_id=user_request_id,
                project_id=project_id,
                analysis_context_id=context_row.id,
                input_snapshot_hash=body.input_snapshot_hash,
                status=row.status,
                research_mode=research_mode,
                parent_run_id=body.parent_run_id,
                output=output,
                progress=self._progress_from_row(row),
            )
        except ResearchPipelineError as exc:
            progress_tracker.mark_failed(
                safe_message=exc.safe_message,
                error_code=exc.failure_code,
            )
            observability.record_transition("failed", stage=exc.failure_stage)
            row.status = BusinessIdeaValidationRunStatus.FAILED
            row.error_code = exc.failure_code
            row.safe_error_message = exc.safe_message
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.progress_json = progress_tracker.snapshot().model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")
            async with transactional(self._session):
                await self._runs.update(row)
            return BusinessIdeaValidationRunResponse(
                run_id=row.id,
                user_request_id=user_request_id,
                project_id=project_id,
                analysis_context_id=context_row.id,
                input_snapshot_hash=body.input_snapshot_hash,
                status=row.status,
                research_mode=research_mode,
                parent_run_id=body.parent_run_id,
                output=None,
                error_code=exc.failure_code,
                safe_message=exc.safe_message,
                progress=self._progress_from_row(row),
            )
        except InvalidStateError as exc:
            error_code = str(exc)
            safe_message = self._commercial_safe_message(error_code)
            progress_tracker.mark_failed(safe_message=safe_message, error_code=error_code)
            observability.record_transition(
                "failed",
                stage=progress_tracker.snapshot().current_stage.value,
            )
            row.status = BusinessIdeaValidationRunStatus.FAILED
            row.error_code = error_code
            row.safe_error_message = safe_message
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.progress_json = progress_tracker.snapshot().model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")
            async with transactional(self._session):
                await self._runs.update(row)
            log.warning(
                "biv_run_lifecycle_failure",
                run_id=str(row.id),
                project_id=str(row.project_id),
                error_code=error_code,
            )
        except Exception:  # noqa: BLE001
            error_code = "research_internal_error"
            safe_message = self._commercial_safe_message(error_code)
            progress_tracker.mark_failed(safe_message=safe_message, error_code=error_code)
            observability.record_transition("failed", stage=progress_tracker.snapshot().current_stage.value)
            row.status = BusinessIdeaValidationRunStatus.FAILED
            row.error_code = error_code
            row.safe_error_message = safe_message
            row.finished_at = utc_now()
            row.updated_at = row.finished_at
            row.progress_json = progress_tracker.snapshot().model_dump(mode="json")
            row.observability_json = observability.snapshot().model_dump(mode="json")
            async with transactional(self._session):
                await self._runs.update(row)
            raise

    async def get_latest(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> BusinessIdeaValidationRunResponse | None:
        row = await self._runs.get_latest_for_user_request(owner_id, user_request_id)
        if row is None:
            return None
        output = None
        if row.result_json:
            user_request = await self._user_requests.get_for_owner(owner_id, user_request_id)
            output = await self._enrich_output(
                BusinessIdeaValidationOutput.model_validate(row.result_json),
                owner_id=owner_id,
                user_request_id=user_request_id,
                analysis_context_id=row.analysis_context_id,
                fallback_idea=user_request.text if user_request else "",
            )
            await self._maybe_persist_enriched(row, output)
        return BusinessIdeaValidationRunResponse(
            run_id=row.id,
            user_request_id=user_request_id,
            project_id=row.project_id,
            analysis_context_id=row.analysis_context_id,
            input_snapshot_hash=row.input_snapshot_hash,
            status=row.status,
            output=output,
            error_code=row.error_code,
            safe_message=row.safe_error_message,
            progress=self._progress_from_row(row),
        )

    async def get_project_hydration(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        analysis_context_id: UUID | None = None,
        input_snapshot_hash: str | None = None,
    ) -> BusinessIdeaValidationProjectHydration | None:
        if analysis_context_id is not None and input_snapshot_hash:
            row = await self._runs.get_latest_succeeded_for_context(
                owner_id,
                project_id,
                analysis_context_id,
                input_snapshot_hash,
            )
            if row is None:
                row = await self._runs.get_latest_partial_for_context(
                    owner_id,
                    project_id,
                    analysis_context_id,
                    input_snapshot_hash,
                )
        else:
            row = await self._runs.get_latest_succeeded_for_project(owner_id, project_id)
            if row is None:
                row = await self._runs.get_latest_partial_for_project(owner_id, project_id)
        if row is None or not row.result_json:
            return None
        user_request = await self._user_requests.get_for_owner(owner_id, row.user_request_id)
        if user_request is None:
            return None
        output = await self._enrich_output(
            BusinessIdeaValidationOutput.model_validate(row.result_json),
            owner_id=owner_id,
            user_request_id=row.user_request_id,
            analysis_context_id=row.analysis_context_id,
            fallback_idea=user_request.text,
        )
        await self._maybe_persist_enriched(row, output)
        if (
            analysis_context_id is not None
            and input_snapshot_hash
            and (
                output.analysis_context_id != analysis_context_id
                or output.input_snapshot_hash != input_snapshot_hash
            )
        ):
            return None
        return BusinessIdeaValidationProjectHydration(
            project_id=project_id,
            user_request_id=row.user_request_id,
            user_request_text=user_request.text,
            run_id=row.id,
            analysis_context_id=row.analysis_context_id,
            input_snapshot_hash=row.input_snapshot_hash,
            status=row.status,
            output=output,
            updated_at=row.updated_at,
        )

    def _build_latest_run_summary(
        self,
        row: BusinessIdeaValidationRunTable,
        *,
        project_id: UUID,
    ) -> BusinessIdeaValidationProjectLatestRunSummary:
        progress = self._progress_from_row(row)
        result_json = row.result_json or {}
        has_output = row.result_json is not None and bool(row.result_json)
        result_kind = result_json.get("result_kind") if has_output else None
        terminal_raw = result_json.get("research_terminal_state") if has_output else None
        research_terminal_state = (
            BivResearchTerminalState(terminal_raw) if terminal_raw else None
        )
        active_statuses = {
            BusinessIdeaValidationRunStatus.QUEUED,
            BusinessIdeaValidationRunStatus.RUNNING,
        }
        retry_allowed = row.status not in active_statuses
        started_at = progress.started_at if progress is not None else row.created_at
        return BusinessIdeaValidationProjectLatestRunSummary(
            project_id=project_id,
            run_id=row.id,
            user_request_id=row.user_request_id,
            status=row.status,
            created_at=row.created_at,
            started_at=started_at,
            finished_at=row.finished_at,
            progress=progress,
            result_kind=result_kind,
            research_terminal_state=research_terminal_state,
            safe_error_code=row.error_code,
            safe_message=row.safe_error_message,
            has_output=has_output,
            retry_allowed=retry_allowed,
            analysis_context_id=row.analysis_context_id,
            input_snapshot_hash=row.input_snapshot_hash,
        )

    async def get_project_latest_run(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationProjectLatestRunSummary | None:
        active = await self._runs.get_active_for_project(owner_id, project_id)
        row = active
        if row is None:
            row = await self._runs.get_latest_for_project(owner_id, project_id)
        if row is None:
            return None
        return self._build_latest_run_summary(row, project_id=project_id)

    @staticmethod
    def is_research_terminal(output: BusinessIdeaValidationOutput | None) -> bool:
        if output is None:
            return False
        return output.research_terminal_state in {
            BivResearchTerminalState.SUCCEEDED_COMPLETE,
            BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
            BivResearchTerminalState.FAILED,
        }
