"""Map coverage + confidence to CMVP.1 verdict and next steps."""

from __future__ import annotations

from app.schemas.contracts import (
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationNextStep,
    BusinessIdeaValidationVerdictKind,
    BusinessVerdictConfidenceLevel,
    VerdictKind,
)


def resolve_verdict_kind(
    *,
    gate_passed: bool,
    confidence: BusinessIdeaValidationConfidence,
    risk_count: int,
    contradiction_count: int,
) -> BusinessIdeaValidationVerdictKind:
    if not gate_passed:
        return BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE

    score = confidence.total_score
    if score >= 72 and contradiction_count == 0 and risk_count <= 2:
        return BusinessIdeaValidationVerdictKind.PROCEED
    if score >= 55:
        return BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS
    if score >= 40 and risk_count >= 3:
        return BusinessIdeaValidationVerdictKind.REVISE
    if score < 35:
        return BusinessIdeaValidationVerdictKind.REJECT
    return BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS


def map_to_business_verdict_kind(
    verdict: BusinessIdeaValidationVerdictKind,
) -> VerdictKind:
    mapping = {
        BusinessIdeaValidationVerdictKind.PROCEED: VerdictKind.CONDITIONAL_GO,
        BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS: VerdictKind.CONDITIONAL_GO,
        BusinessIdeaValidationVerdictKind.REVISE: VerdictKind.CONDITIONAL_GO,
        BusinessIdeaValidationVerdictKind.REJECT: VerdictKind.NO_GO,
        BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE: VerdictKind.INSUFFICIENT_DATA,
    }
    return mapping[verdict]


def map_to_confidence_level(score: int) -> BusinessVerdictConfidenceLevel:
    if score >= 75:
        return BusinessVerdictConfidenceLevel.HIGH
    if score >= 50:
        return BusinessVerdictConfidenceLevel.MEDIUM
    if score > 0:
        return BusinessVerdictConfidenceLevel.LOW
    return BusinessVerdictConfidenceLevel.UNKNOWN


def default_next_steps(
    verdict: BusinessIdeaValidationVerdictKind,
) -> list[BusinessIdeaValidationNextStep]:
    if verdict == BusinessIdeaValidationVerdictKind.PROCEED:
        return [
            BusinessIdeaValidationNextStep(
                id="prepare_launch",
                label="Подготовить запуск",
                action="prepare_launch",
            ),
        ]
    if verdict == BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS:
        return [
            BusinessIdeaValidationNextStep(
                id="prepare_launch",
                label="Подготовить запуск с условиями",
                action="prepare_launch",
            ),
            BusinessIdeaValidationNextStep(
                id="clarify_data",
                label="Уточнить данные",
                action="refine_inputs",
            ),
        ]
    if verdict == BusinessIdeaValidationVerdictKind.REVISE:
        return [
            BusinessIdeaValidationNextStep(
                id="revise_idea",
                label="Изменить идею",
                action="revise_idea",
            ),
            BusinessIdeaValidationNextStep(
                id="request_alternative",
                label="Получить рекомендуемую корректировку",
                action="request_alternative",
            ),
        ]
    if verdict == BusinessIdeaValidationVerdictKind.REJECT:
        return [
            BusinessIdeaValidationNextStep(
                id="request_alternative",
                label="Получить альтернативный вариант",
                action="request_alternative",
            ),
            BusinessIdeaValidationNextStep(
                id="finish_project",
                label="Завершить проект",
                action="stop_project",
            ),
        ]
    return [
        BusinessIdeaValidationNextStep(
            id="clarify_data",
            label="Уточнить исходные данные",
            action="refine_inputs",
        ),
        BusinessIdeaValidationNextStep(
            id="revise_idea",
            label="Повторить исследование",
            action="revise_idea",
        ),
    ]
