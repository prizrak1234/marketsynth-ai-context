"""Prompt messages for commercial chat general_answer (one LLM call per user turn)."""

from __future__ import annotations

from app.llm.contracts import LLMMessage

_SYSTEM_RU = (
    "Ты — деловой ассистент Marketsynth. Отвечай по существу на вопрос пользователя "
    "на русском языке. Не предлагай автоматически создавать проект, не запускай "
    "исследование рынка и не подменяй ответ шаблоном про проверку бизнес-идеи. "
    "Если вопрос вне компетенции — честно скажи об ограничении."
)

_SYSTEM_EN = (
    "You are the Marketsynth business assistant. Answer the user's question directly. "
    "Do not auto-create projects or substitute canned business-validation text."
)


def build_general_answer_messages(*, user_text: str, locale: str = "ru") -> list[LLMMessage]:
    system = _SYSTEM_RU if locale.lower().startswith("ru") else _SYSTEM_EN
    return [
        LLMMessage(role="system", content=system),
        LLMMessage(role="user", content=user_text),
    ]
