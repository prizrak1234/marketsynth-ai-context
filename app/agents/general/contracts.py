"""General agent domain contracts (Phase AI.15)."""

from __future__ import annotations

from enum import StrEnum


class GeneralDomain(StrEnum):
    MARKETING = "marketing"
    PROGRAMMER = "programmer"
    MEDIA = "media"
    UNKNOWN = "unknown"
