"""Shared helpers for optional local smoke scripts (Phase 3.16)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def smoke_env() -> tuple[str | None, str]:
    api_key = os.environ.get("BOTFAZER_API_KEY") or os.environ.get("SMOKE_API_KEY")
    base_url = os.environ.get("BOTFAZER_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return api_key, base_url


def skip(message: str) -> int:
    print(f"skip: {message}")
    return 0


def request_json(
    method: str,
    url: str,
    *,
    api_key: str,
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any] | list[Any] | None]:
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"detail": raw}
        return exc.code, parsed  # type: ignore[return-value]


def fail(message: str) -> int:
    print(f"fail: {message}", file=sys.stderr)
    return 1


def ok(message: str) -> int:
    print(f"ok: {message}")
    return 0
