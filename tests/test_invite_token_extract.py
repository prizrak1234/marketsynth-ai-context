"""Unit helpers for invite token extraction (no secrets)."""

from __future__ import annotations

# Mirrors web/src/lib/auth/invite-token.ts logic for backend-side tests of UX contract.


def extract_invite_token(input_value: str) -> str | None:
    import re

    raw = (input_value or "").strip()
    if not raw:
        return None
    token_re = re.compile(r"mpi_[A-Za-z0-9_-]+")
    if raw.startswith("mpi_"):
        only = re.split(r"[\s?#&]", raw, maxsplit=1)[0]
        return only if token_re.fullmatch(only) else None
    if "://" in raw:
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(raw)
        qs = parse_qs(parsed.query)
        token = (qs.get("token") or [None])[0]
        if token and token_re.fullmatch(token):
            return token
    match = token_re.search(raw)
    return match.group(0) if match else None


def test_extract_token_from_url() -> None:
    token = "mpi_abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    url = f"http://localhost:3000/activate-invite?token={token}"
    assert extract_invite_token(url) == token


def test_extract_token_raw() -> None:
    token = "mpi_abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    assert extract_invite_token(token) == token


def test_extract_empty() -> None:
    assert extract_invite_token("") is None
    assert extract_invite_token("   ") is None
