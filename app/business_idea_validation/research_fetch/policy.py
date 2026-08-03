"""Provider order and fallback eligibility policy."""

from __future__ import annotations

from app.core.config import Settings
from app.schemas.contracts import BivFetchOutcomeCode

_PROVIDER_ALIASES = {
    "direct_http": "trafilatura",
}

_DEFAULT_ORDER = ("firecrawl", "jina", "tavily", "trafilatura", "playwright")

# Outcomes that may trigger fallback to the next provider in chain.
_FALLBACK_ELIGIBLE: frozenset[BivFetchOutcomeCode] = frozenset(
    {
        BivFetchOutcomeCode.TIMEOUT,
        BivFetchOutcomeCode.CONNECTION_ERROR,
        BivFetchOutcomeCode.TLS_ERROR,
        BivFetchOutcomeCode.DNS_ERROR,
        BivFetchOutcomeCode.HTTP_429,
        BivFetchOutcomeCode.RATE_LIMITED,
        BivFetchOutcomeCode.HTTP_5XX,
        BivFetchOutcomeCode.PROVIDER_REJECTED,
        BivFetchOutcomeCode.CREDITS_EXHAUSTED,
        BivFetchOutcomeCode.EMPTY_CONTENT,
        BivFetchOutcomeCode.CONTENT_TOO_SHORT,
        BivFetchOutcomeCode.JAVASCRIPT_REQUIRED,
        BivFetchOutcomeCode.UNSUPPORTED_CONTENT_TYPE,
        BivFetchOutcomeCode.UNKNOWN_ERROR,
    }
)

_NO_FALLBACK: frozenset[BivFetchOutcomeCode] = frozenset(
    {
        BivFetchOutcomeCode.MALFORMED_CONTENT,
        BivFetchOutcomeCode.UNSAFE_URL,
        BivFetchOutcomeCode.ROBOTS_BLOCKED,
        BivFetchOutcomeCode.HTTP_401,
        BivFetchOutcomeCode.HTTP_403,
        BivFetchOutcomeCode.DUPLICATE_URL,
        BivFetchOutcomeCode.CANCELLED,
    }
)


def normalize_provider_name(name: str) -> str:
    key = (name or "").strip().lower()
    return _PROVIDER_ALIASES.get(key, key)


def parse_provider_order(settings: Settings) -> list[str]:
    raw = (settings.research_fetch_provider_order or "").strip()
    if not raw:
        names = list(_DEFAULT_ORDER)
    else:
        names = [normalize_provider_name(p) for p in raw.split(",") if p.strip()]
    if not settings.research_fetch_playwright_enabled:
        names = [n for n in names if n != "playwright"]
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped


def is_fallback_eligible(outcome: BivFetchOutcomeCode, *, error_class: str | None = None) -> bool:
    if outcome in _NO_FALLBACK:
        return False
    if outcome == BivFetchOutcomeCode.PROVIDER_REJECTED and error_class in {
        "invalid_credentials",
        "auth_error",
        "not_configured",
    }:
        return False
    if error_class == "unsafe_url":
        return False
    if error_class == "robots_denied":
        return False
    return outcome in _FALLBACK_ELIGIBLE or (
        outcome == BivFetchOutcomeCode.PROVIDER_REJECTED
        and error_class in {"credits_exhausted", "rate_limited", "provider_unavailable", "timeout"}
    )


def max_provider_attempts(settings: Settings) -> int:
    return settings.research_fetch_max_provider_attempts
