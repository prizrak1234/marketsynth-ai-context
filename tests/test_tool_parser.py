"""Tool call parser tests."""

from __future__ import annotations

import pytest
from app.tools.errors import ToolParseError, ToolValidationError
from app.tools.parser import parse_tool_calls


def test_parses_openai_like_tool_call() -> None:
    calls = parse_tool_calls(
        [
            {
                "id": "call_abc",
                "type": "function",
                "function": {
                    "name": "search_brief",
                    "arguments": '{"query": "audience"}',
                },
            },
        ],
    )
    assert len(calls) == 1
    assert calls[0].id == "call_abc"
    assert calls[0].name == "search_brief"
    assert calls[0].arguments == {"query": "audience"}


def test_parses_arguments_json_string() -> None:
    calls = parse_tool_calls(
        [
            {
                "function": {
                    "name": "summarize",
                    "arguments": '{"topic":"Q2","limit":3}',
                },
            },
        ],
    )
    assert calls[0].arguments == {"topic": "Q2", "limit": 3}


def test_accepts_arguments_dict() -> None:
    calls = parse_tool_calls(
        [
            {
                "function": {
                    "name": "summarize",
                    "arguments": {"topic": "Q2"},
                },
            },
        ],
    )
    assert calls[0].arguments == {"topic": "Q2"}


def test_rejects_bad_json_safely() -> None:
    with pytest.raises(ToolParseError, match="invalid JSON"):
        parse_tool_calls(
            [
                {
                    "function": {
                        "name": "summarize",
                        "arguments": "{not-json",
                    },
                },
            ],
        )


def test_rejects_secrets_in_arguments() -> None:
    with pytest.raises(ToolValidationError, match="api_key"):
        parse_tool_calls(
            [
                {
                    "function": {
                        "name": "summarize",
                        "arguments": {"query": "hello", "api_key": "sk-test"},
                    },
                },
            ],
        )
