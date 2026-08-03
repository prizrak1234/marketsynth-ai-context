"""Frontend-safe assistant message blocks (Phase AI.21)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.security import sanitize_text
from app.db.base import utc_now
from app.schemas.agent_chat import (
    AgentChatExecutionMetadata,
    AgentChatGeneratedAssets,
    AgentChatPlanDraftCreated,
    AgentChatRevisedAsset,
)
from app.schemas.contracts import (
    ChatAssistantMessageBlock,
    ChatAssistantMessageBlockType,
    ChatAssistantMessageDomain,
    MarketingExecutionPlan,
)
from app.services.chat_block_actions import attach_actions_to_blocks

_SAFE_ERROR_MESSAGE = "Agent temporarily unavailable. Please try again later."

_FORBIDDEN_ERROR_MARKERS = (
    "traceback",
    "stack trace",
    "exception",
    "openai",
    "anthropic",
    "api_key",
    "secret",
    "password",
    "token",
    "raw_response",
    "provider",
)


@dataclass(frozen=True)
class ChatBlockBuildResult:
    blocks: list[ChatAssistantMessageBlock]
    readable_content: str
    message_metadata: dict[str, Any]
    output: dict[str, Any]


def resolve_block_domain(
    execution_metadata: AgentChatExecutionMetadata | None,
    *,
    clarification: bool = False,
) -> ChatAssistantMessageDomain:
    if execution_metadata is None:
        return ChatAssistantMessageDomain.UNKNOWN
    raw = execution_metadata.domain
    if clarification and raw == "unknown":
        return ChatAssistantMessageDomain.UNKNOWN
    mapping = {
        "unknown": ChatAssistantMessageDomain.UNKNOWN,
        "marketing": ChatAssistantMessageDomain.MARKETING,
        "programmer": ChatAssistantMessageDomain.PROGRAMMER,
        "media": ChatAssistantMessageDomain.MEDIA,
    }
    return mapping.get(raw, ChatAssistantMessageDomain.UNKNOWN)


def build_safe_error_block(
    message: str | None = None,
    *,
    domain: ChatAssistantMessageDomain = ChatAssistantMessageDomain.UNKNOWN,
) -> ChatAssistantMessageBlock:
    safe = sanitize_text(message or _SAFE_ERROR_MESSAGE).strip()
    lowered = safe.lower()
    if not safe or any(marker in lowered for marker in _FORBIDDEN_ERROR_MARKERS):
        safe = _SAFE_ERROR_MESSAGE
    return ChatAssistantMessageBlock(
        type=ChatAssistantMessageBlockType.ERROR,
        domain=domain,
        content=safe,
        created_at=utc_now(),
    )


def format_technical_task_summary(draft: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = str(draft.get("summary", "")).strip()
    if summary:
        lines.append(summary)
    scope = str(draft.get("scope", "")).strip()
    if scope:
        lines.append(scope)
    deliverables = draft.get("deliverables")
    if isinstance(deliverables, list) and deliverables:
        lines.append("Deliverables: " + ", ".join(str(item) for item in deliverables[:6]))
    excerpt = str(draft.get("assistant_excerpt", "")).strip()
    if excerpt and excerpt not in "\n".join(lines):
        lines.append(excerpt)
    if not lines:
        return "Technical task draft prepared for review (consultation only, not persisted)."
    return "\n\n".join(lines)


def format_visual_brief_summary(brief: dict[str, Any]) -> str:
    lines: list[str] = []
    visual_format = str(brief.get("format", "")).strip()
    if visual_format:
        lines.append(f"Format: {visual_format}")
    concept = str(brief.get("concept", "")).strip()
    if concept:
        lines.append(concept)
    composition = str(brief.get("composition", "")).strip()
    if composition:
        lines.append(composition)
    text_overlay = str(brief.get("text_overlay", "")).strip()
    if text_overlay:
        lines.append(f"Text overlay: {text_overlay}")
    style_notes = str(brief.get("style_notes", "")).strip()
    if style_notes:
        lines.append(style_notes)
    shot_list = brief.get("shot_list")
    if isinstance(shot_list, list) and shot_list:
        lines.append("Shot list: " + "; ".join(str(item) for item in shot_list[:5]))
    excerpt = str(brief.get("assistant_excerpt", "")).strip()
    if excerpt and excerpt not in "\n".join(lines):
        lines.append(excerpt)
    if not lines:
        return "Visual brief prepared for designers (consultation only, not persisted)."
    return "\n\n".join(lines)


def format_marketing_execution_plan_summary(plan: dict[str, Any]) -> str:
    from app.agents.marketer.planning import format_marketing_execution_plan_summary as _fmt

    try:
        model = MarketingExecutionPlan.model_validate(plan)
    except Exception:
        goal = str(plan.get("goal", "")).strip()
        return goal or "Marketing execution plan (planning mode only)."
    return _fmt(model)


def format_marketing_brief_summary(brief: dict[str, Any]) -> str:
    title = str(brief.get("title", "")).strip()
    body = str(brief.get("body", brief.get("summary", ""))).strip()
    parts = [part for part in (title, body) if part]
    if not parts:
        return "Marketing brief summary."
    return "\n\n".join(parts)[:2000]


def blocks_readable_content(blocks: list[ChatAssistantMessageBlock]) -> str:
    parts = [block.content.strip() for block in blocks if block.content.strip()]
    return "\n\n".join(parts)


def build_assistant_message_blocks(
    *,
    output: dict[str, Any],
    execution_metadata: AgentChatExecutionMetadata | None,
    clarification: str | None = None,
    plan_draft: AgentChatPlanDraftCreated | None = None,
    generated_assets: AgentChatGeneratedAssets | None = None,
    revised_assets: list[AgentChatRevisedAsset] | None = None,
    fallback_text: str,
) -> ChatBlockBuildResult:
    """Map run output and chat artifacts into frontend-safe blocks."""
    now = utc_now()
    blocks: list[ChatAssistantMessageBlock] = []
    domain = resolve_block_domain(execution_metadata)

    if clarification:
        blocks.append(
            ChatAssistantMessageBlock(
                type=ChatAssistantMessageBlockType.CLARIFICATION,
                domain=resolve_block_domain(execution_metadata, clarification=True),
                content=sanitize_text(clarification).strip(),
                created_at=now,
            ),
        )
    else:
        draft_payload = output.get("technical_task_draft")
        if isinstance(draft_payload, dict):
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.DRAFT,
                    domain=ChatAssistantMessageDomain.PROGRAMMER,
                    title="Technical task draft",
                    content=format_technical_task_summary(draft_payload),
                    data={"technical_task_draft": draft_payload},
                    persisted=bool(draft_payload.get("persisted", False)),
                    created_at=now,
                ),
            )

        brief_payload = output.get("visual_brief")
        if isinstance(brief_payload, dict):
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.BRIEF,
                    domain=ChatAssistantMessageDomain.MEDIA,
                    title="Visual brief",
                    content=format_visual_brief_summary(brief_payload),
                    data={"visual_brief": brief_payload},
                    persisted=bool(brief_payload.get("persisted", False)),
                    created_at=now,
                ),
            )

        marketing_plan = output.get("marketing_execution_plan")
        if isinstance(marketing_plan, dict):
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.MARKETING_PLAN,
                    domain=ChatAssistantMessageDomain.MARKETING,
                    title="Marketing execution plan",
                    content=format_marketing_execution_plan_summary(marketing_plan),
                    data={"marketing_execution_plan": marketing_plan},
                    created_at=now,
                ),
            )

        marketing_brief = output.get("marketing_brief")
        if isinstance(marketing_brief, dict):
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.BRIEF,
                    domain=ChatAssistantMessageDomain.MARKETING,
                    title="Marketing brief",
                    content=format_marketing_brief_summary(marketing_brief),
                    data={"marketing_brief": marketing_brief},
                    created_at=now,
                ),
            )

        content_plan = output.get("content_plan") or output.get("content_plan_draft")
        if isinstance(content_plan, dict):
            summary = str(content_plan.get("body", content_plan.get("summary", ""))).strip()
            plan_block_data: dict[str, Any] = {"content_plan": content_plan}
            for key in (
                "approved_source_asset_id",
                "source_approved_asset_id",
                "source_asset_id",
            ):
                if output.get(key) is not None:
                    plan_block_data[key] = output[key]
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.DRAFT,
                    domain=ChatAssistantMessageDomain.MARKETING,
                    title="Content plan draft",
                    content=summary or "Content plan draft prepared for review.",
                    data=plan_block_data,
                    created_at=now,
                ),
            )

        if plan_draft is not None:
            plan_text = sanitize_text(fallback_text).strip() or (
                f"Campaign plan draft created.\n"
                f"draft_id: {plan_draft.draft_id}\n"
                f"campaign_id: {plan_draft.campaign_id}"
            )
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.DRAFT,
                    domain=ChatAssistantMessageDomain.MARKETING,
                    title="Campaign plan draft",
                    content=plan_text,
                    data={"plan_draft": plan_draft.model_dump(mode="json")},
                    created_at=now,
                ),
            )

        if generated_assets is not None:
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.TEXT,
                    domain=ChatAssistantMessageDomain.MARKETING,
                    content=(
                        "Draft assets already generated."
                        if generated_assets.already_generated
                        else f"Draft assets created ({generated_assets.created_count})."
                    ),
                    data={"generated_assets": generated_assets.model_dump(mode="json")},
                    created_at=now,
                ),
            )

        if revised_assets:
            blocks.append(
                ChatAssistantMessageBlock(
                    type=ChatAssistantMessageBlockType.TEXT,
                    domain=ChatAssistantMessageDomain.MARKETING,
                    content=f"Revised {len(revised_assets)} asset(s).",
                    data={
                        "revised_assets": [
                            item.model_dump(mode="json") for item in revised_assets
                        ],
                    },
                    created_at=now,
                ),
            )

        run_error = output.get("error")
        if isinstance(run_error, str) and run_error.strip():
            blocks.append(build_safe_error_block(run_error, domain=domain))

        if not blocks:
            text = sanitize_text(fallback_text).strip()
            if text:
                blocks.append(
                    ChatAssistantMessageBlock(
                        type=ChatAssistantMessageBlockType.TEXT,
                        domain=domain,
                        content=text,
                        created_at=now,
                    ),
                )

    readable = blocks_readable_content(blocks) or sanitize_text(fallback_text).strip()
    block_types = [block.type.value for block in blocks]
    primary_domain = blocks[0].domain.value if blocks else domain.value

    message_metadata: dict[str, Any] = {
        "block_types": block_types,
        "domain": primary_domain,
    }
    if execution_metadata is not None:
        message_metadata["execution_metadata"] = execution_metadata.model_dump()

    return ChatBlockBuildResult(
        blocks=attach_actions_to_blocks(blocks),
        readable_content=readable,
        message_metadata=message_metadata,
        output=dict(output),
    )
