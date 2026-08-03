"""Router matrix — commercial chat routes with confidence, rationale, no false positives."""

from __future__ import annotations

import pytest

from app.domain.user_request_assistant import chat_route_for_decision
from app.domain.user_request_routing import route_user_request
from app.schemas.contracts import UserRequestRouteKind

ACCEPTANCE_TEXT = (
    "Делаю SaaS проект. ИИ-маркетинговое агентство, "
    "которое заменяет реальное агентство. "
    "Функционал — от идеи до полноценной рекламной кампании, "
    "а также создание контента для разных каналов."
)

ROUTES = {
    "general_answer": {
        "positive": [
            "Что такое unit-экономика SaaS и как её считать?",
            "Explain what CAC means in subscription businesses.",
            "Почему важна сегментация аудитории в B2B?",
        ],
        "negative": [
            "реклама",
            "сделай пост",
        ],
    },
    "business_idea_validation": {
        "positive": [
            "Хочу проверить бизнес-идею кофейни в центре города",
            "Проверить идею открыть стоматологию",
            "idea validation for a local gym",
        ],
        "negative": [
            "Что такое бизнес-идея?",
            "напиши пост про кофейню",
        ],
    },
    "content_generation": {
        "positive": [
            "Напиши пост для Telegram про запуск SaaS",
            "Создай 3 поста для соцсетей про доставку еды",
            "Need an email newsletter draft for product launch",
        ],
        "negative": [
            "контент",
            "Что такое контент-маркетинг?",
        ],
    },
    "campaign_planning": {
        "positive": [
            "Нужна маркетинговая стратегия для SaaS продукта",
            "Подготовь marketing strategy для B2B сервиса",
            "Сформируй маркетинговую стратегию на квартал",
        ],
        "negative": [
            "стратегия",
            "Как работает маркетинговая стратегия?",
        ],
    },
    "channel_operation": {
        "positive": [
            "Создай telegram-бот для записи клиентов",
            "Нужен лендинг для SaaS продукта",
            "Автоматизируй обработку заявок из формы",
        ],
        "negative": [
            "сайт",
            "бот",
        ],
    },
    "asset_generation": {
        "positive": [
            "Сгенерируй баннер 16:9 для рекламы SaaS",
            "Сделай фотореалистичное изображение продукта на столе",
            "Generate an image of a minimalist app icon",
        ],
        "negative": [
            "баннер",
            "картинка",
        ],
    },
    "project_action": {
        "positive": [
            ACCEPTANCE_TEXT,
            "Исследовать рынок доставки еды в Москве",
            "Нужен анализ конкурентов для SaaS CRM",
        ],
        "negative": [
            "Что такое SaaS?",
            "исследование",
        ],
    },
    "clarification": {
        "positive": [
            "реклама",
            "контент",
            "стратегия",
        ],
        "negative": [
            "Напиши пост для Telegram про запуск SaaS",
            ACCEPTANCE_TEXT,
        ],
    },
    "unsupported": {
        "positive": [
            "x" * 4001,
        ],
        "negative": [
            ACCEPTANCE_TEXT,
            "Что такое SEO?",
        ],
    },
}


@pytest.mark.parametrize("route_name,cases", [(k, v) for k, v in ROUTES.items()])
def test_router_matrix_positive(route_name: str, cases: dict) -> None:
    for text in cases["positive"]:
        decision = route_user_request(text)
        actual = chat_route_for_decision(decision)
        if route_name == "unsupported":
            assert decision.kind == UserRequestRouteKind.UNSUPPORTED, text
        elif route_name == "clarification":
            assert decision.kind == UserRequestRouteKind.CLARIFY, text
        else:
            assert actual == route_name, f"{text!r} → {actual}"
        assert decision.confidence >= 0.0
        assert decision.rationale


@pytest.mark.parametrize("route_name,cases", [(k, v) for k, v in ROUTES.items()])
def test_router_matrix_negative_no_false_positive(route_name: str, cases: dict) -> None:
    for text in cases["negative"]:
        decision = route_user_request(text)
        actual = chat_route_for_decision(decision)
        if route_name == "unsupported":
            assert decision.kind != UserRequestRouteKind.UNSUPPORTED, text
        elif route_name == "clarification":
            assert decision.kind != UserRequestRouteKind.CLARIFY or actual != route_name, text
        else:
            assert actual != route_name, f"{text!r} falsely matched {route_name}"


def test_saas_brief_not_clarification() -> None:
    decision = route_user_request(ACCEPTANCE_TEXT)
    assert chat_route_for_decision(decision) == "project_action"
    assert decision.kind != UserRequestRouteKind.CLARIFY


def test_general_question_not_project_action() -> None:
    decision = route_user_request("Что такое unit-экономика SaaS?")
    assert chat_route_for_decision(decision) == "general_answer"


def test_post_creation_not_general_answer() -> None:
    decision = route_user_request("Напиши пост для Telegram про запуск SaaS")
    assert chat_route_for_decision(decision) == "content_generation"
