"""Deterministic conversational routing for UserRequest (Phase H1).

No LLM. Backend values stay English enums; UI labels via frontend i18n.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.contracts import UserRequestRouteCategory, UserRequestRouteKind

_SPECIALIST_ALIASES: dict[UserRequestRouteCategory, str | None] = {
    UserRequestRouteCategory.CONTENT: "content_specialist",
    UserRequestRouteCategory.CONTENT_PLAN: "content_planner",
    UserRequestRouteCategory.SOCIAL_MEDIA: "content_specialist",
    UserRequestRouteCategory.YOUTUBE: "content_specialist",
    UserRequestRouteCategory.IMAGE_GENERATION: "visual_specialist",
    UserRequestRouteCategory.TELEGRAM_BOT: "programmer",
    UserRequestRouteCategory.WEBSITE: "programmer",
    UserRequestRouteCategory.SAAS: "programmer",
    UserRequestRouteCategory.AUTOMATION: "programmer",
    UserRequestRouteCategory.IDEA_VALIDATION: "researcher",
    UserRequestRouteCategory.MARKET_RESEARCH: "researcher",
    UserRequestRouteCategory.COMPETITOR_ANALYSIS: "researcher",
    UserRequestRouteCategory.MARKETING_STRATEGY: "strategist",
    UserRequestRouteCategory.GENERAL: None,
    UserRequestRouteCategory.UNSUPPORTED: None,
}

_AVOIDS_INVESTIGATION = frozenset(
    {
        UserRequestRouteCategory.CONTENT,
        UserRequestRouteCategory.CONTENT_PLAN,
        UserRequestRouteCategory.SOCIAL_MEDIA,
        UserRequestRouteCategory.YOUTUBE,
        UserRequestRouteCategory.IMAGE_GENERATION,
        UserRequestRouteCategory.TELEGRAM_BOT,
        UserRequestRouteCategory.WEBSITE,
        UserRequestRouteCategory.AUTOMATION,
    }
)


@dataclass(frozen=True, slots=True)
class RouteDecision:
    category: UserRequestRouteCategory
    kind: UserRequestRouteKind
    confidence: float
    requires_project: bool
    avoids_investigation: bool
    assigned_specialist: str | None
    clarification_question: str | None
    next_href: str | None
    next_action_label: str
    assistant_message: str
    title: str
    rationale: str = ""


def normalize_request_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _specialist(category: UserRequestRouteCategory) -> str | None:
    return _SPECIALIST_ALIASES.get(category)


def _avoids(category: UserRequestRouteCategory) -> bool:
    return category in _AVOIDS_INVESTIGATION


def route_user_request(
    text: str,
    *,
    selected_scenario: str | None = None,
    has_reference_set: bool = False,
) -> RouteDecision:
    """Deterministic route. Optional scenario shortcuts when user picks a card."""
    normalized = normalize_request_text(text)
    lower = normalized.lower()

    if selected_scenario:
        forced = _from_scenario(selected_scenario, normalized)
        if forced is not None:
            return forced

    if not normalized:
        return _clarify(
            category=UserRequestRouteCategory.GENERAL,
            question="Опишите задачу: продукт, цель, аудитория и желаемый результат.",
            assistant="Пустой запрос. Уточните задачу — тогда выберем маршрут.",
            confidence=0.0,
        )

    if len(normalized) > 4000:
        return RouteDecision(
            category=UserRequestRouteCategory.UNSUPPORTED,
            kind=UserRequestRouteKind.UNSUPPORTED,
            confidence=1.0,
            requires_project=False,
            avoids_investigation=True,
            assigned_specialist=None,
            clarification_question=None,
            next_href=None,
            next_action_label="Сократить запрос",
            assistant_message="Запрос слишком длинный. Сократите текст до 4000 символов.",
            title="Запрос слишком длинный",
            rationale="Request exceeds maximum length — unsupported.",
        )

    # Ambiguous advertising
    if _is_ambiguous_ads(lower):
        return _clarify(
            category=UserRequestRouteCategory.GENERAL,
            question="Для какого продукта реклама, на какой площадке и с какой целью?",
            assistant="Запрос пока слишком общий. Не создаю проект и не запускаю исследование.",
            confidence=0.55,
        )

    # Bare website → clarify type
    if re.fullmatch(r"(нужен|хочу|сделай|нужна)?\s*сайт\.?", lower):
        return _clarify(
            category=UserRequestRouteCategory.WEBSITE,
            question="Какой тип сайта нужен: лендинг, корпоративный сайт или интернет-магазин?",
            assistant="Уточните тип сайта — от этого зависит маршрут специалиста.",
            confidence=0.6,
        )

    # Bare content → clarify channel
    if re.fullmatch(r"(сделай|нужен|нужна|хочу)?\s*контент\.?", lower):
        return _clarify(
            category=UserRequestRouteCategory.CONTENT,
            question="Для какой площадки нужны материалы, какая тема и какая цель?",
            assistant="Понял, что нужен контент. Уточните площадку, тему и цель — тогда продолжим без полного исследования.",
            confidence=0.6,
        )

    # Image generation — before generic content (поста / картинка)
    if _is_image_generation_request(lower) or (
        has_reference_set and len(normalized) >= 40
    ):
        if _is_banner_without_specs(lower):
            return _clarify(
                category=UserRequestRouteCategory.IMAGE_GENERATION,
                question="Какой формат баннера нужен (например 1:1, 16:9, 1080×1920) и какой текст на нём?",
                assistant="Это задача на изображение. Для баннера нужны размер/пропорции и текст, если он должен быть на макете.",
                confidence=0.82,
            )
        if _is_logo_without_specs(lower) and not has_reference_set:
            return _clarify(
                category=UserRequestRouteCategory.IMAGE_GENERATION,
                question="Как называется бренд и какой стиль логотипа нужен (минимализм, шрифтовой, знак)?",
                assistant="Это задача на логотип. Уточните название и стиль — затем сгенерирую варианты.",
                confidence=0.82,
            )
        return _routed(
            category=UserRequestRouteCategory.IMAGE_GENERATION,
            kind=UserRequestRouteKind.SPECIALIST_TASK,
            requires_project=False,
            next_href="/workspace/tasks?intent=image_generation",
            next_action_label="Открыть задачу",
            text=normalized,
            confidence=0.94 if has_reference_set else 0.92,
        )

    # Ordinary Q&A — before business task rules (prevents SaaS/BIV false positives).
    if _is_general_question(normalized, lower):
        return _general_answer_route(
            text=normalized,
            confidence=0.78,
            rationale="Ordinary question — general_answer via LLM, no project intake.",
        )

    rules: list[tuple[UserRequestRouteCategory, list[re.Pattern[str]], UserRequestRouteKind, bool, str, str | None]] = [
        (
            UserRequestRouteCategory.TELEGRAM_BOT,
            [
                re.compile(r"telegram[\s-]?бот", re.I),
                re.compile(r"телеграм[\s-]?бот", re.I),
                re.compile(r"\bбот\b.*запис", re.I),
                re.compile(r"созда(ть|й).*бот", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            False,
            "Открыть сценарий Telegram-бота",
            "/workspace/tasks?intent=telegram_bot",
        ),
        (
            UserRequestRouteCategory.AUTOMATION,
            [
                re.compile(r"автоматиз", re.I),
                re.compile(r"обработк[ау].*заявок", re.I),
                re.compile(r"\bautomation\b", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            True,
            "Открыть сценарий автоматизации",
            "/workspace/tasks?intent=automation",
        ),
        (
            UserRequestRouteCategory.YOUTUBE,
            [
                re.compile(r"youtube", re.I),
                re.compile(r"ютуб", re.I),
                re.compile(r"сценари(й|я).*youtube", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            False,
            "Открыть сценарий YouTube",
            "/workspace/tasks?intent=youtube",
        ),
        (
            UserRequestRouteCategory.WEBSITE,
            [
                re.compile(r"лендинг", re.I),
                re.compile(r"landing", re.I),
                re.compile(r"интернет[\s-]?магазин", re.I),
                re.compile(r"корпоративн\w*\s+сайт", re.I),
                re.compile(r"веб[\s-]?сайт", re.I),
                re.compile(r"website", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            False,
            "Открыть сценарий сайта",
            "/workspace/tasks?intent=website",
        ),
        (
            UserRequestRouteCategory.CONTENT_PLAN,
            [
                re.compile(r"контент[\s-]?план", re.I),
                re.compile(r"content[\s-]?plan", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            False,
            "Открыть контент-план",
            "/workspace/tasks?intent=content_plan",
        ),
        (
            UserRequestRouteCategory.SOCIAL_MEDIA,
            [
                re.compile(r"соцсет", re.I),
                re.compile(r"telegram на месяц", re.I),
                re.compile(r"посты?\s+в\s+telegram", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            False,
            "Открыть контент-сценарий",
            "/workspace/tasks?intent=social_media",
        ),
        (
            UserRequestRouteCategory.CONTENT,
            [
                re.compile(r"напис(ать|ать).*(пост|контент)", re.I),
                re.compile(r"\d+\s*пост", re.I),
                re.compile(r"созда(ть|й).*контент", re.I),
                re.compile(r"\bpost\b", re.I),
                re.compile(r"\bпост\b", re.I),
                re.compile(r"\bemail\b", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            False,
            "Открыть контент-сценарий",
            "/workspace/tasks?intent=content",
        ),
        (
            UserRequestRouteCategory.COMPETITOR_ANALYSIS,
            [re.compile(r"конкурент", re.I), re.compile(r"competitor", re.I)],
            UserRequestRouteKind.PROJECT_INTAKE,
            True,
            "Начать подготовку проекта",
            "/workspace/projects/new?scenario=competitor_analysis",
        ),
        (
            UserRequestRouteCategory.MARKET_RESEARCH,
            [
                re.compile(r"исследова(ть|ние).*рынок", re.I),
                re.compile(r"market research", re.I),
                re.compile(r"изучить рынок", re.I),
            ],
            UserRequestRouteKind.PROJECT_INTAKE,
            True,
            "Начать подготовку проекта",
            "/workspace/projects/new?scenario=market_research",
        ),
        (
            UserRequestRouteCategory.MARKETING_STRATEGY,
            [
                re.compile(r"маркетингов(ую|ая|ой)?\s*стратег", re.I),
                re.compile(r"marketing strategy", re.I),
            ],
            UserRequestRouteKind.PROJECT_INTAKE,
            True,
            "Начать подготовку проекта",
            "/workspace/projects/new?scenario=marketing_strategy",
        ),
        (
            UserRequestRouteCategory.IDEA_VALIDATION,
            [
                re.compile(r"бизнес[\s-]?иде", re.I),
                re.compile(r"проверить иде", re.I),
                re.compile(r"хочу открыть", re.I),
                re.compile(r"открыть.*(кофейн|кафе|стоматолог|магазин|клиник|ресторан|салон)", re.I),
                re.compile(r"валид(ация|ировать)", re.I),
                re.compile(r"idea validation", re.I),
            ],
            UserRequestRouteKind.PROJECT_INTAKE,
            True,
            "Начать подготовку проекта",
            "/workspace/projects/new?scenario=idea_validation",
        ),
        (
            UserRequestRouteCategory.SAAS,
            [
                re.compile(r"\bsaas\b", re.I),
                re.compile(r"саас", re.I),
            ],
            UserRequestRouteKind.SPECIALIST_TASK,
            True,
            "Начать подготовку проекта",
            "/workspace/projects/new?scenario=saas",
        ),
    ]

    for category, patterns, kind, requires_project, action, href in rules:
        if any(p.search(normalized) for p in patterns):
            return _routed(
                category=category,
                kind=kind,
                requires_project=requires_project,
                next_href=href,
                next_action_label=action,
                text=normalized,
                confidence=0.86,
            )

    if len(normalized) < 12:
        return _clarify(
            category=UserRequestRouteCategory.GENERAL,
            question="Опишите чуть конкретнее: проверка идеи, контент, бот, сайт или стратегия?",
            assistant="Пока не уверен в маршруте. Не направляю в исследование без ясности.",
            confidence=0.4,
            rationale="Short message without task keywords — needs clarification.",
        )

    return _clarify(
        category=UserRequestRouteCategory.GENERAL,
        question="Уточните задачу: продукт, цель, аудитория и желаемый результат.",
        assistant="Запрос пока слишком общий. Не создаю проект и не запускаю исследование.",
        confidence=0.45,
        rationale="Descriptive text without clear task route — clarification required.",
    )


def apply_clarification_answer(
    original: RouteDecision,
    *,
    original_text: str,
    answer: str,
) -> RouteDecision:
    """Re-route after clarification. Prefer combined text for site type etc."""
    combined = normalize_request_text(f"{original_text} {answer}")
    return route_user_request(combined, selected_scenario=None)


def _from_scenario(scenario: str, text: str) -> RouteDecision | None:
    try:
        category = UserRequestRouteCategory(scenario)
    except ValueError:
        return None
    if category == UserRequestRouteCategory.GENERAL:
        return None
    # Scenario "website" with bare seed still may need type — if text is bare сайт clarify
    if category == UserRequestRouteCategory.WEBSITE and re.fullmatch(
        r"(нужен|хочу|сделай|нужна)?\s*сайт\.?",
        text.lower(),
    ):
        return _clarify(
            category=UserRequestRouteCategory.WEBSITE,
            question="Какой тип сайта нужен: лендинг, корпоративный сайт или интернет-магазин?",
            assistant="Уточните тип сайта — от этого зависит маршрут специалиста.",
            confidence=0.7,
        )
    kind = (
        UserRequestRouteKind.PROJECT_INTAKE
        if category
        in {
            UserRequestRouteCategory.IDEA_VALIDATION,
            UserRequestRouteCategory.MARKET_RESEARCH,
            UserRequestRouteCategory.COMPETITOR_ANALYSIS,
            UserRequestRouteCategory.MARKETING_STRATEGY,
        }
        else UserRequestRouteKind.SPECIALIST_TASK
    )
    requires = kind == UserRequestRouteKind.PROJECT_INTAKE or category in {
        UserRequestRouteCategory.SAAS,
        UserRequestRouteCategory.AUTOMATION,
    }
    href_map = {
        UserRequestRouteCategory.IDEA_VALIDATION: "/workspace/projects/new?scenario=idea_validation",
        UserRequestRouteCategory.MARKET_RESEARCH: "/workspace/projects/new?scenario=market_research",
        UserRequestRouteCategory.COMPETITOR_ANALYSIS: "/workspace/projects/new?scenario=competitor_analysis",
        UserRequestRouteCategory.MARKETING_STRATEGY: "/workspace/projects/new?scenario=marketing_strategy",
        UserRequestRouteCategory.SAAS: "/workspace/projects/new?scenario=saas",
        UserRequestRouteCategory.CONTENT: "/workspace/tasks?intent=content",
        UserRequestRouteCategory.CONTENT_PLAN: "/workspace/tasks?intent=content_plan",
        UserRequestRouteCategory.SOCIAL_MEDIA: "/workspace/tasks?intent=social_media",
        UserRequestRouteCategory.YOUTUBE: "/workspace/tasks?intent=youtube",
        UserRequestRouteCategory.TELEGRAM_BOT: "/workspace/tasks?intent=telegram_bot",
        UserRequestRouteCategory.WEBSITE: "/workspace/tasks?intent=website",
        UserRequestRouteCategory.AUTOMATION: "/workspace/tasks?intent=automation",
    }
    return _routed(
        category=category,
        kind=kind,
        requires_project=requires,
        next_href=href_map.get(category),
        next_action_label="Продолжить",
        text=text or category.value,
        confidence=0.9,
    )


def _is_image_generation_request(lower: str) -> bool:
    patterns = [
        r"сгенерируй\s+(изображен|картинк|фото|иллюстрац|обложк|постер|баннер)",
        r"созда(й|ть)\s+(изображен|картинк|фото|иллюстрац|обложк|постер|баннер)",
        r"нарисуй",
        r"сделай\s+(фотореалистичн|картинк|изображен|иллюстрац|обложк|постер|баннер|логотип)",
        r"визуализируй",
        r"фотореалистичн\w*\s+(изображен|фото|картинк)",
        r"\bgenerate\s+(an?\s+)?(image|picture|poster|illustration)\b",
        r"\bcreate\s+(an?\s+)?(image|picture|poster|illustration)\b",
        r"\bmake\s+(an?\s+)?(image|picture|poster|banner)\b",
        r"\bdraw\b",
    ]
    return any(re.search(p, lower) for p in patterns)


def _is_banner_without_specs(lower: str) -> bool:
    if not re.search(r"баннер|banner|постер|poster", lower):
        return False
    if re.search(r"\d+\s*[x×х]\s*\d+|1:1|16:9|9:16|4:5|текст|text|размер|формат", lower):
        return False
    # Bare banner request
    return bool(re.search(r"^(сделай|создай|сгенерируй)?\s*(баннер|banner|постер|poster)\.?$", lower)) or (
        re.search(r"баннер|banner", lower) and len(lower) < 40 and not re.search(r"девушк|стол|ночь|сцен", lower)
    )


def _is_logo_without_specs(lower: str) -> bool:
    if not re.search(r"логотип|logo", lower):
        return False
    if re.search(r"бренд|назван|стиль|минимал|шрифт|brand|name|style", lower):
        return False
    return True


def _is_ambiguous_ads(lower: str) -> bool:
    if len(lower) > 80 and re.search(
        r"saas|саас|агентств|платформ|функцион|кампани|контент|иде|проект",
        lower,
    ):
        return False
    if re.match(r"^(нужна|хочу|сделай|запусти)?\s*реклам", lower) or re.fullmatch(
        r"реклам[ауы]?",
        lower,
    ):
        return True
    if "реклам" in lower and not re.search(
        r"продукт|аудитор|бюджет|youtube|instagram|telegram|лендинг|сайт|"
        r"saas|саас|агентств|платформ|функцион|кампани|контент|иде|проект",
        lower,
    ):
        return True
    return False


def _is_general_question(normalized: str, lower: str) -> bool:
    """Detect ordinary Q&A — not a business task route."""
    task_markers = re.compile(
        r"(созда(й|ть)|напиш(и|ать)|сгенериру|запуст(и|ить)|"
        r"провер(ить|ку)\s+(иде|бизнес)|хочу\s+открыть|"
        r"нужен\s+(лендинг|сайт|бот|контент)|"
        r"сделай\s+(пост|контент|баннер|логотип|изображен)|"
        r"исследова(ть|ние)\s+рын|анализ\s+конкурент|"
        r"валид(ация|ировать)|автоматиз)",
        re.I,
    )
    if task_markers.search(lower):
        return False
    if "?" in normalized:
        return True
    if re.match(
        r"^(что|как|почему|зачем|когда|где|кто|сколько|можно ли|"
        r"explain|what|how|why|when|where|who|tell me)\b",
        lower,
    ):
        return True
    if re.match(r"^(расскажи|объясни|поясни)\b", lower):
        return True
    return False


def _general_answer_route(
    *,
    text: str,
    confidence: float,
    rationale: str,
) -> RouteDecision:
    return RouteDecision(
        category=UserRequestRouteCategory.GENERAL,
        kind=UserRequestRouteKind.SPECIALIST_TASK,
        confidence=confidence,
        requires_project=False,
        avoids_investigation=True,
        assigned_specialist=None,
        clarification_question=None,
        next_href=None,
        next_action_label="",
        assistant_message="",
        title=text[:80] if text else "Вопрос",
        rationale=rationale,
    )


def _clarify(
    *,
    category: UserRequestRouteCategory,
    question: str,
    assistant: str,
    confidence: float,
    rationale: str = "Ambiguous or incomplete request — clarification required.",
) -> RouteDecision:
    return RouteDecision(
        category=category,
        kind=UserRequestRouteKind.CLARIFY,
        confidence=confidence,
        requires_project=False,
        avoids_investigation=True,
        assigned_specialist=None,
        clarification_question=question,
        next_href=None,
        next_action_label="Ответить уточнением",
        assistant_message=assistant,
        title="Нужно уточнение",
        rationale=rationale,
    )


def _routed(
    *,
    category: UserRequestRouteCategory,
    kind: UserRequestRouteKind,
    requires_project: bool,
    next_href: str | None,
    next_action_label: str,
    text: str,
    confidence: float,
) -> RouteDecision:
    messages = {
        UserRequestRouteCategory.TELEGRAM_BOT: (
            "Это задача для разработчика. Уточните основные сценарии бота и нужные "
            "интеграции — полный маркетинговый цикл не запускаю."
        ),
        UserRequestRouteCategory.CONTENT: (
            "Понял. Это контент-задача, полный анализ не требуется. "
            "Если чего-то не хватает — уточню площадку, тему и цель."
        ),
        UserRequestRouteCategory.CONTENT_PLAN: (
            "Понял. Нужен контент-план — без полного исследования. "
            "Уточню канал и период, если их ещё нет."
        ),
        UserRequestRouteCategory.SOCIAL_MEDIA: (
            "Понял. Это материалы для соцсетей — исследование рынка не запускаю."
        ),
        UserRequestRouteCategory.YOUTUBE: (
            "Понял. Нужен сценарий для YouTube — подготовлю как контент-задачу."
        ),
        UserRequestRouteCategory.IMAGE_GENERATION: (
            "Понял. Это задача на создание изображения — исследование и полный "
            "маркетинговый цикл не нужны. Готовлю визуал."
        ),
        UserRequestRouteCategory.WEBSITE: (
            "Это задача на сайт. Уточню тип и основные требования, если нужно, "
            "без полного исследования рынка."
        ),
        UserRequestRouteCategory.AUTOMATION: (
            "Это задача на автоматизацию для разработчика. "
            "Уточню триггеры и системы, если их нет в запросе."
        ),
        UserRequestRouteCategory.SAAS: (
            "Для SaaS обычно нужен устойчивый проект. "
            "Соберём исходные данные и план реализации."
        ),
        UserRequestRouteCategory.IDEA_VALIDATION: (
            "Здесь лучше сначала проверить жизнеспособность идеи. "
            "Создадим проект и соберём исходные данные."
        ),
        UserRequestRouteCategory.MARKET_RESEARCH: (
            "Нужно исследование рынка. Создадим проект и соберём источники."
        ),
        UserRequestRouteCategory.COMPETITOR_ANALYSIS: (
            "Нужен анализ конкурентов. Создадим проект и зафиксируем сравниваемые стороны."
        ),
        UserRequestRouteCategory.MARKETING_STRATEGY: (
            "Нужна маркетинговая стратегия. Сначала соберём контекст в проекте."
        ),
    }
    title = text[:80] if text else category.value
    rationale_map = {
        UserRequestRouteCategory.TELEGRAM_BOT: "Telegram bot development task.",
        UserRequestRouteCategory.CONTENT: "Content creation task — no full research.",
        UserRequestRouteCategory.CONTENT_PLAN: "Content plan task.",
        UserRequestRouteCategory.SOCIAL_MEDIA: "Social media content task.",
        UserRequestRouteCategory.YOUTUBE: "YouTube content task.",
        UserRequestRouteCategory.IMAGE_GENERATION: "Visual asset generation task.",
        UserRequestRouteCategory.WEBSITE: "Website build task.",
        UserRequestRouteCategory.AUTOMATION: "Automation development task.",
        UserRequestRouteCategory.SAAS: "SaaS project intake — contextual confirmation.",
        UserRequestRouteCategory.IDEA_VALIDATION: "Business idea validation intake.",
        UserRequestRouteCategory.MARKET_RESEARCH: "Market research project intake.",
        UserRequestRouteCategory.COMPETITOR_ANALYSIS: "Competitor analysis project intake.",
        UserRequestRouteCategory.MARKETING_STRATEGY: "Marketing strategy / campaign planning.",
    }
    return RouteDecision(
        category=category,
        kind=kind,
        confidence=confidence,
        requires_project=requires_project,
        avoids_investigation=_avoids(category),
        assigned_specialist=_specialist(category),
        clarification_question=None,
        next_href=next_href,
        next_action_label=next_action_label,
        assistant_message=messages.get(
            category,
            "Понял задачу. Следующий шаг — по кнопке ниже.",
        ),
        title=title,
        rationale=rationale_map.get(category, f"Routed to {category.value}."),
    )
