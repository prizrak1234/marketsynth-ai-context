"""Publication job idempotency — hashed keys only (Phase AI.66)."""

from __future__ import annotations

import hashlib
from uuid import UUID

from app.executors.idempotency import normalize_idempotency_key


def hash_idempotency_key(normalized_key: str) -> str:
    return hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()


def build_idempotency_fingerprint(
    *,
    owner_id: UUID,
    project_id: UUID,
    package_id: UUID,
    channel_id: UUID,
) -> str:
    payload = f"{owner_id}:{project_id}:{package_id}:{channel_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_publication_job_idempotency_key(raw: str | None) -> str | None:
    return normalize_idempotency_key(raw)
