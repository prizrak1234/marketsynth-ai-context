"""Contextual assistant responses for UserRequest chat (no duplicate canned fallbacks)."""

from __future__ import annotations

import re

from app.domain.user_request_routing import RouteDecision
from app.schemas.contracts import UserRequestRouteCategory, UserRequestRouteKind


def chat_route_for_decision(decision: RouteDecision) -> str:
    """Map RouteDecision → commercial chat route label."""
    if decision.kind == UserRequestRouteKind.CLARIFY:
        return "clarification"
    if decision.kind == UserRequestRouteKind.UNSUPPORTED:
        return "unsupported"
    if decision.category == UserRequestRouteCategory.IDEA_VALIDATION:
        return "business_idea_validation"
    if decision.category in {
        UserRequestRouteCategory.CONTENT,
        UserRequestRouteCategory.CONTENT_PLAN,
        UserRequestRouteCategory.SOCIAL_MEDIA,
        UserRequestRouteCategory.YOUTUBE,
    }:
        return "content_generation"
    if decision.category == UserRequestRouteCategory.MARKETING_STRATEGY:
        return "campaign_planning"
    if decision.category in {
        UserRequestRouteCategory.SAAS,
        UserRequestRouteCategory.MARKET_RESEARCH,
        UserRequestRouteCategory.COMPETITOR_ANALYSIS,
    }:
        return "project_action"
    if decision.category == UserRequestRouteCategory.IMAGE_GENERATION:
        return "asset_generation"
    if decision.category in {
        UserRequestRouteCategory.TELEGRAM_BOT,
        UserRequestRouteCategory.WEBSITE,
        UserRequestRouteCategory.AUTOMATION,
    }:
        return "channel_operation"
    if decision.category == UserRequestRouteCategory.GENERAL:
        return "general_answer"
    return "general_answer"


def build_assistant_message(text: str, decision: RouteDecision) -> str:
    """Build a contextual assistant message — never a universal BIV stub."""
    if decision.kind == UserRequestRouteKind.CLARIFY:
        return decision.assistant_message

    if decision.kind == UserRequestRouteKind.UNSUPPORTED:
        return decision.assistant_message

    normalized = " ".join((text or "").strip().split())
    lower = normalized.lower()

    if decision.category == UserRequestRouteCategory.IDEA_VALIDATION:
        return _project_intake_contextual(normalized, lower, focus="проверку жизнеспособности идеи")

    if decision.category == UserRequestRouteCategory.SAAS:
        return _saas_contextual(normalized, lower)

    if decision.category in {
        UserRequestRouteCategory.MARKET_RESEARCH,
        UserRequestRouteCategory.COMPETITOR_ANALYSIS,
        UserRequestRouteCategory.MARKETING_STRATEGY,
    }:
        focus_map = {
            UserRequestRouteCategory.MARKET_RESEARCH: "исследование рынка",
            UserRequestRouteCategory.COMPETITOR_ANALYSIS: "анализ конкурентов",
            UserRequestRouteCategory.MARKETING_STRATEGY: "маркетинговую стратегию",
        }
        return _project_intake_contextual(
            normalized,
            lower,
            focus=focus_map.get(decision.category, "подготовку проекта"),
        )

    if len(normalized) >= 80 and decision.category == UserRequestRouteCategory.GENERAL:
        return _general_descriptive_answer(normalized, lower)

    return decision.assistant_message


def _saas_contextual(text: str, lower: str) -> str:
    product_hint = _extract_product_hint(text, lower)
    capabilities: list[str] = []
    if re.search(r"агентств|agency|маркетинг", lower):
        capabilities.append("маркетинговый цикл вместо агентства")
    if re.search(r"контент|реклам|кампани", lower):
        capabilities.append("создание контента и запуск кампаний")
    if re.search(r"иде|валид|biv|viability", lower):
        capabilities.append("проверку бизнес-идеи")
    cap_text = (
        ", ".join(capabilities)
        if capabilities
        else "полный цикл от идеи до рекламной кампании и контента"
    )
    return (
        f"Понял задачу. {product_hint} "
        f"Платформа должна закрывать {cap_text}. "
        "Для полноценной работы лучше создать проект и зафиксировать: "
        "целевую аудиторию, регион, модель монетизации и ключевой сценарий. "
        "Создать проект на основе этого описания?"
    )


def _project_intake_contextual(text: str, lower: str, *, focus: str) -> str:
    product_hint = _extract_product_hint(text, lower)
    return (
        f"Понял. {product_hint} "
        f"Для {focus} лучше создать проект и собрать исходные данные: "
        "аудитория, география, монетизация и цель. "
        "Создать проект на основе этого описания?"
    )


def _general_descriptive_answer(text: str, lower: str) -> str:
    product_hint = _extract_product_hint(text, lower)
    return (
        f"Понял задачу. {product_hint} "
        "Чтобы двигаться дальше, уточните: что сделать в первую очередь — "
        "проверить идею, подготовить контент или спланировать кампанию?"
    )


def _extract_product_hint(text: str, lower: str) -> str:
    if re.search(r"\bsaas\b|саас", lower):
        if re.search(r"агентств|agency|маркетинг", lower):
            return "Это SaaS-платформа — ИИ-маркетинговое агентство."
        return "Это SaaS-проект."
    if re.search(r"агентств|agency", lower):
        return "Это платформа, которая заменяет маркетинговое агентство."
    if len(text) > 40:
        snippet = text[:120].rstrip()
        if len(text) > 120:
            snippet += "…"
        return f"Кратко: {snippet}"
    return "Задача понятна."


def model_unavailable_fallback() -> str:
    return "Не удалось подготовить ответ. Повторите запрос."

