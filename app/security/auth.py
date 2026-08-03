"""API key generation and verification."""

from __future__ import annotations

import hashlib
import secrets

API_KEY_PREFIX = "bfz_"
KEY_PREFIX_LENGTH = 12


def generate_api_key() -> tuple[str, str, str]:
    """Return (plain_key, key_prefix, key_hash). Plain key is shown only once."""
    token = secrets.token_urlsafe(32)
    plain_key = f"{API_KEY_PREFIX}{token}"
    prefix = plain_key[:KEY_PREFIX_LENGTH]
    return plain_key, prefix, hash_api_key(plain_key)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_api_key(plain_key: str, key_hash: str) -> bool:
    return secrets.compare_digest(hash_api_key(plain_key), key_hash)
