"""Chat block action definitions and attachment (Phase AI.22)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.schemas.contracts import (
    ChatAssistantMessageBlock,
    ChatAssistantMessageBlockType,
    ChatAssistantMessageDomain,
    ChatBlockAction,
    ChatBlockActionType,
)

_PROGRAMMER_PERSISTENCE_REASON = "Programmer artifacts are consultation-only in this phase"
_MEDIA_PERSISTENCE_REASON = "Media artifacts are consultation-only in this phase"

_COPY_LABEL = "Copy"
_EXPORT_MD_LABEL = "Export markdown"
_SAVE_ASSET_LABEL = "Save as content asset"
_SAVE_BRIEF_LABEL = "Save as marketing brief"
_SAVE_MARKETING_PLAN_LABEL = "Save marketing plan"
_CREATE_REVISION_LABEL = "Create revision"


def _copy_export_actions(*, include_copy: bool) -> list[ChatBlockAction]:
    actions: list[ChatBlockAction] = []
    if include_copy:
        actions.append(
            ChatBlockAction(type=ChatBlockActionType.COPY_TEXT, label=_COPY_LABEL, enabled=True),
        )
        actions.append(
            ChatBlockAction(
                type=ChatBlockActionType.EXPORT_MARKDOWN,
                label=_EXPORT_MD_LABEL,
                enabled=True,
            ),
        )
    return actions


def _disabled_persistence_stub(
    action_type: ChatBlockActionType,
    *,
    label: str,
    reason: str,
) -> ChatBlockAction:
    return ChatBlockAction(
        type=action_type,
        label=label,
        enabled=False,
        reason=reason,
        payload={},
    )


def _block_data_dict(block: ChatAssistantMessageBlock) -> dict[str, Any]:
    return dict(block.data) if isinstance(block.data, dict) else {}


def _has_content_asset_source(data: dict[str, Any]) -> bool:
    content_plan = data.get("content_plan")
    if isinstance(content_plan, dict):
        body = content_plan.get("body") or content_plan.get("summary") or content_plan.get("text")
        if body and str(body).strip():
            return True
    if data.get("plan_draft"):
        return True
    body = data.get("body")
    return bool(body and str(body).strip())


def _has_marketing_execution_plan(data: dict[str, Any]) -> bool:
    plan = data.get("marketing_execution_plan")
    if not isinstance(plan, dict):
        return False
    goal = str(plan.get("goal", "")).strip()
    tasks = plan.get("specialist_tasks")
    return bool(goal) and isinstance(tasks, list) and len(tasks) > 0


def _has_marketing_brief_source(data: dict[str, Any]) -> bool:
    brief = data.get("marketing_brief")
    if not isinstance(brief, dict):
        return False
    return bool(
        str(brief.get("title", "")).strip()
        or str(brief.get("body", brief.get("summary", ""))).strip(),
    )


def _approved_source_asset_id(data: dict[str, Any]) -> str | None:
    for key in ("approved_source_asset_id", "source_approved_asset_id", "source_asset_id"):
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    revision_ctx = data.get("revision_context")
    if isinstance(revision_ctx, dict):
        for key in ("approved_source_asset_id", "source_asset_id"):
            value = revision_ctx.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return None


def attach_block_actions(block: ChatAssistantMessageBlock) -> ChatAssistantMessageBlock:
    """Attach server-computed actions; never trust client block payloads."""
    data = _block_data_dict(block)
    has_content = bool(block.content.strip())
    actions: list[ChatBlockAction] = []

    if block.type == ChatAssistantMessageBlockType.ERROR:
        return block.model_copy(update={"actions": []})

    if block.type == ChatAssistantMessageBlockType.CLARIFICATION:
        actions.extend(_copy_export_actions(include_copy=has_content))
        return block.model_copy(update={"actions": actions})

    if block.type == ChatAssistantMessageBlockType.MARKETING_PLAN:
        if _has_marketing_execution_plan(data):
            actions.append(
                ChatBlockAction(
                    type=ChatBlockActionType.SAVE_MARKETING_PLAN,
                    label=_SAVE_MARKETING_PLAN_LABEL,
                    enabled=True,
                    payload={},
                ),
            )
        actions.extend(_copy_export_actions(include_copy=has_content))
        return block.model_copy(update={"actions": actions})

    if block.domain == ChatAssistantMessageDomain.PROGRAMMER:
        actions.extend(_copy_export_actions(include_copy=has_content))
        actions.extend(
            [
                _disabled_persistence_stub(
                    ChatBlockActionType.CREATE_MARKETING_ASSET,
                    label=_SAVE_ASSET_LABEL,
                    reason=_PROGRAMMER_PERSISTENCE_REASON,
                ),
            ],
        )
        return block.model_copy(update={"actions": actions})

    if block.domain == ChatAssistantMessageDomain.MEDIA:
        actions.extend(_copy_export_actions(include_copy=has_content))
        actions.extend(
            [
                _disabled_persistence_stub(
                    ChatBlockActionType.CREATE_MARKETING_ASSET,
                    label=_SAVE_ASSET_LABEL,
                    reason=_MEDIA_PERSISTENCE_REASON,
                ),
            ],
        )
        return block.model_copy(update={"actions": actions})

    if block.domain == ChatAssistantMessageDomain.MARKETING or (
        block.type in (ChatAssistantMessageBlockType.DRAFT, ChatAssistantMessageBlockType.BRIEF)
        and block.domain != ChatAssistantMessageDomain.PROGRAMMER
    ):
        if _has_content_asset_source(data):
            actions.append(
                ChatBlockAction(
                    type=ChatBlockActionType.CREATE_MARKETING_ASSET,
                    label=_SAVE_ASSET_LABEL,
                    enabled=True,
                    payload={},
                ),
            )
        if _has_marketing_brief_source(data):
            actions.append(
                ChatBlockAction(
                    type=ChatBlockActionType.CREATE_MARKETING_BRIEF,
                    label=_SAVE_BRIEF_LABEL,
                    enabled=True,
                    payload={},
                ),
            )
        approved_id = _approved_source_asset_id(data)
        if approved_id is not None:
            try:
                UUID(approved_id)
                actions.append(
                    ChatBlockAction(
                        type=ChatBlockActionType.CREATE_REVISION_FROM_APPROVED,
                        label=_CREATE_REVISION_LABEL,
                        enabled=True,
                        payload={"approved_source_asset_id": approved_id},
                    ),
                )
            except ValueError:
                pass
        actions.extend(_copy_export_actions(include_copy=has_content))
        return block.model_copy(update={"actions": actions})

    actions.extend(_copy_export_actions(include_copy=has_content))
    return block.model_copy(update={"actions": actions})


def attach_actions_to_blocks(
    blocks: list[ChatAssistantMessageBlock],
) -> list[ChatAssistantMessageBlock]:
    return [attach_block_actions(block) for block in blocks]


def block_to_markdown(block: ChatAssistantMessageBlock) -> str:
    lines: list[str] = []
    if block.title:
        lines.append(f"## {block.title}")
    if block.content.strip():
        lines.append(block.content.strip())
    data = _block_data_dict(block)
    plan = data.get("marketing_execution_plan")
    if isinstance(plan, dict):
        goal = str(plan.get("goal", "")).strip()
        if goal:
            lines.append(f"\n**Goal:** {goal}")
        tasks = plan.get("specialist_tasks")
        if isinstance(tasks, list):
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                specialist = task.get("specialist", "specialist")
                objective = task.get("objective", "")
                expected = task.get("expected_output", "")
                lines.append(f"- **{specialist}**: {objective} → {expected}")
    return "\n\n".join(lines) if lines else ""


def extract_marketing_execution_plan_from_block(
    block: ChatAssistantMessageBlock,
    *,
    run_output: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve plan payload from block data or stored run output."""
    data = _block_data_dict(block)
    raw = data.get("marketing_execution_plan")
    if not isinstance(raw, dict) and isinstance(run_output, dict):
        raw = run_output.get("marketing_execution_plan")
    if isinstance(raw, dict) and _has_marketing_execution_plan({"marketing_execution_plan": raw}):
        return raw
    return None


def extract_content_asset_fields(
    block: ChatAssistantMessageBlock,
    *,
    project_id: UUID,
    source_run_id: UUID | None,
) -> tuple[str, str, dict[str, Any]]:
    data = _block_data_dict(block)
    title = (block.title or "Chat content draft").strip()[:512]
    body = block.content.strip()
    metadata: dict[str, Any] = {"source": "agent_chat_block"}

    content_plan = data.get("content_plan")
    if isinstance(content_plan, dict):
        plan_body = content_plan.get("body") or content_plan.get("summary") or content_plan.get("text")
        if plan_body and str(plan_body).strip():
            body = str(plan_body).strip()
        plan_title = content_plan.get("title")
        if plan_title and str(plan_title).strip():
            title = str(plan_title).strip()[:512]

    if not body:
        raise ValueError("missing content body")

    if source_run_id is not None:
        metadata["source_agent_run_id"] = str(source_run_id)
    metadata["source_project_id"] = str(project_id)
    return title, body, metadata


def extract_marketing_brief_fields(
    block: ChatAssistantMessageBlock,
) -> tuple[str, str, str, list[str], dict[str, Any]]:
    data = _block_data_dict(block)
    brief = data.get("marketing_brief")
    if not isinstance(brief, dict):
        raise ValueError("missing marketing_brief")
    title = str(brief.get("title", block.title or "Marketing brief")).strip()[:512]
    description = str(brief.get("body", brief.get("summary", block.content))).strip()
    audience = str(brief.get("target_audience", "")).strip()
    goals_raw = brief.get("goals")
    goals = [str(item) for item in goals_raw] if isinstance(goals_raw, list) else []
    constraints = brief.get("constraints")
    constraints_dict = dict(constraints) if isinstance(constraints, dict) else {}
    if not title and not description:
        raise ValueError("missing marketing brief fields")
    return title, description, audience, goals, constraints_dict
