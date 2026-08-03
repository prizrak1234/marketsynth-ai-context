"""One-time pilot invitation tokens — raw token never persisted."""

from __future__ import annotations

import hashlib
import hmac
import secrets

INVITE_TOKEN_PREFIX = "mpi_"


def generate_invite_token() -> tuple[str, str]:
    """Return (plain_token, token_hash). Plain is returned only once to operators."""
    plain = f"{INVITE_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    return plain, hash_invite_token(plain)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invite_tokens_equal(a: str, b: str) -> bool:
    """Constant-time compare for already-hashed values."""
    return hmac.compare_digest(a, b)
