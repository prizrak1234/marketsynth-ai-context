"""Source classification and publisher independence for CMVP.1.1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.schemas.contracts import BusinessIdeaValidationSourceClass, BivSourceQualityTier

_OFFICIAL_HINTS = (".gov", "rosstat", "gks.ru", "cbr.ru", "stat.gov")
_REGULATORY_HINTS = ("regulator", "regulation", "legal", "закон", "регулир")
_INDUSTRY_HINTS = ("research", "report", "analytics", "исследован", "отчет")
_FINANCIAL_HINTS = ("invest", "finance", "econom", "финанс", "инвест")
_MEDIA_HINTS = (
    "vc.ru",
    "rbc.ru",
    "kommersant",
    "forbes",
    "hbr.org",
    "bbc.com",
    "reuters",
)
_MARKETPLACE_HINTS = ("ozon.", "wildberries", "amazon.", "market.yandex", "avito.")
_UGC_HINTS = ("youtube.com", "reddit.com", "tiktok.com", "instagram.com", "vk.com")
_BLOG_HINTS = ("blog.", "medium.com", "tilda.", "wordpress", "livejournal")


@dataclass(frozen=True, slots=True)
class SourceQualityAssessment:
    source_class: BusinessIdeaValidationSourceClass
    independence_group: str
    reliability_score: float
    reliability_rationale: str


def publisher_root(domain: str | None) -> str:
    if not domain:
        return "unknown"
    host = domain.lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def classify_source(*, url: str, domain: str | None, title: str, body_excerpt: str) -> SourceQualityAssessment:
    host = (domain or urlparse(url).netloc or "").lower()
    blob = f"{host} {title} {body_excerpt[:400]}".lower()
    source_class = BusinessIdeaValidationSourceClass.UNKNOWN

    if any(h in blob for h in _OFFICIAL_HINTS):
        source_class = BusinessIdeaValidationSourceClass.OFFICIAL_STATISTICS
    elif any(h in blob for h in _REGULATORY_HINTS):
        source_class = BusinessIdeaValidationSourceClass.REGULATORY
    elif any(h in host for h in _MARKETPLACE_HINTS):
        source_class = BusinessIdeaValidationSourceClass.MARKETPLACE
    elif any(h in host for h in _UGC_HINTS):
        source_class = BusinessIdeaValidationSourceClass.USER_GENERATED
    elif any(h in host for h in _MEDIA_HINTS):
        source_class = BusinessIdeaValidationSourceClass.PROFESSIONAL_MEDIA
    elif any(h in blob for h in _FINANCIAL_HINTS):
        source_class = BusinessIdeaValidationSourceClass.FINANCIAL_RESEARCH
    elif any(h in blob for h in _INDUSTRY_HINTS):
        source_class = BusinessIdeaValidationSourceClass.INDUSTRY_RESEARCH
    elif any(h in blob for h in _BLOG_HINTS):
        source_class = BusinessIdeaValidationSourceClass.COMMERCIAL_BLOG

    group = publisher_root(host)
    reliability_score, rationale = _reliability_for_class(source_class)
    return SourceQualityAssessment(
        source_class=source_class,
        independence_group=group,
        reliability_score=reliability_score,
        reliability_rationale=rationale,
    )


def _reliability_for_class(source_class: BusinessIdeaValidationSourceClass) -> tuple[float, str]:
    mapping: dict[BusinessIdeaValidationSourceClass, tuple[float, str]] = {
        BusinessIdeaValidationSourceClass.OFFICIAL_STATISTICS: (
            0.92,
            "Official statistics or government source.",
        ),
        BusinessIdeaValidationSourceClass.REGULATORY: (0.88, "Regulatory or legal reference."),
        BusinessIdeaValidationSourceClass.INDUSTRY_RESEARCH: (0.78, "Industry research publication."),
        BusinessIdeaValidationSourceClass.FINANCIAL_RESEARCH: (0.76, "Financial research source."),
        BusinessIdeaValidationSourceClass.PROFESSIONAL_MEDIA: (0.72, "Professional media outlet."),
        BusinessIdeaValidationSourceClass.COMMERCIAL_BLOG: (0.55, "Commercial blog or marketing content."),
        BusinessIdeaValidationSourceClass.MARKETPLACE: (0.58, "Marketplace listing or platform page."),
        BusinessIdeaValidationSourceClass.USER_GENERATED: (0.45, "User-generated content platform."),
        BusinessIdeaValidationSourceClass.UNKNOWN: (0.50, "Unclassified web source."),
    }
    return mapping[source_class]


def source_quality_tier(source_class: BusinessIdeaValidationSourceClass) -> BivSourceQualityTier:
    tier_a = {
        BusinessIdeaValidationSourceClass.OFFICIAL_STATISTICS,
        BusinessIdeaValidationSourceClass.REGULATORY,
    }
    tier_b = {
        BusinessIdeaValidationSourceClass.INDUSTRY_RESEARCH,
        BusinessIdeaValidationSourceClass.FINANCIAL_RESEARCH,
        BusinessIdeaValidationSourceClass.PROFESSIONAL_MEDIA,
    }
    tier_c = {
        BusinessIdeaValidationSourceClass.COMMERCIAL_BLOG,
        BusinessIdeaValidationSourceClass.MARKETPLACE,
    }
    tier_d = {
        BusinessIdeaValidationSourceClass.USER_GENERATED,
        BusinessIdeaValidationSourceClass.UNKNOWN,
    }
    if source_class in tier_a:
        return BivSourceQualityTier.A
    if source_class in tier_b:
        return BivSourceQualityTier.B
    if source_class in tier_c:
        return BivSourceQualityTier.C
    if source_class in tier_d:
        return BivSourceQualityTier.D
    return BivSourceQualityTier.D


def count_independent_groups(sources: list) -> set[str]:
    groups: set[str] = set()
    for source in sources:
        group = getattr(source, "independence_group", None) or publisher_root(
            getattr(source, "domain", None)
        )
        if group and group != "unknown":
            groups.add(group)
    return groups
