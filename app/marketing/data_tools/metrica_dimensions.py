"""Yandex Metrica metrics/dimensions knowledge base (Phase AI.219)."""

from __future__ import annotations

_METRIC_ALIASES: dict[str, str] = {
    "visits": "ym:s:visits",
    "visit": "ym:s:visits",
    "users": "ym:s:users",
    "user": "ym:s:users",
    "pageviews": "ym:s:pageviews",
    "pageview": "ym:s:pageviews",
    "bounce": "ym:s:bounceRate",
    "bouncerate": "ym:s:bounceRate",
    "duration": "ym:s:avgVisitDurationSeconds",
}

_DIMENSION_ALIASES: dict[str, str] = {
    "traffic": "ym:s:trafficSource",
    "trafficsource": "ym:s:trafficSource",
    "source": "ym:s:trafficSource",
    "device": "ym:s:deviceCategory",
    "devicecategory": "ym:s:deviceCategory",
    "content": "ym:s:startURL",
    "page": "ym:s:startURL",
    "url": "ym:s:startURL",
}


def resolve_metric(name: str) -> str | None:
    return _METRIC_ALIASES.get(name.strip().lower())


def resolve_dimension(name: str) -> str | None:
    return _DIMENSION_ALIASES.get(name.strip().lower())


def default_metrics() -> list[str]:
    return ["ym:s:visits", "ym:s:users", "ym:s:pageviews"]
