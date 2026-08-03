"""Shared specialist execution helpers (Phase AI.31)."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ExecutorError
from app.core.security import sanitize_text
from app.llm.config import resolve_llm_config
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.prompts.safety import assert_no_prompt_secrets, sanitize_prompt_context
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistType,
)

_SAFE_SUMMARY_MAX = 500
_CONTENT_MAX = 8192


def resolve_project_llm_config() -> tuple[LLMProvider, str, float | None, int | None]:
    """Project-level LLM settings via global defaults (no agent run)."""
    return resolve_llm_config({}, settings=get_settings())


def build_specialist_llm_metadata(
    *,
    execution_run_id: str,
    task_index: int,
    specialist: MarketingSpecialistType,
) -> dict[str, Any]:
    return {
        "marketing_specialist_execution": True,
        "execution_run_id": execution_run_id,
        "task_index": task_index,
        "specialist": specialist.value,
    }


def build_specialist_llm_input(
    *,
    provider: LLMProvider,
    model: str,
    messages: list[LLMMessage],
    temperature: float | None,
    max_tokens: int | None,
    metadata: dict[str, Any],
) -> LLMGenerateInput:
    return LLMGenerateInput(
        provider=provider,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=None,
        tool_choice=None,
        metadata=metadata,
    )


def sanitize_execution_input(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionInput:
    context = data.project_context
    if context is not None:
        assert_no_prompt_secrets(context)
        context = sanitize_prompt_context(context)
    return data.model_copy(
        update={
            "objective": sanitize_text(data.objective),
            "expected_output": sanitize_text(data.expected_output),
            "plan_goal": sanitize_text(data.plan_goal),
            "project_context": context,
        },
    )


def safe_summary_from_content(content: str, *, prefix: str = "") -> str:
    cleaned = sanitize_text(content).strip()
    if prefix:
        cleaned = f"{prefix} {cleaned}".strip()
    if len(cleaned) <= _SAFE_SUMMARY_MAX:
        return cleaned or "Specialist output ready for review."
    return cleaned[: _SAFE_SUMMARY_MAX - 3].rstrip() + "..."


def truncate_content(content: str) -> str:
    return sanitize_text(content).strip()[:_CONTENT_MAX]


def llm_execution_metadata(
    *,
    provider: LLMProvider,
    model: str,
) -> dict[str, Any]:
    return {
        "llm_provider": provider.value,
        "model": model,
        "mock": provider == LLMProvider.MOCK,
    }


def merge_structured_with_llm_meta(
    structured: dict[str, Any],
    *,
    provider: LLMProvider,
    model: str,
) -> dict[str, Any]:
    merged = dict(structured)
    merged.update(llm_execution_metadata(provider=provider, model=model))
    return merged


def reject_tool_calls(tool_calls: object) -> None:
    if tool_calls:
        raise ExecutorError("Specialist execution must not invoke tools")


def _section_value(content: str, label: str) -> str | None:
    pattern = rf"(?:^|\n)#{{1,3}}\s*{re.escape(label)}\s*\n+(.+?)(?=\n#{{1,3}}\s|\Z)"
    match = re.search(pattern, content, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def parse_markdown_sections(content: str, labels: tuple[str, ...]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for label in labels:
        value = _section_value(content, label)
        if value:
            parsed[label.lower().replace(" ", "_")] = value
    return parsed


def format_project_context_block(context: dict[str, Any] | None) -> str:
    if not context:
        return "No additional project context."
    return json.dumps(context, ensure_ascii=False, indent=2)
