"""Domain-level exceptions — no FastAPI imports here."""


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""


class ConflictError(Exception):
    """Raised when an operation conflicts with current entity state."""


class InvalidStateError(ConflictError):
    """Raised when an operation is invalid for the current entity state."""


class ResearchPipelineError(ConflictError):
    """Raised when BIV research pipeline hard-fails validation."""

    def __init__(
        self,
        failure_code: str,
        *,
        failure_stage: str = "pipeline",
        retryable: bool = False,
        safe_message: str | None = None,
    ) -> None:
        self.failure_code = failure_code
        self.failure_stage = failure_stage
        self.retryable = retryable
        self.safe_message = safe_message or failure_code
        super().__init__(failure_code)


class OwnershipError(Exception):
    """Raised when the caller does not own the requested resource."""


class DuplicateResourceError(ConflictError):
    """Raised when a unique resource already exists."""


class ExecutorError(Exception):
    """Raised when executor pipeline fails after cleanup."""


class RateLimitExceededError(ConflictError):
    """Raised when beta soft limits are exceeded (Phase AI.87)."""

    def __init__(
        self,
        *,
        error_code: str,
        safe_message: str,
        limit: int | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.limit = limit


class BetaAccessDeniedError(Exception):
    """Raised when closed-beta gate blocks MVP usage (Phase AI.96)."""

    def __init__(self, *, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class ApiClientError(Exception):
    """Base for API errors with a stable client-facing envelope (Phase AI.88)."""

    def __init__(
        self,
        *,
        error_code: str,
        safe_message: str,
        status_code: int = 400,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.status_code = status_code
        self.details = details or {}
