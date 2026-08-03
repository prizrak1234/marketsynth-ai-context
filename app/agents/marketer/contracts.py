"""Marketer sub-agent contracts (Phase AI.10)."""

from __future__ import annotations

from enum import StrEnum


class MarketerSubAgentType(StrEnum):
    """First marketer sub-agent set — architecture 3.2 (four personas, not twelve)."""

    STRATEGIST = "strategist"
    COPYWRITER = "copywriter"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
