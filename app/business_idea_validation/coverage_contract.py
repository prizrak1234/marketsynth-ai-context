"""PRODUCT-01.3B.2 — verifiable research coverage contract."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.business_idea_validation.coverage_categories import (
    CANONICAL_CATEGORIES,
    CATEGORY_LABELS_RU,
    normalize_category,
    required_categories,
)
from app.business_idea_validation.source_quality import count_independent_groups
from app.schemas.contracts import (
    BivCategoryCoverageSummary,
    BivCoverageAttemptStatus,
    BivIntakeHypothesis,
    BivPartialResearchReport,
    BivRemediationQuestion,
    BivResearchGapPresentation,
    BivResearchStopReason,
    BivResearchStopReasonCode,
    BivSemanticGapGroup,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationResearchPlanItem,
    BusinessIdeaValidationSourceSummary,
)

CUSTOMER_STATUS_LABELS: dict[BivCoverageAttemptStatus, str] = {
    BivCoverageAttemptStatus.NOT_RESEARCHED: "Не исследовано",
    BivCoverageAttemptStatus.NOT_FOUND: "Недостаточно данных",
    BivCoverageAttemptStatus.FOUND_BUT_IRRELEVANT: "Источники не по теме",
    BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY: "Низкое качество источников",
    BivCoverageAttemptStatus.NOT_CONFIRMED: "Не подтверждено",
    BivCoverageAttemptStatus.CONFIRMED: "Подтверждено",
    BivCoverageAttemptStatus.CONFLICTED: "Противоречивые данные",
    BivCoverageAttemptStatus.USER_HYPOTHESIS: "Гипотеза пользователя",
}

SEMANTIC_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("market_and_demand", "Рынок и спрос", ("market", "demand")),
    ("competitors", "Конкуренты", ("competitors",)),
    ("audience", "Аудитория", ("audience",)),
    ("pricing_economics", "Цена и экономика", ("pricing",)),
    ("local_and_risks", "Локальный контекст и риски", ("local_context", "commercial_risks")),
)


@dataclass
class CategoryAttemptStats:
    category: str
    executed_query: str | None = None
    sources_found: int = 0
    sources_relevant: int = 0
    sources_irrelevant: int = 0
    sources_low_quality: int = 0
    evidence_confirmed: int = 0
    evidence_hypothesis: int = 0
    searched: bool = False
    has_conflict: bool = False


@dataclass
class CoverageAttemptTracker:
    stats: dict[str, CategoryAttemptStats] = field(default_factory=dict)
    queries_by_category: dict[str, str] = field(default_factory=dict)

    def ensure(self, category: str) -> CategoryAttemptStats:
        canonical = normalize_category(category)
        if canonical not in self.stats:
            self.stats[canonical] = CategoryAttemptStats(category=canonical)
        return self.stats[canonical]

    def record_query(self, category: str, query: str) -> None:
        canonical = normalize_category(category)
        row = self.ensure(canonical)
        row.searched = True
        if not row.executed_query:
            row.executed_query = query[:512]
        self.queries_by_category[canonical] = query[:512]

    def record_fetch(self, category: str, *, relevant: bool, low_quality: bool) -> None:
        row = self.ensure(category)
        row.sources_found += 1
        if relevant:
            row.sources_relevant += 1
        elif low_quality:
            row.sources_low_quality += 1
        else:
            row.sources_irrelevant += 1

    def record_evidence(
        self,
        category: str,
        *,
        confirmed: bool,
        hypothesis: bool = False,
    ) -> None:
        row = self.ensure(category)
        if confirmed:
            row.evidence_confirmed += 1
        elif hypothesis:
            row.evidence_hypothesis += 1

    def mark_conflict(self, category: str) -> None:
        self.ensure(category).has_conflict = True


def derive_coverage_status(
    stats: CategoryAttemptStats,
    *,
    user_hypothesis: bool = False,
) -> BivCoverageAttemptStatus:
    if user_hypothesis:
        return BivCoverageAttemptStatus.USER_HYPOTHESIS
    if not stats.searched:
        return BivCoverageAttemptStatus.NOT_RESEARCHED
    if stats.has_conflict:
        return BivCoverageAttemptStatus.CONFLICTED
    if stats.evidence_confirmed > 0:
        return BivCoverageAttemptStatus.CONFIRMED
    if stats.evidence_hypothesis > 0:
        return BivCoverageAttemptStatus.NOT_CONFIRMED
    if stats.sources_found == 0:
        return BivCoverageAttemptStatus.NOT_FOUND
    if stats.sources_relevant == 0 and stats.sources_irrelevant > 0:
        return BivCoverageAttemptStatus.FOUND_BUT_IRRELEVANT
    if stats.sources_relevant == 0 and stats.sources_low_quality > 0:
        return BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY
    if stats.sources_relevant > 0:
        return BivCoverageAttemptStatus.NOT_CONFIRMED
    return BivCoverageAttemptStatus.NOT_FOUND


def _category_stop_reason(status: BivCoverageAttemptStatus) -> str | None:
    mapping = {
        BivCoverageAttemptStatus.NOT_RESEARCHED: "Направление не было исследовано в этом запуске.",
        BivCoverageAttemptStatus.NOT_FOUND: "Поиск выполнен, но релевантные источники не найдены.",
        BivCoverageAttemptStatus.FOUND_BUT_IRRELEVANT: "Найденные страницы не относятся к вашей идее.",
        BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY: "Источники не прошли проверку качества.",
        BivCoverageAttemptStatus.NOT_CONFIRMED: "Есть сигналы, но недостаточно для подтверждения.",
        BivCoverageAttemptStatus.USER_HYPOTHESIS: "Данные указаны пользователем и не подтверждены рынком.",
    }
    return mapping.get(status)


def build_category_coverage(
    *,
    inp: BusinessIdeaValidationInput,
    tracker: CoverageAttemptTracker,
    plan_items: list[BusinessIdeaValidationResearchPlanItem],
) -> list[BivCategoryCoverageSummary]:
    query_map = {normalize_category(i.category): i.query for i in plan_items}
    for cat, query in tracker.queries_by_category.items():
        query_map.setdefault(cat, query)

    user_hypothesis_categories: set[str] = set()
    if (inp.pricing_or_revenue_model or inp.budget or "").strip():
        user_hypothesis_categories.add("pricing")
    if (inp.target_audience or "").strip():
        user_hypothesis_categories.add("audience")

    summaries: list[BivCategoryCoverageSummary] = []
    for category in required_categories(inp):
        stats = tracker.stats.get(category, CategoryAttemptStats(category=category))
        if category in user_hypothesis_categories and stats.evidence_confirmed == 0:
            status = BivCoverageAttemptStatus.USER_HYPOTHESIS
        else:
            status = derive_coverage_status(stats)
        summaries.append(
            BivCategoryCoverageSummary(
                category=category,
                label=CATEGORY_LABELS_RU.get(category, category),
                executed_query=stats.executed_query or query_map.get(category),
                coverage_status=status,
                customer_status_label=CUSTOMER_STATUS_LABELS[status],
                sources_found=stats.sources_found,
                sources_relevant=stats.sources_relevant,
                evidence_confirmed=stats.evidence_confirmed,
                evidence_hypothesis=stats.evidence_hypothesis,
                stop_reason=_category_stop_reason(status),
            )
        )
    return summaries


def build_intake_hypotheses(inp: BusinessIdeaValidationInput) -> list[BivIntakeHypothesis]:
    items: list[BivIntakeHypothesis] = []
    pricing = (inp.pricing_or_revenue_model or inp.budget or "").strip()
    if pricing:
        items.append(
            BivIntakeHypothesis(
                field="pricing_or_revenue_model",
                label="Цена / монетизация",
                value=pricing,
                message="Указано пользователем и не подтверждено рынком.",
            )
        )
    audience = (inp.target_audience or "").strip()
    if audience:
        items.append(
            BivIntakeHypothesis(
                field="target_customer",
                label="Целевая аудитория",
                value=audience,
                message="Указано пользователем — требуется подтверждение источниками.",
            )
        )
    monetization = (inp.market or "").strip()
    if monetization:
        items.append(
            BivIntakeHypothesis(
                field="business_model",
                label="Модель монетизации",
                value=monetization,
                message="Указано пользователем и не подтверждено рынком.",
            )
        )
    competitors = (inp.known_competitors or inp.constraints or "").strip()
    if competitors:
        items.append(
            BivIntakeHypothesis(
                field="known_competitors",
                label="Известные конкуренты",
                value=competitors,
                message="Список от пользователя — не проверен автоматически.",
            )
        )
    stage = (inp.current_stage or "").strip()
    if stage:
        items.append(
            BivIntakeHypothesis(
                field="current_stage",
                label="Стадия проекта",
                value=stage,
                message="Указано пользователем.",
            )
        )
    return items


def build_partial_report(
    *,
    inp: BusinessIdeaValidationInput,
    findings: list[BusinessIdeaValidationFinding],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    gate_passed: bool,
    category_coverage: list[BivCategoryCoverageSummary],
) -> BivPartialResearchReport:
    from app.business_idea_validation.commercial_relevance import assess_commercial_relevance

    confirmed = [
        f
        for f in findings
        if not f.is_hypothesis
        and assess_commercial_relevance(
            inp=inp,
            category=f.category,
            observation=f.statement,
        ).relevant
    ]
    hypotheses = [f for f in findings if f.is_hypothesis]
    probable = [
        e.observation or e.claim
        for e in evidence
        if e.classification.value == "hypothesis"
        and (e.observation or e.claim)
        and assess_commercial_relevance(
            inp=inp,
            category=e.category,
            observation=e.observation or e.claim or "",
        ).relevant
    ][:5]

    established = [f.statement for f in confirmed if f.statement][:6]
    contradictions: list[str] = []
    for cat in category_coverage:
        if cat.coverage_status == BivCoverageAttemptStatus.CONFLICTED:
            contradictions.append(f"Противоречивые сигналы по блоку «{cat.label}».")

    intake_hypotheses = build_intake_hypotheses(inp)
    if gate_passed:
        interim = (
            "Данных достаточно для предварительного вывода. "
            "Рекомендуется подтвердить ключевые гипотезы на пилоте."
        )
    elif established or probable:
        interim = (
            "По отдельным блокам есть подтверждённые сигналы, но данных недостаточно "
            "для решения о запуске. Ниже — что удалось установить, что осталось неясным "
            "и какие шаги снизят риск ошибочного решения."
        )
    else:
        interim = (
            "Автоматическое исследование не собрало достаточно подтверждённых фактов "
            "для полного вердикта. Это не означает, что идея обречена — уточните контекст "
            "и повторите исследование или проверьте гипотезы вручную на пилоте."
        )

    return BivPartialResearchReport(
        established_findings=established,
        probable_signals=probable,
        user_hypotheses=intake_hypotheses,
        contradictions=contradictions,
        interim_conclusion=interim,
    )


def build_research_stop_reason(
    *,
    inp: BusinessIdeaValidationInput,
    gate_passed: bool,
    limitations: list[str],
    sources: list[BusinessIdeaValidationSourceSummary],
    category_coverage: list[BivCategoryCoverageSummary],
    mcp_search_calls: int,
) -> BivResearchStopReason:
    limitation_set = set(limitations)
    not_researched = [
        c for c in category_coverage
        if c.coverage_status == BivCoverageAttemptStatus.NOT_RESEARCHED
    ]
    low_quality = [
        c for c in category_coverage
        if c.coverage_status == BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY
    ]

    if not_researched:
        return BivResearchStopReason(
            code=BivResearchStopReasonCode.CATEGORIES_NOT_RESEARCHED,
            customer_message=(
                f"Часть направлений не была исследована ({len(not_researched)} из "
                f"{len(category_coverage)}). Повторите исследование или сузьте запрос."
            ),
        )
    if "fewer_than_3_independent_publishers" in limitation_set:
        return BivResearchStopReason(
            code=BivResearchStopReasonCode.FEW_INDEPENDENT_SOURCES,
            customer_message=(
                "Найдено слишком мало независимых изданий. "
                "Добавьте известных конкурентов или уточните сегмент."
            ),
        )
    if low_quality:
        return BivResearchStopReason(
            code=BivResearchStopReasonCode.LOW_QUALITY_SOURCES,
            customer_message=(
                "Источники не прошли проверку качества или релевантности. "
                "Попробуйте указать конкретных конкурентов или сузить регион."
            ),
        )
    if mcp_search_calls >= 8 and len(sources) < 2:
        return BivResearchStopReason(
            code=BivResearchStopReasonCode.CONNECTOR_INSUFFICIENT,
            customer_message=(
                "Поисковый контур вернул мало результатов по вашему запросу. "
                "Сузьте сегмент, уточните регион или добавьте конкурентов."
            ),
        )
    if not (inp.target_audience or "").strip():
        return BivResearchStopReason(
            code=BivResearchStopReasonCode.ICP_UNKNOWN,
            customer_message=(
                "Неизвестен приоритетный платящий клиент (ICP). "
                "Уточните, кто покупает: блогер, агентство или in-house маркетолог."
            ),
        )
    if len(sources) < 3 and not gate_passed:
        broad = not inp.known_competitors and not inp.product_or_service
        if broad:
            return BivResearchStopReason(
                code=BivResearchStopReasonCode.QUERY_TOO_BROAD,
                customer_message=(
                    "Запрос слишком широкий для автоматического поиска. "
                    "Укажите основной use case, 2–3 конкурентов и приоритетный регион."
                ),
            )
        return BivResearchStopReason(
            code=BivResearchStopReasonCode.MARKET_POORLY_COVERED,
            customer_message=(
                "Выбранный рынок или сегмент плохо покрывается открытыми источниками. "
                "Сузьте нишу или добавьте конкурентов для точечного поиска."
            ),
        )
    return BivResearchStopReason(
        code=BivResearchStopReasonCode.INSUFFICIENT_EVIDENCE,
        customer_message=(
            "Подтверждённых данных недостаточно для вердикта. "
            "Используйте вопросы ниже и запустите исследование повторно."
        ),
    )


_REMEDIATION_BY_GROUP: dict[str, list[tuple[str, str | None]]] = {
    "market_and_demand": [
        (
            "Какой основной сценарий использования продукта (1–2 предложения)?",
            "idea_description",
        ),
        (
            "Какой ожидаемый месячный объём использования или контента?",
            "budget_context",
        ),
    ],
    "competitors": [
        (
            "Какие 3 конкурента вы уже рассматриваете (названия или ссылки)?",
            "known_competitors",
        ),
        (
            "Что именно заменяет продукт: агентство, сотрудника или набор сервисов?",
            "idea_description",
        ),
    ],
    "audience": [
        (
            "Кто платящий пользователь: блогер, агентство или in-house маркетолог?",
            "target_customer",
        ),
        (
            "Какой регион приоритетный: вся РФ или конкретные города?",
            "geography",
        ),
    ],
    "pricing_economics": [
        (
            "Какой диапазон цены вы считаете реалистичным и на чём основываетесь?",
            "pricing_or_revenue_model",
        ),
        (
            "Какие текущие затраты клиента на агентство и инструменты?",
            "budget_context",
        ),
    ],
    "local_and_risks": [
        (
            "Есть ли регуляторные или локальные ограничения для вашего сегмента?",
            "geography",
        ),
        (
            "Какой минимальный набор функций MVP вы планируете?",
            "idea_description",
        ),
    ],
}


def build_remediation_questions(
    category_coverage: list[BivCategoryCoverageSummary],
) -> list[BivRemediationQuestion]:
    weak_groups: set[str] = set()
    for cat in category_coverage:
        if cat.coverage_status in {
            BivCoverageAttemptStatus.NOT_RESEARCHED,
            BivCoverageAttemptStatus.NOT_FOUND,
            BivCoverageAttemptStatus.FOUND_BUT_IRRELEVANT,
            BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY,
            BivCoverageAttemptStatus.NOT_CONFIRMED,
            BivCoverageAttemptStatus.USER_HYPOTHESIS,
        }:
            for group_id, _, cats in SEMANTIC_GROUPS:
                if cat.category in cats:
                    weak_groups.add(group_id)

    questions: list[BivRemediationQuestion] = []
    seen: set[str] = set()
    for group_id, _, cats in SEMANTIC_GROUPS:
        if group_id not in weak_groups:
            continue
        for question, intake_field in _REMEDIATION_BY_GROUP.get(group_id, []):
            if question in seen:
                continue
            seen.add(question)
            questions.append(
                BivRemediationQuestion(
                    question=question,
                    intake_field=intake_field,
                    related_categories=list(cats),
                    semantic_group=group_id,
                )
            )
    return questions[:8]


def _group_summary(
    group_id: str,
    categories: list[BivCategoryCoverageSummary],
) -> str:
    if not categories:
        return "Данные по этому блоку не собраны."
    parts: list[str] = []
    for cat in categories:
        parts.append(f"{cat.label}: {cat.customer_status_label.lower()}.")
    return " ".join(parts)


def build_semantic_gap_groups(
    *,
    category_coverage: list[BivCategoryCoverageSummary],
    gap_items: list[BivResearchGapPresentation],
    remediation_questions: list[BivRemediationQuestion],
) -> list[BivSemanticGapGroup]:
    coverage_by_cat = {c.category: c for c in category_coverage}
    groups: list[BivSemanticGapGroup] = []

    for group_id, title, cat_names in SEMANTIC_GROUPS:
        cats = [coverage_by_cat[c] for c in cat_names if c in coverage_by_cat]
        weak = any(
            c.coverage_status
            not in {
                BivCoverageAttemptStatus.CONFIRMED,
            }
            for c in cats
        )
        if not cats:
            continue
        if not weak and not remediation_questions:
            continue
        group_questions = [q for q in remediation_questions if q.semantic_group == group_id]
        if not weak and not group_questions:
            continue
        summary = _group_summary(group_id, cats)
        if gap_items:
            related_messages = [
                g.customer_message
                for g in gap_items
                if g.semantic_group == group_id
            ]
            if related_messages:
                summary = related_messages[0]
        groups.append(
            BivSemanticGapGroup(
                group_id=group_id,
                title=title,
                summary=summary,
                related_categories=list(cat_names),
                questions=group_questions,
            )
        )
    return groups


_PRIMARY_GAP_CODES = frozenset(
    {
        "missing_market_finding",
        "missing_competitor_finding",
        "missing_audience_finding",
        "missing_demand_finding",
        "missing_pricing_finding",
        "missing_risk_finding",
        "missing_local_context",
        "fewer_than_3_fetched_sources",
        "fewer_than_3_independent_publishers",
        "fewer_than_3_evidence_records",
        "fewer_than_3_confirmed_evidence",
        "business_verdict_missing",
    }
)


def dedupe_research_gaps(codes: list[str]) -> list[str]:
    """Keep primary gate codes; drop redundant coverage_* duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    has_primary = any(c in _PRIMARY_GAP_CODES for c in codes)
    for code in codes:
        normalized = (code or "").strip()
        if not normalized or normalized in seen:
            continue
        if has_primary and normalized.startswith("coverage_"):
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def attach_semantic_groups_to_gaps(
    gap_items: list[BivResearchGapPresentation],
) -> list[BivResearchGapPresentation]:
    code_to_group: dict[str, str] = {
        "missing_market_finding": "market_and_demand",
        "missing_demand_finding": "market_and_demand",
        "missing_competitor_finding": "competitors",
        "missing_audience_finding": "audience",
        "missing_pricing_finding": "pricing_economics",
        "missing_risk_finding": "local_and_risks",
        "missing_local_context": "local_and_risks",
    }
    updated: list[BivResearchGapPresentation] = []
    for item in gap_items:
        group = code_to_group.get(item.code)
        if not group and item.code.startswith("coverage_"):
            for cat, gid in (
                ("market", "market_and_demand"),
                ("demand", "market_and_demand"),
                ("competitors", "competitors"),
                ("audience", "audience"),
                ("pricing", "pricing_economics"),
                ("local_context", "local_and_risks"),
                ("commercial_risks", "local_and_risks"),
            ):
                if f"coverage_{cat}_" in item.code:
                    group = gid
                    break
        if group:
            updated.append(item.model_copy(update={"semantic_group": group}))
        else:
            updated.append(item)
    return updated
