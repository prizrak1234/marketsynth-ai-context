"""Convert ToolDefinition objects to OpenAI-compatible function tool schemas."""

from __future__ import annotations

import re
from typing import Any

from app.tools.contracts import ToolDefinition
from app.tools.errors import ToolValidationError
from app.tools.security import assert_no_tool_secrets

OPENAI_FUNCTION_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")


def _validate_openai_function_name(name: str) -> None:
    if not OPENAI_FUNCTION_NAME_PATTERN.fullmatch(name):
        raise ToolValidationError(
            f"Tool name is invalid for OpenAI function calling: {name}",
            tool_name=name,
            original_error_type="InvalidOpenAIToolName",
        )


def _validate_parameters_schema(schema: dict[str, Any], *, tool_name: str) -> dict[str, Any]:
    if not isinstance(schema, dict):
        raise ToolValidationError(
            "Tool parameters schema must be a JSON object",
            tool_name=tool_name,
            original_error_type="InvalidParametersSchema",
        )
    schema_type = schema.get("type", "object")
    if schema_type != "object":
        raise ToolValidationError(
            "Tool parameters schema type must be object",
            tool_name=tool_name,
            original_error_type="InvalidParametersSchemaType",
        )
    assert_no_tool_secrets(schema)
    return schema


def tool_definition_to_openai_tool(tool: ToolDefinition) -> dict[str, Any]:
    if not tool.enabled:
        raise ToolValidationError(
            f"Disabled tool cannot be converted: {tool.name}",
            tool_name=tool.name,
            original_error_type="DisabledTool",
        )

    _validate_openai_function_name(tool.name)
    parameters = _validate_parameters_schema(tool.parameters_schema, tool_name=tool.name)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        },
    }


def tool_definitions_to_openai_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for tool in tools:
        if not tool.enabled:
            continue
        converted.append(tool_definition_to_openai_tool(tool))
    return converted
