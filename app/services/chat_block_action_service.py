"""Execute chat block actions server-side (Phase AI.22)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError
from app.core.security import sanitize_text
from app.db.models.agent_chat import AgentChatMessageTable
from app.db.models.agent_run import AgentRunTable
from app.db.repositories.agent_runs import AgentRunRepository
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatAssistantMessageBlock,
    ChatAuditEventType,
    ChatBlockActionType,
    ChatAssistantMessageDomain,
)
from app.marketing.contracts import ContentAssetType, ContentAssetVersionSource
from app.services.agent_chat_plan_draft import find_plan_drafts_by_run_ids
from app.schemas.contracts import MarketingExecutionPlan
from app.services.chat_block_actions import (
    block_to_markdown,
    extract_content_asset_fields,
    extract_marketing_brief_fields,
    extract_marketing_execution_plan_from_block,
)
from app.services.marketing_plan_service import MarketingPlanService
from app.services.chat_history_blocks import (
    rebuild_assistant_blocks,
    source_run_id_from_message,
)
from app.services.chat_audit_service import ChatAuditService
from app.services.chat_session_service import ChatSessionService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.transaction import transactional

_PERSISTENCE_ACTIONS = frozenset(
    {
        ChatBlockActionType.CREATE_MARKETING_ASSET,
        ChatBlockActionType.CREATE_MARKETING_BRIEF,
        ChatBlockActionType.CREATE_REVISION_FROM_APPROVED,
    },
)

_CONSULTATION_ONLY_DOMAINS = frozenset(
    {
        ChatAssistantMessageDomain.PROGRAMMER,
        ChatAssistantMessageDomain.MEDIA,
    },
)

_INSUFFICIENT_DATA = "This block does not contain enough data to create that artifact"


@dataclass(frozen=True)
class ChatBlockActionResult:
    status: str
    message: str
    created_resource_type: str | None = None
    created_resource_id: UUID | None = None
    text: str | None = None
    markdown: str | None = None


@dataclass(frozen=True)
class ResolvedChatBlock:
    session_id: UUID
    message: AgentChatMessageTable
    block: ChatAssistantMessageBlock
    block_index: int
    source_run_id: UUID | None


class ChatBlockActionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._chat_sessions = ChatSessionService(session)
        self._run_repo = AgentRunRepository(session)
        self._audit = ChatAuditService(session)

    async def resolve_block(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        session_id: UUID,
        assistant_message_id: UUID,
        block_index: int,
    ) -> ResolvedChatBlock:
        session_row = await self._chat_sessions.get_session(owner_id, project_id, session_id)
        if session_row is None:
            raise NotFoundError("Chat session not found")

        message = await self._load_assistant_message(
            session_id,
            assistant_message_id,
        )
        blocks = await self._rebuild_blocks(
            owner_id,
            project_id,
            message=message,
        )
        if block_index < 0 or block_index >= len(blocks):
            raise NotFoundError("Block index out of range")

        source_run_id = source_run_id_from_message(message)
        return ResolvedChatBlock(
            session_id=session_id,
            message=message,
            block=blocks[block_index],
            block_index=block_index,
            source_run_id=source_run_id,
        )

    async def execute(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        session_id: UUID,
        assistant_message_id: UUID,
        block_index: int,
        action_type: ChatBlockActionType,
        payload: dict[str, Any] | None = None,
    ) -> ChatBlockActionResult:
        session_row = await self._chat_sessions.get_session(owner_id, project_id, session_id)
        if session_row is None:
            raise NotFoundError("Chat session not found")

        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.BLOCK_ACTION_REQUESTED,
            status="requested",
            domain=session_row.domain,
            entrypoint=session_row.entrypoint,
            session_id=session_id,
            message_id=assistant_message_id,
            agent_id=session_row.agent_id,
            safe_metadata={
                "action_type": action_type.value,
                "block_index": block_index,
            },
        )

        try:
            resolved = await self.resolve_block(
                owner_id,
                project_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
                block_index=block_index,
            )
            block = resolved.block
            allowed = {action.type for action in block.actions if action.enabled}
            if action_type not in allowed:
                if action_type in _PERSISTENCE_ACTIONS and block.domain in _CONSULTATION_ONLY_DOMAINS:
                    raise InvalidStateError(
                        "Persistence actions are not allowed for consultation-only blocks",
                    )
                raise InvalidStateError("Action is not allowed for this block")

            if action_type == ChatBlockActionType.COPY_TEXT:
                result = ChatBlockActionResult(
                    status="ok",
                    message="Text ready to copy",
                    text=block.content,
                )
            elif action_type == ChatBlockActionType.EXPORT_MARKDOWN:
                markdown = block_to_markdown(block)
                result = ChatBlockActionResult(
                    status="ok",
                    message="Markdown ready",
                    markdown=markdown,
                )
            elif action_type == ChatBlockActionType.CREATE_MARKETING_ASSET:
                result = await self._create_marketing_asset(
                    owner_id,
                    project_id,
                    block=block,
                    source_run_id=resolved.source_run_id,
                )
            elif action_type == ChatBlockActionType.CREATE_MARKETING_BRIEF:
                result = await self._create_marketing_brief(owner_id, project_id, block=block)
            elif action_type == ChatBlockActionType.CREATE_REVISION_FROM_APPROVED:
                result = await self._create_revision_from_approved(
                    owner_id,
                    project_id,
                    block=block,
                    source_run_id=resolved.source_run_id,
                    payload=payload or {},
                )
            elif action_type == ChatBlockActionType.SAVE_MARKETING_PLAN:
                result = await self._save_marketing_plan(
                    owner_id,
                    project_id,
                    block=block,
                    session_id=session_id,
                    source_run_id=resolved.source_run_id,
                )
            else:
                raise InvalidStateError("Unsupported action type")
        except (InvalidStateError, NotFoundError) as exc:
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=ChatAuditEventType.BLOCK_ACTION_FAILED,
                status="failed",
                domain=session_row.domain,
                entrypoint=session_row.entrypoint,
                session_id=session_id,
                message_id=assistant_message_id,
                agent_id=session_row.agent_id,
                safe_metadata={
                    "action_type": action_type.value,
                    "block_index": block_index,
                    "error_code": type(exc).__name__,
                    "safe_message": str(exc)[:200],
                },
            )
            raise

        success_meta: dict[str, Any] = {
            "action_type": action_type.value,
            "block_index": block_index,
            "result_status": result.status,
        }
        if result.created_resource_type is not None:
            success_meta["created_resource_type"] = result.created_resource_type
        if result.created_resource_id is not None:
            success_meta["created_resource_id"] = str(result.created_resource_id)

        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.BLOCK_ACTION_SUCCEEDED,
            status="succeeded",
            domain=session_row.domain,
            entrypoint=session_row.entrypoint,
            session_id=session_id,
            message_id=assistant_message_id,
            agent_id=session_row.agent_id,
            safe_metadata=success_meta,
        )
        return result

    async def _load_assistant_message(
        self,
        session_id: UUID,
        assistant_message_id: UUID,
    ) -> AgentChatMessageTable:
        row = await self._chat_sessions.get_session_message(session_id, assistant_message_id)
        if row is None:
            raise NotFoundError("Assistant message not found")
        if row.role != AgentChatMessageRole.ASSISTANT:
            raise InvalidStateError("Message is not an assistant message")
        return row

    async def _rebuild_blocks(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        message: AgentChatMessageTable,
    ) -> list[ChatAssistantMessageBlock]:
        source_run_id = source_run_id_from_message(message)
        runs_by_id: dict[UUID, AgentRunTable] = {}
        plan_drafts_by_run_id = {}
        if source_run_id is not None:
            runs = await self._run_repo.list_by_ids_for_owner(
                [source_run_id],
                owner_id,
                project_id=project_id,
            )
            runs_by_id = {run.id: run for run in runs}
            plan_drafts_by_run_id = await find_plan_drafts_by_run_ids(
                self._session,
                owner_id,
                project_id,
                [source_run_id],
            )
        return rebuild_assistant_blocks(
            message,
            owner_id=owner_id,
            project_id=project_id,
            runs_by_id=runs_by_id,
            plan_drafts_by_run_id=plan_drafts_by_run_id,
            strict_run=True,
        )

    async def _create_marketing_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        block: ChatAssistantMessageBlock,
        source_run_id: UUID | None,
    ) -> ChatBlockActionResult:
        try:
            title, body, asset_metadata = extract_content_asset_fields(
                block,
                project_id=project_id,
                source_run_id=source_run_id,
            )
        except ValueError as exc:
            raise InvalidStateError(_INSUFFICIENT_DATA) from exc

        data = block.data if isinstance(block.data, dict) else {}
        plan_draft = data.get("plan_draft")
        campaign_id: UUID | None = None
        if isinstance(plan_draft, dict):
            raw_campaign = plan_draft.get("campaign_id")
            if raw_campaign is not None:
                try:
                    campaign_id = UUID(str(raw_campaign))
                except ValueError:
                    campaign_id = None

        async with transactional(self._session):
            created = await ContentAssetService(self._session).create(
                owner_id,
                project_id,
                asset_type=ContentAssetType.TEXT,
                title=title,
                body=body,
                metadata=asset_metadata,
                campaign_id=campaign_id,
                agent_run_id=source_run_id,
                created_by_source=ContentAssetVersionSource.HTTP_API,
                created_by_agent_run_id=source_run_id,
            )
        if created is None:
            raise NotFoundError("Project or linked resource not found")

        return ChatBlockActionResult(
            status="created",
            message="Content asset draft created",
            created_resource_type="content_asset",
            created_resource_id=created.id,
        )

    async def _save_marketing_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        block: ChatAssistantMessageBlock,
        session_id: UUID,
        source_run_id: UUID | None,
    ) -> ChatBlockActionResult:
        run_output: dict[str, Any] | None = None
        if source_run_id is not None:
            run = await self._run_repo.get_by_id_for_owner(source_run_id, owner_id)
            if run is not None and run.project_id == project_id:
                run_output = dict(run.output_payload or {})

        raw_plan = extract_marketing_execution_plan_from_block(
            block,
            run_output=run_output,
        )
        if raw_plan is None:
            raise InvalidStateError(_INSUFFICIENT_DATA)

        try:
            execution_plan = MarketingExecutionPlan.model_validate(raw_plan)
        except Exception as exc:
            raise InvalidStateError(_INSUFFICIENT_DATA) from exc

        async with transactional(self._session):
            created = await MarketingPlanService(self._session).create_from_execution_plan(
                owner_id,
                project_id,
                execution_plan,
                source_run_id=source_run_id,
                source_session_id=session_id,
                created_by_run_id=source_run_id,
            )
        if created is None:
            raise NotFoundError("Project not found")

        return ChatBlockActionResult(
            status="created",
            message="Marketing plan saved as draft",
            created_resource_type="marketing_plan",
            created_resource_id=created.id,
        )

    async def _create_marketing_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        block: ChatAssistantMessageBlock,
    ) -> ChatBlockActionResult:
        try:
            title, description, audience, goals, constraints = extract_marketing_brief_fields(block)
        except ValueError as exc:
            raise InvalidStateError(_INSUFFICIENT_DATA) from exc

        async with transactional(self._session):
            created = await MarketingBriefService(self._session).create(
                owner_id,
                project_id,
                title=title,
                product_description=description,
                target_audience=audience,
                goals=goals,
                constraints=constraints,
            )
        if created is None:
            raise NotFoundError("Project not found")

        return ChatBlockActionResult(
            status="created",
            message="Marketing brief created",
            created_resource_type="marketing_brief",
            created_resource_id=created.id,
        )

    async def _create_revision_from_approved(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        block: ChatAssistantMessageBlock,
        source_run_id: UUID | None,
        payload: dict[str, Any],
    ) -> ChatBlockActionResult:
        data = block.data if isinstance(block.data, dict) else {}
        raw_id = payload.get("approved_source_asset_id")
        if raw_id is None:
            for key in ("approved_source_asset_id", "source_approved_asset_id", "source_asset_id"):
                if data.get(key) is not None:
                    raw_id = data.get(key)
                    break
        if raw_id is None:
            raise InvalidStateError(_INSUFFICIENT_DATA)
        try:
            source_asset_id = UUID(str(raw_id))
        except ValueError as exc:
            raise InvalidStateError(_INSUFFICIENT_DATA) from exc

        body_override = sanitize_text(str(payload.get("body", block.content))).strip() or None
        title_override = payload.get("title")
        title = str(title_override).strip()[:512] if title_override else None

        async with transactional(self._session):
            created = await ContentAssetService(self._session).create_revision_from_approved(
                owner_id,
                project_id,
                source_asset_id,
                title=title,
                body=body_override,
                created_by_source=ContentAssetVersionSource.HTTP_API,
                created_by_agent_run_id=source_run_id,
            )
        if created is None:
            raise InvalidStateError(_INSUFFICIENT_DATA)

        return ChatBlockActionResult(
            status="created",
            message="Revision draft created from approved asset",
            created_resource_type="content_asset",
            created_resource_id=created.id,
        )
