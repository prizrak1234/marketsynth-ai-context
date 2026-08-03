"""Validate tool arguments against JSON-schema-like definitions before dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.tools.contracts import ToolDefinition
from app.tools.executors.project_context_get import (
    FORBIDDEN_ARGUMENT_KEYS as PROJECT_CONTEXT_FORBIDDEN,
)
from app.tools.task_tools import TASK_FORBIDDEN_ARGUMENT_KEYS

TOOL_FORBIDDEN_ARGUMENT_KEYS: dict[str, frozenset[str]] = {
    "memory.search": frozenset(
        {
            "owner_id",
            "project_id",
            "agent_run_id",
            "run_id",
        },
    ),
    "project_context.get": PROJECT_CONTEXT_FORBIDDEN,
    "task.get": TASK_FORBIDDEN_ARGUMENT_KEYS,
    "task.list_recent": TASK_FORBIDDEN_ARGUMENT_KEYS | frozenset({"task_id"}),
}


@dataclass(frozen=True)
class ToolArgumentValidationResult:
    ok: bool
    message: str = ""
    field: str | None = None


def validate_tool_arguments(
    tool: ToolDefinition,
    arguments: Any,
    *,
    forbidden_keys: frozenset[str] | None = None,
) -> ToolArgumentValidationResult:
    if not isinstance(arguments, dict):
        return ToolArgumentValidationResult(
            ok=False,
            message="Tool arguments must be a JSON object",
        )

    extra_forbidden = forbidden_keys or TOOL_FORBIDDEN_ARGUMENT_KEYS.get(tool.name, frozenset())
    for key in extra_forbidden:
        if key in arguments:
            return ToolArgumentValidationResult(
                ok=False,
                message=f"Tool does not accept argument: {key}",
                field=key,
            )

    schema = tool.parameters_schema
    if not isinstance(schema, dict) or schema.get("type", "object") != "object":
        return ToolArgumentValidationResult(ok=True)

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}

    additional_properties = schema.get("additionalProperties", True)
    if additional_properties is False:
        unknown = set(arguments) - set(properties)
        if unknown:
            first = sorted(unknown)[0]
            return ToolArgumentValidationResult(
                ok=False,
                message=f"Unknown argument: {first}",
                field=first,
            )

    required = schema.get("required", [])
    if isinstance(required, list):
        for field_name in required:
            if not isinstance(field_name, str):
                continue
            if field_name not in arguments:
                return ToolArgumentValidationResult(
                    ok=False,
                    message=f"Missing required argument: {field_name}",
                    field=field_name,
                )

    for field_name, raw_value in arguments.items():
        field_schema = properties.get(field_name)
        if field_schema is None:
            continue
        if not isinstance(field_schema, dict):
            continue
        field_error = _validate_field(field_name, raw_value, field_schema)
        if field_error is not None:
            return field_error

    return ToolArgumentValidationResult(ok=True)


def _validate_field(
    field_name: str,
    value: Any,
    field_schema: dict[str, Any],
) -> ToolArgumentValidationResult | None:
    expected_type = field_schema.get("type")
    if expected_type == "string":
        if not isinstance(value, str):
            return ToolArgumentValidationResult(
                ok=False,
                message=f"{field_name} must be a string",
                field=field_name,
            )
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return ToolArgumentValidationResult(
                ok=False,
                message=f"{field_name} must be an integer",
                field=field_name,
            )
        minimum = field_schema.get("minimum")
        maximum = field_schema.get("maximum")
        if isinstance(minimum, int) and value < minimum:
            return ToolArgumentValidationResult(
                ok=False,
                message=f"{field_name} must be at least {minimum}",
                field=field_name,
            )
        if isinstance(maximum, int) and value > maximum:
            return ToolArgumentValidationResult(
                ok=False,
                message=f"{field_name} must be at most {maximum}",
                field=field_name,
            )
    elif expected_type == "boolean" and not isinstance(value, bool):
        return ToolArgumentValidationResult(
            ok=False,
            message=f"{field_name} must be a boolean",
            field=field_name,
        )
    return None
