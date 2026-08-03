"""Project Command Center summary + General recommend-only chat."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import sanitize_text
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.project import ProjectTable
from app.db.repositories.agent_chat_messages import ChatMessageRepository
from app.db.repositories.agent_chat_sessions import ChatSessionRepository
from app.db.repositories.business_idea_validation_runs import (
    BusinessIdeaValidationRunRepository,
)
from app.db.repositories.content_director import ContentRequestRepository
from app.db.repositories.visual_director import VisualRequestRepository
from app.domain.project_command_center_routing import route_project_general
from app.product_skills.runtime_service import ProductSkillRuntimeService
from app.product_skills.tools_avito import avito_configured
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionStatus,
    PccActivityItem,
    PccAttentionItem,
    PccCapabilityCard,
    PccCapabilityStatus,
    PccGeneralConversation,
    PccGeneralMessage,
    PccGeneralSendResponse,
    PccRecentResult,
    PccSkillChip,
    ProjectCommandCenterSummary,
)
from app.services.transaction import transactional

_STATUS_LABELS: dict[PccCapabilityStatus, str] = {
    PccCapabilityStatus.AVAILABLE: "Доступно",
    PccCapabilityStatus.IN_PROGRESS: "В работе",
    PccCapabilityStatus.REQUIRES_INPUT: "Нужны данные",
    PccCapabilityStatus.REQUIRES_APPROVAL: "Ожидает согласования",
    PccCapabilityStatus.COMPLETED: "Завершено",
    PccCapabilityStatus.PAUSED: "Временно приостановлено",
    PccCapabilityStatus.PLANNED: "Запланировано",
    PccCapabilityStatus.UNCONFIGURED: "Требуется подключение",
    PccCapabilityStatus.BLOCKED: "Недоступно",
    PccCapabilityStatus.COMING_SOON: "Скоро",
}


def _label(status: PccCapabilityStatus) -> str:
    return _STATUS_LABELS[status]


def _cd_href(project_id: UUID, mode: str | None = None) -> str:
    base = f"/workspace?project={project_id}&view=content_director"
    if mode:
        return f"{base}&mode={mode}"
    return base


class ProjectCommandCenterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = ChatSessionRepository(session)
        self._messages = ChatMessageRepository(session)
        self._content = ContentRequestRepository(session)
        self._visual = VisualRequestRepository(session)
        self._biv_runs = BusinessIdeaValidationRunRepository(session)
        self._skills = ProductSkillRuntimeService(session)

    async def _project(self, owner_id: UUID, project_id: UUID) -> ProjectTable:
        row = await self._session.get(ProjectTable, project_id)
        if row is None or row.owner_id != owner_id:
            raise NotFoundError("Project not found")
        return row

    async def get_summary(
        self, owner_id: UUID, project_id: UUID
    ) -> ProjectCommandCenterSummary:
        project = await self._project(owner_id, project_id)
        text_rows = await self._content.list_for_project(owner_id, project_id)
        image_rows = await self._visual.list_for_project(owner_id, project_id)
        biv_latest = await self._biv_runs.get_latest_for_project(owner_id, project_id)

        skills_index = await self._skills.list_skills(owner_id)
        skill_by_id = {s.skill_id: s for s in skills_index}
        xmlriver = skill_by_id.get("marketsynth.xmlriver.wordstat")
        avito = skill_by_id.get("marketsynth.avito")
        copywriter = skill_by_id.get("marketsynth.copywriter")

        xmlriver_ok = bool(xmlriver and xmlriver.configured and xmlriver.enabled)
        avito_ok = avito_configured()

        last_changed = project.updated_at
        for row in (*text_rows, *image_rows):
            if row.updated_at and (last_changed is None or row.updated_at > last_changed):
                last_changed = row.updated_at
        if biv_latest is not None:
            biv_ts = biv_latest.updated_at or biv_latest.finished_at or biv_latest.created_at
            if biv_ts and (last_changed is None or biv_ts > last_changed):
                last_changed = biv_ts

        approved_text = [r for r in text_rows if r.approved_asset_id]
        approved_image = [r for r in image_rows if r.approved_asset_id]
        active_text = [r for r in text_rows if r.current_run_id and not r.approved_asset_id]
        active_image = [r for r in image_rows if r.current_run_id and not r.approved_asset_id]

        capabilities = self._capability_cards(
            project_id=project_id,
            text_rows=text_rows,
            image_rows=image_rows,
            xmlriver_ok=xmlriver_ok,
            avito_ok=avito_ok,
            biv_latest=biv_latest,
        )

        active_work: list[PccActivityItem] = []
        for r in active_text:
            active_work.append(
                PccActivityItem(
                    id=str(r.id),
                    title=r.title,
                    kind="text",
                    status="in_progress",
                    status_label="В работе",
                    updated_at=r.updated_at,
                    open_href=_cd_href(project_id, "text"),
                )
            )
        for r in active_image:
            active_work.append(
                PccActivityItem(
                    id=str(r.id),
                    title=r.title,
                    kind="image",
                    status="in_progress",
                    status_label="В работе",
                    updated_at=r.updated_at,
                    open_href=_cd_href(project_id, "image"),
                )
            )

        recent: list[PccRecentResult] = []
        if biv_latest is not None:
            biv_status = str(getattr(biv_latest.status, "value", biv_latest.status))
            biv_label = {
                "succeeded": "Завершено",
                "partial": "Частичный результат",
                "failed": "Ошибка",
                "queued": "В очереди",
                "running": "В работе",
                "cancelled": "Отменено",
            }.get(biv_status, biv_status)
            verdict = None
            if isinstance(biv_latest.result_json, dict):
                verdict = biv_latest.result_json.get("verdict")
            title = "Проверка идеи"
            if verdict:
                title = f"Проверка идеи — {verdict}"
            recent.append(
                PccRecentResult(
                    id=str(biv_latest.id),
                    title=title,
                    kind="research",
                    status=biv_status,
                    status_label=biv_label,
                    version=None,
                    updated_at=biv_latest.updated_at
                    or biv_latest.finished_at
                    or biv_latest.created_at,
                    open_href=f"/workspace?project={project_id}#pcc-recent",
                )
            )
        for r in approved_text[:5]:
            recent.append(
                PccRecentResult(
                    id=str(r.id),
                    title=r.title,
                    kind="text",
                    status="approved",
                    status_label="Утверждено",
                    version=r.version,
                    updated_at=r.updated_at,
                    open_href=_cd_href(project_id, "text"),
                )
            )
        for r in approved_image[:5]:
            recent.append(
                PccRecentResult(
                    id=str(r.id),
                    title=r.title,
                    kind="image",
                    status="approved",
                    status_label="Утверждено",
                    version=r.version,
                    updated_at=r.updated_at,
                    open_href=_cd_href(project_id, "image"),
                )
            )
        recent.sort(key=lambda x: x.updated_at or datetime.min, reverse=True)
        recent = recent[:8]

        attention: list[PccAttentionItem] = []
        if avito and not avito_ok:
            attention.append(
                PccAttentionItem(
                    id="avito-unconfigured",
                    title="Avito не подключён",
                    message="Навык установлен, но credentials не настроены. Внешние вызовы запрещены.",
                    severity="warning",
                    cta_label="Открыть навыки",
                    cta_href="/workspace/settings/skills",
                )
            )

        skill_chips: list[PccSkillChip] = []
        for sid, name, fallback_ok in (
            ("marketsynth.copywriter", "Copywriter", True),
            ("marketsynth.xmlriver.wordstat", "XMLRiver Wordstat", xmlriver_ok),
            ("marketsynth.avito", "Avito", avito_ok),
        ):
            item = skill_by_id.get(sid)
            if sid == "marketsynth.avito":
                status = "configured" if avito_ok else "unconfigured"
                label = "подключён" if avito_ok else "требуется подключение"
            elif sid == "marketsynth.xmlriver.wordstat":
                ok = bool(item and item.configured) if item else fallback_ok
                status = "configured" if ok else "unconfigured"
                label = "подключён" if ok else "требуется подключение"
            else:
                status = "configured"
                label = "подключён"
            skill_chips.append(
                PccSkillChip(skill_id=sid, name=name, status=status, status_label=label)
            )

        # Copywriter always available as builtin; keep variable referenced
        _ = copywriter

        project_status = "Не проверялось"
        if biv_latest is not None:
            project_status = "Есть Research"
        if approved_text or approved_image:
            project_status = "Есть материалы"
        if active_work:
            project_status = "В работе"

        return ProjectCommandCenterSummary(
            project_id=project.id,
            project_name=project.name,
            project_status=project_status,
            project_summary=None,
            last_changed_at=last_changed,
            capabilities=capabilities,
            active_work=active_work,
            recent_results=recent,
            attention=attention,
            skills=skill_chips,
        )

    def _capability_cards(
        self,
        *,
        project_id: UUID,
        text_rows: list,
        image_rows: list,
        xmlriver_ok: bool,
        avito_ok: bool,
        biv_latest=None,
    ) -> list[PccCapabilityCard]:
        text_last = text_rows[0] if text_rows else None
        image_last = image_rows[0] if image_rows else None
        research_note = (
            "Новые запуски ограничены до 18.08. Сохранённый прогон отображается в «Последних результатах»."
            if biv_latest is not None
            else "Новые запуски ограничены до 18.08. Сохранённых результатов Research по проекту пока нет."
        )
        research_summary = None
        if biv_latest is not None:
            research_summary = str(getattr(biv_latest.status, "value", biv_latest.status))
        cards: list[PccCapabilityCard] = [
            PccCapabilityCard(
                capability_id="project.research",
                title="Проверка идеи",
                value_proposition="Исследование рынка и доказательства по проекту.",
                status=PccCapabilityStatus.PAUSED,
                status_label=_label(PccCapabilityStatus.PAUSED),
                last_result_summary=research_summary,
                last_changed_at=(
                    (biv_latest.updated_at or biv_latest.finished_at or biv_latest.created_at)
                    if biv_latest is not None
                    else None
                ),
                primary_cta_label=None,
                primary_cta_href=None,
                cta_enabled=False,
                placeholder_note=research_note,
            ),
            PccCapabilityCard(
                capability_id="project.strategy",
                title="Стратегия",
                value_proposition="Позиционирование и стратегические решения после Research.",
                status=PccCapabilityStatus.PLANNED,
                status_label=_label(PccCapabilityStatus.PLANNED),
                cta_enabled=False,
                placeholder_note="Strategy Runtime ещё не подключён.",
            ),
            PccCapabilityCard(
                capability_id="project.launch",
                title="Запуск",
                value_proposition="Пакет запуска и публикационный контур.",
                status=PccCapabilityStatus.PLANNED,
                status_label=_label(PccCapabilityStatus.PLANNED),
                cta_enabled=False,
                placeholder_note="Launch Runtime ещё не подключён.",
            ),
            PccCapabilityCard(
                capability_id="project.content_director.text",
                title="Тексты",
                value_proposition="Telegram-посты и тексты для каналов проекта.",
                status=PccCapabilityStatus.AVAILABLE,
                status_label=_label(PccCapabilityStatus.AVAILABLE),
                last_result_summary=text_last.title if text_last else None,
                last_changed_at=text_last.updated_at if text_last else None,
                primary_cta_label="Создать текст",
                primary_cta_href=_cd_href(project_id, "text"),
                cta_enabled=True,
            ),
            PccCapabilityCard(
                capability_id="project.content_director.image",
                title="Изображения",
                value_proposition="Визуалы к материалам проекта.",
                status=PccCapabilityStatus.AVAILABLE,
                status_label=_label(PccCapabilityStatus.AVAILABLE),
                last_result_summary=image_last.title if image_last else None,
                last_changed_at=image_last.updated_at if image_last else None,
                primary_cta_label="Создать изображение",
                primary_cta_href=_cd_href(project_id, "image"),
                cta_enabled=True,
            ),
            PccCapabilityCard(
                capability_id="launch.visuals",
                title="Видео",
                value_proposition="Короткие ролики в том же контуре проекта.",
                status=PccCapabilityStatus.COMING_SOON,
                status_label=_label(PccCapabilityStatus.COMING_SOON),
                cta_enabled=False,
                placeholder_note="Video Runtime не реализован. Не открывает пустой экран.",
            ),
            PccCapabilityCard(
                capability_id="launch.publication",
                title="Публикация",
                value_proposition="Согласованная публикация в каналы.",
                status=PccCapabilityStatus.PLANNED,
                status_label=_label(PccCapabilityStatus.PLANNED),
                cta_enabled=False,
                placeholder_note="Публикация в новом creative flow ещё не подключена.",
            ),
            PccCapabilityCard(
                capability_id="workspace.analytics",
                title="Аналитика",
                value_proposition="Показатели по проекту и результатам.",
                status=PccCapabilityStatus.PLANNED,
                status_label=_label(PccCapabilityStatus.PLANNED),
                cta_enabled=False,
                placeholder_note="Аналитика зарезервирована в IA.",
            ),
            PccCapabilityCard(
                capability_id="workspace.knowledge",
                title="Материалы Content Director",
                value_proposition="Черновики и утверждённые тексты/изображения проекта.",
                status=PccCapabilityStatus.AVAILABLE,
                status_label=_label(PccCapabilityStatus.AVAILABLE),
                primary_cta_label="Открыть Content Director",
                primary_cta_href=_cd_href(project_id),
                cta_enabled=True,
            ),
            PccCapabilityCard(
                capability_id="project.integrations",
                title="Интеграции и навыки",
                value_proposition="Copywriter, XMLRiver, Avito и другие skills.",
                status=(
                    PccCapabilityStatus.UNCONFIGURED
                    if not avito_ok
                    else PccCapabilityStatus.AVAILABLE
                ),
                status_label=_label(
                    PccCapabilityStatus.UNCONFIGURED
                    if not avito_ok
                    else PccCapabilityStatus.AVAILABLE
                ),
                primary_cta_label="Открыть навыки",
                primary_cta_href="/workspace/settings/skills",
                cta_enabled=True,
                placeholder_note=(
                    None
                    if avito_ok and xmlriver_ok
                    else "Часть навыков требует подключения credentials."
                ),
            ),
        ]
        return cards

    async def _get_or_create_general_session(
        self, owner_id: UUID, project_id: UUID
    ) -> AgentChatSessionTable:
        existing = await self._sessions.list_for_project(
            owner_id,
            project_id,
            status=ChatSessionStatus.ACTIVE,
            limit=50,
        )
        for row in existing:
            if row.entrypoint == ChatSessionEntrypoint.PROJECT_GENERAL:
                return row
        row = AgentChatSessionTable(
            owner_id=owner_id,
            project_id=project_id,
            agent_id=None,
            entrypoint=ChatSessionEntrypoint.PROJECT_GENERAL,
            domain=ChatSessionDomain.MARKETING,
            status=ChatSessionStatus.ACTIVE,
            title="General",
        )
        async with transactional(self._session):
            await self._sessions.create(row)
        return row

    def _to_message(self, row: AgentChatMessageTable) -> PccGeneralMessage:
        meta = row.message_metadata or {}
        return PccGeneralMessage(
            id=row.id,
            role=str(row.role.value if hasattr(row.role, "value") else row.role),
            content=row.content,
            created_at=row.created_at,
            capability_id=meta.get("capability_id"),
            skill_id=meta.get("skill_id"),
            next_href=meta.get("next_href"),
            next_action_label=meta.get("next_action_label"),
            requires_paid=bool(meta.get("requires_paid")),
            requires_external=bool(meta.get("requires_external")),
            requires_approval=bool(meta.get("requires_approval")),
            status_notes=meta.get("status_notes"),
        )

    async def get_general(
        self, owner_id: UUID, project_id: UUID
    ) -> PccGeneralConversation:
        await self._project(owner_id, project_id)
        session = await self._get_or_create_general_session(owner_id, project_id)
        rows = await self._messages.list_for_session(session.id, limit=100)
        return PccGeneralConversation(
            session_id=session.id,
            project_id=project_id,
            messages=[self._to_message(r) for r in rows],
        )

    async def send_general(
        self, owner_id: UUID, project_id: UUID, message: str
    ) -> PccGeneralSendResponse:
        await self._project(owner_id, project_id)
        cleaned = sanitize_text(message)
        if not cleaned.strip():
            raise ValueError("empty_message")

        skills = await self._skills.list_skills(owner_id)
        by_id = {s.skill_id: s for s in skills}
        xmlriver = by_id.get("marketsynth.xmlriver.wordstat")
        xmlriver_ok = bool(xmlriver and xmlriver.configured and xmlriver.enabled)
        avito_ok = avito_configured()
        biv_latest = await self._biv_runs.get_latest_for_project(owner_id, project_id)

        decision = route_project_general(
            cleaned,
            project_id=str(project_id),
            xmlriver_configured=xmlriver_ok,
            avito_configured=avito_ok,
            has_research_result=biv_latest is not None,
        )

        session = await self._get_or_create_general_session(owner_id, project_id)

        user_row = AgentChatMessageTable(
            session_id=session.id,
            role=AgentChatMessageRole.USER,
            content=cleaned,
            message_metadata={},
        )
        assistant_meta = {
            "capability_id": decision.capability_id,
            "skill_id": decision.skill_id,
            "next_href": decision.next_href,
            "next_action_label": decision.next_action_label,
            "requires_paid": decision.requires_paid,
            "requires_external": decision.requires_external,
            "requires_approval": decision.requires_approval,
            "status_notes": decision.status_notes,
            "recommend_only": True,
        }
        assistant_row = AgentChatMessageTable(
            session_id=session.id,
            role=AgentChatMessageRole.ASSISTANT,
            content=decision.assistant_message,
            message_metadata=assistant_meta,
        )

        async with transactional(self._session):
            self._session.add(user_row)
            self._session.add(assistant_row)
            session.updated_at = datetime.utcnow()
            self._session.add(session)

        await self._session.refresh(assistant_row)
        conversation = await self.get_general(owner_id, project_id)
        return PccGeneralSendResponse(
            conversation=conversation,
            assistant=self._to_message(assistant_row),
        )
