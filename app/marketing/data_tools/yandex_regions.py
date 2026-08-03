"""Yandex Wordstat region knowledge base (Phase AI.218)."""

from __future__ import annotations

_GLOBAL_REGION = {"code": 0, "name": "All regions"}


_REGIONS: dict[str, dict[str, int | str]] = {
    "moscow": {"code": 213, "name": "Moscow"},
    "москва": {"code": 213, "name": "Moscow"},
    "spb": {"code": 2, "name": "Saint Petersburg"},
    "saint petersburg": {"code": 2, "name": "Saint Petersburg"},
    "санкт-петербург": {"code": 2, "name": "Saint Petersburg"},
    "russia": {"code": 225, "name": "Russia"},
    "россия": {"code": 225, "name": "Russia"},
    "kazan": {"code": 43, "name": "Kazan"},
    "казань": {"code": 43, "name": "Kazan"},
}


def resolve_region(region: str | None) -> dict[str, int | str]:
    """Map human region name to Yandex region code; unknown → global."""
    if not region or not str(region).strip():
        return dict(_GLOBAL_REGION)
    key = str(region).strip().lower()
    if key.isdigit():
        return {"code": int(key), "name": region.strip()}
    matched = _REGIONS.get(key)
    if matched is None:
        return dict(_GLOBAL_REGION)
    return dict(matched)
