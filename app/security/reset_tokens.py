"""One-time password reset tokens — raw token never persisted."""

from __future__ import annotations

import hashlib
import hmac
import secrets

RESET_TOKEN_PREFIX = "mpr_"


def generate_reset_token() -> tuple[str, str]:
    """Return (plain_token, token_hash). Plain returned once to operator."""
    plain = f"{RESET_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    return plain, hash_reset_token(plain)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reset_tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
