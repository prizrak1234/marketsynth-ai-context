"""Copywriter specialist execution (Phase AI.34) — draft copy only, no ContentAsset."""

from __future__ import annotations

import json
from typing import Any

from app.agents.marketer.specialists.base import (
    build_specialist_llm_input,
    build_specialist_llm_metadata,
    format_project_context_block,
    merge_structured_with_llm_meta,
    reject_tool_calls,
    resolve_project_llm_config,
    safe_summary_from_content,
    sanitize_execution_input,
    truncate_content,
)
from app.agents.marketer.specialists.researcher import (
    STRATEGIST_PRIOR_STRUCTURED_KEYS,
    RESEARCHER_PRIOR_STRUCTURED_KEYS,
    CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
)
from app.core.exceptions import ExecutorError
from app.llm.contracts import LLMMessage
from app.llm.registry import get_llm_adapter
from app.marketing.contracts import ContentAssetType
from app.marketing.copy_quality import build_mock_copy_draft_body
from app.marketing.copywriter_output_parser import (
    CopywriterOutputUnparseableError,
    extract_brief_channel,
    parse_copywriter_llm_content,
)
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistPriorOutput,
    MarketingSpecialistType,
)

_COPYWRITER_SYSTEM_PROMPT = (
    "You are a marketing copywriter for BotFazer. Write draft copy only.\n"
    "Use strategist direction, researcher insights, and the content plan structure.\n"
    "Do not create content assets, publish, or schedule. Do not request tools.\n"
    "Return ONLY valid JSON with this shape:\n"
    '{"content_items":[{"title":"...","body":"...","channel":"telegram",'
    '"angle":"...","slot_index":1,"hook":"...","cta":"..."}]}\n'
    "Minimum 3 content_items. Each item must have distinct title and body.\n"
    "Use the brief channel exactly. Write in the brief language (Russian when brief is Russian).\n"
    "No markdown wrappers in title fields. No final approval actions."
)

_COPYWRITER_TITLE = "Content copy"
_COPYWRITER_OUTPUT_TYPE = "content_copy"

_PRIOR_KEYS_BY_SPECIALIST = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CONTENT_PLANNER: CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
}

def _format_prior_outputs_block(prior_outputs: list[MarketingSpecialistPriorOutput]) -> str:
    if not prior_outputs:
        return "No prior specialist outputs."
    blocks: list[str] = []
    for item in prior_outputs:
        structured = item.structured_data or {}
        allowed = _PRIOR_KEYS_BY_SPECIALIST.get(item.specialist, ())
        safe_structured = {key: structured[key] for key in allowed if key in structured}
        blocks.append(
            json.dumps(
                {
                    "specialist": item.specialist.value,
                    "title": item.title,
                    "output_type": item.output_type,
                    "safe_summary": item.safe_summary,
                    "structured_data": safe_structured,
                    "content_excerpt": item.content_excerpt,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return "\n\n".join(blocks)


def _build_user_message(data: MarketingSpecialistExecutionInput) -> str:
    return (
        f"Plan goal:\n{data.plan_goal}\n\n"
        f"Task objective:\n{data.objective}\n\n"
        f"Expected output:\n{data.expected_output}\n\n"
        f"Project context:\n{format_project_context_block(data.project_context)}\n\n"
        f"Prior strategist, researcher, and content planner outputs:\n"
        f"{_format_prior_outputs_block(data.prior_outputs)}"
    )


def _build_messages(data: MarketingSpecialistExecutionInput) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=_COPYWRITER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=_build_user_message(data)),
    ]


def _prior_present(
    prior_outputs: list[MarketingSpecialistPriorOutput],
    specialist: MarketingSpecialistType,
) -> bool:
    return any(item.specialist == specialist for item in prior_outputs)


def validate_copywriter_prior_outputs(
    prior_outputs: list[MarketingSpecialistPriorOutput],
) -> None:
    if not _prior_present(prior_outputs, MarketingSpecialistType.STRATEGIST):
        raise ExecutorError("Copywriter execution requires prior strategist context")
    if not _prior_present(prior_outputs, MarketingSpecialistType.RESEARCHER):
        raise ExecutorError("Copywriter execution requires prior researcher context")
    if not _prior_present(prior_outputs, MarketingSpecialistType.CONTENT_PLANNER):
        raise ExecutorError("Copywriter execution requires prior content planner context")


def _channel_to_asset_type(channel: str) -> ContentAssetType:
    normalized = (channel or "").strip().lower()
    if normalized in {"email", "newsletter"}:
        return ContentAssetType.EMAIL
    if normalized in {"ad", "ads", "ad_copy"}:
        return ContentAssetType.AD_COPY
    if normalized in {"telegram", "social", "telegram_post"}:
        return ContentAssetType.TELEGRAM_POST
    return ContentAssetType.EMAIL


def _normalize_post_idea(
    idea: Any,
    *,
    index: int,
    default_channel: str,
) -> dict[str, str]:
    if isinstance(idea, dict):
        return {
            "title": str(idea.get("title") or f"Post idea {index + 1}"),
            "channel": str(idea.get("channel") or default_channel or "telegram"),
            "funnel_stage": str(idea.get("funnel_stage") or "awareness"),
            "brief": str(idea.get("brief") or idea.get("title") or ""),
        }
    text = str(idea).strip() or f"Post idea {index + 1}"
    return {
        "title": text[:120],
        "channel": default_channel or "telegram",
        "funnel_stage": "consideration",
        "brief": text,
    }


def _build_content_item(
    *,
    idea: dict[str, str],
    pillar: str,
    key_message: str,
    goal: str,
) -> dict[str, Any]:
    channel = idea["channel"]
    asset_type = _channel_to_asset_type(channel)
    body = build_mock_copy_draft_body(asset_type, goal=goal or key_message)
    hook = f"Attention hook for {idea['title'][:80]}"
    return {
        "headline": idea["title"][:200],
        "hook": hook[:300],
        "body": truncate_content(body)[:4000],
        "cta": "Take the next step — draft for human review",
        "funnel_stage": idea["funnel_stage"][:64],
        "content_pillar": pillar[:200],
        "channel": channel[:64],
        "source_post_idea": idea["title"][:200],
    }


def _mock_content_items(data: MarketingSpecialistExecutionInput) -> list[dict[str, Any]]:
    strategist = next(
        p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.STRATEGIST
    )
    planner = next(
        p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.CONTENT_PLANNER
    )
    key_message = ""
    if strategist.structured_data:
        key_message = str(strategist.structured_data.get("key_message", ""))
    pillars = []
    post_ideas: list[Any] = []
    if planner.structured_data:
        raw_pillars = planner.structured_data.get("content_pillars")
        if isinstance(raw_pillars, list):
            pillars = [str(p) for p in raw_pillars]
        raw_ideas = planner.structured_data.get("post_ideas")
        if isinstance(raw_ideas, list):
            post_ideas = raw_ideas

    default_channel = extract_brief_channel(data.project_context) or "telegram"
    if not post_ideas:
        post_ideas = [
            {
                "title": "Primary campaign message",
                "channel": default_channel,
                "funnel_stage": "conversion",
            },
        ]

    items: list[dict[str, Any]] = []
    for index, raw_idea in enumerate(post_ideas[:3]):
        idea = _normalize_post_idea(raw_idea, index=index, default_channel=default_channel)
        pillar = pillars[index % len(pillars)] if pillars else "Core pillar"
        items.append(
            _build_content_item(
                idea=idea,
                pillar=pillar,
                key_message=key_message,
                goal=data.plan_goal,
            ),
        )
    return items


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {"content_items": _mock_content_items(data)}


def _build_mock_output(
    data: MarketingSpecialistExecutionInput,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    structured = merge_structured_with_llm_meta(
        _mock_structured_data(data),
        provider=provider,
        model=model,
    )
    items = structured["content_items"]
    lines = [
        f"Content copy package — {len(items)} draft item(s) from the approved content plan.",
        "This is not persisted as ContentAsset; human review required.",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            f"\n## Item {index}: {item['headline']}\n"
            f"Channel: {item['channel']} · Stage: {item['funnel_stage']}\n"
            f"{item['hook']}\n\n{item['body'][:500]}..."
        )
    content = truncate_content("\n".join(lines))
    headline = str(items[0]["headline"]) if items else "Content copy"
    return MarketingSpecialistExecutionOutput(
        title=_COPYWRITER_TITLE,
        output_type=_COPYWRITER_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(headline, prefix="Content copy (mock):"),
    )


def _build_from_llm_content(
    content: str,
    data: MarketingSpecialistExecutionInput,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    body = truncate_content(content)
    expected_channel = extract_brief_channel(data.project_context)
    try:
        items = parse_copywriter_llm_content(
            body,
            expected_channel=expected_channel,
            minimum_items=3,
        )
    except CopywriterOutputUnparseableError as exc:
        raise ExecutorError(str(exc)) from exc

    structured = merge_structured_with_llm_meta(
        {
            "content_items": items,
            "brief_channel": expected_channel,
        },
        provider=provider,
        model=model,
    )
    headline = str(items[0].get("headline") or items[0].get("title") or "Content copy draft")
    return MarketingSpecialistExecutionOutput(
        title=_COPYWRITER_TITLE,
        output_type=_COPYWRITER_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(headline, prefix="Content copy:"),
    )


async def execute_copywriter_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    """Draft copy from plan + prior outputs — no ContentAsset, tools, or child runs."""
    sanitized = sanitize_execution_input(data)
    validate_copywriter_prior_outputs(sanitized.prior_outputs)

    provider, model, temperature, max_tokens = resolve_project_llm_config()

    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    metadata = build_specialist_llm_metadata(
        execution_run_id=str(sanitized.execution_run_id),
        task_index=sanitized.task_index,
        specialist=MarketingSpecialistType.COPYWRITER,
    )
    llm_input = build_specialist_llm_input(
        provider=provider,
        model=model,
        messages=_build_messages(sanitized),
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=metadata,
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Copywriter LLM returned empty content")
    return _build_from_llm_content(
        output.content,
        sanitized,
        provider=provider,
        model=model or output.model or "unknown",
    )
