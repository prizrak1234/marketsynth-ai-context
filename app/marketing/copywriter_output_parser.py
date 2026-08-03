"""Tolerant parser for Copywriter LLM output — no template fallback bodies."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.exceptions import ExecutorError
from app.core.security import sanitize_text

_MIN_BODY_CHARS = 80
_FALLBACK_MARKERS = (
    "quick win for founders building funnels",
    "take the next step — draft for human review",
    "attention hook for",
)

_ITEM_SECTION_RE = re.compile(
    r"(?:^|\n)(?:#{1,4}\s*)?(?:content\s+item|item|post)\s*(\d+)\b",
    re.IGNORECASE,
)
_FIELD_LINE_RE = re.compile(
    r"^\s*[-*]?\s*\**(?P<key>headline|title|hook|body|cta|channel|funnel\s*stage|"
    r"content\s*pillar|angle|slot\s*index)\**:\s*(?P<value>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_MARKDOWN_TITLE_WRAPPER_RE = re.compile(
    r"^\s*(?:\d+\.\s*)?\*{0,2}(?:post\s*\d+\s*:?\s*|item\s*\d+\s*:?\s*)\*{0,2}\s*",
    re.IGNORECASE,
)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class CopywriterOutputUnparseableError(ExecutorError):
    """LLM copy could not be structured — commercial generation must fail."""

    def __init__(self, detail: str = "Copywriter LLM output could not be parsed") -> None:
        super().__init__(detail)
        self.error_code = "copywriter_output_unparseable"


def extract_brief_channel(project_context: dict[str, Any] | None) -> str:
    if not project_context:
        return ""
    brief = project_context.get("content_factory_brief")
    if isinstance(brief, dict):
        channel = str(brief.get("channel") or "").strip()
        if channel:
            return channel.lower()
    primary = str(project_context.get("primary_channel") or "").strip()
    return primary.lower()


def clean_copywriter_title(raw: str) -> str:
    text = sanitize_text(raw).strip()
    text = _MARKDOWN_TITLE_WRAPPER_RE.sub("", text)
    text = re.sub(r"\*{1,2}", "", text)
    text = text.strip(" \"'«»:-")
    return text[:512]


def _normalize_item_fields(raw: dict[str, Any], *, slot_index: int, default_channel: str) -> dict[str, Any]:
    title = clean_copywriter_title(
        str(raw.get("title") or raw.get("headline") or raw.get("name") or ""),
    )
    hook = sanitize_text(str(raw.get("hook") or "")).strip()
    body = sanitize_text(str(raw.get("body") or raw.get("text") or "")).strip()
    if not body and hook:
        body = hook
    cta = sanitize_text(str(raw.get("cta") or "")).strip()
    channel = sanitize_text(str(raw.get("channel") or default_channel or "telegram")).strip().lower()
    channel = channel.strip("*").strip()
    angle = sanitize_text(str(raw.get("angle") or raw.get("content_pillar") or "")).strip()
    funnel_stage = sanitize_text(str(raw.get("funnel_stage") or "")).strip()
    content_pillar = sanitize_text(str(raw.get("content_pillar") or angle)).strip()
    slot_raw = raw.get("slot_index", slot_index)
    try:
        slot = int(slot_raw)
    except (TypeError, ValueError):
        slot = slot_index
    return {
        "headline": title,
        "title": title,
        "hook": hook[:300],
        "body": body[:8000],
        "cta": cta[:300],
        "channel": channel[:64],
        "angle": angle[:200],
        "funnel_stage": funnel_stage[:64],
        "content_pillar": content_pillar[:200],
        "slot_index": slot,
    }


def _parse_json_payload(content: str) -> list[dict[str, Any]] | None:
    stripped = content.strip()
    candidates: list[str] = [stripped]
    for match in _JSON_BLOCK_RE.finditer(content):
        block = match.group(1).strip()
        if block:
            candidates.append(block)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            items = parsed.get("content_items")
            if isinstance(items, list):
                return [entry for entry in items if isinstance(entry, dict)]
        if isinstance(parsed, list):
            return [entry for entry in parsed if isinstance(entry, dict)]
    return None


def _parse_markdown_sections(content: str) -> list[dict[str, Any]]:
    matches = list(_ITEM_SECTION_RE.finditer(content))
    if not matches:
        return []

    items: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = content[start:end].strip()
        if not section:
            continue
        fields: dict[str, str] = {}
        for field_match in _FIELD_LINE_RE.finditer(section):
            key = field_match.group("key").lower().replace(" ", "_")
            value = field_match.group("value").strip().strip("*").strip()
            fields[key] = value
        if fields.get("headline") or fields.get("title") or fields.get("body"):
            fields.setdefault("slot_index", int(match.group(1)))
            items.append(fields)
    return items


def _parse_numbered_blocks(content: str) -> list[dict[str, Any]]:
    blocks = re.split(r"\n(?=\d+[\.)]\s+)", content.strip())
    items: list[dict[str, Any]] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        title_match = re.match(r"^\d+[\.)]\s*(.+?)(?:\n|$)", block)
        if not title_match:
            continue
        title = title_match.group(1).strip()
        body = block[title_match.end() :].strip()
        if title and body and len(body) >= _MIN_BODY_CHARS:
            items.append({"title": title, "body": body})
    return items


def parse_copywriter_llm_content(
    content: str,
    *,
    expected_channel: str = "",
    minimum_items: int = 3,
) -> list[dict[str, Any]]:
    """Parse LLM prose/JSON into normalized content_items. Raises on failure."""
    text = sanitize_text(content).strip()
    if not text:
        raise CopywriterOutputUnparseableError("Copywriter LLM returned empty content")

    default_channel = (expected_channel or "telegram").lower()
    raw_items: list[dict[str, Any]] | None = None

    raw_items = _parse_json_payload(text)
    if not raw_items:
        raw_items = _parse_markdown_sections(text)
    if not raw_items:
        raw_items = _parse_numbered_blocks(text)

    if not raw_items:
        raise CopywriterOutputUnparseableError("Copywriter LLM output format not recognized")

    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items, start=1):
        slot = int(raw.get("slot_index") or index)
        item = _normalize_item_fields(raw, slot_index=slot, default_channel=default_channel)
        if item["headline"] and item["body"]:
            normalized.append(item)

    if len(normalized) < minimum_items:
        raise CopywriterOutputUnparseableError(
            f"Copywriter output has fewer than {minimum_items} parseable items",
        )
    return normalized[: max(minimum_items, len(normalized))]
