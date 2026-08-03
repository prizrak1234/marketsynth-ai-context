"""Deterministic tokenization and normalization."""

from __future__ import annotations

import re
import unicodedata

_TOKEN_RE = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^\w\s\u0400-\u04FF-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return _TOKEN_RE.findall(normalized)


def stem_token(token: str) -> str:
    """Deterministic local suffix normalization for RU/EN token overlap."""
    if len(token) >= 8:
        return token[:-2]
    if len(token) >= 5:
        return token[:-1]
    return token


def contains_phrase(text: str, phrase: str) -> bool:
    norm_text = normalize_text(text)
    norm_phrase = normalize_text(phrase)
    if norm_phrase in norm_text:
        return True
    phrase_tokens = tokenize(norm_phrase)
    if not phrase_tokens:
        return False
    text_tokens = tokenize(norm_text)
    text_stems = {stem_token(token) for token in text_tokens}
    for phrase_token in phrase_tokens:
        phrase_stem = stem_token(phrase_token)
        if phrase_token in text_tokens or phrase_stem in text_stems:
            continue
        prefix = phrase_stem[: max(4, len(phrase_stem) - 1)]
        if not any(
            text_stem.startswith(prefix)
            or phrase_stem.startswith(text_stem[: max(4, len(text_stem) - 1)])
            for text_stem in text_stems
        ):
            return False
    return True
