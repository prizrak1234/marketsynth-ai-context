"""Parse provider tool_calls into normalized ToolCall objects."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.tools.contracts import ToolCall
from app.tools.errors import ToolParseError, ToolValidationError
from app.tools.security import assert_no_tool_secrets, sanitize_tool_payload


def _coerce_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    if hasattr(raw, "__dict__"):
        return {
            key: value
            for key, value in vars(raw).items()
            if not key.startswith("_")
        }
    raise ToolParseError(
        "Tool call must be a mapping-like object",
        original_error_type="InvalidToolCallShape",
    )


def _extract_function_block(raw: dict[str, Any]) -> dict[str, Any]:
    function_block = raw.get("function")
    if function_block is None:
        if "name" in raw and "arguments" in raw:
            return {"name": raw.get("name"), "arguments": raw.get("arguments")}
        raise ToolParseError(
            "Tool call is missing function block",
            original_error_type="MissingFunctionBlock",
        )
    if isinstance(function_block, Mapping):
        return dict(function_block)
    if hasattr(function_block, "model_dump"):
        return function_block.model_dump()
    return {
        "name": getattr(function_block, "name", None),
        "arguments": getattr(function_block, "arguments", None),
    }


def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
    if raw_arguments is None:
        return {}
    if isinstance(raw_arguments, Mapping):
        return dict(raw_arguments)
    if isinstance(raw_arguments, str):
        text = raw_arguments.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ToolParseError(
                "Tool call arguments contain invalid JSON",
                original_error_type="InvalidToolArgumentsJSON",
            ) from exc
        if not isinstance(parsed, dict):
            raise ToolParseError(
                "Tool call arguments JSON must decode to an object",
                original_error_type="InvalidToolArgumentsShape",
            )
        return parsed
    raise ToolParseError(
        "Tool call arguments must be a JSON object or string",
        original_error_type="InvalidToolArgumentsType",
    )


def _parse_single_tool_call(raw: Any, index: int) -> ToolCall:
    try:
        payload = _coerce_mapping(raw)
        function_block = _extract_function_block(payload)
        name = function_block.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ToolParseError(
                f"Tool call at index {index} is missing function name",
                tool_name=str(name) if name is not None else None,
                original_error_type="MissingToolName",
            )

        raw_arguments = function_block.get("arguments")
        arguments = _parse_arguments(raw_arguments)
        assert_no_tool_secrets(arguments)
        sanitized_arguments = sanitize_tool_payload(arguments)

        call_id = payload.get("id")
        if call_id is not None and not isinstance(call_id, str):
            call_id = str(call_id)

        raw_arguments_value: dict[str, Any] | str | None
        if isinstance(raw_arguments, str):
            raw_arguments_value = json.dumps(sanitized_arguments, sort_keys=True)
        elif isinstance(raw_arguments, Mapping):
            raw_arguments_value = sanitized_arguments
        else:
            raw_arguments_value = None

        return ToolCall(
            id=call_id,
            name=name,
            arguments=sanitized_arguments,
            raw_arguments=raw_arguments_value,
        )
    except ToolParseError:
        raise
    except ToolValidationError:
        raise
    except Exception as exc:
        raise ToolParseError(
            f"Failed to parse tool call at index {index}",
            original_error_type=type(exc).__name__,
        ) from exc


def parse_tool_calls(raw_tool_calls: list[Any] | None) -> list[ToolCall]:
    if not raw_tool_calls:
        return []

    parsed: list[ToolCall] = []
    for index, raw in enumerate(raw_tool_calls):
        call = _parse_single_tool_call(raw, index)
        parsed.append(call)
    return parsed
