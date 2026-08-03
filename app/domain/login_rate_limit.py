"""Simple in-process login throttle (CPH.3 minimum — not a full WAF)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
_failures: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 300
MAX_FAILURES = 10


def _prune(bucket: list[float], now: float) -> list[float]:
    cutoff = now - WINDOW_SECONDS
    return [t for t in bucket if t >= cutoff]


def is_login_rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _lock:
        bucket = _prune(_failures[key], now)
        _failures[key] = bucket
        return len(bucket) >= MAX_FAILURES


def record_login_failure(key: str) -> None:
    now = time.monotonic()
    with _lock:
        bucket = _prune(_failures[key], now)
        bucket.append(now)
        _failures[key] = bucket


def clear_login_failures(key: str) -> None:
    with _lock:
        _failures.pop(key, None)
