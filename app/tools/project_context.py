"""project_context.get tool definition and argument schema."""

from __future__ import annotations

PROJECT_CONTEXT_GET_TOOL_NAME = "project_context.get"

PROJECT_CONTEXT_GET_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "include_agents": {
            "type": "boolean",
            "default": True,
        },
        "include_recent_tasks": {
            "type": "boolean",
            "default": True,
        },
        "include_memory_summary": {
            "type": "boolean",
            "default": False,
        },
        "task_limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 5,
        },
        "memory_limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 5,
        },
    },
    "additionalProperties": False,
}
