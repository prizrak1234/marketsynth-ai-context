"""PII sanitization — simple regex masks until Presidio in a later phase."""

from __future__ import annotations

import re
from typing import overload

_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE = re.compile(r"\+?\d[\d\s\-()]{8,}\d")
_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def mask_email(value: str) -> str:
    return _EMAIL.sub("[EMAIL]", value)


def mask_phone(value: str) -> str:
    if _UUID.fullmatch(value.strip()):
        return value

    protected: list[str] = []

    def _protect_uuid(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"__UUID_{len(protected) - 1}__"

    temp = _UUID.sub(_protect_uuid, value)
    temp = _PHONE.sub("[PHONE]", temp)
    for index, token in enumerate(protected):
        temp = temp.replace(f"__UUID_{index}__", token)
    return temp


def sanitize_text(value: str, *, enabled: bool = True) -> str:
    if not enabled or not value:
        return value
    return mask_phone(mask_email(value))


@overload
def sanitize_payload(payload: None, *, enabled: bool = True) -> None: ...


@overload
def sanitize_payload(payload: str, *, enabled: bool = True) -> str: ...


@overload
def sanitize_payload(payload: dict, *, enabled: bool = True) -> dict: ...


@overload
def sanitize_payload(payload: list, *, enabled: bool = True) -> list: ...


def sanitize_payload(
    payload: dict | list | str | None,
    *,
    enabled: bool = True,
) -> dict | list | str | None:
    if payload is None or not enabled:
        return payload
    if isinstance(payload, str):
        return sanitize_text(payload, enabled=True)
    if isinstance(payload, dict):
        return {key: sanitize_payload(item, enabled=enabled) for key, item in payload.items()}
    if isinstance(payload, list):
        return [sanitize_payload(item, enabled=enabled) for item in payload]
    return payload
