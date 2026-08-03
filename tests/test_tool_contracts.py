"""Agent tool contracts and registry tests — no execution."""

from __future__ import annotations

import pytest
from app.schemas.contracts import AgentType
from app.tools.contracts import ToolDefinition, ToolParameterSchema, ToolResult
from app.tools.errors import (
    ToolDisabledError,
    ToolNotAllowedForAgentError,
    ToolNotFoundError,
    ToolValidationError,
)
from app.tools.registry import ToolRegistry
from app.tools.security import (
    assert_no_tool_secrets,
    sanitize_tool_payload,
    sanitize_tool_result,
)
from fastapi.testclient import TestClient


def _sample_tool(
    *,
    name: str = "search_brief",
    enabled: bool = True,
    allowed_agent_types: list[AgentType] | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Search marketing brief snippets",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        enabled=enabled,
        allowed_agent_types=allowed_agent_types,
        metadata={"phase": "test"},
    )


def test_tool_definition_and_parameter_schema_create() -> None:
    parameter = ToolParameterSchema(
        name="query",
        description="Search query",
        json_schema={"type": "string"},
    )
    tool = _sample_tool()
    assert tool.name == "search_brief"
    assert tool.enabled is True
    assert parameter.name == "query"


def test_registry_register_get_and_list() -> None:
    registry = ToolRegistry()
    tool = _sample_tool()
    registry.register(tool)

    loaded = registry.get("search_brief")
    assert loaded.name == tool.name
    assert registry.list_for_agent(AgentType.RESEARCHER) == [tool]


def test_disabled_tool_is_not_listed_as_active() -> None:
    registry = ToolRegistry()
    registry.register(_sample_tool(name="disabled_tool", enabled=False))
    registry.register(_sample_tool(name="search_brief", enabled=True))

    active = registry.list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in active] == ["search_brief"]

    with pytest.raises(ToolDisabledError):
        registry.validate_tool_allowed("disabled_tool", AgentType.RESEARCHER)


def test_allowed_agent_types_are_filtered() -> None:
    registry = ToolRegistry()
    registry.register(
        _sample_tool(
            name="memory.search",
            allowed_agent_types=[AgentType.STRATEGIST],
        ),
    )

    assert registry.list_for_agent(AgentType.STRATEGIST)[0].name == "memory.search"
    assert registry.list_for_agent(AgentType.RESEARCHER) == []

    with pytest.raises(ToolNotAllowedForAgentError):
        registry.validate_tool_allowed("memory.search", AgentType.RESEARCHER)


def test_unknown_tool_raises_not_found() -> None:
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError, match="missing_tool"):
        registry.get("missing_tool")


def test_secrets_in_arguments_are_blocked() -> None:
    with pytest.raises(ToolValidationError, match="api_key"):
        assert_no_tool_secrets({"query": "hello", "api_key": "sk-test"})


def test_sanitize_tool_payload_redacts_secret_keys() -> None:
    sanitized = sanitize_tool_payload(
        {
            "query": "campaign",
            "token": "secret-token",
            "nested": {"password": "pw"},
        },
    )
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["query"] == "campaign"


def test_sanitize_tool_result_redacts_output_and_metadata() -> None:
    result = ToolResult(
        name="search_brief",
        status="succeeded",
        output={"summary": "ok", "authorization": "Bearer abc"},
        metadata={"cookie": "session-id"},
    )
    sanitized = sanitize_tool_result(result)
    assert sanitized.output["authorization"] == "[REDACTED]"
    assert sanitized.metadata["cookie"] == "[REDACTED]"


def test_dry_run_request_metadata_contains_tools_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Tools Meta Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "hello"}},
        headers=auth_headers,
    ).json()["id"]
    execute = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)
    assert execute.status_code == 200

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    tools_metadata = llm_request["request_metadata"]["tools_metadata"]
    assert tools_metadata["tools_enabled"] is True
    from tests.researcher_tool_names import (
        RESEARCHER_READ_ONLY_TOOL_COUNT,
        RESEARCHER_READ_ONLY_TOOL_NAMES,
    )

    assert tools_metadata["tool_count"] == RESEARCHER_READ_ONLY_TOOL_COUNT
    assert tools_metadata["tool_names"] == RESEARCHER_READ_ONLY_TOOL_NAMES
    assert tools_metadata["tool_calls_detected"] == 0
    assert tools_metadata["tool_calls_executed"] == 0
    assert tools_metadata["tool_calls_skipped"] == 0
    assert tools_metadata["tool_choice"] is None
    assert tools_metadata["permission_policy"]["execution_mode"] == "no_op"
    assert tools_metadata["permission_policy"]["agent_type"] == "researcher"
    assert tools_metadata["tool_executions"] == []

    detail = client.get(f"/llm-requests/{llm_request['id']}", headers=auth_headers).json()
    assert detail["response"]["raw_response"] == {}
    assert "tool_calls" not in detail["response"]["output_payload"]
