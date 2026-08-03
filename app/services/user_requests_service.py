"""UserRequest persistence service — owner-scoped home intake + H2.5 skill context."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.user_request import UserRequestTable
from app.domain.user_request_assistant import build_assistant_message, chat_route_for_decision
from app.domain.user_request_routing import (
    apply_clarification_answer,
    normalize_request_text,
    route_user_request,
)
from app.domain.user_request_skill_context import (
    apply_attachment_to_row,
    attach_skill_context,
)
from app.schemas.contracts import (
    SpecialistSkillCode,
    UserRequestRouteCategory,
    UserRequestStatus,
)
from app.services.content_draft_service import (
    ContentDraftService,
    ContentDraftUnavailableError,
    apply_draft_unavailable,
)
from app.services.design_image_generation_service import (
    DesignImageGenerationService,
    ImageGenerationUnavailableError,
    apply_generation_success,
    apply_generation_unavailable,
)


class UserRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_by_idempotency_key(
        self,
        owner_id: UUID,
        idempotency_key: str,
    ) -> UserRequestTable | None:
        stmt = select(UserRequestTable).where(
            UserRequestTable.owner_id == owner_id,
            UserRequestTable.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_client_message_id(
        self,
        owner_id: UUID,
        client_message_id: str,
    ) -> UserRequestTable | None:
        stmt = select(UserRequestTable).where(
            UserRequestTable.owner_id == owner_id,
            UserRequestTable.client_message_id == client_message_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _next_sequence_number(self, owner_id: UUID) -> int:
        stmt = select(func.max(UserRequestTable.sequence_number)).where(
            UserRequestTable.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        current = result.scalar_one_or_none()
        return int(current or 0) + 1

    async def create(
        self,
        *,
        owner_id: UUID,
        text: str,
        selected_scenario: str | None = None,
        source: str = "home_conversation",
        skill_inputs: dict[str, Any] | None = None,
        locale: str = "ru",
        client_message_id: str | None = None,
        idempotency_key: str | None = None,
        conversation_id: UUID | None = None,
    ) -> UserRequestTable:
        if idempotency_key:
            existing = await self._get_by_idempotency_key(owner_id, idempotency_key)
            if existing is not None:
                return existing
        if client_message_id:
            existing = await self._get_by_client_message_id(owner_id, client_message_id)
            if existing is not None:
                return existing

        cleaned = sanitize_text(text or "")
        normalized = normalize_request_text(cleaned)
        has_refs = bool((skill_inputs or {}).get("reference_set_id"))
        force_image = str((skill_inputs or {}).get("force_image_generation") or "").lower() in {
            "1",
            "true",
            "yes",
        }
        scenario = selected_scenario
        if force_image and not scenario:
            scenario = UserRequestRouteCategory.IMAGE_GENERATION.value
        decision = route_user_request(
            normalized,
            selected_scenario=scenario,
            has_reference_set=has_refs,
        )
        chat_route = chat_route_for_decision(decision)
        routing_decision_id = uuid4()
        sequence_number = await self._next_sequence_number(owner_id)

        merged_skill_inputs = dict(skill_inputs or {})
        if decision.rationale:
            merged_skill_inputs["_route_rationale"] = decision.rationale
        merged_skill_inputs["_routing_decision_id"] = str(routing_decision_id)

        execution_provider: str | None = None
        execution_model: str | None = None
        assistant_text: str

        if chat_route == "general_answer":
            from app.services.user_request_general_answer_service import (
                GeneralAnswerFailure,
                UserRequestGeneralAnswerService,
            )

            try:
                ga_result = await UserRequestGeneralAnswerService().generate(
                    cleaned,
                    locale=locale,
                )
                assistant_text = ga_result.content
                execution_provider = ga_result.provider
                execution_model = ga_result.model
                merged_skill_inputs["_llm_call_count"] = 1
                status = UserRequestStatus.ROUTED
            except GeneralAnswerFailure as exc:
                assistant_text = exc.message
                status = UserRequestStatus.FAILED
        else:
            assistant_text = build_assistant_message(normalized, decision)
            status = (
                UserRequestStatus.NEEDS_CLARIFICATION
                if decision.kind.value == "clarify"
                else UserRequestStatus.ROUTED
                if decision.kind.value != "unsupported"
                else UserRequestStatus.FAILED
            )
        row = UserRequestTable(
            owner_id=owner_id,
            text=cleaned[:8000],
            normalized_text=normalized[:8000],
            selected_scenario=selected_scenario,
            route_category=decision.category,
            route_kind=decision.kind,
            route_confidence=decision.confidence,
            status=status,
            clarification_question=decision.clarification_question,
            assigned_specialist=decision.assigned_specialist,
            requires_project=decision.requires_project,
            avoids_investigation=decision.avoids_investigation,
            next_href=decision.next_href,
            next_action_label=decision.next_action_label,
            assistant_message=assistant_text[:4000],
            title=(decision.title or normalized[:80] or "Запрос")[:512],
            source=source[:64],
            skill_inputs=merged_skill_inputs,
            missing_inputs=[],
            client_message_id=client_message_id,
            idempotency_key=idempotency_key,
            conversation_id=conversation_id or owner_id,
            sequence_number=sequence_number,
            assistant_run_id=None,
            routing_decision_id=routing_decision_id,
            chat_route=chat_route,
            execution_provider=execution_provider,
            execution_model=execution_model,
        )
        if (skill_inputs or {}).get("home_agency_flow"):
            row.next_href = None
            row.requires_project = False
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        if row.assistant_run_id is None:
            row.assistant_run_id = row.id
            row.updated_at = utc_now()
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)

        attachment = await attach_skill_context(
            self._session,
            row,
            structured_inputs=skill_inputs,
            locale=locale,
        )
        apply_attachment_to_row(row, attachment)
        row.updated_at = utc_now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        row = await self._maybe_execute_image_generation(row)
        row = await self._maybe_execute_content_draft(row)
        return row

    async def list_for_owner(
        self,
        owner_id: UUID,
        *,
        limit: int = 100,
    ) -> list[UserRequestTable]:
        stmt = (
            select(UserRequestTable)
            .where(UserRequestTable.owner_id == owner_id)
            .order_by(UserRequestTable.created_at.desc())
            .limit(min(max(limit, 1), 200))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_owner(
        self,
        owner_id: UUID,
        request_id: UUID,
    ) -> UserRequestTable | None:
        stmt = select(UserRequestTable).where(
            UserRequestTable.id == request_id,
            UserRequestTable.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def clarify(
        self,
        *,
        owner_id: UUID,
        request_id: UUID,
        answer: str,
        skill_inputs: dict[str, Any] | None = None,
        locale: str = "ru",
    ) -> UserRequestTable | None:
        row = await self.get_for_owner(owner_id, request_id)
        if row is None:
            return None
        cleaned = sanitize_text(answer or "")
        # Allow structured-only clarify without free-text when skill_inputs provided.
        if not cleaned.strip() and not skill_inputs:
            return row
        from app.domain.user_request_routing import RouteDecision

        prior = RouteDecision(
            category=row.route_category,
            kind=row.route_kind,
            confidence=row.route_confidence,
            requires_project=row.requires_project,
            avoids_investigation=row.avoids_investigation,
            assigned_specialist=row.assigned_specialist,
            clarification_question=row.clarification_question,
            next_href=row.next_href,
            next_action_label=row.next_action_label or "",
            assistant_message=row.assistant_message,
            title=row.title,
        )
        if cleaned.strip():
            decision = apply_clarification_answer(
                prior,
                original_text=row.text,
                answer=cleaned,
            )
            row.clarification_answer = cleaned[:4000]
            row.route_category = decision.category
            row.route_kind = decision.kind
            row.route_confidence = decision.confidence
            row.requires_project = decision.requires_project
            row.avoids_investigation = decision.avoids_investigation
            row.assigned_specialist = decision.assigned_specialist
            row.clarification_question = decision.clarification_question
            row.next_href = decision.next_href
            row.next_action_label = decision.next_action_label
            row.assistant_message = build_assistant_message(
                f"{row.text} {cleaned}".strip(),
                decision,
            )[:4000]
            row.title = (decision.title or row.title)[:512]
            row.status = (
                UserRequestStatus.NEEDS_CLARIFICATION
                if decision.kind.value == "clarify"
                else UserRequestStatus.ROUTED
                if decision.kind.value != "unsupported"
                else UserRequestStatus.FAILED
            )

        merged_inputs = dict(row.skill_inputs or {})
        if skill_inputs:
            merged_inputs.update(
                {k: v for k, v in skill_inputs.items() if v is not None and str(v).strip()}
            )
        row.skill_inputs = merged_inputs

        attachment = await attach_skill_context(
            self._session,
            row,
            structured_inputs=merged_inputs,
            locale=locale,
        )
        apply_attachment_to_row(row, attachment)
        row.updated_at = utc_now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        row = await self._maybe_execute_image_generation(row)
        row = await self._maybe_execute_content_draft(row)
        return row

    async def review_content_draft(
        self,
        *,
        owner_id: UUID,
        request_id: UUID,
        action: Any,
        note: str | None = None,
    ) -> UserRequestTable | None:
        from app.schemas.contracts import (
            ContentDraftReviewAction,
            ContentDraftReviewStatus,
        )

        row = await self.get_for_owner(owner_id, request_id)
        if row is None:
            return None
        if not row.content_draft:
            return row
        draft = dict(row.content_draft)
        if action == ContentDraftReviewAction.ACCEPT:
            new_status = ContentDraftReviewStatus.ACCEPTED
        elif action == ContentDraftReviewAction.REJECT:
            new_status = ContentDraftReviewStatus.REJECTED
        elif action in (
            ContentDraftReviewAction.REQUEST_REVISION,
            ContentDraftReviewAction.CREATE_VARIANT,
        ):
            new_status = ContentDraftReviewStatus.REVISION_REQUESTED
        else:
            new_status = ContentDraftReviewStatus.PENDING
        draft["review_status"] = new_status.value
        row.content_draft = draft
        row.content_draft_review_status = new_status.value
        if note:
            row.assistant_message = sanitize_text(note)[:4000]
        row.updated_at = utc_now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def _maybe_execute_content_draft(
        self,
        row: UserRequestTable,
    ) -> UserRequestTable:
        if row.skill_code != SpecialistSkillCode.CONTENT_TELEGRAM_POST.value:
            return row
        if row.execution_readiness.value != "ready_for_draft":
            return row
        if row.content_draft and row.content_draft_review_status:
            return row
        service = ContentDraftService(self._session)
        if not service.readiness()["content_draft_execution_enabled"]:
            return row
        try:
            await service.execute_for_user_request(row)
        except ContentDraftUnavailableError as exc:
            apply_draft_unavailable(row, message=exc.user_message, category=exc.category)
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)
        return row

    async def _maybe_execute_image_generation(
        self,
        row: UserRequestTable,
    ) -> UserRequestTable:
        if row.skill_code != SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value:
            return row
        if row.execution_readiness.value != "ready_for_draft":
            return row
        if row.generation_status == "succeeded" and row.generated_visual_asset_ids:
            return row
        service = DesignImageGenerationService(self._session)
        inputs = dict(row.skill_inputs or {})
        await self._bind_reference_set_and_prior_prompt(row, inputs)
        prompt = str(inputs.get("prompt") or row.text)
        try:
            asset = await service.execute_for_user_request(
                row,
                prompt=prompt,
                skill_inputs=inputs,
            )
            apply_generation_success(
                row,
                asset,
                warnings=list((asset.generation_metadata or {}).get("warnings") or []),
            )
        except ImageGenerationUnavailableError as exc:
            apply_generation_unavailable(
                row,
                message=exc.user_message,
                category=exc.category,
            )
        row.skill_inputs = inputs
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def _bind_reference_set_and_prior_prompt(
        self,
        row: UserRequestTable,
        inputs: dict,
    ) -> None:
        """Link ReferenceSet → UserRequest and recover prior prompt for meta-only follow-ups."""
        from uuid import UUID as _UUID

        from sqlalchemy import select as sa_select

        from app.db.models.reference_visual import ReferenceSetTable
        from app.domain.image_prompt_integrity import is_meta_only_image_prompt

        ref_raw = inputs.get("reference_set_id")
        if ref_raw:
            try:
                ref_id = _UUID(str(ref_raw))
            except Exception:  # noqa: BLE001
                ref_id = None
            if ref_id is not None:
                ref_set = await self._session.get(ReferenceSetTable, ref_id)
                if ref_set is not None and ref_set.owner_id == row.owner_id:
                    if ref_set.user_request_id is None:
                        ref_set.user_request_id = row.id
                        self._session.add(ref_set)
                    inputs["_reference_count"] = str(len(ref_set.reference_asset_ids or []))

        prompt = str(inputs.get("prompt") or row.text or "")
        if not is_meta_only_image_prompt(prompt):
            return
        # Recover last substantive image prompt from same owner (+ same ref set when present).
        stmt = (
            sa_select(UserRequestTable)
            .where(
                UserRequestTable.owner_id == row.owner_id,
                UserRequestTable.skill_code == SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value,
                UserRequestTable.id != row.id,
            )
            .order_by(UserRequestTable.created_at.desc())
            .limit(8)
        )
        result = await self._session.execute(stmt)
        for prior in result.scalars().all():
            prior_inputs = dict(prior.skill_inputs or {})
            if ref_raw and str(prior_inputs.get("reference_set_id") or "") != str(ref_raw):
                continue
            candidate = str(prior_inputs.get("prompt") or prior.text or "").strip()
            if candidate and not is_meta_only_image_prompt(candidate):
                inputs["_prior_prompt"] = candidate
                inputs["prompt"] = candidate
                inputs["_prompt_recovered_from_prior"] = "1"
                return
