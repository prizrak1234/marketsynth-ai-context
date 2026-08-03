"""task.get and task.list_recent tool definitions and argument schemas."""

from __future__ import annotations

TASK_GET_TOOL_NAME = "task.get"
TASK_LIST_RECENT_TOOL_NAME = "task.list_recent"

TASK_FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "owner_id",
        "project_id",
        "agent_id",
        "agent_run_id",
        "run_id",
    },
)

TASK_GET_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Task id inside current project",
        },
        "include_metadata": {
            "type": "boolean",
            "default": True,
        },
    },
    "required": ["task_id"],
    "additionalProperties": False,
}

TASK_LIST_RECENT_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 5,
        },
        "status": {
            "type": "string",
            "description": "Optional task status filter",
        },
        "include_metadata": {
            "type": "boolean",
            "default": False,
        },
    },
    "additionalProperties": False,
}
