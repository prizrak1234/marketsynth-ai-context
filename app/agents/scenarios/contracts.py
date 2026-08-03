"""Marketing orchestrator scenario contracts (Phase AI.9)."""

from __future__ import annotations

from enum import StrEnum


class MarketingScenarioType(StrEnum):
    """High-level marketing playbooks the orchestrator can coordinate."""

    CONTENT_LAUNCH = "content_launch"
    TELEGRAM_CONTENT_MONTH = "telegram_content_month"
    LEAD_MAGNET = "lead_magnet"
    PRODUCT_ANNOUNCEMENT = "product_announcement"
    CAMPAIGN_REVIVAL = "campaign_revival"
