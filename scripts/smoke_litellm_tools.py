"""Manual LiteLLM + tools smoke — real OpenAI tool round outside pytest.

Usage:
    uv run python scripts/smoke_litellm_tools.py

Requires OPENAI_API_KEY in .env and optional extra: uv sync --extra llm
Without a key the script exits 0 with a skip message (CI-safe).
"""

from __future__ import annotations

import asyncio
import os
import sys
from uuid import uuid4

from app.core.config import get_settings
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import close_db, get_engine, get_session_factory, init_db
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.errors import LLMError
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.provider_config import get_provider_runtime_config
from app.schemas.contracts import AgentType, LLMProvider
from app.services.memory_service import MemoryService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.registry import PROJECT_CONTEXT_GET_TOOL, ToolRegistry
from app.tools.result_messages import build_assistant_tool_call_message, build_tool_result_message
from sqlmodel import SQLModel

from scripts.smoke_seed import SMOKE_PROJECT_NAME, SMOKE_TELEGRAM_ID, run_smoke_seed

OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
SMOKE_PROMPT = "Use project_context.get and summarize the current project in one sentence."


def _resolve_smoke_model(default_model: str) -> str:
    if not default_model or default_model == "mock-model":
        return OPENAI_FALLBACK_MODEL
    return default_model


def _safe_error_message(exc: BaseException) -> str:
    message = str(exc).strip() or "(no message)"
    lowered = message.lower()
    if "sk-" in lowered or "api_key" in lowered or "authorization" in lowered:
        return "(error message redacted — may contain secrets)"
    return message


async def _ensure_smoke_project() -> tuple:
    await run_smoke_seed()
    factory = get_session_factory()
    async with factory() as session:
        user = await UserRepository(session).get_by_telegram_id(SMOKE_TELEGRAM_ID)
        if user is None:
            raise RuntimeError("Smoke user missing after seed")
        projects = await ProjectRepository(session).list_by_owner(user.id)
        project = next((row for row in projects if row.name == SMOKE_PROJECT_NAME), None)
        if project is None:
            raise RuntimeError("Smoke project missing after seed")
        return user.id, project.id


async def run_smoke_litellm_tools() -> int:
    os.environ.setdefault("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()

    settings = get_settings()
    runtime = get_provider_runtime_config(LLMProvider.OPENAI, settings)
    if not runtime.api_key:
        print("SKIP: OPENAI_API_KEY is not set — tool smoke not run.")
        return 0

    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    owner_id, project_id = await _ensure_smoke_project()
    model = _resolve_smoke_model(settings.default_llm_model)
    adapter = LiteLLMAdapter()
    registry = ToolRegistry()
    registry.register(PROJECT_CONTEXT_GET_TOOL)

    initial_messages = [
        LLMMessage(
            role="system",
            content="You are a marketing assistant. Call tools when needed.",
        ),
        LLMMessage(role="user", content=SMOKE_PROMPT),
    ]
    initial = LLMGenerateInput(
        provider=LLMProvider.OPENAI,
        model=model,
        messages=initial_messages,
        temperature=0.2,
        max_tokens=500,
        tools=[PROJECT_CONTEXT_GET_TOOL],
        tool_choice="auto",
        metadata={"source": "smoke_litellm_tools", "project_id": str(project_id)},
    )

    try:
        first_output = await adapter.generate(initial)
    except LLMError as exc:
        print(f"ERROR: initial LLM call failed: {_safe_error_message(exc)}", file=sys.stderr)
        return 1

    tool_calls = first_output.tool_calls or []
    print(f"initial tool_calls: {len(tool_calls)}")
    if not tool_calls:
        print("ERROR: model did not return tool_calls", file=sys.stderr)
        return 1

    factory = get_session_factory()
    async with factory() as session:
        executor = SafeNoOpToolExecutor(
            registry,
            memory_service=MemoryService(session),
            audit_service=ToolExecutionLogService(session),
            session=session,
        )
        context = ToolExecutionContext(
            owner_id=owner_id,
            project_id=project_id,
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            agent_run_id=uuid4(),
            request_id=uuid4(),
        )
        tool_results = []
        for tool_call in tool_calls:
            tool_results.append(await executor.execute(tool_call, context))
        await session.commit()

        follow_up_messages = list(initial_messages)
        follow_up_messages.append(
            build_assistant_tool_call_message(tool_calls, content=first_output.content or None),
        )
        for tool_call, result in zip(tool_calls, tool_results, strict=True):
            follow_up_messages.append(build_tool_result_message(tool_call, result))

        second = LLMGenerateInput(
            provider=LLMProvider.OPENAI,
            model=model,
            messages=follow_up_messages,
            temperature=0.2,
            max_tokens=300,
            metadata={"source": "smoke_litellm_tools_follow_up"},
        )
        try:
            final_output = await adapter.generate(second)
        except LLMError as exc:
            print(f"ERROR: follow-up LLM call failed: {_safe_error_message(exc)}", file=sys.stderr)
            return 1

    print(f"provider: {final_output.provider.value}")
    print(f"model: {final_output.model or model}")
    print(f"final content: {final_output.content}")
    print(f"tool execution statuses: {[result.status for result in tool_results]}")
    preview = tool_results[0].output
    if isinstance(preview, dict):
        print(f"first tool envelope ok={preview.get('ok')}")
    if any(result.status == "failed" for result in tool_results):
        print("ERROR: tool execution failed", file=sys.stderr)
        return 1
    print("OK: tools attached, executed, injected, final answer received")
    return 0


async def _main_async() -> int:
    try:
        return await run_smoke_litellm_tools()
    finally:
        await close_db()


def main() -> None:
    exit_code = asyncio.run(_main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
