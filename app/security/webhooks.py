"""Outbound project webhook signing secrets."""

from __future__ import annotations

import secrets

WEBHOOK_SECRET_PREFIX = "bwhsec_"


def generate_webhook_signing_secret() -> str:
    """Return a one-time signing secret for outbound webhook delivery."""
    return f"{WEBHOOK_SECRET_PREFIX}{secrets.token_urlsafe(32)}"
