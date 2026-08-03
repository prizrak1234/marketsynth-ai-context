"""Browser session token minting — raw token never persisted."""

from __future__ import annotations

import hashlib
import secrets

SESSION_TOKEN_PREFIX = "mss_"


def generate_session_token() -> tuple[str, str]:
    """Return (plain_token, token_hash). Plain shown only via Set-Cookie."""
    plain = f"{SESSION_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    return plain, hash_session_token(plain)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
