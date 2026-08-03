"""Build minimal ProjectBrief from UserRequest text (Phase 1B.1 bootstrap)."""

from __future__ import annotations

from app.core.security import sanitize_text
from app.schemas.contracts import (
    ProjectBriefBasicsSection,
    ProjectBriefContent,
    ProjectBriefCreateRequest,
    ProjectBriefProductSection,
    ProjectBriefReadinessStatus,
)


def _truncate(value: str, max_len: int) -> str:
    cleaned = sanitize_text(value).strip()
    return cleaned[:max_len]


def brief_content_from_user_request(
    *,
    text: str,
    title: str = "",
    locale: str = "ru",
) -> ProjectBriefCreateRequest:
    idea = _truncate(text, 8000)
    name = _truncate(title or idea[:80] or "Новый проект", 256)
    return ProjectBriefCreateRequest(
        language=locale[:16] or "ru",
        project_basics=ProjectBriefBasicsSection(
            project_name=name,
            idea_description=idea,
            business_type="unknown",
            project_stage="exploring",
            geography="",
            preferred_language=locale[:16] or "ru",
        ),
        product=ProjectBriefProductSection(
            product_or_service=idea[:4000],
            customer_problem="",
            value_proposition="",
        ),
        assumptions=["Сформировано автоматически из запроса на главной."],
        missing_data=[
            "Детали продукта",
            "География",
            "Экономика",
            "Конкуренты",
        ],
        readiness_status=ProjectBriefReadinessStatus.INSUFFICIENT_DATA,
        readiness_reasons=["Автоматический бриф — требуется исследование."],
    )


def brief_content_from_text_update(
    *,
    text: str,
    title: str = "",
    locale: str = "ru",
) -> ProjectBriefContent:
    return ProjectBriefContent.model_validate(
        brief_content_from_user_request(text=text, title=title, locale=locale).model_dump()
    )
