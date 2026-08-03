"""Rebuild assistant message blocks for chat history (Phase AI.23)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import sanitize_text
from app.db.models.agent_chat import AgentChatMessageTable
from app.db.models.agent_run import AgentRunTable
from app.db.repositories.agent_runs import AgentRunRepository
from app.schemas.agent_chat import AgentChatExecutionMetadata, AgentChatPlanDraftCreated
from app.services.agent_chat_plan_draft import find_plan_drafts_by_run_ids
from app.services.chat_block_actions import attach_actions_to_blocks
from app.services.chat_message_blocks import build_assistant_message_blocks
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatAssistantMessageBlock,
    ChatAssistantMessageBlockType,
    ChatAssistantMessageDomain,
)


def source_run_id_from_message(message: AgentChatMessageTable) -> UUID | None:
    metadata = message.message_metadata or {}
    raw = metadata.get("source_run_id") or message.agent_run_id
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        return message.agent_run_id


def domain_from_message_metadata(message: AgentChatMessageTable) -> ChatAssistantMessageDomain:
    metadata = message.message_metadata or {}
    raw = str(metadata.get("domain", "unknown"))
    try:
        return ChatAssistantMessageDomain(raw)
    except ValueError:
        return ChatAssistantMessageDomain.UNKNOWN


def build_fallback_assistant_blocks(
    message: AgentChatMessageTable,
) -> list[ChatAssistantMessageBlock]:
    content = sanitize_text(message.content).strip()
    domain = domain_from_message_metadata(message)
    block = ChatAssistantMessageBlock(
        type=ChatAssistantMessageBlockType.TEXT,
        domain=domain,
        content=content,
    )
    return attach_actions_to_blocks([block]) if content else []


def rebuild_assistant_blocks(
    message: AgentChatMessageTable,
    *,
    owner_id: UUID,
    project_id: UUID,
    runs_by_id: dict[UUID, AgentRunTable],
    plan_drafts_by_run_id: dict[UUID, AgentChatPlanDraftCreated],
    strict_run: bool = False,
) -> list[ChatAssistantMessageBlock]:
    """Rebuild blocks from stored run output; degrade to text fallback unless strict_run."""
    metadata = message.message_metadata or {}
    block_types = metadata.get("block_types")

    if isinstance(block_types, list) and block_types == ["clarification"]:
        domain = domain_from_message_metadata(message)
        block = ChatAssistantMessageBlock(
            type=ChatAssistantMessageBlockType.CLARIFICATION,
            domain=domain,
            content=sanitize_text(message.content).strip(),
        )
        return attach_actions_to_blocks([block])

    source_run_id = source_run_id_from_message(message)
    output: dict[str, Any] = {}
    execution_metadata: AgentChatExecutionMetadata | None = None
    plan_draft: AgentChatPlanDraftCreated | None = None

    if source_run_id is not None:
        run = runs_by_id.get(source_run_id)
        if run is None or run.owner_id != owner_id or run.project_id != project_id:
            if strict_run:
                raise NotFoundError("Source agent run not found")
            return build_fallback_assistant_blocks(message)
        output = dict(run.output_payload or {})
        exec_raw = metadata.get("execution_metadata")
        if isinstance(exec_raw, dict):
            execution_metadata = AgentChatExecutionMetadata.model_validate(exec_raw)
        plan_draft = plan_drafts_by_run_id.get(source_run_id)
    elif strict_run:
        raise NotFoundError("Source agent run not found")

    clarification = (
        sanitize_text(message.content).strip()
        if isinstance(block_types, list) and "clarification" in block_types
        else None
    )
    built = build_assistant_message_blocks(
        output=output,
        execution_metadata=execution_metadata,
        clarification=clarification,
        plan_draft=plan_draft,
        fallback_text=message.content,
    )
    blocks = attach_actions_to_blocks(built.blocks)
    if blocks:
        return blocks
    return build_fallback_assistant_blocks(message)


async def rebuild_blocks_for_session_messages(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    messages: list[AgentChatMessageTable],
) -> dict[UUID, list[ChatAssistantMessageBlock]]:
    """Batch-rebuild assistant blocks for a session message list."""
    assistant_messages = [row for row in messages if row.role == AgentChatMessageRole.ASSISTANT]
    if not assistant_messages:
        return {}

    run_ids: list[UUID] = []
    for message in assistant_messages:
        source_run_id = source_run_id_from_message(message)
        if source_run_id is not None:
            run_ids.append(source_run_id)

    unique_run_ids = list(dict.fromkeys(run_ids))
    runs_by_id: dict[UUID, AgentRunTable] = {}
    if unique_run_ids:
        runs = await AgentRunRepository(session).list_by_ids_for_owner(
            unique_run_ids,
            owner_id,
            project_id=project_id,
        )
        runs_by_id = {run.id: run for run in runs}

    plan_drafts_by_run_id = await find_plan_drafts_by_run_ids(
        session,
        owner_id,
        project_id,
        unique_run_ids,
    )

    blocks_by_message_id: dict[UUID, list[ChatAssistantMessageBlock]] = {}
    for message in assistant_messages:
        blocks_by_message_id[message.id] = rebuild_assistant_blocks(
            message,
            owner_id=owner_id,
            project_id=project_id,
            runs_by_id=runs_by_id,
            plan_drafts_by_run_id=plan_drafts_by_run_id,
            strict_run=False,
        )
    return blocks_by_message_id
