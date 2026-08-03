"""Controlled ImplementationPlan → MarketingPlan draft handoff (Commercial MVP P1.2).

Preview → explicit confirm → MarketingPlan draft only.
Never approves MarketingPlan, creates Agent Runs, Campaigns, or dispatches specialists.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.implementation_marketing_plan_handoff import (
    ImplementationMarketingPlanHandoffTable,
)
from app.db.repositories.implementation_marketing_plan_handoffs import (
    ImplementationMarketingPlanHandoffRepository,
)
from app.db.repositories.implementation_plans import ImplementationPlanRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.domain.implementation_marketing_plan_handoff_engine import (
    assert_plan_eligible_for_confirm,
    assert_plan_previewable,
    build_execution_plan_from_mapped,
    classify_and_map_tasks,
    compute_mapping_fingerprint,
    confirm_eligibility_blockers,
    mapped_payload_for_fingerprint,
)
from app.schemas.contracts import (
    HandoffExistingPlanPolicy,
    ImplementationMarketingPlanHandoffConfirmRequest,
    ImplementationMarketingPlanHandoffConfirmResponse,
    ImplementationMarketingPlanHandoffPreviewResponse,
    ImplementationMarketingPlanHandoffStatus,
    ImplementationPlanLifecycleStatus,
    MAPPING_VERSION_V1,
    MarketingPlanStatus,
)
from app.services.marketing_plan_service import MarketingPlanService
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class ImplementationMarketingPlanHandoffService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._plans = ImplementationPlanRepository(session)
        self._handoffs = ImplementationMarketingPlanHandoffRepository(session)
        self._marketing_plans = MarketingPlanRepository(session)
        self._mp_service = MarketingPlanService(session)

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _existing_plans_summary(
        self, owner_id: UUID, project_id: UUID
    ) -> list[dict[str, Any]]:
        rows = await self._marketing_plans.list_by_project(owner_id, project_id, limit=50)
        out: list[dict[str, Any]] = []
        for row in rows or []:
            out.append(
                {
                    "id": str(row.id),
                    "title": row.title,
                    "status": getattr(row.status, "value", str(row.status)),
                    "version": row.current_version_number,
                }
            )
        return out

    async def preview(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        *,
        actor_id: UUID,
    ) -> ImplementationMarketingPlanHandoffPreviewResponse | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        plan = await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)
        if plan is None:
            return None
        assert_plan_previewable(plan)

        (
            included,
            transformed,
            excluded,
            unsupported,
            blocked,
            role_notes,
            dep_warnings,
            ac_warnings,
            gate_blockers,
        ) = classify_and_map_tasks(plan)

        mapped_payload = mapped_payload_for_fingerprint(included, transformed)
        fingerprint = compute_mapping_fingerprint(
            plan_id=str(plan.id),
            plan_version=plan.version,
            mapping_version=MAPPING_VERSION_V1,
            policy=HandoffExistingPlanPolicy.CREATE_NEW_DRAFT.value,
            mapped_payload=mapped_payload,
        )

        completed = await self._handoffs.get_completed_by_fingerprint(
            owner_id, project_id, fingerprint
        )
        existing = await self._existing_plans_summary(owner_id, project_id)
        approved_existing = [
            p for p in existing if p["status"] == MarketingPlanStatus.APPROVED.value
        ]

        blockers = confirm_eligibility_blockers(
            plan,
            included_count=len(included) + len(transformed),
            blocked=blocked,
            gate_blockers=gate_blockers,
        )
        preview_eligible = (
            ImplementationPlanLifecycleStatus(plan.lifecycle_status)
            == ImplementationPlanLifecycleStatus.APPROVED
            and not blockers
        )

        warnings = list(dep_warnings) + list(ac_warnings) + list(gate_blockers)
        if approved_existing:
            warnings.append(
                "Approved MarketingPlan(s) exist — will never overwrite; create_new_draft only"
            )

        handoff_id = uuid4()
        payload = {
            "included": [i.model_dump(mode="json") for i in included],
            "transformed": [i.model_dump(mode="json") for i in transformed],
            "excluded": [i.model_dump(mode="json") for i in excluded],
            "unsupported": [i.model_dump(mode="json") for i in unsupported],
            "blocked": [i.model_dump(mode="json") for i in blocked],
            "proposed_title": (plan.title or "Marketing plan")[:512],
            "proposed_goal": (plan.summary or plan.title)[:4000],
            "generated_by": str(actor_id),
            "side_effects": [],
        }

        existing_preview = await self._handoffs.get_by_fingerprint_any(
            owner_id, project_id, fingerprint
        )
        if (
            existing_preview is not None
            and ImplementationMarketingPlanHandoffStatus(existing_preview.lifecycle_status)
            == ImplementationMarketingPlanHandoffStatus.PREVIEW
        ):
            handoff = existing_preview
            handoff.preview_payload = payload
            handoff.included_task_count = len(included) + len(transformed)
            handoff.excluded_task_count = len(excluded) + len(unsupported)
            handoff.blocked_task_count = len(blocked)
            handoff.warnings = warnings
            handoff.updated_at = utc_now()
            async with transactional(self._session):
                await self._handoffs.update(handoff)
        elif completed is not None:
            handoff = completed
        else:
            handoff = ImplementationMarketingPlanHandoffTable(
                id=handoff_id,
                owner_id=owner_id,
                project_id=project_id,
                implementation_plan_id=plan.id,
                implementation_plan_version=plan.version,
                marketing_strategy_id=plan.marketing_strategy_id,
                business_verdict_id=plan.business_verdict_id,
                source_snapshot_hash=plan.evidence_snapshot_hash,
                mapping_version=MAPPING_VERSION_V1,
                mapping_fingerprint=fingerprint,
                lifecycle_status=ImplementationMarketingPlanHandoffStatus.PREVIEW,
                preview_payload=payload,
                included_task_count=len(included) + len(transformed),
                excluded_task_count=len(excluded) + len(unsupported),
                blocked_task_count=len(blocked),
                warnings=warnings,
                metadata_json={
                    "creates_marketing_plan_approval": False,
                    "creates_agent_run": False,
                    "creates_campaign": False,
                    "dispatches_specialist_tasks": False,
                    "review_events": [
                        {
                            "action": "preview",
                            "actor_id": str(actor_id),
                            "at": utc_now().isoformat(),
                        }
                    ],
                },
            )
            async with transactional(self._session):
                await self._handoffs.create(handoff)

        return ImplementationMarketingPlanHandoffPreviewResponse(
            handoff_id=handoff.id,
            implementation_plan_id=plan.id,
            implementation_plan_version=plan.version,
            mapping_version=MAPPING_VERSION_V1,
            mapping_fingerprint=fingerprint,
            project_id=project_id,
            proposed_title=payload["proposed_title"],
            proposed_goal=payload["proposed_goal"],
            included_tasks=included,
            transformed_tasks=transformed,
            excluded_tasks=excluded,
            unsupported_tasks=unsupported,
            blocked_tasks=blocked,
            role_mapping_notes=role_notes,
            dependency_warnings=dep_warnings,
            acceptance_criteria_warnings=ac_warnings,
            gate_blockers=gate_blockers,
            existing_marketing_plans=existing,
            duplicate_handoff_id=completed.id if completed else None,
            eligible=preview_eligible,
            blockers=blockers,
            warnings=warnings,
            side_effects=[],
            creates_marketing_plan_draft=False,
            creates_marketing_plan_approval=False,
            creates_agent_run=False,
            creates_campaign=False,
            dispatches_specialist_tasks=False,
        )

    async def confirm(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        body: ImplementationMarketingPlanHandoffConfirmRequest,
        *,
        actor_id: UUID,
    ) -> ImplementationMarketingPlanHandoffConfirmResponse | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        if not body.explicit_confirmation:
            raise InvalidStateError("explicit_confirmation_required")
        if body.existing_plan_policy == HandoffExistingPlanPolicy.CANCEL:
            raise InvalidStateError("existing_marketing_plan_conflict")

        plan = await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)
        if plan is None:
            return None
        if int(plan.version) != int(body.expected_implementation_plan_version):
            raise InvalidStateError("stale_implementation_plan")

        assert_plan_eligible_for_confirm(plan)

        handoff = await self._handoffs.get_by_id_for_owner(
            body.handoff_preview_id, owner_id, project_id
        )
        if handoff is None:
            raise InvalidStateError("preview_stale")
        if handoff.implementation_plan_id != plan.id:
            raise InvalidStateError("preview_stale")
        if handoff.mapping_fingerprint != body.mapping_fingerprint:
            raise InvalidStateError("fingerprint_mismatch")
        if handoff.implementation_plan_version != plan.version:
            raise InvalidStateError("stale_implementation_plan")

        if ImplementationMarketingPlanHandoffStatus(handoff.lifecycle_status) == (
            ImplementationMarketingPlanHandoffStatus.COMPLETED
        ):
            if handoff.marketing_plan_id is None:
                raise InvalidStateError("ambiguous_create_result")
            return ImplementationMarketingPlanHandoffConfirmResponse(
                handoff_id=handoff.id,
                lifecycle_status=ImplementationMarketingPlanHandoffStatus.COMPLETED,
                marketing_plan_id=handoff.marketing_plan_id,
                marketing_plan_version=int(handoff.marketing_plan_version or 1),
                marketing_plan_status=MarketingPlanStatus.DRAFT,
                mapping_fingerprint=handoff.mapping_fingerprint,
                included_task_count=handoff.included_task_count,
                excluded_task_count=handoff.excluded_task_count,
                blocked_task_count=handoff.blocked_task_count,
                warnings=list(handoff.warnings or []),
                idempotent_replay=True,
            )

        if ImplementationMarketingPlanHandoffStatus(handoff.lifecycle_status) != (
            ImplementationMarketingPlanHandoffStatus.PREVIEW
        ):
            raise InvalidStateError("preview_stale")

        (
            included,
            transformed,
            _excluded,
            _unsupported,
            _blocked,
            *_rest,
        ) = classify_and_map_tasks(plan)
        mapped_payload = mapped_payload_for_fingerprint(included, transformed)
        fingerprint = compute_mapping_fingerprint(
            plan_id=str(plan.id),
            plan_version=plan.version,
            mapping_version=MAPPING_VERSION_V1,
            policy=body.existing_plan_policy.value,
            mapped_payload=mapped_payload,
        )
        if fingerprint != body.mapping_fingerprint:
            raise InvalidStateError("fingerprint_mismatch")

        prior = await self._handoffs.get_completed_by_fingerprint(
            owner_id, project_id, fingerprint
        )
        if prior is not None and prior.id != handoff.id and prior.marketing_plan_id:
            return ImplementationMarketingPlanHandoffConfirmResponse(
                handoff_id=prior.id,
                lifecycle_status=ImplementationMarketingPlanHandoffStatus.COMPLETED,
                marketing_plan_id=prior.marketing_plan_id,
                marketing_plan_version=int(prior.marketing_plan_version or 1),
                marketing_plan_status=MarketingPlanStatus.DRAFT,
                mapping_fingerprint=prior.mapping_fingerprint,
                included_task_count=prior.included_task_count,
                excluded_task_count=prior.excluded_task_count,
                blocked_task_count=prior.blocked_task_count,
                warnings=list(prior.warnings or []),
                idempotent_replay=True,
            )

        execution_plan = build_execution_plan_from_mapped(
            plan=plan,
            included=included,
            transformed=transformed,
            handoff_id=str(handoff.id),
            fingerprint=fingerprint,
        )

        handoff.lifecycle_status = ImplementationMarketingPlanHandoffStatus.CONFIRMED
        handoff.confirmed_by = actor_id
        handoff.confirmed_at = utc_now()
        note = sanitize_text(body.note or "").strip()[:2000] if body.note else None
        meta = dict(handoff.metadata_json or {})
        events = list(meta.get("review_events") or [])
        events.append(
            {
                "action": "confirm",
                "actor_id": str(actor_id),
                "note": note,
                "at": utc_now().isoformat(),
            }
        )
        meta["review_events"] = events
        handoff.metadata_json = meta
        handoff.updated_at = utc_now()
        async with transactional(self._session):
            await self._handoffs.update(handoff)

        created = await self._mp_service.create_from_execution_plan(
            owner_id,
            project_id,
            execution_plan,
            title=execution_plan.goal[:512],
            source_run_id=None,
            source_session_id=None,
            source_scenario_id=None,
            created_by_run_id=None,
        )
        if created is None:
            handoff.lifecycle_status = ImplementationMarketingPlanHandoffStatus.FAILED
            async with transactional(self._session):
                await self._handoffs.update(handoff)
            raise InvalidStateError("marketing_plan_create_unsafe")

        if MarketingPlanStatus(created.status) != MarketingPlanStatus.DRAFT:
            raise InvalidStateError("marketing_plan_create_unsafe")

        handoff.lifecycle_status = ImplementationMarketingPlanHandoffStatus.COMPLETED
        handoff.marketing_plan_id = created.id
        handoff.marketing_plan_version = created.current_version_number
        handoff.updated_at = utc_now()
        events.append(
            {
                "action": "completed",
                "actor_id": str(actor_id),
                "marketing_plan_id": str(created.id),
                "marketing_plan_version": created.current_version_number,
                "at": utc_now().isoformat(),
            }
        )
        meta["review_events"] = events
        handoff.metadata_json = meta
        async with transactional(self._session):
            await self._handoffs.update(handoff)

        return ImplementationMarketingPlanHandoffConfirmResponse(
            handoff_id=handoff.id,
            lifecycle_status=ImplementationMarketingPlanHandoffStatus.COMPLETED,
            marketing_plan_id=created.id,
            marketing_plan_version=int(created.current_version_number or 1),
            marketing_plan_status=MarketingPlanStatus.DRAFT,
            mapping_fingerprint=fingerprint,
            included_task_count=len(included) + len(transformed),
            excluded_task_count=handoff.excluded_task_count,
            blocked_task_count=handoff.blocked_task_count,
            warnings=list(handoff.warnings or []),
            idempotent_replay=False,
            creates_marketing_plan_approval=False,
            creates_agent_run=False,
            creates_campaign=False,
            dispatches_specialist_tasks=False,
            side_effects=[],
        )
