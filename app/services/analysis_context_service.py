"""PRODUCT-01.3A — analysis context intake gate service."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_idea_validation.analysis_context_gate import (
    compute_input_snapshot_hash,
    evaluate_specificity,
    is_specificity_sufficient,
)
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.analysis_context import AnalysisContextTable
from app.db.models.project import ProjectTable
from app.db.repositories.analysis_contexts import AnalysisContextRepository
from app.db.repositories.business_idea_validation_runs import BusinessIdeaValidationRunRepository
from app.db.repositories.project_briefs import ProjectBriefRepository
from app.schemas.contracts import (
    AnalysisContextConfirmRequest,
    AnalysisContextCreateDraftRequest,
    AnalysisContextCurrentResponse,
    AnalysisContextDataSourceLabel,
    AnalysisContextEditRequest,
    AnalysisContextFields,
    AnalysisContextRecord,
    AnalysisContextSourceMode,
    AnalysisContextStartNewResponse,
    AnalysisContextState,
    BusinessIdeaValidationRunStatus,
)
from app.schemas.crud import ProjectCreate
from app.services.projects_service import ProjectService
from app.services.transaction import transactional
from app.services.user_requests_service import UserRequestService


class AnalysisContextService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._contexts = AnalysisContextRepository(session)
        self._projects = ProjectService(session)
        self._briefs = ProjectBriefRepository(session)
        self._biv_runs = BusinessIdeaValidationRunRepository(session)
        self._user_requests = UserRequestService(session)

    def _fields_from_row(self, row: AnalysisContextTable) -> AnalysisContextFields:
        return AnalysisContextFields(
            idea_description=row.idea_description,
            product_or_service=row.product_or_service,
            target_customer=row.target_customer,
            geography=row.geography,
            business_model=row.business_model,
            pricing_or_revenue_model=row.pricing_or_revenue_model,
            current_stage=row.current_stage,
            budget_context=row.budget_context,
            known_competitors=row.known_competitors,
            analysis_goal=row.analysis_goal,
            target_customer_unknown=row.target_customer_unknown,
            geography_unknown=row.geography_unknown,
        )

    def _to_record(self, row: AnalysisContextTable) -> AnalysisContextRecord:
        fields = self._fields_from_row(row)
        missing, warnings = evaluate_specificity(fields)
        return AnalysisContextRecord(
            context_id=row.id,
            owner_id=row.owner_id,
            project_id=row.project_id,
            state=row.state,
            source_mode=row.source_mode,
            data_source_label=row.data_source_label,
            idea_description=row.idea_description,
            product_or_service=row.product_or_service,
            target_customer=row.target_customer,
            geography=row.geography,
            business_model=row.business_model,
            pricing_or_revenue_model=row.pricing_or_revenue_model,
            current_stage=row.current_stage,
            budget_context=row.budget_context,
            known_competitors=row.known_competitors,
            analysis_goal=row.analysis_goal,
            target_customer_unknown=row.target_customer_unknown,
            geography_unknown=row.geography_unknown,
            confirmed_by_user=row.confirmed_by_user,
            confirmed_at=row.confirmed_at,
            input_snapshot_hash=row.input_snapshot_hash,
            source_snapshot_id=row.source_snapshot_id,
            is_active=row.is_active,
            missing_fields=missing,
            warnings=warnings,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _assert_project_owner(self, owner_id: UUID, project_id: UUID) -> ProjectTable:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            raise NotFoundError("project_not_found")
        return project

    async def _hydrate_from_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> AnalysisContextTable:
        now = utc_now()
        idea = ""
        product = None
        target = None
        geo = None
        business_model = None
        data_label = AnalysisContextDataSourceLabel.SAVED_PROJECT

        brief = await self._briefs.get_latest_any(owner_id, project_id)
        if brief is not None and brief.content:
            basics = brief.content.get("project_basics") or {}
            idea = sanitize_text(str(basics.get("idea_description") or "")).strip()
            product = basics.get("product_or_service")
            target = basics.get("target_audience") or basics.get("target_customer")
            geo = basics.get("geography") or basics.get("market")
            business_model = basics.get("business_model")

        biv_row = await self._biv_runs.get_latest_succeeded_for_project(owner_id, project_id)
        if biv_row is not None:
            user_request = await self._user_requests.get_for_owner(
                owner_id,
                biv_row.user_request_id,
            )
            if user_request is not None and user_request.text:
                if not idea:
                    idea = sanitize_text(user_request.text).strip()
                data_label = AnalysisContextDataSourceLabel.PREVIOUS_SESSION

        fields = AnalysisContextFields(
            idea_description=idea,
            product_or_service=product,
            target_customer=target,
            geography=geo,
            business_model=business_model,
            analysis_goal="Проверить жизнеспособность бизнес-идеи",
        )
        snapshot_hash = compute_input_snapshot_hash(fields)

        row = AnalysisContextTable(
            id=uuid4(),
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project_id,
            state=AnalysisContextState.HYDRATED_UNCONFIRMED,
            source_mode=AnalysisContextSourceMode.RESTORED_PROJECT_CONTEXT,
            data_source_label=data_label,
            idea_description=fields.idea_description,
            product_or_service=fields.product_or_service,
            target_customer=fields.target_customer,
            geography=fields.geography,
            business_model=fields.business_model,
            analysis_goal=fields.analysis_goal,
            confirmed_by_user=False,
            input_snapshot_hash=snapshot_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        async with transactional(self._session):
            await self._contexts.deactivate_project_contexts(owner_id, project_id)
            return await self._contexts.create(row)

    async def get_current(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        auto_hydrate: bool = True,
    ) -> AnalysisContextCurrentResponse:
        await self._assert_project_owner(owner_id, project_id)
        row = await self._contexts.get_active_for_project(owner_id, project_id)
        if row is None and auto_hydrate:
            brief = await self._briefs.get_latest_any(owner_id, project_id)
            biv_row = await self._biv_runs.get_latest_succeeded_for_project(owner_id, project_id)
            if brief is not None or biv_row is not None:
                row = await self._hydrate_from_project(owner_id, project_id)

        completed_run_id = None
        has_completed = False
        if row is not None and row.input_snapshot_hash:
            biv_row = await self._biv_runs.get_latest_succeeded_for_project(owner_id, project_id)
            if (
                biv_row is not None
                and biv_row.input_snapshot_hash == row.input_snapshot_hash
                and biv_row.status == BusinessIdeaValidationRunStatus.SUCCEEDED
            ):
                has_completed = True
                completed_run_id = biv_row.id
                if row.state == AnalysisContextState.CONFIRMED:
                    row.state = AnalysisContextState.COMPLETED
                    row.updated_at = utc_now()
                    async with transactional(self._session):
                        row = await self._contexts.update(row)

        return AnalysisContextCurrentResponse(
            project_id=project_id,
            context=self._to_record(row) if row else None,
            has_completed_analysis=has_completed,
            completed_run_id=completed_run_id,
        )

    async def create_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: AnalysisContextCreateDraftRequest,
    ) -> AnalysisContextRecord:
        await self._assert_project_owner(owner_id, project_id)
        now = utc_now()
        fields = AnalysisContextFields.model_validate(body.model_dump())
        fields.idea_description = sanitize_text(fields.idea_description).strip()
        snapshot_hash = compute_input_snapshot_hash(fields)
        missing, _ = evaluate_specificity(fields)
        state = (
            AnalysisContextState.DRAFT_ENTERED
            if fields.idea_description
            else AnalysisContextState.EMPTY
        )
        if missing and fields.idea_description:
            state = AnalysisContextState.DRAFT_ENTERED

        existing = await self._contexts.get_active_for_project(owner_id, project_id)
        if existing is not None and existing.state in {
            AnalysisContextState.HYDRATED_UNCONFIRMED,
            AnalysisContextState.DRAFT_ENTERED,
            AnalysisContextState.EMPTY,
            AnalysisContextState.EDITING,
        }:
            row = existing
            row.idea_description = fields.idea_description
            row.product_or_service = fields.product_or_service
            row.target_customer = fields.target_customer
            row.geography = fields.geography
            row.business_model = fields.business_model
            row.pricing_or_revenue_model = fields.pricing_or_revenue_model
            row.current_stage = fields.current_stage
            row.budget_context = fields.budget_context
            row.known_competitors = fields.known_competitors
            row.analysis_goal = fields.analysis_goal
            row.target_customer_unknown = fields.target_customer_unknown
            row.geography_unknown = fields.geography_unknown
            row.state = state
            row.confirmed_by_user = False
            row.confirmed_at = None
            row.input_snapshot_hash = snapshot_hash
            row.source_mode = AnalysisContextSourceMode.NEW_USER_INPUT
            row.updated_at = now
            async with transactional(self._session):
                row = await self._contexts.update(row)
            return self._to_record(row)

        row = AnalysisContextTable(
            id=uuid4(),
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project_id,
            state=state,
            source_mode=AnalysisContextSourceMode.NEW_USER_INPUT,
            idea_description=fields.idea_description,
            product_or_service=fields.product_or_service,
            target_customer=fields.target_customer,
            geography=fields.geography,
            business_model=fields.business_model,
            pricing_or_revenue_model=fields.pricing_or_revenue_model,
            current_stage=fields.current_stage,
            budget_context=fields.budget_context,
            known_competitors=fields.known_competitors,
            analysis_goal=fields.analysis_goal,
            target_customer_unknown=fields.target_customer_unknown,
            geography_unknown=fields.geography_unknown,
            confirmed_by_user=False,
            input_snapshot_hash=snapshot_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        async with transactional(self._session):
            await self._contexts.deactivate_project_contexts(owner_id, project_id)
            row = await self._contexts.create(row)
        return self._to_record(row)

    async def confirm(
        self,
        owner_id: UUID,
        project_id: UUID,
        context_id: UUID,
        body: AnalysisContextConfirmRequest,
    ) -> AnalysisContextRecord:
        await self._assert_project_owner(owner_id, project_id)
        row = await self._contexts.get_by_id(owner_id, context_id)
        if row is None or row.project_id != project_id:
            raise NotFoundError("analysis_context_not_found")

        if row.state not in {
            AnalysisContextState.DRAFT_ENTERED,
            AnalysisContextState.HYDRATED_UNCONFIRMED,
            AnalysisContextState.EDITING,
            AnalysisContextState.CONFIRMED,
        }:
            raise InvalidStateError("invalid_analysis_context_state")

        fields = self._fields_from_row(row)
        missing, _ = evaluate_specificity(fields)
        if missing:
            row.state = AnalysisContextState.BLOCKED
            row.updated_at = utc_now()
            async with transactional(self._session):
                row = await self._contexts.update(row)
            raise InvalidStateError("analysis_context_incomplete")

        snapshot_hash = compute_input_snapshot_hash(fields)
        if body.input_snapshot_hash and body.input_snapshot_hash != snapshot_hash:
            raise InvalidStateError("analysis_context_stale")

        if (
            row.confirmed_by_user
            and row.input_snapshot_hash == snapshot_hash
            and row.state == AnalysisContextState.CONFIRMED
        ):
            return self._to_record(row)

        now = utc_now()
        row.confirmed_by_user = True
        row.confirmed_at = now
        row.input_snapshot_hash = snapshot_hash
        row.state = AnalysisContextState.CONFIRMED
        row.updated_at = now
        async with transactional(self._session):
            row = await self._contexts.update(row)
        return self._to_record(row)

    async def edit(
        self,
        owner_id: UUID,
        project_id: UUID,
        context_id: UUID,
        body: AnalysisContextEditRequest,
    ) -> AnalysisContextRecord:
        await self._assert_project_owner(owner_id, project_id)
        row = await self._contexts.get_by_id(owner_id, context_id)
        if row is None or row.project_id != project_id:
            raise NotFoundError("analysis_context_not_found")

        source_id = row.id if row.confirmed_by_user else row.source_snapshot_id
        fields = AnalysisContextFields.model_validate(body.model_dump())
        fields.idea_description = sanitize_text(fields.idea_description).strip()
        now = utc_now()
        snapshot_hash = compute_input_snapshot_hash(fields)

        row.source_snapshot_id = source_id
        row.idea_description = fields.idea_description
        row.product_or_service = fields.product_or_service
        row.target_customer = fields.target_customer
        row.geography = fields.geography
        row.business_model = fields.business_model
        row.pricing_or_revenue_model = fields.pricing_or_revenue_model
        row.current_stage = fields.current_stage
        row.budget_context = fields.budget_context
        row.known_competitors = fields.known_competitors
        row.analysis_goal = fields.analysis_goal
        row.target_customer_unknown = fields.target_customer_unknown
        row.geography_unknown = fields.geography_unknown
        row.confirmed_by_user = False
        row.confirmed_at = None
        row.input_snapshot_hash = snapshot_hash
        row.state = AnalysisContextState.EDITING
        row.source_mode = AnalysisContextSourceMode.EDITED_RESTORED_CONTEXT
        row.updated_at = now
        async with transactional(self._session):
            row = await self._contexts.update(row)
        return self._to_record(row)

    async def start_new(
        self,
        owner_id: UUID,
        project_id: UUID | None = None,
    ) -> AnalysisContextStartNewResponse:
        now = utc_now()
        if project_id is not None:
            await self._assert_project_owner(owner_id, project_id)
            async with transactional(self._session):
                await self._contexts.deactivate_project_contexts(owner_id, project_id)

        project = await self._projects.create(
            ProjectCreate(
                owner_id=owner_id,
                name="Новый проект",
                description=None,
            ),
        )
        row = AnalysisContextTable(
            id=uuid4(),
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project.id,
            state=AnalysisContextState.EMPTY,
            source_mode=AnalysisContextSourceMode.NEW_USER_INPUT,
            confirmed_by_user=False,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        async with transactional(self._session):
            row = await self._contexts.create(row)
        return AnalysisContextStartNewResponse(
            project_id=project.id,
            context=self._to_record(row),
        )

    async def get_for_run(
        self,
        owner_id: UUID,
        context_id: UUID,
        input_snapshot_hash: str,
    ) -> AnalysisContextTable:
        row = await self._contexts.get_by_id(owner_id, context_id)
        if row is None:
            raise NotFoundError("analysis_context_not_found")
        if row.input_snapshot_hash != input_snapshot_hash:
            raise InvalidStateError("analysis_context_stale")
        if not row.confirmed_by_user:
            if row.state == AnalysisContextState.HYDRATED_UNCONFIRMED:
                raise InvalidStateError("hydrated_context_confirmation_required")
            raise InvalidStateError("analysis_context_required")
        return row

    async def assert_runnable(
        self,
        owner_id: UUID,
        project_id: UUID,
        context_id: UUID,
        input_snapshot_hash: str,
    ) -> AnalysisContextTable:
        row = await self._contexts.get_by_id(owner_id, context_id)
        if row is None or row.project_id != project_id:
            raise NotFoundError("analysis_context_not_found")

        if not row.confirmed_by_user:
            if row.state == AnalysisContextState.HYDRATED_UNCONFIRMED:
                raise InvalidStateError("hydrated_context_confirmation_required")
            raise InvalidStateError("analysis_context_required")

        if row.input_snapshot_hash != input_snapshot_hash:
            raise InvalidStateError("analysis_context_stale")

        fields = self._fields_from_row(row)
        if not is_specificity_sufficient(fields):
            raise InvalidStateError("analysis_context_incomplete")

        if row.state not in {
            AnalysisContextState.CONFIRMED,
            AnalysisContextState.COMPLETED,
        }:
            raise InvalidStateError("invalid_analysis_context_state")

        return row

    async def mark_analysis_requested(
        self,
        row: AnalysisContextTable,
    ) -> AnalysisContextTable:
        row.state = AnalysisContextState.ANALYSIS_REQUESTED
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._contexts.update(row)

    async def mark_analyzing(self, row: AnalysisContextTable) -> AnalysisContextTable:
        row.state = AnalysisContextState.ANALYZING
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._contexts.update(row)

    async def mark_completed(self, row: AnalysisContextTable) -> AnalysisContextTable:
        row.state = AnalysisContextState.COMPLETED
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._contexts.update(row)

    async def mark_rerun_ready(self, row: AnalysisContextTable) -> AnalysisContextTable:
        """RUNTIME-01D — terminal partial/failed research must allow explicit rerun."""
        if row.state == AnalysisContextState.ANALYZING and row.confirmed_by_user:
            row.state = AnalysisContextState.CONFIRMED
            row.updated_at = utc_now()
            async with transactional(self._session):
                return await self._contexts.update(row)
        return row

    def build_biv_input_from_context(self, row: AnalysisContextTable) -> dict[str, str | None]:
        return {
            "idea": row.idea_description,
            "market": row.business_model,
            "location": row.geography,
            "target_audience": row.target_customer,
            "budget": row.budget_context,
            "constraints": row.known_competitors,
            "product_or_service": row.product_or_service,
            "pricing_or_revenue_model": row.pricing_or_revenue_model,
            "known_competitors": row.known_competitors,
            "analysis_goal": row.analysis_goal,
            "current_stage": row.current_stage,
        }
