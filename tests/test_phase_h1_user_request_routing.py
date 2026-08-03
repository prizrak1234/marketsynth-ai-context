"""Phase H1 — deterministic UserRequest routing."""

from app.domain.user_request_routing import route_user_request
from app.schemas.contracts import UserRequestRouteCategory, UserRequestRouteKind


def test_content_posts_route_without_investigation() -> None:
    d = route_user_request("Напиши 10 постов для Telegram о бурении.")
    assert d.category == UserRequestRouteCategory.CONTENT
    assert d.kind == UserRequestRouteKind.SPECIALIST_TASK
    assert d.avoids_investigation is True
    assert d.assigned_specialist == "content_specialist"
    assert d.requires_project is False


def test_content_plan_route() -> None:
    d = route_user_request("Составь контент-план для Telegram на месяц.")
    assert d.category == UserRequestRouteCategory.CONTENT_PLAN
    assert d.avoids_investigation is True


def test_telegram_bot_to_programmer() -> None:
    d = route_user_request("Создай Telegram-бота для записи клиентов.")
    assert d.category == UserRequestRouteCategory.TELEGRAM_BOT
    assert d.assigned_specialist == "programmer"
    assert d.avoids_investigation is True


def test_website_bare_asks_clarification() -> None:
    d = route_user_request("Нужен сайт.")
    assert d.kind == UserRequestRouteKind.CLARIFY
    assert d.clarification_question
    assert "лендинг" in (d.clarification_question or "").lower()


def test_landing_routes_to_website() -> None:
    d = route_user_request("Сделай лендинг для продукта.")
    assert d.category == UserRequestRouteCategory.WEBSITE
    assert d.kind == UserRequestRouteKind.SPECIALIST_TASK


def test_saas_requires_project() -> None:
    d = route_user_request("Хочу SaaS для риелторов.")
    assert d.category == UserRequestRouteCategory.SAAS
    assert d.requires_project is True


def test_idea_validation_project_intake() -> None:
    d = route_user_request("Хочу открыть кафе в центре Баку.")
    assert d.category == UserRequestRouteCategory.IDEA_VALIDATION
    assert d.kind == UserRequestRouteKind.PROJECT_INTAKE
    assert d.next_href and "projects/new" in d.next_href


def test_market_research_intake() -> None:
    d = route_user_request("Нужно исследовать рынок и понять спрос.")
    assert d.category == UserRequestRouteCategory.MARKET_RESEARCH
    assert d.kind == UserRequestRouteKind.PROJECT_INTAKE


def test_ambiguous_ads_clarification() -> None:
    d = route_user_request("Нужна реклама")
    assert d.kind == UserRequestRouteKind.CLARIFY


def test_automation_route() -> None:
    d = route_user_request("Автоматизируй обработку заявок с сайта.")
    assert d.category == UserRequestRouteCategory.AUTOMATION
    assert d.assigned_specialist == "programmer"
