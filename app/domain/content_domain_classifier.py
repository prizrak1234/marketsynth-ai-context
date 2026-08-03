"""Deterministic domain classification for content requests (Phase H2.8)."""

from __future__ import annotations

import re

from app.schemas.contracts import ContentDomainClassification, ContentDomainCode

_DOMAIN_LABELS: dict[ContentDomainCode, str] = {
    ContentDomainCode.GENERAL_MARKETING: "Маркетинг",
    ContentDomainCode.OIL_AND_GAS: "Нефтегаз",
    ContentDomainCode.INDUSTRIAL_SAFETY: "Промышленная безопасность",
    ContentDomainCode.DRILLING_OPERATIONS: "Буровые операции",
    ContentDomainCode.HEALTHCARE: "Здравоохранение",
    ContentDomainCode.DENTISTRY: "Стоматология",
    ContentDomainCode.SAAS: "SaaS",
    ContentDomainCode.AUTOMATION: "Автоматизация",
    ContentDomainCode.SOFTWARE_DEVELOPMENT: "Разработка ПО",
    ContentDomainCode.E_COMMERCE: "E-commerce",
    ContentDomainCode.UNKNOWN: "Общая тематика",
}

_RULES: list[tuple[ContentDomainCode, re.Pattern[str], float]] = [
    (
        ContentDomainCode.DRILLING_OPERATIONS,
        re.compile(
            r"буров|бурени|скважин|супервайзер|drilling|rig\b|torque|drag|"
            r"долив|flow\s*check|near\s*miss|буровой",
            re.I,
        ),
        0.92,
    ),
    (
        ContentDomainCode.INDUSTRIAL_SAFETY,
        re.compile(
            r"промышленн.*безопас|инцидент|авари|near\s*miss|слаб\w*\s+сигнал|"
            r"industrial\s+safety|hse\b|охран\w*\s+труд",
            re.I,
        ),
        0.88,
    ),
    (
        ContentDomainCode.OIL_AND_GAS,
        re.compile(r"нефтегаз|oil\s+and\s+gas|нефт\w*|газов\w*\s+пром", re.I),
        0.85,
    ),
    (
        ContentDomainCode.DENTISTRY,
        re.compile(r"стоматолог|dental|зубн", re.I),
        0.85,
    ),
    (
        ContentDomainCode.HEALTHCARE,
        re.compile(r"здравоохран|медицин|клиник|healthcare", re.I),
        0.82,
    ),
    (
        ContentDomainCode.SAAS,
        re.compile(r"\bsaas\b|подписочн\w*\s+сервис|software\s+as\s+a\s+service", re.I),
        0.8,
    ),
    (
        ContentDomainCode.SOFTWARE_DEVELOPMENT,
        re.compile(r"разработк\w*\s+по|software\s+dev|программирован", re.I),
        0.78,
    ),
    (
        ContentDomainCode.AUTOMATION,
        re.compile(r"автоматизац|workflow|n8n|make\.com", re.I),
        0.75,
    ),
    (
        ContentDomainCode.E_COMMERCE,
        re.compile(r"e-?commerce|интернет-?магазин|онлайн-?продаж", re.I),
        0.75,
    ),
]


def _labels_for(*codes: ContentDomainCode) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for code in codes:
        label = _DOMAIN_LABELS.get(code, code.value)
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def classify_content_domain(text: str) -> ContentDomainClassification:
    """Rule-based domain classification — no LLM."""
    blob = (text or "").strip()
    if not blob:
        return ContentDomainClassification(
            primary=ContentDomainCode.UNKNOWN,
            confidence=0.0,
            labels=[_DOMAIN_LABELS[ContentDomainCode.UNKNOWN]],
        )

    hits: list[tuple[ContentDomainCode, float]] = []
    for domain, pattern, weight in _RULES:
        if pattern.search(blob):
            hits.append((domain, weight))

    if not hits:
        return ContentDomainClassification(
            primary=ContentDomainCode.GENERAL_MARKETING,
            secondary=[],
            confidence=0.5,
            labels=[_DOMAIN_LABELS[ContentDomainCode.GENERAL_MARKETING]],
        )

    hits.sort(key=lambda h: h[1], reverse=True)
    primary, conf = hits[0]
    secondary = [d for d, _ in hits[1:3] if d != primary]
    labels = _labels_for(primary, *secondary)
    return ContentDomainClassification(
        primary=primary,
        secondary=secondary,
        confidence=conf,
        labels=labels,
    )


def domain_codes_for_retrieval(classification: ContentDomainClassification) -> list[str]:
    codes = [classification.primary.value]
    codes.extend(c.value for c in classification.secondary if c.value not in codes)
    return codes
