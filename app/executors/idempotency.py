"""Idempotency-Key normalization for agent run execute (Phase 3.14)."""

from __future__ import annotations

import re

from app.core.exceptions import InvalidStateError

IDEMPOTENCY_KEY_MAX_LENGTH = 128
_SAFE_IDEMPOTENCY_KEY = re.compile(r"^[a-zA-Z0-9._:-]+$")


def normalize_idempotency_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if len(cleaned) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise InvalidStateError("idempotency_key_too_long")
    if not _SAFE_IDEMPOTENCY_KEY.fullmatch(cleaned):
        raise InvalidStateError("invalid_idempotency_key")
    return cleaned
