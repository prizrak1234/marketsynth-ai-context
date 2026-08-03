"""CWF.1 — commercial verdict model (GO / CONDITIONAL_GO / PILOT_ONLY / HOLD / NO_GO)."""

from __future__ import annotations

from app.schemas.contracts import (
    BivCommercialVerdict,
    BivCommercialVerdictKind,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationVerdictKind,
)


def map_legacy_verdict_kind(
    legacy: BusinessIdeaValidationVerdictKind,
    *,
    gate_passed: bool,
    confidence: int,
    confirmed_count: int,
) -> BivCommercialVerdictKind:
    if legacy == BusinessIdeaValidationVerdictKind.REJECT:
        return BivCommercialVerdictKind.NO_GO
    if not gate_passed or confirmed_count < 2:
        if confidence >= 35 and confirmed_count >= 1:
            return BivCommercialVerdictKind.PILOT_ONLY
        return BivCommercialVerdictKind.HOLD
    if legacy == BusinessIdeaValidationVerdictKind.PROCEED and confidence >= 70:
        return BivCommercialVerdictKind.GO
    if legacy in {
        BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS,
        BusinessIdeaValidationVerdictKind.REVISE,
    }:
        return BivCommercialVerdictKind.CONDITIONAL_GO
    if legacy == BusinessIdeaValidationVerdictKind.PROCEED:
        return BivCommercialVerdictKind.CONDITIONAL_GO
    if legacy == BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE:
        return BivCommercialVerdictKind.PILOT_ONLY if confirmed_count else BivCommercialVerdictKind.HOLD
    return BivCommercialVerdictKind.HOLD


def build_commercial_verdict(
    *,
    kind: BivCommercialVerdictKind,
    confidence: int,
    findings: list[BusinessIdeaValidationFinding],
    risks: list[BusinessIdeaValidationRisk],
    unconfirmed_topics: list[str],
    gate_passed: bool,
) -> BivCommercialVerdict:
    confirmed = [f.statement for f in findings if not f.is_hypothesis][:6]
    unconfirmed = unconfirmed_topics[:6]
    critical_risks = [r.title for r in risks[:5]]

    if kind == BivCommercialVerdictKind.GO:
        rationale = (
            "Достаточно подтверждённых сигналов по ключевым блокам для ограниченного пилота "
            "с контролируемым масштабом."
        )
        go_conditions = ["Подтвердить монетизацию на пилоте", "Зафиксировать ICP на первых продажах"]
        next_action = "Запустить пилот с измеримыми KPI (лиды, оплаты, retention)."
    elif kind == BivCommercialVerdictKind.CONDITIONAL_GO:
        rationale = (
            "Есть подтверждённые сигналы, но остаются пробелы, влияющие на масштабирование."
        )
        go_conditions = unconfirmed[:4] or ["Закрыть пробелы по спросу и конкурентам"]
        next_action = "Выполнить условия и повторить исследование с уточнённым брифом."
    elif kind == BivCommercialVerdictKind.PILOT_ONLY:
        rationale = (
            "Полный запуск не обоснован, но ограниченный MVP/pilot допустим для проверки "
            "готовности ICP платить."
        )
        go_conditions = [
            "Провести не менее 10 интервью с ICP",
            "Получить минимум 3 сигнала willingness-to-pay",
        ]
        next_action = "Запустить узкий pilot-only тест без масштабирования бюджета."
    elif kind == BivCommercialVerdictKind.NO_GO:
        rationale = (
            "Текущая версия идеи не проходит коммерческую проверку: риски и пробелы "
            "перевешивают подтверждённые преимущества."
        )
        go_conditions = ["Пересмотреть сегмент, offer или канал монетизации"]
        next_action = "Изменить гипотезу или выбрать смежный сценарий с лучшим evidence."
    else:  # HOLD
        rationale = (
            "Критически не хватает подтверждённых данных для любого решения о бюджете."
        )
        go_conditions = unconfirmed[:4] or ["Уточнить ICP, конкурентов и модель монетизации"]
        next_action = "Дозаполнить бриф и повторить исследование — решение о запуске преждевременно."

    return BivCommercialVerdict(
        kind=kind,
        rationale=rationale,
        confirmed_assumptions=confirmed,
        unconfirmed_assumptions=unconfirmed,
        critical_risks=critical_risks,
        go_no_go_conditions=go_conditions,
        confidence=confidence,
        next_validation_action=next_action,
    )
