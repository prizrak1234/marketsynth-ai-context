"""Bounded Project Command Center General routing (recommend-only).

No autonomous COO. No provider execution. Maps intent → capability/skill → deep link.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.user_request_routing import normalize_request_text, route_user_request
from app.schemas.contracts import UserRequestRouteCategory


@dataclass(frozen=True, slots=True)
class PccRouteDecision:
    assistant_message: str
    capability_id: str | None
    skill_id: str | None
    next_href: str | None
    next_action_label: str | None
    requires_paid: bool = False
    requires_external: bool = False
    requires_approval: bool = False
    status_notes: str | None = None


def _cd_href(project_id: str, mode: str | None = None) -> str:
    params = f"project={project_id}&view=content_director"
    if mode:
        params += f"&mode={mode}"
    return f"/workspace?{params}"


def _skills_href() -> str:
    return "/workspace/settings/skills"


def route_project_general(
    text: str,
    *,
    project_id: str,
    xmlriver_configured: bool = True,
    avito_configured: bool = False,
    has_research_result: bool = False,
) -> PccRouteDecision:
    """Recommend capability/skill and deep link. Never executes paid/external calls."""
    normalized = normalize_request_text(text)
    lower = normalized.lower()

    if not normalized:
        return PccRouteDecision(
            assistant_message=(
                "Опишите задачу: текст, изображение, ключевые слова или состояние проекта."
            ),
            capability_id=None,
            skill_id=None,
            next_href=None,
            next_action_label=None,
        )

    # Video — honest coming soon
    if re.search(r"\b(видео|video|ролик|reel)\b", lower):
        return PccRouteDecision(
            assistant_message=(
                "Видео — следующий модуль Creative Platform. Генерация пока недоступна. "
                "Могу помочь подготовить текст или изображение к будущему ролику."
            ),
            capability_id="launch.visuals",
            skill_id=None,
            next_href=None,
            next_action_label=None,
            status_notes="coming_soon",
        )

    # Avito — never execute when unconfigured
    if re.search(r"\bavito\b|авито", lower):
        if not avito_configured:
            return PccRouteDecision(
                assistant_message=(
                    "Навык Avito установлен, но не подключён. Внешние запросы к Avito "
                    "не выполняются без credentials. Подключите интеграцию в настройках навыков."
                ),
                capability_id="project.integrations",
                skill_id="marketsynth.avito",
                next_href=_skills_href(),
                next_action_label="Подключить Avito",
                requires_external=True,
                requires_approval=True,
                status_notes="unconfigured",
            )
        return PccRouteDecision(
            assistant_message=(
                "Avito подключён. Откройте навыки, чтобы выполнить read-only запрос с явным подтверждением."
            ),
            capability_id="project.integrations",
            skill_id="marketsynth.avito",
            next_href=_skills_href(),
            next_action_label="Открыть навыки",
            requires_external=True,
            requires_approval=True,
        )

    # Wordstat / keywords
    if re.search(
        r"частотн|ключ(ев|ев\w*)|wordstat|семантик|xmlriver|запрос(ов|ы)?\b",
        lower,
    ):
        if not xmlriver_configured:
            return PccRouteDecision(
                assistant_message=(
                    "Проверка ключевых слов через XMLRiver требует подключённый credential. "
                    "Сейчас навык недоступен для исполнения."
                ),
                capability_id="project.integrations",
                skill_id="marketsynth.xmlriver.wordstat",
                next_href=_skills_href(),
                next_action_label="Проверить навыки",
                requires_external=True,
                status_notes="unconfigured",
            )
        return PccRouteDecision(
            assistant_message=(
                "Могу направить вас к навыку XMLRiver Wordstat для проверки частотности. "
                "Исполнение запускается только явно из Skills — General сам не вызывает провайдер."
            ),
            capability_id="project.integrations",
            skill_id="marketsynth.xmlriver.wordstat",
            next_href=_skills_href(),
            next_action_label="Открыть навыки",
            requires_external=True,
            requires_approval=True,
        )

    # Image before generic text (e.g. «изображение к посту»)
    if re.search(
        r"изображен|картинк|visual|\bimage\b|баннер|картинка",
        lower,
    ):
        return PccRouteDecision(
            assistant_message=(
                "Задача похожа на создание изображения. Маршрут: Content Director → Изображение. "
                "Платный image provider вызывается только после явного действия в Image Runtime."
            ),
            capability_id="project.content_director",
            skill_id="marketsynth.visual_generation",
            next_href=_cd_href(project_id, "image"),
            next_action_label="Создать изображение",
            requires_paid=True,
            requires_approval=True,
        )

    # Research — paused: no new run CTA; only claim Recent when a run exists
    if re.search(
        r"исслед|research|провер\w*\s+иде|иде\w*\s+заново|\bbiv\b|вердикт",
        lower,
    ):
        if has_research_result:
            return PccRouteDecision(
                assistant_message=(
                    "Исследование идеи временно ограничено (Decision Engine до 18.08). "
                    "Новый запуск не предлагаю. Сохранённый прогон этого проекта "
                    "отображается в «Последних результатах»."
                ),
                capability_id="project.research",
                skill_id=None,
                next_href=f"/workspace?project={project_id}#pcc-recent",
                next_action_label="К результатам",
                status_notes="paused",
            )
        return PccRouteDecision(
            assistant_message=(
                "Исследование идеи временно ограничено (Decision Engine до 18.08). "
                "Новый запуск не предлагаю. Сохранённых результатов Research по этому "
                "проекту пока нет — раздел «Последние результаты» показывает только "
                "то, что уже есть (тексты, изображения, прошлый Research при наличии)."
            ),
            capability_id="project.research",
            skill_id=None,
            next_href=f"/workspace?project={project_id}#pcc-capabilities",
            next_action_label="К возможностям",
            status_notes="paused",
        )

    # Materials / project state
    if re.search(r"материал|истори(я|ю)|состоян(ие|ия) проект|что готов|overview", lower) or (
        "проект" in lower and re.search(r"покажи|статус|обзор", lower)
    ):
        return PccRouteDecision(
            assistant_message=(
                "Откройте Content Director для материалов или оставайтесь в Command Center "
                "для обзора capability и последних результатов."
            ),
            capability_id="project.content_director",
            skill_id=None,
            next_href=_cd_href(project_id),
            next_action_label="Открыть материалы",
        )

    decision = route_user_request(normalized)

    if decision.category == UserRequestRouteCategory.IMAGE_GENERATION:
        return PccRouteDecision(
            assistant_message=(
                "Задача похожа на создание изображения. Маршрут: Content Director → Изображение. "
                "Платный image provider вызывается только после явного действия в Image Runtime."
            ),
            capability_id="project.content_director",
            skill_id="marketsynth.visual_generation",
            next_href=_cd_href(project_id, "image"),
            next_action_label="Создать изображение",
            requires_paid=True,
            requires_approval=True,
        )

    if decision.category in (
        UserRequestRouteCategory.CONTENT,
        UserRequestRouteCategory.CONTENT_PLAN,
        UserRequestRouteCategory.SOCIAL_MEDIA,
        UserRequestRouteCategory.YOUTUBE,
    ) or re.search(r"текст|пост|telegram|телеграм|копирайт|напиш", lower):
        return PccRouteDecision(
            assistant_message=(
                "Задача похожа на создание текста. Маршрут: Content Director → Текст, "
                "навык marketsynth.copywriter. Генерация не запускается из General — "
                "откройте контур и подтвердите действие там."
            ),
            capability_id="project.content_director",
            skill_id="marketsynth.copywriter",
            next_href=_cd_href(project_id, "text"),
            next_action_label="Создать текст",
            requires_paid=False,
            requires_approval=True,
        )

    if decision.category in (
        UserRequestRouteCategory.IDEA_VALIDATION,
        UserRequestRouteCategory.MARKET_RESEARCH,
        UserRequestRouteCategory.COMPETITOR_ANALYSIS,
    ):
        return PccRouteDecision(
            assistant_message=(
                "Research/проверка идеи сейчас в режиме ограничения. Новый прогон не запускаю. "
                "Смотрите сохранённые результаты в Command Center, если они есть."
            ),
            capability_id="project.research",
            skill_id=None,
            next_href=f"/workspace?project={project_id}#pcc-recent",
            next_action_label="К результатам",
            status_notes="paused",
        )

    if decision.category == UserRequestRouteCategory.MARKETING_STRATEGY:
        return PccRouteDecision(
            assistant_message=(
                "Стратегия ещё не подключена как Runtime. Место в жизненном цикле сохранено "
                "(статус: запланировано)."
            ),
            capability_id="project.strategy",
            skill_id=None,
            next_href=None,
            next_action_label=None,
            status_notes="planned",
        )

    # Fallback: show capabilities
    return PccRouteDecision(
        assistant_message=(
            decision.assistant_message
            or "Уточните задачу. Ниже — возможности агентства: тексты, изображения, "
            "навыки и честно обозначенные будущие модули."
        ),
        capability_id=None,
        skill_id=None,
        next_href=f"/workspace?project={project_id}#pcc-capabilities",
        next_action_label="Показать возможности",
        status_notes=decision.rationale or None,
    )
