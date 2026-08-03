"""OpenAI tool schema conversion tests."""

from __future__ import annotations

import pytest
from app.tools.contracts import ToolDefinition
from app.tools.errors import ToolValidationError
from app.tools.openai_schema import tool_definition_to_openai_tool, tool_definitions_to_openai_tools


def _sample_tool(**overrides: object) -> ToolDefinition:
    payload = {
        "name": "search_brief",
        "description": "Search marketing brief snippets",
        "parameters_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        "enabled": True,
    }
    payload.update(overrides)
    return ToolDefinition(**payload)


def test_converts_enabled_tool() -> None:
    converted = tool_definition_to_openai_tool(_sample_tool())
    assert converted == {
        "type": "function",
        "function": {
            "name": "search_brief",
            "description": "Search marketing brief snippets",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        },
    }


def test_rejects_invalid_name() -> None:
    with pytest.raises(ToolValidationError, match="invalid for OpenAI"):
        tool_definition_to_openai_tool(_sample_tool(name="bad name!"))


def test_rejects_disabled_tool() -> None:
    with pytest.raises(ToolValidationError, match="Disabled tool"):
        tool_definition_to_openai_tool(_sample_tool(enabled=False))


def test_rejects_non_object_parameters() -> None:
    with pytest.raises(ToolValidationError, match="type must be object"):
        tool_definition_to_openai_tool(
            _sample_tool(parameters_schema={"type": "string"}),
        )


def test_rejects_schema_with_secret_like_keys() -> None:
    with pytest.raises(ToolValidationError, match="api_key"):
        tool_definition_to_openai_tool(
            _sample_tool(
                parameters_schema={
                    "type": "object",
                    "properties": {"api_key": {"type": "string"}},
                },
            ),
        )


def test_batch_converter_skips_disabled_tools() -> None:
    converted = tool_definitions_to_openai_tools(
        [
            _sample_tool(name="search_brief", enabled=True),
            _sample_tool(name="legacy_tool", enabled=False),
        ],
    )
    assert [tool["function"]["name"] for tool in converted] == ["search_brief"]
