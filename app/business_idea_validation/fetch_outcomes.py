"""Fetch outcome taxonomy and safe error mapping."""

from __future__ import annotations

import re

from app.business_tools.contracts import BusinessToolError
from app.schemas.contracts import BivFetchOutcomeCode

_RETRYABLE = frozenset(
    {
        BivFetchOutcomeCode.TIMEOUT,
        BivFetchOutcomeCode.CONNECTION_ERROR,
        BivFetchOutcomeCode.TLS_ERROR,
        BivFetchOutcomeCode.HTTP_429,
        BivFetchOutcomeCode.RATE_LIMITED,
        BivFetchOutcomeCode.HTTP_5XX,
        BivFetchOutcomeCode.UNKNOWN_ERROR,
    }
)

_JS_HEAVY = re.compile(
    r"(enable javascript|javascript is disabled|requires javascript|"
    r"document\.getelementbyid|<noscript)",
    re.I,
)


def is_retryable(outcome: BivFetchOutcomeCode) -> bool:
    return outcome in _RETRYABLE


def map_business_tool_error(category: str) -> BivFetchOutcomeCode:
    mapping = {
        "timeout": BivFetchOutcomeCode.TIMEOUT,
        "rate_limited": BivFetchOutcomeCode.RATE_LIMITED,
        "invalid_credentials": BivFetchOutcomeCode.HTTP_401,
        "auth_error": BivFetchOutcomeCode.HTTP_401,
        "invalid_url": BivFetchOutcomeCode.MALFORMED_CONTENT,
        "provider_unavailable": BivFetchOutcomeCode.CONNECTION_ERROR,
        "provider_error": BivFetchOutcomeCode.PROVIDER_REJECTED,
        "provider_rejected": BivFetchOutcomeCode.PROVIDER_REJECTED,
        "credits_exhausted": BivFetchOutcomeCode.CREDITS_EXHAUSTED,
        "not_configured": BivFetchOutcomeCode.PROVIDER_REJECTED,
        "unsafe_url": BivFetchOutcomeCode.UNSAFE_URL,
        "robots_denied": BivFetchOutcomeCode.ROBOTS_BLOCKED,
    }
    if category.startswith("http_"):
        try:
            return BivFetchOutcomeCode(category)
        except ValueError:
            pass
    return mapping.get(category, BivFetchOutcomeCode.UNKNOWN_ERROR)


def map_http_status(status: int) -> BivFetchOutcomeCode:
    if status == 401:
        return BivFetchOutcomeCode.HTTP_401
    if status == 403:
        return BivFetchOutcomeCode.HTTP_403
    if status == 404:
        return BivFetchOutcomeCode.HTTP_404
    if status == 409:
        return BivFetchOutcomeCode.HTTP_409
    if status == 429:
        return BivFetchOutcomeCode.HTTP_429
    if status >= 500:
        return BivFetchOutcomeCode.HTTP_5XX
    return BivFetchOutcomeCode.UNKNOWN_ERROR


def map_exception(exc: Exception) -> tuple[BivFetchOutcomeCode, str, str | None]:
    name = type(exc).__name__
    if isinstance(exc, TimeoutError):
        return BivFetchOutcomeCode.TIMEOUT, name, "Request timed out."
    if isinstance(exc, BusinessToolError):
        return map_business_tool_error(exc.category), name, (exc.user_message or str(exc))[:500]
    msg = str(exc).lower()
    if "dns" in msg or "getaddrinfo" in msg:
        return BivFetchOutcomeCode.DNS_ERROR, name, "DNS resolution failed."
    if "ssl" in msg or "tls" in msg or "certificate" in msg:
        return BivFetchOutcomeCode.TLS_ERROR, name, "TLS handshake failed."
    if "connect" in msg or "connection" in msg:
        return BivFetchOutcomeCode.CONNECTION_ERROR, name, "Connection failed."
    return BivFetchOutcomeCode.UNKNOWN_ERROR, name, "Fetch failed."


def classify_extracted_body(body: str, *, content_type: str | None = None) -> BivFetchOutcomeCode:
    text = (body or "").strip()
    if not text:
        return BivFetchOutcomeCode.EMPTY_CONTENT
    if len(text) < 80:
        return BivFetchOutcomeCode.CONTENT_TOO_SHORT
    if _JS_HEAVY.search(text[:2000]) and len(text) < 400:
        return BivFetchOutcomeCode.JAVASCRIPT_REQUIRED
    ct = (content_type or "").lower()
    if ct and not any(t in ct for t in ("text", "html", "json", "markdown", "xml")):
        if "pdf" in ct or "office" in ct or "octet-stream" in ct:
            return BivFetchOutcomeCode.UNSUPPORTED_CONTENT_TYPE
    return BivFetchOutcomeCode.SUCCESS


def safe_error_message(outcome: BivFetchOutcomeCode) -> str:
    messages = {
        BivFetchOutcomeCode.SUCCESS: "OK",
        BivFetchOutcomeCode.TIMEOUT: "Fetch timed out.",
        BivFetchOutcomeCode.RATE_LIMITED: "Provider rate limit reached.",
        BivFetchOutcomeCode.HTTP_403: "Access forbidden.",
        BivFetchOutcomeCode.HTTP_404: "Page not found.",
        BivFetchOutcomeCode.HTTP_429: "Too many requests.",
        BivFetchOutcomeCode.EMPTY_CONTENT: "Empty page content.",
        BivFetchOutcomeCode.CONTENT_TOO_SHORT: "Insufficient page text.",
        BivFetchOutcomeCode.JAVASCRIPT_REQUIRED: "Page requires JavaScript rendering.",
        BivFetchOutcomeCode.DUPLICATE_URL: "Duplicate URL skipped.",
        BivFetchOutcomeCode.UNSAFE_URL: "URL blocked by security policy.",
        BivFetchOutcomeCode.CREDITS_EXHAUSTED: "Provider credits exhausted.",
        BivFetchOutcomeCode.ROBOTS_BLOCKED: "Blocked by robots policy.",
    }
    return messages.get(outcome, "Fetch could not complete.")
