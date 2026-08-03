"""CWF.1 — commercial Customer Research Report (no engine diagnostics)."""

from __future__ import annotations

from app.business_idea_validation.coverage_categories import CATEGORY_LABELS_RU, normalize_category
from app.business_idea_validation.market_confidence import (
    calculate_coverage_score,
    calculate_dimension_confidence,
)
from app.business_idea_validation.evidence_validation import (
    clean_excerpt_for_finding,
    is_valid_source_url,
)
from app.business_idea_validation.findings import confirmed_evidence
from app.schemas.contracts import (
    BivCategoryCoverageSummary,
    BivConfirmedFinding,
    BivCoverageAttemptStatus,
    BivCustomerResearchReport,
    BivCustomerSourceCitation,
    BivExecutiveSummary,
    BivStructuredResearchVerdict,
    BivUnconfirmedTopic,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationResearchPlanItem,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationVerdictKind,
)

_STRATEGIC_QUESTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Какой результат пользователь получает за первые 10 минут?",
        ("audience", "demand"),
    ),
    ("Что продукт заменяет сегодня?", ("competitors", "audience")),
    ("Кто принимает решение о покупке?", ("audience",)),
    ("Как сейчас решается эта проблема?", ("demand", "audience")),
    (
        "Почему пользователь сменит существующее решение?",
        ("competitors", "demand"),
    ),
    (
        "Сколько сейчас стоит решение этой проблемы?",
        ("pricing",),
    ),
    ("Какая главная боль клиента?", ("audience", "demand")),
    (
        "Какие три конкурента вы считаете основными?",
        ("competitors",),
    ),
    ("Как выглядит MVP?", ("audience", "demand")),
    (
        "Какие функции являются обязательными?",
        ("audience", "demand"),
    ),
    (
        "Какой регион запуска является приоритетным?",
        ("local_context",),
    ),
)

_UNCONFIRMED_REASON: dict[BivCoverageAttemptStatus, str] = {
    BivCoverageAttemptStatus.NOT_FOUND: "Нет открытых отраслевых исследований по этому блоку.",
    BivCoverageAttemptStatus.FOUND_BUT_IRRELEVANT: (
        "Найденные материалы не дают прямого подтверждения для вашей идеи."
    ),
    BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY: (
        "Источники не прошли проверку надёжности для коммерческого вывода."
    ),
    BivCoverageAttemptStatus.NOT_CONFIRMED: (
        "Есть косвенные сигналы, но недостаточно независимых подтверждений."
    ),
    BivCoverageAttemptStatus.USER_HYPOTHESIS: (
        "Пока это предположение из вашего брифа — рынок не подтвердил."
    ),
    BivCoverageAttemptStatus.NOT_RESEARCHED: (
        "Блок не был полностью закрыт в рамках текущего прогона."
    ),
    BivCoverageAttemptStatus.CONFLICTED: (
        "Источники дают противоречивые сигналы — нужна ручная проверка."
    ),
}

_METHODS_BY_PHASE: dict[str, str] = {
    "direct": "прямые отраслевые источники",
    "indirect": "косвенные обзоры и кейсы",
    "international": "международные отчёты",
    "local": "локальные публикации и статистика",
    "adjacent": "смежные рынки",
    "transferability": "оценка переносимости данных",
}


def _status_line(
    *,
    gate_passed: bool,
    confidence: int,
    verdict: BusinessIdeaValidationVerdictKind,
) -> str:
    if gate_passed and verdict == BusinessIdeaValidationVerdictKind.PROCEED:
        return "Перспективно при подтверждении ключевых гипотез на пилоте."
    if confidence >= 55:
        return "Перспективно, но требует дополнительной проверки."
    if confidence >= 35:
        return "Есть сигналы, но доказательная база ограничена."
    return "Пока недостаточно оснований для уверенного решения о запуске."


def _build_confirmed(
    findings: list[BusinessIdeaValidationFinding],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> list[BivConfirmedFinding]:
    confirmed = [f for f in findings if not f.is_hypothesis]
    ev_by_id = {e.evidence_id: e for e in evidence}
    items: list[BivConfirmedFinding] = []

    for finding in confirmed:
        sources: list[BivCustomerSourceCitation] = []
        for eid in finding.linked_evidence_ids:
            ev = ev_by_id.get(eid)
            if not ev or not is_valid_source_url(ev.source_url):
                continue
            sources.append(
                BivCustomerSourceCitation(
                    title=ev.source_title or (ev.source_reference.title if ev.source_reference else "Источник"),
                    url=ev.source_url,
                    domain=ev.source_reference.domain if ev.source_reference else None,
                )
            )
        if not sources:
            continue
        headline = clean_excerpt_for_finding(finding.statement, max_len=240) or finding.title
        explanation = clean_excerpt_for_finding(finding.statement, max_len=500) or (
            f"Подтверждено по блоку «{finding.title}» на основе {len(sources)} независимых источников."
        )
        items.append(
            BivConfirmedFinding(
                headline=headline,
                explanation=explanation,
                sources=sources,
                category=finding.category,
            )
        )
    return items


def _build_unconfirmed(
    category_coverage: list[BivCategoryCoverageSummary],
    plan_items: list[BusinessIdeaValidationResearchPlanItem],
) -> list[BivUnconfirmedTopic]:
    topics: list[BivUnconfirmedTopic] = []
    for row in category_coverage:
        if row.coverage_status == BivCoverageAttemptStatus.CONFIRMED:
            continue
        label = CATEGORY_LABELS_RU.get(row.category, row.label)
        reason = _UNCONFIRMED_REASON.get(
            row.coverage_status,
            "Недостаточно независимых источников для коммерческого вывода.",
        )
        phases = sorted(
            {
                i.pipeline_phase
                for i in plan_items
                if normalize_category(i.category) == row.category and i.pipeline_phase
            }
        )
        methods = [_METHODS_BY_PHASE.get(p, p) for p in phases] or [
            "международные отчёты",
            "локальные публикации",
            "поиск отраслевых исследований",
        ]
        topics.append(
            BivUnconfirmedTopic(
                topic=label,
                reason=reason,
                methods_used=methods,
                result_summary=(
                    "Недостаточно доказательств для уверенного вывода. "
                    "Это снижает достоверность оценки, но не делает проект неперспективным."
                ),
                confidence_impact="Снижает уверенность по этому блоку.",
            )
        )
    return topics


def _clarification_questions(
    category_coverage: list[BivCategoryCoverageSummary],
) -> list[str]:
    weak_cats: set[str] = set()
    for row in category_coverage:
        if row.coverage_status != BivCoverageAttemptStatus.CONFIRMED:
            weak_cats.add(normalize_category(row.category))

    questions: list[str] = []
    for question, related in _STRATEGIC_QUESTIONS:
        if not weak_cats or any(c in weak_cats for c in related):
            questions.append(question)
    return questions[:10]


def _structured_verdict(
    *,
    confirmed: list[BivConfirmedFinding],
    unconfirmed: list[BivUnconfirmedTopic],
    risks: list[BusinessIdeaValidationRisk],
    clarification: list[str],
    confidence: int,
    gate_passed: bool,
    verdict: BusinessIdeaValidationVerdictKind,
) -> BivStructuredResearchVerdict:
    if gate_passed and confirmed:
        recommendation = (
            "Рекомендуем пилот с фокусом на подтверждение монетизации и ICP. "
            "Запуск масштабирования — после закрытия пробелов ниже."
        )
    elif confirmed:
        recommendation = (
            "Рекомендуем уточнить бриф по вопросам ниже и повторить исследование "
            "с более конкретным сегментом и конкурентами."
        )
    else:
        recommendation = (
            "Рекомендуем сначала закрыть ключевые пробелы брифа, "
            "затем повторить исследование — без этого решение о бюджете преждевременно."
        )

    return BivStructuredResearchVerdict(
        confirmed_summary=[f.headline for f in confirmed[:6]],
        unconfirmed_summary=[u.topic for u in unconfirmed[:6]],
        risks=[r.title for r in risks[:5]],
        verification_needed=clarification[:6],
        recommendation=recommendation,
        confidence_percent=confidence,
    )


def build_customer_research_report(
    *,
    inp: BusinessIdeaValidationInput,
    findings: list[BusinessIdeaValidationFinding],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    risks: list[BusinessIdeaValidationRisk],
    category_coverage: list[BivCategoryCoverageSummary],
    plan_items: list[BusinessIdeaValidationResearchPlanItem],
    confidence: BusinessIdeaValidationConfidence,
    gate_passed: bool,
    verdict: BusinessIdeaValidationVerdictKind,
    phases_executed: list[str],
) -> BivCustomerResearchReport:
    confirmed = _build_confirmed(findings, evidence)
    unconfirmed = _build_unconfirmed(category_coverage, plan_items)
    dimension_confidence = calculate_dimension_confidence(
        inp=inp,
        category_coverage=category_coverage,
        evidence=confirmed_evidence(evidence),
        market_confidence=confidence,
    )
    coverage = calculate_coverage_score(
        inp=inp,
        category_coverage=category_coverage,
        plan_items=plan_items,
        phases_executed=phases_executed,
    )
    clarification = _clarification_questions(category_coverage)

    primary_risk = risks[0].title if risks else None
    if not primary_risk and unconfirmed:
        primary_risk = f"Не подтверждено: {unconfirmed[0].topic.lower()}."

    primary_advantage = confirmed[0].headline if confirmed else None
    if not primary_advantage:
        for dim in dimension_confidence:
            if dim.score >= 60:
                primary_advantage = f"Сильный сигнал по блоку «{dim.label}»."
                break

    overall = confidence.total_score
    executive = BivExecutiveSummary(
        status_line=_status_line(
            gate_passed=gate_passed,
            confidence=overall,
            verdict=verdict,
        ),
        confidence_percent=overall,
        primary_risk=primary_risk,
        primary_advantage=primary_advantage,
    )

    structured = _structured_verdict(
        confirmed=confirmed,
        unconfirmed=unconfirmed,
        risks=risks,
        clarification=clarification,
        confidence=overall,
        gate_passed=gate_passed,
        verdict=verdict,
    )

    return BivCustomerResearchReport(
        executive_summary=executive,
        confirmed_findings=confirmed,
        unconfirmed_topics=unconfirmed,
        dimension_confidence=dimension_confidence,
        overall_confidence_percent=overall,
        coverage=coverage,
        clarification_questions=clarification,
        structured_verdict=structured,
    )
