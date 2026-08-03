"""Shared email normalization for login, invite and registration."""

from __future__ import annotations

import re
import unicodedata

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(raw: str) -> str:
    """Trim, NFC-normalize, lowercase, cap length."""
    text = unicodedata.normalize("NFC", (raw or "").strip()).lower()
    return text[:320]


def is_valid_email(raw: str) -> bool:
    email = normalize_email(raw)
    if len(email) < 5 or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        return False
    return bool(_EMAIL_RE.match(email))
