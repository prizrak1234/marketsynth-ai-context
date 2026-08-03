"""Quality gate before ContentAsset creation from copywriter output."""

from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.marketing.copywriter_output_parser import clean_copywriter_title

_MIN_BODY_CHARS = 80
_MIN_CYRILLIC_RATIO = 0.25
_FALLBACK_MARKERS = (
    "quick win for founders building funnels",
    "take the next step — draft for human review",
)
_TITLE_MARKDOWN_RE = re.compile(r"\*\*post\s*\d+", re.IGNORECASE)


def _normalized_body(item: dict[str, Any]) -> str:
    hook = sanitize_text(str(item.get("hook") or "")).strip()
    body = sanitize_text(str(item.get("body") or "")).strip()
    if hook and body:
        return f"{hook}\n\n{body}".strip()
    return body or hook


def _cyrillic_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    cyrillic = sum(1 for char in letters if "\u0400" <= char <= "\u04FF")
    return cyrillic / len(letters)


def _channel_matches(item_channel: str, expected_channel: str) -> bool:
    item = (item_channel or "").strip().lower()
    expected = (expected_channel or "").strip().lower()
    if not expected:
        return bool(item)
    if item == expected:
        return True
    aliases = {
        "telegram": {"telegram", "telegram_post", "tg"},
        "social": {"social", "instagram", "facebook", "vk"},
        "blog": {"blog", "article", "youtube"},
    }
    for canonical, variants in aliases.items():
        if expected in variants or expected == canonical:
            return item in variants or item == canonical
    return item == expected


def validate_copywriter_content_items(
    items: list[dict[str, Any]],
    *,
    expected_channel: str,
    minimum_items: int = 3,
    require_russian: bool = True,
) -> None:
    """Raise InvalidStateError when copywriter output fails commercial quality gate."""
    if len(items) < minimum_items:
        raise InvalidStateError(
            "Копирайтер вернул некорректный результат. Материалы не созданы.",
        )

    titles: list[str] = []
    bodies: list[str] = []

    for item in items[:minimum_items]:
        title = clean_copywriter_title(str(item.get("headline") or item.get("title") or ""))
        body = _normalized_body(item)
        channel = str(item.get("channel") or "").strip()

        if not title or not body:
            raise InvalidStateError(
                "Копирайтер вернул некорректный результат. Материалы не созданы.",
            )
        if len(body) < _MIN_BODY_CHARS:
            raise InvalidStateError(
                "Копирайтер вернул некорректный результат. Материалы не созданы.",
            )
        if _TITLE_MARKDOWN_RE.search(title) or "**" in title:
            raise InvalidStateError(
                "Копирайтер вернул некорректный результат. Материалы не созданы.",
            )
        lowered_body = body.lower()
        if any(marker in lowered_body for marker in _FALLBACK_MARKERS):
            raise InvalidStateError(
                "Копирайтер вернул некорректный результат. Материалы не созданы.",
            )
        if expected_channel and not _channel_matches(channel, expected_channel):
            raise InvalidStateError(
                "Копирайтер вернул некорректный результат. Материалы не созданы.",
            )
        if require_russian and _cyrillic_ratio(f"{title}\n{body}") < _MIN_CYRILLIC_RATIO:
            raise InvalidStateError(
                "Копирайтер вернул некорректный результат. Материалы не созданы.",
            )

        titles.append(title.lower())
        bodies.append(body.lower())

    if len(set(titles)) < minimum_items or len(set(bodies)) < minimum_items:
        raise InvalidStateError(
            "Копирайтер вернул некорректный результат. Материалы не созданы.",
        )
