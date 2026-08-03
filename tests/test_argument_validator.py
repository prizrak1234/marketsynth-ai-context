"""Phase 2.21 — centralized tool argument validation."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType
from app.schemas.crud import ProjectCreate
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.argument_validator import validate_tool_arguments
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.registry import TASK_GET_TOOL, TASK_LIST_RECENT_TOOL, ToolRegistry
from app.tools.result_contracts import ToolExecutionErrorCode
from sqlalchemy.ext.asyncio import AsyncSession


def _context(**kwargs) -> ToolExecutionContext:
    defaults = {
        "owner_id": uuid4(),
        "project_id": uuid4(),
        "agent_id": uuid4(),
        "agent_type": AgentType.RESEARCHER,
        "agent_run_id": uuid4(),
    }
    defaults.update(kwargs)
    return ToolExecutionContext(**defaults)


def test_unknown_argument_rejected_for_task_get() -> None:
    result = validate_tool_arguments(
        TASK_GET_TOOL,
        {"task_id": str(uuid4()), "unexpected": True},
    )
    assert result.ok is False
    assert result.field == "unexpected"


def test_forbidden_owner_id_rejected_for_task_get() -> None:
    result = validate_tool_arguments(
        TASK_GET_TOOL,
        {"task_id": str(uuid4()), "owner_id": str(uuid4())},
    )
    assert result.ok is False
    assert result.field == "owner_id"


def test_invalid_limit_rejected_for_task_list_recent() -> None:
    result = validate_tool_arguments(TASK_LIST_RECENT_TOOL, {"limit": 99})
    assert result.ok is False
    assert result.field == "limit"


def test_missing_required_task_id_rejected() -> None:
    result = validate_tool_arguments(TASK_GET_TOOL, {"include_metadata": True})
    assert result.ok is False
    assert result.field == "task_id"


@pytest.mark.asyncio
async def test_executor_returns_invalid_arguments_envelope_and_audit(
    db_session: AsyncSession,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9301))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Validator Project"),
    )
    registry = ToolRegistry()
    registry.register(TASK_GET_TOOL)
    executor = SafeNoOpToolExecutor(
        registry,
        session=db_session,
        audit_service=ToolExecutionLogService(db_session),
    )
    context = _context(owner_id=owner.id, project_id=project.id)
    tool_result = await executor.execute(
        ToolCall(
            id="call_invalid_args",
            name="task.get",
            arguments={"task_id": str(uuid4()), "owner_id": str(uuid4())},
        ),
        context,
    )
    await db_session.commit()

    assert tool_result.status == "failed"
    envelope = tool_result.output
    assert isinstance(envelope, dict)
    assert envelope.get("ok") is False
    assert envelope["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value
    assert tool_result.metadata.get("reason") == "invalid_arguments"

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        context.owner_id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].reason == "invalid_arguments"
    assert "owner_id" in json.dumps(logs[0].error_payload or {})
