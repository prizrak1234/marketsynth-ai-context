"""Domain tool errors — safe messages only, no secrets."""

from __future__ import annotations

from app.tools.result_contracts import ToolExecutionErrorCode


class ToolError(Exception):
    error_type = "ToolError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
        error_code: ToolExecutionErrorCode | None = None,
    ) -> None:
        self.safe_message = safe_message.strip() or "Tool error"
        self.tool_name = tool_name
        self.original_error_type = original_error_type
        self.error_code = error_code
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        return self.safe_message


class ToolNotFoundError(ToolError):
    error_type = "ToolNotFoundError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=ToolExecutionErrorCode.NOT_FOUND,
        )


class ToolDisabledError(ToolError):
    error_type = "ToolDisabledError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=ToolExecutionErrorCode.PERMISSION_DENIED,
        )


class ToolNotAllowedForAgentError(ToolError):
    error_type = "ToolNotAllowedForAgentError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=ToolExecutionErrorCode.PERMISSION_DENIED,
        )


class ToolValidationError(ToolError):
    error_type = "ToolValidationError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=ToolExecutionErrorCode.INVALID_ARGUMENTS,
        )


class ToolInvalidArgumentsError(ToolValidationError):
    error_type = "ToolInvalidArgumentsError"


class ToolExecutionError(ToolError):
    error_type = "ToolExecutionError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
        error_code: ToolExecutionErrorCode = ToolExecutionErrorCode.EXECUTION_FAILED,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=error_code,
        )


class ToolPermissionDeniedError(ToolError):
    error_type = "ToolPermissionDeniedError"

    def __init__(
        self,
        safe_message: str,
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=ToolExecutionErrorCode.PERMISSION_DENIED,
        )


class ToolResultTooLargeError(ToolError):
    error_type = "ToolResultTooLargeError"

    def __init__(
        self,
        safe_message: str = "Tool result exceeds size limit",
        *,
        tool_name: str | None = None,
        original_error_type: str | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            tool_name=tool_name,
            original_error_type=original_error_type,
            error_code=ToolExecutionErrorCode.RESULT_TOO_LARGE,
        )


class ToolParseError(ToolError):
    error_type = "ToolParseError"


def normalize_tool_error(
    exc: Exception,
    *,
    tool_name: str,
    default_code: ToolExecutionErrorCode = ToolExecutionErrorCode.EXECUTION_FAILED,
) -> tuple[ToolExecutionErrorCode, str]:
    if isinstance(exc, ToolError):
        code = exc.error_code or default_code
        return code, exc.safe_message

    return default_code, "Tool execution failed"
