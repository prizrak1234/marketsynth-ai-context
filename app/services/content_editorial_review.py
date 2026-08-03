"""Editorial review for content drafts (Phase H2.8 — internal skill)."""

from __future__ import annotations

import re

from app.schemas.contracts import (
    ContentDomainCode,
    ContentDomainClassification,
    ContentDraftResult,
)
from app.services.content_claim_verification import cta_duplicated_in_body

_GENERIC_FILLER = [
    re.compile(r"в\s+современном\s+мире", re.I),
    re.compile(r"важно\s+понимать", re.I),
    re.compile(r"это\s+не\s+просто\s+рекомендац", re.I),
    re.compile(r"безусловно", re.I),
    re.compile(r"уникальн\w+\s+возможност", re.I),
]

_DRILLING_DEPTH_SIGNALS = [
    re.compile(r"слаб\w*\s+сигнал", re.I),
    re.compile(r"near\s*miss|почти[-\s]?инцидент", re.I),
    re.compile(r"torque|drag|долив|flow\s*check|давлен", re.I),
    re.compile(r"смен|бригад|супервайзер|тренд|наблюден", re.I),
    re.compile(r"отклонен|параметр|оборудован", re.I),
]


def run_editorial_review(
    result: ContentDraftResult,
    *,
    domain: ContentDomainClassification | None,
    audience: str = "",
) -> tuple[list[str], dict[str, float]]:
    """Return editorial issue codes and dimension scores (0–1)."""
    issues: list[str] = []
    scores: dict[str, float] = {}

    blob = " ".join([result.hook, result.body, result.cta])
    required_present = bool(result.hook.strip() and result.body.strip() and result.cta.strip())
    scores["structure"] = 1.0 if required_present else 0.3

    if cta_duplicated_in_body(result):
        issues.append("duplicated_final_cta")
        scores["repetition"] = 0.2
        scores["cta_quality"] = 0.2
    else:
        scores["repetition"] = 0.9
        scores["cta_quality"] = 0.85

    filler_hits = sum(1 for p in _GENERIC_FILLER if p.search(blob))
    scores["originality"] = max(0.2, 1.0 - filler_hits * 0.25)
    if filler_hits:
        issues.append("generic_filler")

    body_len = len(result.body or "")
    if body_len < 280:
        issues.append("body_too_short")
        scores["depth"] = 0.35
    elif body_len < 450:
        scores["depth"] = 0.65
    else:
        scores["depth"] = 0.9

    aud = (audience or "").lower()
    if aud and aud not in blob.lower() and "супервайз" not in blob.lower():
        scores["audience_fit"] = 0.55
        issues.append("weak_audience_fit")
    else:
        scores["audience_fit"] = 0.9

    scores["platform_fit"] = 0.85 if body_len <= 2200 else 0.6
    scores["clarity"] = 0.8 if body_len > 120 else 0.5
    scores["language_quality"] = scores["clarity"]
    scores["instruction_adherence"] = 0.85

    primary = domain.primary if domain else ContentDomainCode.UNKNOWN
    if primary in {ContentDomainCode.DRILLING_OPERATIONS, ContentDomainCode.INDUSTRIAL_SAFETY}:
        depth_hits = sum(1 for p in _DRILLING_DEPTH_SIGNALS if p.search(blob))
        domain_score = min(1.0, 0.35 + depth_hits * 0.12)
        scores["domain_depth"] = domain_score
        if depth_hits < 3:
            issues.append("insufficient_domain_depth")
    else:
        scores["domain_depth"] = 0.7

    scores["professional_credibility"] = round(
        sum(
            scores.get(k, 0.7)
            for k in (
                "depth",
                "domain_depth",
                "audience_fit",
                "originality",
                "clarity",
            )
        )
        / 5,
        3,
    )

    return issues, scores


def build_revision_brief(
    issues: list[str],
    editorial_notes: list[str],
) -> str:
    parts = ["Улучши черновик с учётом замечаний редактора:"]
    mapping = {
        "duplicated_final_cta": "Финальный вопрос должен быть только один раз — в CTA, не дублируй в теле.",
        "generic_filler": "Убери общие фразы и клише; добавь предметную конкретику.",
        "body_too_short": "Расширь тело: контекст, примеры, практический вывод.",
        "insufficient_domain_depth": "Добавь отраслевую конкретику: слабые сигналы, наблюдения, параметры, смены.",
        "weak_audience_fit": "Явнее ориентируй текст на указанную аудиторию.",
        "unsupported_statistic": "Не используй точные проценты и статистику без подтверждённого источника.",
    }
    for code in issues:
        if code in mapping:
            parts.append(f"- {mapping[code]}")
    for note in editorial_notes[:5]:
        parts.append(f"- {note}")
    return "\n".join(parts)
