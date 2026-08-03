"""CWF.1a — Launch Pack decision and request service."""

from __future__ import annotations

import contextlib
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial_workflow.decision_branch import (
    build_decision_branch,
    launch_pack_allowed_for_action,
)
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.commercial_next_step_decision import CommercialNextStepDecisionTable
from app.db.models.launch_pack_request import LaunchPackRequestTable
from app.db.repositories.commercial_next_step_decisions import CommercialNextStepDecisionRepository
from app.db.repositories.launch_pack_requests import LaunchPackRequestRepository
from app.product.offer_builder.service import OfferBuilderService
from app.schemas.contracts import (
    CommercialNextStepAction,
    CommercialNextStepDecision,
    CommercialNextStepDecisionCreate,
    CommercialNextStepSubmitResponse,
    LaunchPackJourneyHydration,
    LaunchPackOfferWorkflowStatus,
    LaunchPackRequest,
    LaunchPackRequestStatus,
    OfferArtifactDetail,
    OfferGenerateRequest,
)
from app.services.business_idea_validation_service import BusinessIdeaValidationService
from app.services.transaction import transactional


class LaunchPackService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._decisions = CommercialNextStepDecisionRepository(session)
        self._launch_packs = LaunchPackRequestRepository(session)
        self._biv = BusinessIdeaValidationService(session, settings)

    async def get_journey(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> LaunchPackJourneyHydration | None:
        validation = await self._biv.get_project_hydration(owner_id, project_id)
        if validation is None:
            return None

        branch = build_decision_branch(validation.output)
        verdict_id = validation.output.business_verdict_id
        decision_row = None
        launch_row = None
        offer_detail = None
        if verdict_id is not None:
            decision_row = await self._decisions.get_latest_for_verdict(owner_id, verdict_id)
            launch_row = await self._launch_packs.get_for_verdict(owner_id, verdict_id)
            if launch_row:
                offer_svc = OfferBuilderService(self._session, self._settings)
                offer_detail = await offer_svc.get_offer_for_launch_pack(owner_id, launch_row.id)

        updated_at = validation.updated_at
        if launch_row is not None and launch_row.updated_at > updated_at:
            updated_at = launch_row.updated_at
        elif decision_row is not None and decision_row.updated_at > updated_at:
            updated_at = decision_row.updated_at

        return LaunchPackJourneyHydration(
            project_id=project_id,
            user_request_id=validation.user_request_id,
            user_request_text=validation.user_request_text,
            validation=validation,
            decision_branch=branch,
            next_step_decision=self._map_decision(decision_row) if decision_row else None,
            launch_pack_request=(
                self._map_launch_pack(launch_row, offer_detail) if launch_row else None
            ),
            offer=offer_detail,
            updated_at=updated_at,
        )

    async def submit_next_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: CommercialNextStepDecisionCreate,
    ) -> CommercialNextStepSubmitResponse:
        if not body.idempotency_key.strip():
            raise InvalidStateError("idempotency_key_required")

        existing = await self._decisions.get_by_idempotency_key(owner_id, body.idempotency_key)
        offer_detail = None
        if existing is not None:
            validation = await self._require_validation(owner_id, project_id)
            branch = build_decision_branch(validation.output)
            launch_row = await self._launch_packs.get_for_verdict(
                owner_id,
                existing.business_verdict_id,
            )
            if launch_row:
                offer_svc = OfferBuilderService(self._session, self._settings)
                offer_detail = await offer_svc.get_offer_for_launch_pack(owner_id, launch_row.id)
            return CommercialNextStepSubmitResponse(
                decision=self._map_decision(existing),
                launch_pack_request=(
                self._map_launch_pack(launch_row, offer_detail) if launch_row else None
            ),
                offer=offer_detail,
                decision_branch=branch,
                lineage_reused=True,
            )

        validation = await self._require_validation(owner_id, project_id)
        output = validation.output
        verdict_id = output.business_verdict_id
        if verdict_id is None:
            raise InvalidStateError("business_verdict_missing")

        existing_launch = await self._launch_packs.get_for_verdict(owner_id, verdict_id)
        if (
            body.selected_action == CommercialNextStepAction.PREPARE_LAUNCH
            and existing_launch is not None
            and existing_launch.status == LaunchPackRequestStatus.REQUESTED
        ):
            decision_row = await self._decisions.get_latest_for_verdict(owner_id, verdict_id)
            branch = build_decision_branch(output)
            if decision_row is None:
                raise InvalidStateError("launch_pack_already_requested")
            return CommercialNextStepSubmitResponse(
                decision=self._map_decision(decision_row),
                launch_pack_request=self._map_launch_pack(existing_launch, None),
                decision_branch=branch,
                lineage_reused=True,
            )

        branch = build_decision_branch(output)
        accepted = [sanitize_text(c).strip() for c in body.accepted_conditions if c.strip()]
        override = sanitize_text(body.override_reason).strip() if body.override_reason else None

        self._validate_action(branch, body.selected_action, accepted, override)

        now = utc_now()
        decision_row = CommercialNextStepDecisionTable(
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project_id,
            user_request_id=validation.user_request_id,
            business_verdict_id=verdict_id,
            selected_action=body.selected_action,
            accepted_conditions=accepted,
            override_reason=override or None,
            idempotency_key=body.idempotency_key,
            created_at=now,
            updated_at=now,
        )

        launch_payload: dict | None = None
        if body.selected_action == CommercialNextStepAction.PREPARE_LAUNCH:
            allowed = launch_pack_allowed_for_action(
                branch,
                body.selected_action,
                accepted_conditions=accepted,
                override_reason=override,
            )
            launch_payload = {
                "status": (
                    LaunchPackRequestStatus.REQUESTED
                    if allowed
                    else LaunchPackRequestStatus.BLOCKED
                ),
                "offer_workflow_status": (
                    LaunchPackOfferWorkflowStatus.REQUESTED.value
                    if allowed
                    else LaunchPackOfferWorkflowStatus.BLOCKED_BY_VERDICT.value
                ),
                "selected_next_step": body.selected_action,
                "accepted_conditions": accepted,
                "source_verdict_type": output.verdict,
                "source_confidence": output.confidence.total_score,
            }
        elif (
            body.selected_action == CommercialNextStepAction.STOP_PROJECT
            and existing_launch is None
        ):
            launch_payload = {
                "status": LaunchPackRequestStatus.CANCELLED,
                "selected_next_step": body.selected_action,
                "accepted_conditions": accepted,
                "source_verdict_type": output.verdict,
                "source_confidence": output.confidence.total_score,
            }

        async with transactional(self._session):
            decision_row = await self._decisions.create(decision_row)
            launch_row = None
            if launch_payload is not None:
                launch_row = LaunchPackRequestTable(
                    owner_id=owner_id,
                    tenant_id=owner_id,
                    project_id=project_id,
                    user_request_id=validation.user_request_id,
                    business_verdict_id=verdict_id,
                    next_step_decision_id=decision_row.id,
                    created_at=now,
                    updated_at=now,
                    **launch_payload,
                )
                launch_row = await self._launch_packs.create(launch_row)
                if launch_row.status == LaunchPackRequestStatus.REQUESTED:
                    offer_svc = OfferBuilderService(self._session, self._settings)
                    idem = f"offer-{launch_row.id}-{body.idempotency_key}"
                    await offer_svc.generate_for_launch_pack(
                        owner_id,
                        project_id,
                        launch_row.id,
                        OfferGenerateRequest(idempotency_key=idem),
                    )
                    launch_row = await self._launch_packs.get_by_id(owner_id, launch_row.id)

        offer_detail = None
        if launch_row is not None:
            offer_svc = OfferBuilderService(self._session, self._settings)
            offer_detail = await offer_svc.get_offer_for_launch_pack(owner_id, launch_row.id)

        return CommercialNextStepSubmitResponse(
            decision=self._map_decision(decision_row),
            launch_pack_request=(
                self._map_launch_pack(launch_row, offer_detail) if launch_row else None
            ),
            offer=offer_detail,
            decision_branch=branch,
        )

    async def _require_validation(self, owner_id: UUID, project_id: UUID):
        validation = await self._biv.get_project_hydration(owner_id, project_id)
        if validation is None:
            raise NotFoundError("validation_not_found")
        return validation

    def _validate_action(
        self,
        branch,
        action: CommercialNextStepAction,
        accepted: list[str],
        override: str | None,
    ) -> None:
        allowed_actions = {branch.primary_cta.action if branch.primary_cta else None}
        allowed_actions.update(cta.action for cta in branch.secondary_ctas)
        allowed_actions.discard(None)
        if action not in allowed_actions:
            raise InvalidStateError("action_not_allowed_for_verdict")

        if action == CommercialNextStepAction.PREPARE_LAUNCH:
            if not branch.launch_pack_allowed and not override:
                raise InvalidStateError("launch_pack_not_allowed")
            if (
                branch.verdict.value == "proceed_with_conditions"
                and branch.conditions
                and (not accepted or not all(c in accepted for c in branch.conditions))
            ):
                raise InvalidStateError("conditions_required")
            if branch.verdict.value == "revise" and not override:
                raise InvalidStateError("risk_override_required")

    @staticmethod
    def _map_decision(row: CommercialNextStepDecisionTable) -> CommercialNextStepDecision:
        return CommercialNextStepDecision(
            id=row.id,
            tenant_id=row.tenant_id,
            project_id=row.project_id,
            user_request_id=row.user_request_id,
            business_verdict_id=row.business_verdict_id,
            selected_action=row.selected_action,
            accepted_conditions=list(row.accepted_conditions or []),
            override_reason=row.override_reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _map_launch_pack(
        row: LaunchPackRequestTable,
        offer: OfferArtifactDetail | None = None,
    ) -> LaunchPackRequest:
        from app.schemas.contracts import OfferArtifactStatus

        workflow = LaunchPackOfferWorkflowStatus.NOT_STARTED
        with contextlib.suppress(ValueError):
            workflow = LaunchPackOfferWorkflowStatus(row.offer_workflow_status)
        next_action = None
        if workflow == LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED:
            next_action = "review_offer"
        elif workflow in {
            LaunchPackOfferWorkflowStatus.REQUESTED,
            LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
        }:
            next_action = "build_offer"
        elif workflow == LaunchPackOfferWorkflowStatus.OFFER_APPROVED:
            next_action = "continue_launch_pack"
        elif workflow == LaunchPackOfferWorkflowStatus.REVISION_REQUIRED:
            next_action = "review_offer"
        offer_status: OfferArtifactStatus | None = offer.status if offer else None
        offer_version = offer.version_number if offer else None
        return LaunchPackRequest(
            id=row.id,
            tenant_id=row.tenant_id,
            project_id=row.project_id,
            user_request_id=row.user_request_id,
            business_verdict_id=row.business_verdict_id,
            next_step_decision_id=row.next_step_decision_id,
            status=row.status,
            selected_next_step=row.selected_next_step,
            accepted_conditions=list(row.accepted_conditions or []),
            source_verdict_type=row.source_verdict_type,
            source_confidence=row.source_confidence,
            offer_workflow_status=workflow,
            offer_artifact_id=row.offer_artifact_id,
            offer_version=offer_version,
            offer_status=offer_status,
            blocker_codes=list(row.blocker_codes or []),
            next_allowed_action=next_action,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
