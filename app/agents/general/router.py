"""General agent domain routing (Phase AI.15–AI.17) — marketing, programmer, media, unknown."""

from __future__ import annotations

from app.agents.general.contracts import GeneralDomain

# Before marketing «telegram» — bot intents stay with Programmer.
_PROGRAMMER_PRIORITY_PHRASES: tuple[str, ...] = (
    "telegram bot",
    "telegram-бот",
    "telegram бот",
    "телеграм бот",
    "телеграм-бот",
)

# Before broad marketing — visual banner intents for Telegram channels.
_MEDIA_PRIORITY_PHRASES: tuple[str, ...] = (
    "баннер для telegram",
    "баннер в telegram",
    "баннер для телеграм",
    "баннер в телеграм",
    "telegram banner",
    "banner for telegram",
    "баннер для телеграм-канал",
)

# Before bare «telegram» / generic marketing — post and campaign copy.
_MARKETING_PRIORITY_PHRASES: tuple[str, ...] = (
    "пост в telegram",
    "пост для telegram",
    "telegram post",
    "контент для telegram",
    "контент в telegram",
    "кампания в telegram",
    "кампания для telegram",
    "telegram campaign",
    "campaign in telegram",
)

_MARKETING_PHRASES: tuple[str, ...] = (
    "создай кампанию",
    "создать кампанию",
    "сделай контент-план",
    "создай контент-план",
    "запусти продукт",
    "запусти новый продукт",
    "улучши пост",
    "перепиши пост",
    "перепиши этот пост",
    "перепиши",
    "маркетинг",
    "telegram",
    "контент",
    "контент-план",
    "кампани",
    "campaign",
    "content plan",
    "launch",
    "marketing",
    "аудитор",
    "audience",
    "оффер",
    "позиционирован",
)

_PROGRAMMER_PHRASES: tuple[str, ...] = (
    "код",
    "программа",
    "бот",
    "интеграция",
    "api",
    "автоматизация",
    "n8n",
    "make",
    "webhook",
    "сайт",
    "tilda",
    "скрипт",
    "python",
    "backend",
    "frontend",
    "разработ",
    "программист",
)

_MEDIA_PHRASES: tuple[str, ...] = (
    "картинка",
    "изображение",
    "баннер",
    "визуал",
    "дизайн",
    "креатив",
    "обложка",
    "видео",
    "сторис",
    "stories",
    "reels",
    "shorts",
    "превью",
    "preview",
    "логотип",
    "logo",
    "макет",
    "баннер",
    "creative",
    "visual",
    "thumbnail",
    "shot list",
    "шот-лист",
)


def detect_general_domain(*, message: str) -> GeneralDomain:
    """
    Route to marketing, programmer, media, or unknown.

    Priority: programmer bot → media banners → marketing posts/campaigns →
    broad marketing → programmer tech → media visual → unknown.
    """
    normalized = " ".join((message or "").lower().split())
    if not normalized:
        return GeneralDomain.UNKNOWN

    if any(phrase in normalized for phrase in _PROGRAMMER_PRIORITY_PHRASES):
        return GeneralDomain.PROGRAMMER

    if any(phrase in normalized for phrase in _MEDIA_PRIORITY_PHRASES):
        return GeneralDomain.MEDIA

    if any(phrase in normalized for phrase in _MARKETING_PRIORITY_PHRASES):
        return GeneralDomain.MARKETING

    if any(phrase in normalized for phrase in _MARKETING_PHRASES):
        return GeneralDomain.MARKETING

    if any(phrase in normalized for phrase in _PROGRAMMER_PHRASES):
        return GeneralDomain.PROGRAMMER

    if any(phrase in normalized for phrase in _MEDIA_PHRASES):
        return GeneralDomain.MEDIA

    return GeneralDomain.UNKNOWN
