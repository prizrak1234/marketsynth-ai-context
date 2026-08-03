"""SSRF-safe URL validation for research fetch."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

_LITERAL_ELLIPSIS = re.compile(r"\.{3,}|…")
_CREDENTIALS_IN_URL = re.compile(r"://[^/@]+:[^/@]+@")


def _host_blocked(host: str) -> str | None:
    lowered = (host or "").strip().lower().rstrip(".")
    if not lowered:
        return "invalid_url"
    if lowered in {"localhost", "localhost.localdomain"}:
        return "unsafe_url"
    if lowered.endswith(".localhost") or lowered.endswith(".local"):
        return "unsafe_url"
    if lowered == "0.0.0.0":
        return "unsafe_url"
    # Strip brackets for IPv6
    bare = lowered[1:-1] if lowered.startswith("[") and lowered.endswith("]") else lowered
    try:
        addr = ipaddress.ip_address(bare)
    except ValueError:
        return None
    if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved:
        return "unsafe_url"
    if addr.is_multicast:
        return "unsafe_url"
    return None


def validate_fetch_url(url: str) -> tuple[bool, str | None]:
    """Return (safe, safe_error_code). Rejects SSRF-prone targets."""
    raw = (url or "").strip()
    if not raw or _LITERAL_ELLIPSIS.search(raw):
        return False, "invalid_url"
    if _CREDENTIALS_IN_URL.search(raw):
        return False, "unsafe_url"
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return False, "unsafe_url"
    host = parsed.hostname
    if not host:
        return False, "invalid_url"
    blocked = _host_blocked(host)
    if blocked:
        return False, blocked
    return True, None


def resolve_host_is_public(host: str) -> tuple[bool, str | None]:
    """DNS resolution check — reject if any resolved address is non-public."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, "dns_error"
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        blocked = _host_blocked(ip_str)
        if blocked:
            return False, blocked
    return True, None


def validate_redirect_target(url: str) -> tuple[bool, str | None]:
    """Re-validate URL after redirect."""
    return validate_fetch_url(url)
