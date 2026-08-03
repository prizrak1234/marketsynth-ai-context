"""Map domain fetch status to BIV outcome codes."""

from __future__ import annotations

from app.business_idea_validation.research_fetch.port import ResearchFetchStatus
from app.schemas.contracts import BivFetchOutcomeCode

_STATUS_TO_OUTCOME: dict[ResearchFetchStatus, BivFetchOutcomeCode] = {
    ResearchFetchStatus.SUCCEEDED: BivFetchOutcomeCode.SUCCESS,
    ResearchFetchStatus.TIMEOUT: BivFetchOutcomeCode.TIMEOUT,
    ResearchFetchStatus.RATE_LIMITED: BivFetchOutcomeCode.RATE_LIMITED,
    ResearchFetchStatus.CREDITS_EXHAUSTED: BivFetchOutcomeCode.CREDITS_EXHAUSTED,
    ResearchFetchStatus.NOT_FOUND: BivFetchOutcomeCode.HTTP_404,
    ResearchFetchStatus.BLOCKED: BivFetchOutcomeCode.HTTP_403,
    ResearchFetchStatus.ROBOTS_DENIED: BivFetchOutcomeCode.ROBOTS_BLOCKED,
    ResearchFetchStatus.UNSUPPORTED_CONTENT: BivFetchOutcomeCode.UNSUPPORTED_CONTENT_TYPE,
    ResearchFetchStatus.EMPTY_CONTENT: BivFetchOutcomeCode.EMPTY_CONTENT,
    ResearchFetchStatus.INVALID_URL: BivFetchOutcomeCode.MALFORMED_CONTENT,
    ResearchFetchStatus.UNSAFE_URL: BivFetchOutcomeCode.UNSAFE_URL,
    ResearchFetchStatus.PROVIDER_UNAVAILABLE: BivFetchOutcomeCode.CONNECTION_ERROR,
    ResearchFetchStatus.EXTRACTION_FAILED: BivFetchOutcomeCode.EMPTY_CONTENT,
    ResearchFetchStatus.UNKNOWN_FAILURE: BivFetchOutcomeCode.UNKNOWN_ERROR,
}


def invalid_url_status(code: str | None) -> ResearchFetchStatus:
    if code == "unsafe_url":
        return ResearchFetchStatus.UNSAFE_URL
    return ResearchFetchStatus.INVALID_URL


def status_to_outcome(status: ResearchFetchStatus) -> BivFetchOutcomeCode:
    return _STATUS_TO_OUTCOME.get(status, BivFetchOutcomeCode.UNKNOWN_ERROR)
