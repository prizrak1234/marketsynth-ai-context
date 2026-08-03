"""CWF.1 — deterministic Customer Report export (TXT/Markdown)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.schemas.contracts import BivCustomerResearchReport, BusinessIdeaValidationOutput

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]{2,}$")
_EMPTY_MD = re.compile(r"\[[^\]]+\]\(\s*\)")


def _verdict_label(output: BusinessIdeaValidationOutput) -> str:
    labels = {
        "proceed": "GO — запуск целесообразен",
        "proceed_with_conditions": "CONDITIONAL GO — запуск с условиями",
        "revise": "HOLD — требуется доработка идеи",
        "reject": "NO GO — запуск не рекомендуется",
        "insufficient_evidence": "PILOT ONLY — недостаточно доказательств для масштаба",
    }
    return labels.get(output.verdict.value if hasattr(output.verdict, "value") else str(output.verdict), "HOLD")


def build_customer_report_txt(
    *,
    report: BivCustomerResearchReport,
    output: BusinessIdeaValidationOutput,
    project_name: str = "Marketsynth",
    exported_at: datetime | None = None,
) -> str:
    when = (exported_at or datetime.now(UTC)).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "MARKETSYNTH — КОММЕРЧЕСКОЕ ИССЛЕДОВАНИЕ",
        f"Проект: {project_name}",
        f"Дата экспорта: {when}",
        f"Run ID: {output.run_id or '—'}",
        "",
        "=== ИТОГОВЫЙ СТАТУС ===",
        _verdict_label(output),
        report.executive_summary.status_line,
        f"Общая уверенность: {report.overall_confidence_percent}%",
        f"Покрытие: {report.coverage.overall_percent}%",
        "",
        "=== EXECUTIVE SUMMARY ===",
        report.executive_summary.status_line,
    ]
    if report.executive_summary.primary_advantage:
        lines += ["", "Главное преимущество:", report.executive_summary.primary_advantage]
    if report.executive_summary.primary_risk:
        lines += ["", "Основной риск:", report.executive_summary.primary_risk]

    if report.confirmed_findings:
        lines += ["", "=== ЧТО ПОДТВЕРЖДЕНО ==="]
        for idx, item in enumerate(report.confirmed_findings, 1):
            lines.append(f"{idx}. {item.headline}")
            lines.append(f"   {item.explanation}")
            for src in item.sources:
                if src.url:
                    domain = src.domain or src.url
                    lines.append(f"   — {src.title} ({domain}): {src.url}")
                elif src.domain:
                    lines.append(f"   — {src.title} ({src.domain})")

    if report.unconfirmed_topics:
        lines += ["", "=== ЧТО НЕ ПОДТВЕРЖДЕНО ==="]
        for item in report.unconfirmed_topics:
            lines += [
                f"• {item.topic}",
                f"  Причина: {item.reason}",
                f"  Что проверялось: {', '.join(item.methods_used) or '—'}",
                f"  Итог: {item.result_summary}",
            ]

    sv = report.structured_verdict
    lines += [
        "",
        "=== ВЕРДИКТ ===",
        sv.recommendation,
        f"Уверенность вердикта: {sv.confidence_percent}%",
    ]
    if sv.risks:
        lines += ["", "Риски:"] + [f"• {r}" for r in sv.risks]
    if sv.verification_needed:
        lines += ["", "Что проверить дальше:"] + [f"• {q}" for q in sv.verification_needed]

    sources = _numbered_sources(report)
    if sources:
        lines += ["", "=== ИСТОЧНИКИ ==="]
        lines.extend(sources)

    return "\n".join(lines).strip() + "\n"


def _numbered_sources(report: BivCustomerResearchReport) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    n = 1
    for finding in report.confirmed_findings:
        for src in finding.sources:
            key = src.url or f"{src.title}|{src.domain}"
            if not key or key in seen:
                continue
            if not src.url:
                continue
            seen.add(key)
            domain = f" ({src.domain})" if src.domain else ""
            out.append(f"{n}. {src.title}{domain} — {src.url}")
            n += 1
    return out


def validate_export_content(text: str) -> list[str]:
    violations: list[str] = []
    if _EMPTY_MD.search(text):
        violations.append("empty_markdown_links")
    for line in text.splitlines():
        stripped = line.strip()
        if _SNAKE_CASE.fullmatch(stripped):
            violations.append(f"raw_code:{stripped}")
    if "to main content" in text.lower() or "skip to navigation" in text.lower():
        violations.append("navigation_boilerplate")
    if len(text.strip()) < 80:
        violations.append("export_too_short")
    return violations
