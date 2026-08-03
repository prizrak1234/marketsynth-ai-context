"""Route marketer chat messages to sub-agent personas (Phase AI.10+) — chains via AI.14."""

from __future__ import annotations

from app.agents.marketer.chains import (
    CONTENT_LAUNCH,
    CONTENT_PLAN,
    RESEARCH,
    REWRITE,
    MarketingExecutionChain,
)
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.execution import _SUPPORTED_SUBAGENTS

# Copywriter: phrase + verb/noun intent (natural speech, not only contiguous substrings).
_COPYWRITER_PHRASES: tuple[str, ...] = (
    "перепиши",
    "переписать",
    "улучши",
    "улучшить",
    "сделай текст",
    "улучши текст",
    "улучши пост",
    "перепиши пост",
    "перепиши текст",
    "rewrite the post",
    "rewrite this post",
    "rewrite",
    "improve the copy",
    "improve this post",
    "improve",
    "адаптируй тон",
)

_COPYWRITER_VERBS: tuple[str, ...] = (
    "перепиши",
    "переписать",
    "улучши",
    "улучшить",
    "rewrite",
    "improve",
)

_COPYWRITER_NOUNS: tuple[str, ...] = (
    "пост",
    "текст",
    "copy",
)

_SUBAGENT_PHRASES: dict[MarketerSubAgentType, tuple[str, ...]] = {
    MarketerSubAgentType.COPYWRITER: (),
    MarketerSubAgentType.ANALYST: (
        "проанализируй кампанию",
        "анализ кампании",
        "analyze the campaign",
        "campaign analysis",
        "что показывает кампания",
        "review queue status",
        "статус review queue",
    ),
    MarketerSubAgentType.STRATEGIST: (
        "сделай контент-план",
        "создай контент-план",
        "разработай стратегию",
        "стратегия запуска",
        "позиционирование",
        "оффер",
        "план кампании",
        "сделай контент план",
        "create a content plan",
        "создай план кампании",
    ),
    MarketerSubAgentType.RESEARCHER: (
        "исследуй аудиторию",
        "исследование аудитории",
        "research the audience",
        "audience research",
        "изучи бриф",
        "study the brief",
        "marketing brief research",
    ),
}


def _token_has_verb_prefix(token: str, verb: str) -> bool:
    return token == verb or token.startswith(verb)


def score_copywriter_intent(normalized: str) -> int:
    """
    Score copywriter routing intent using phrases and rewrite-verb + content-noun pairs.

    Supports natural phrasing such as «Перепиши этот пост» (verb and noun need not be adjacent).
    """
    if not normalized:
        return 0

    tokens = normalized.split()
    score = 0
    for phrase in _COPYWRITER_PHRASES:
        if phrase in normalized:
            score += len(phrase)

    has_verb = any(
        verb in tokens or any(_token_has_verb_prefix(token, verb) for token in tokens)
        for verb in _COPYWRITER_VERBS
    )
    has_noun = any(noun in tokens for noun in _COPYWRITER_NOUNS)

    if has_verb and has_noun:
        score = max(score, 12)

    return score


def detect_best_subagent(*, message: str) -> MarketerSubAgentType | None:
    """
    Return the best-matching marketer sub-agent persona, or None to keep orchestrator voice.

    None means no explicit sub-agent intent — orchestrator coordinates without persona overlay.
    """
    normalized = " ".join((message or "").lower().split())
    if not normalized:
        return None

    scores: dict[MarketerSubAgentType, int] = {}
    for subagent_type, phrases in _SUBAGENT_PHRASES.items():
        for phrase in phrases:
            if phrase in normalized:
                scores[subagent_type] = scores.get(subagent_type, 0) + len(phrase)

    copywriter_score = score_copywriter_intent(normalized)
    if copywriter_score:
        scores[MarketerSubAgentType.COPYWRITER] = max(
            scores.get(MarketerSubAgentType.COPYWRITER, 0),
            copywriter_score,
        )

    if ("контент-план" in normalized or "content plan" in normalized) and any(
        token in normalized for token in ("сделай", "создай", "create", "build")
    ):
        scores[MarketerSubAgentType.STRATEGIST] = (
            scores.get(MarketerSubAgentType.STRATEGIST, 0) + 12
        )

    if not scores:
        return None

    return max(scores.items(), key=lambda item: item[1])[0]


_LAUNCH_CHAIN_PHRASES: tuple[str, ...] = (
    "запусти новый продукт",
    "запусти продукт",
    "launch new product",
    "launch the product",
    "new product launch",
)

_CONTENT_PLAN_CHAIN_PHRASES: tuple[str, ...] = (
    "сделай контент-план",
    "создай контент-план",
    "сделай контент план",
    "создай контент план",
    "create a content plan",
)

_RESEARCH_CHAIN_PHRASES: tuple[str, ...] = _SUBAGENT_PHRASES[MarketerSubAgentType.RESEARCHER]


def detect_execution_chain(*, message: str) -> MarketingExecutionChain | None:
    """
    Return a linear sub-agent execution chain, or None for orchestrator-only / persona overlay.

    Frozen examples (AI.14):
    - «Запусти новый продукт» → researcher → strategist → copywriter
    - «Сделай контент-план» → strategist → copywriter
    - «Перепиши пост» → copywriter
    - «Исследуй аудиторию» → researcher
    - «Проанализируй рынок» → None (AI.12.1)
    """
    normalized = " ".join((message or "").lower().split())
    if not normalized:
        return None

    if any(phrase in normalized for phrase in _LAUNCH_CHAIN_PHRASES):
        return CONTENT_LAUNCH

    if any(phrase in normalized for phrase in _CONTENT_PLAN_CHAIN_PHRASES):
        return CONTENT_PLAN

    if score_copywriter_intent(normalized):
        return REWRITE

    if any(phrase in normalized for phrase in _RESEARCH_CHAIN_PHRASES):
        return RESEARCH

    return None


def resolve_execution_chain(*, message: str) -> MarketingExecutionChain | None:
    """Chain from detect_execution_chain, else single supported sub-agent from persona router."""
    chain = detect_execution_chain(message=message)
    if chain is not None:
        return chain

    single = detect_best_subagent(message=message)
    if single is not None and single in _SUPPORTED_SUBAGENTS:
        return (single,)

    return None
