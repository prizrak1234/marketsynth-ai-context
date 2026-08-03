"""Phase 2.16 — tool result envelope and normalized tool errors."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType, MemoryLayer
from app.schemas.crud import MemoryItemCreate, ProjectCreate
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.tools.audit_preview import build_result_preview
from app.tools.contracts import ToolCall, ToolExecutionContext, ToolResult
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executor import SafeNoOpToolExecutor, build_tools_run_summary
from app.tools.permissions import REAL_READ_ONLY_EXECUTABLE_TOOLS, ToolExecutionMode
from app.tools.registry import MEMORY_SEARCH_TOOL, PROJECT_CONTEXT_GET_TOOL, ToolRegistry
from app.tools.result_builder import (
    build_tool_error,
    build_tool_success,
    enforce_result_size_limit,
    envelope_from_execution,
)
from app.tools.result_contracts import ToolExecutionErrorCode, ToolResultEnvelope
from app.tools.result_messages import build_tool_result_message
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _context(
    *,
    owner_id=None,
    project_id=None,
    agent_id=None,
    agent_type: AgentType = AgentType.RESEARCHER,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id or uuid4(),
        project_id=project_id or uuid4(),
        agent_id=agent_id or uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
    )


def _tool_data(result: ToolResult) -> dict:
    assert isinstance(result.output, dict)
    assert result.output["ok"] is True
    return result.output["data"]


def test_success_envelope_schema() -> None:
    envelope = build_tool_success(
        "memory.search",
        {"items": [], "count": 0},
    )
    parsed = ToolResultEnvelope.model_validate(envelope)
    assert parsed.ok is True
    assert parsed.tool == "memory.search"
    assert parsed.data["count"] == 0
    assert parsed.error is None
    assert parsed.meta.items_count == 0


def test_error_envelope_schema() -> None:
    envelope = build_tool_error(
        "project_context.get",
        code=ToolExecutionErrorCode.PERMISSION_DENIED,
        message="Tool execution failed",
    )
    parsed = ToolResultEnvelope.model_validate(envelope)
    assert parsed.ok is False
    assert parsed.error is not None
    assert parsed.error.code == ToolExecutionErrorCode.PERMISSION_DENIED
    assert parsed.error.message == "Tool execution failed"


@pytest.mark.asyncio
async def test_memory_search_returns_envelope(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9401))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Envelope Memory Project"),
    )
    memory = MemoryService(db_session)
    await memory.create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="note:1",
            content="Envelope memory content preview test",
        ),
    )

    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=memory)
    result = await executor.execute(
        ToolCall(id="call_env_ms", name="memory.search", arguments={"query": "preview"}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=uuid4()),
    )

    assert result.status == "succeeded"
    assert result.output["ok"] is True
    assert result.output["tool"] == "memory.search"
    data = _tool_data(result)
    assert data["count"] == 1
    assert "content" not in data["items"][0]
    assert "content_preview" in data["items"][0]


@pytest.mark.asyncio
async def test_project_context_get_returns_envelope(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9402))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Envelope Context Project"),
    )

    registry = ToolRegistry()
    registry.register(PROJECT_CONTEXT_GET_TOOL)
    executor = SafeNoOpToolExecutor(registry, session=db_session)
    result = await executor.execute(
        ToolCall(id="call_env_pc", name="project_context.get", arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=uuid4()),
    )

    assert result.status == "succeeded"
    assert result.output["ok"] is True
    assert result.output["tool"] == "project_context.get"
    data = _tool_data(result)
    assert data["project"]["name"] == "Envelope Context Project"


@pytest.mark.asyncio
async def test_invalid_args_normalized(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_bad", name="memory.search", arguments={"query": "   "}),
        _context(),
    )

    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value


@pytest.mark.asyncio
async def test_permission_denied_normalized(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(
        MEMORY_SEARCH_TOOL.model_copy(update={"allowed_agent_types": [AgentType.RESEARCHER]}),
    )
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_perm", name="memory.search", arguments={"query": "x"}),
        _context(agent_type=AgentType.COPYWRITER),
    )

    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value


@pytest.mark.asyncio
async def test_unsupported_tool_normalized() -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_unsup", name="memory.search", arguments={"query": "x"}),
        _context(),
    )

    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.UNSUPPORTED_TOOL.value


@pytest.mark.asyncio
async def test_unexpected_exception_normalized_without_raw_leak(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))

    with patch.object(
        executor._memory_search,
        "execute",
        new_callable=AsyncMock,
        side_effect=RuntimeError("sk-secret-internal-db-password"),
    ):
        result = await executor.execute(
            ToolCall(id="call_exc", name="memory.search", arguments={"query": "x"}),
            _context(),
        )

    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.EXECUTION_FAILED.value
    serialized = json.dumps(result.output)
    assert "sk-secret-internal-db-password" not in serialized
    assert "RuntimeError" not in serialized


def test_result_size_limit_enforced() -> None:
    huge_data = {"items": [{"content_preview": "x" * 50_000}]}
    envelope = build_tool_success("memory.search", huge_data)
    limited = enforce_result_size_limit(envelope, max_bytes=512)
    assert limited["ok"] is False
    assert limited["error"]["code"] == ToolExecutionErrorCode.RESULT_TOO_LARGE.value


def test_audit_result_preview_compact() -> None:
    preview = build_result_preview(
        ToolResult(
            call_id="call_preview",
            name="memory.search",
            status="succeeded",
            output=build_tool_success(
                "memory.search",
                {"items": [{"content_preview": "SECRET"}], "count": 1},
            ),
            metadata={"result_count": 1},
        ),
    )
    assert preview["ok"] is True
    assert preview["items_count"] == 1
    assert "items" not in preview
    assert "SECRET" not in json.dumps(preview)


@patch("app.llm.mock_adapter.MockLLMAdapter.generate", new_callable=AsyncMock)
def test_agent_run_executor_injects_envelope_into_tool_message(
    mock_generate: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.llm.contracts import LLMGenerateOutput
    from app.schemas.contracts import LLMProvider
    from app.tools.contracts import ToolCall

    mock_generate.side_effect = [
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[ToolCall(id="call_env", name="memory.search", arguments={"query": "x"})],
        ),
        LLMGenerateOutput(
            content="Mock LLM final answer after tools",
            provider=LLMProvider.MOCK,
            model="mock-model",
        ),
    ]

    project_id = client.post(
        "/projects",
        json={"name": "Envelope Injection Project"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        "/memory",
        json={
            "project_id": project_id,
            "layer": "l1_session",
            "key": "env:1",
            "content": "injection envelope test",
            "metadata": {},
        },
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {"prompt": "search", "force_tool_call": "memory.search"},
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200

    second_call_messages = mock_generate.await_args_list[1].args[0].messages
    tool_messages = [message for message in second_call_messages if message.role == "tool"]
    assert len(tool_messages) == 1
    payload = json.loads(tool_messages[0].content or "")
    assert payload["ok"] is True
    assert payload["tool"] == "memory.search"
    assert response.json()["output_payload"]["tools"] == {
        "executed_count": 1,
        "failed_count": 0,
        "tool_names": ["memory.search"],
    }


def test_failed_tool_result_still_allows_llm_follow_up(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_response = client.post(
        "/projects",
        json={"name": "Failed Tool Project"},
        headers=auth_headers,
    )
    project_id = project_response.json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "search",
                "mock_tool_call": {
                    "id": "call_bad",
                    "type": "function",
                    "function": {
                        "name": "memory.search",
                        "arguments": {"query": "   "},
                    },
                },
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock researcher final answer after tools"
    assert body["output_payload"]["tools"] == {
        "executed_count": 0,
        "failed_count": 1,
        "tool_names": ["memory.search"],
    }


def test_tool_result_message_contains_envelope_json() -> None:
    envelope = build_tool_success("memory.search", {"items": [], "count": 0})
    result = ToolResult(
        call_id="call_env",
        name="memory.search",
        status="succeeded",
        output=envelope,
    )
    message = build_tool_result_message(
        ToolCall(id="call_env", name="memory.search", arguments={"query": "x"}),
        result,
    )
    payload = json.loads(message.content or "")
    assert payload["ok"] is True
    assert payload["tool"] == "memory.search"


def test_tool_summary_counts_success_and_failure() -> None:
    success = ToolResult(
        call_id="call_ok",
        name="memory.search",
        status="succeeded",
        output=build_tool_success("memory.search", {"items": [], "count": 0}),
    )
    failure = ToolResult(
        call_id="call_fail",
        name="memory.search",
        status="failed",
        output=build_tool_error(
            "memory.search",
            code=ToolExecutionErrorCode.INVALID_ARGUMENTS,
            message="Invalid arguments",
        ),
    )
    summary = build_tools_run_summary([success, failure])
    assert summary == {
        "executed_count": 1,
        "failed_count": 1,
        "tool_names": ["memory.search"],
    }


def test_envelope_from_execution_maps_validation_failure() -> None:
    execution = ToolExecutionResult(
        tool_name="memory.search",
        execution_mode=ToolExecutionMode.READ_ONLY,
        status=ToolExecutionStatus.FAILED,
        reason="invalid_tool_arguments",
        error_payload={
            "error_type": "ToolValidationError",
            "safe_message": "memory.search requires a non-empty query string",
        },
    )
    envelope = envelope_from_execution(execution)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value


def test_normalize_tool_error_maps_tool_errors() -> None:
    from app.tools.errors import normalize_tool_error

    exc = ToolValidationError("bad args", tool_name="memory.search")
    code, message = normalize_tool_error(exc, tool_name="memory.search")
    assert code == ToolExecutionErrorCode.INVALID_ARGUMENTS
    assert message == "bad args"


def test_real_executable_tools_use_envelope_codes() -> None:
    assert "memory.search" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert "project_context.get" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert "task.get" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert "task.list_recent" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert "marketing_brief.get" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert "content_asset.list" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert len(REAL_READ_ONLY_EXECUTABLE_TOOLS) == 12
