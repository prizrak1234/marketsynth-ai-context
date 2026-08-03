"""Safe URL previews for webhook delivery logs."""

from __future__ import annotations

from urllib.parse import urlparse


def build_target_url_preview(url: str) -> str:
    """Return scheme + host + path only (no query, fragment, or credentials)."""
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    host = parsed.hostname or ""
    if parsed.port and parsed.port not in (80, 443):
        host = f"{host}:{parsed.port}"
    path = parsed.path or "/"
    return f"{scheme}://{host}{path}"
