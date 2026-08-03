"""Publication dispatch outcome (Phase 6.1+)."""

from __future__ import annotations

from dataclasses import dataclass

from app.publishing.contracts import PublicationDeliveryLogStatus

RESPONSE_PREVIEW_MAX = 500


@dataclass(frozen=True)
class PublicationDispatchResult:
    status: PublicationDeliveryLogStatus
    duration_ms: int
    error_code: str | None = None
    error_message: str | None = None
    response_preview: str | None = None


def truncate_preview(value: str, *, max_length: int = RESPONSE_PREVIEW_MAX) -> str:
    cleaned = value.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 3]}..."
