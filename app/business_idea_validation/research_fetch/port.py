"""Domain port for research URL fetch — provider-independent contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID


class ResearchFetchStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CREDITS_EXHAUSTED = "credits_exhausted"
    ROBOTS_DENIED = "robots_denied"
    UNSUPPORTED_CONTENT = "unsupported_content"
    EMPTY_CONTENT = "empty_content"
    INVALID_URL = "invalid_url"
    UNSAFE_URL = "unsafe_url"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    EXTRACTION_FAILED = "extraction_failed"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(slots=True)
class FetchRequest:
    tenant_id: str | None
    research_run_id: UUID
    source_url: str
    normalized_url: str
    requested_at: datetime
    timeout_seconds: float
    max_content_bytes: int
    preferred_content_type: str | None = None
    trace_context: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class FetchAttemptLineage:
    provider: str
    status: ResearchFetchStatus
    safe_error_code: str | None = None
    latency_ms: int | None = None
    attempt_number: int = 1


@dataclass(slots=True)
class FetchResult:
    provider: str
    source_url: str
    final_url: str
    normalized_url: str
    fetched_at: datetime
    status: ResearchFetchStatus
    http_status: int | None
    content_type: str | None
    title: str | None
    raw_html: str | None
    extracted_text: str
    markdown: str | None
    language: str | None
    content_hash: str
    byte_count: int
    latency_ms: int
    attempt_number: int
    fallback_reason: str | None = None
    safe_error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    attempt_lineage: list[FetchAttemptLineage] = field(default_factory=list)


class ResearchFetchPort(Protocol):
    provider_name: str

    def is_available(self) -> bool: ...

    async def fetch(self, request: FetchRequest) -> FetchResult: ...
