"""Attach skill + capability pack + knowledge snapshot to UserRequest (Phase H2.5/H2.7).

No AgentRun. Draft generation is triggered later by UserRequestService when
CONTENT_DRAFT_EXECUTION_ENABLED and readiness == ready_for_draft.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_request import UserRequestTable
from app.domain.content_domain_classifier import (
    classify_content_domain,
    domain_codes_for_retrieval,
)
from app.core.config import get_settings
from app.knowledge_foundation.ingestion import ingest_approved_content_pack
from app.knowledge_foundation.retrieval_adapter import KnowledgeRetrievalAdapter
from app.knowledge_foundation.snapshot_service import KnowledgeSnapshotService
from app.knowledge_governance.governed_snapshot import (
    InsufficientGovernedKnowledgeError,
    create_governed_snapshot,
    list_eligible_published_versions,
)
from app.schemas.contracts import (
    ContentDomainCode,
    KnowledgeRetrievalRequest,
    SpecialistSkillCode,
    UserRequestExecutionReadiness,
    UserRequestRouteCategory,
    UserRequestRouteKind,
    UserRequestStatus,
)
from app.specialist_skills.capability_packs import get_capability_pack
from app.specialist_skills.registry import get_skill
from app.specialist_skills.route_mapping import map_route_to_skill

# Domains where Runtime must use published+fresh governed knowledge only.
_GOVERNED_REQUIRED_DOMAINS = frozenset(
    {
        ContentDomainCode.DRILLING_OPERATIONS,
        ContentDomainCode.INDUSTRIAL_SAFETY,
        ContentDomainCode.OIL_AND_GAS,
    }
)

# Hard required — block without these.
TELEGRAM_POST_HARD_REQUIRED = ("topic", "audience", "objective")
# Backward-compatible alias used by older tests/docs.
TELEGRAM_POST_REQUIRED = TELEGRAM_POST_HARD_REQUIRED

# Soft fields — defaults or inference; never block owner-test prompts.
TELEGRAM_LENGTH_STANDARD = "standard"  # 700–1200 characters
TELEGRAM_LENGTH_SHORT = "short"  # 400–700
TELEGRAM_LENGTH_LONG = "long"  # 1200–2000

_CTA_SEMANTICS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "discussion_question",
        re.compile(
            r"(?:в\s+конце\s+)?(?:задай|заверши|добавь|поставь)\s+(?:вопрос|вопросом)"
            r"|заверши\s+вопросом|вопрос\s+в\s+конце|ask\s+a\s+question\s+at\s+the\s+end",
            re.I,
        ),
        "Задать вопрос для обсуждения в конце поста",
    ),
    (
        "comment_prompt",
        re.compile(
            r"(?:поделиться(?:ться)?\s+мнением|написать\s+в\s+комментари[яи]|обсудите\s+в\s+комментари[яи]"
            r"|предложи\s+поделиться(?:ться)?|ask\s+(?:for\s+)?comments?)",
            re.I,
        ),
        "Предложить поделиться мнением в комментариях",
    ),
    (
        "subscribe",
        re.compile(r"(?:подписаться|призови\s+подписаться|subscribe)", re.I),
        "Призвать подписаться",
    ),
    (
        "follow_link",
        re.compile(
            r"(?:перейти\s+по\s+ссылке|пригласи\s+перейти|follow\s+(?:the\s+)?link|click\s+(?:the\s+)?link)",
            re.I,
        ),
        "Пригласить перейти по ссылке",
    ),
    (
        "contact",
        re.compile(r"(?:написать\s+нам|связаться|свяжитесь|contact\s+us)", re.I),
        "Предложить связаться",
    ),
    (
        "save_post",
        re.compile(r"(?:сохранить\s+пост|попроси\s+сохранить|save\s+(?:the\s+)?post)", re.I),
        "Попросить сохранить пост",
    ),
]

_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "topic": re.compile(
        r"(?:topic|тема|о\s+теме)\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "audience": re.compile(
        r"(?:audience|аудитори[яи])\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "objective": re.compile(
        r"(?:objective|цель|задач[аи])\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "tone": re.compile(
        r"(?:tone|тон)\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "length": re.compile(
        r"(?:length|длин[аы]|объ[её]м|примерн(?:ая|ую)\s+длин[уы])\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "CTA": re.compile(
        r"(?:cta|призыв(?:\s+к\s+действию)?)\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "factuality_mode": re.compile(
        r"(?:factuality|фактичность|режим\s+фактов)\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
    "brand_constraints": re.compile(
        r"(?:brand|бренд|ограничен)\s*[:=\-—–]\s*(.+?)(?:\n|$)",
        re.I,
    ),
}


@dataclass(frozen=True, slots=True)
class SkillContextAttachment:
    skill_code: str | None
    skill_version: str | None
    capability_pack_code: str | None
    capability_pack_version: str | None
    knowledge_snapshot_id: UUID | None
    knowledge_snapshot_hash: str | None
    execution_readiness: UserRequestExecutionReadiness
    missing_inputs: list[str]
    quality_profile_code: str | None
    skill_inputs: dict[str, Any]
    approved_knowledge_count: int
    status: UserRequestStatus
    clarification_question: str | None
    assistant_message: str | None


def _clean_value(raw: str) -> str:
    return re.sub(r"^[\s:=\-—–]+", "", (raw or "").strip()).strip(" .;")


def merge_image_inputs(
    *,
    text: str,
    clarification_answer: str | None,
    structured: dict[str, Any] | None,
) -> dict[str, str]:
    """Build image skill_inputs. Always refresh ``prompt`` from current text.

    Structured values (e.g. ``reference_set_id``) are kept, but a stale
    ``prompt`` from a prior clarify/pass must never win over the latest text.
    """
    merged: dict[str, str] = {}
    if structured:
        for key, value in structured.items():
            if value is not None and str(value).strip():
                merged[key] = str(value).strip()
    blob = " ".join(p for p in [text or "", clarification_answer or ""] if p).strip()
    # Always overwrite — setdefault previously kept a stale first-pass prompt.
    merged["prompt"] = blob
    lower = blob.lower()
    if "фотореалист" in lower or "photoreal" in lower:
        merged["realism"] = "photorealistic"
        merged["style"] = "photorealistic"
    else:
        merged.setdefault("realism", "default")
        merged.setdefault("style", "default")
    merged.setdefault("aspect_ratio", "1:1")
    merged.setdefault("number_of_variants", "1")
    if "текст" in lower or "надпис" in lower:
        merged.setdefault("text_overlay", "requested")
    if merged.get("reference_set_id"):
        merged.setdefault("_source_reference_set_id", "explicit")
    return merged


def _attach_image_generation(*, row, skill, pack, inputs: dict[str, str]) -> SkillContextAttachment:
    image_inputs = merge_image_inputs(
        text=row.text,
        clarification_answer=row.clarification_answer,
        structured=inputs,
    )
    if row.route_kind == UserRequestRouteKind.CLARIFY:
        return SkillContextAttachment(
            skill_code=skill.code.value,
            skill_version=skill.version,
            capability_pack_code=pack.specialist_role,
            capability_pack_version=pack.version,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.NEEDS_CLARIFICATION,
            missing_inputs=[],
            quality_profile_code="visual_quality_v1",
            skill_inputs=image_inputs,
            approved_knowledge_count=0,
            status=UserRequestStatus.NEEDS_CLARIFICATION,
            clarification_question=row.clarification_question,
            assistant_message=row.assistant_message or None,
        )
    prompt = (image_inputs.get("prompt") or "").strip()
    if len(prompt) < 8:
        return SkillContextAttachment(
            skill_code=skill.code.value,
            skill_version=skill.version,
            capability_pack_code=pack.specialist_role,
            capability_pack_version=pack.version,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.NEEDS_CLARIFICATION,
            missing_inputs=["prompt"],
            quality_profile_code="visual_quality_v1",
            skill_inputs=image_inputs,
            approved_knowledge_count=0,
            status=UserRequestStatus.NEEDS_CLARIFICATION,
            clarification_question="Опишите сцену подробнее: кто/что, место, настроение, стиль.",
            assistant_message="Нужно чуть больше деталей для изображения.",
        )
    return SkillContextAttachment(
        skill_code=skill.code.value,
        skill_version=skill.version,
        capability_pack_code=pack.specialist_role,
        capability_pack_version=pack.version,
        knowledge_snapshot_id=None,
        knowledge_snapshot_hash=None,
        execution_readiness=UserRequestExecutionReadiness.READY_FOR_DRAFT,
        missing_inputs=[],
        quality_profile_code="visual_quality_v1",
        skill_inputs=image_inputs,
        approved_knowledge_count=0,
        status=UserRequestStatus.READY_FOR_DRAFT,
        clarification_question=None,
        assistant_message=(
            "Понял. Это задача на создание изображения — исследование и полный "
            "маркетинговый цикл не нужны. Генерирую визуал."
        ),
    )


def infer_cta_from_text(blob: str) -> tuple[str, str] | None:
    """Return (cta_type, cta_text) when a natural CTA instruction is present."""
    for cta_type, pattern, label in _CTA_SEMANTICS:
        if pattern.search(blob):
            return cta_type, label
    return None


def infer_length_from_text(blob: str) -> tuple[str, str] | None:
    """Return (length_band, source) when length is mentioned; None otherwise."""
    lower = blob.lower()
    if re.search(r"\b(коротк\w*|кратко|short)\b", lower):
        return TELEGRAM_LENGTH_SHORT, "inferred"
    if re.search(r"\b(длинн\w*|подробн\w*|развёрнут\w*|развернут\w*|long)\b", lower):
        return TELEGRAM_LENGTH_LONG, "inferred"
    if re.search(r"\b(стандартн\w*|средн\w*|standard)\b", lower):
        return TELEGRAM_LENGTH_STANDARD, "inferred"
    m = re.search(r"(\d{3,4})\s*[-–—]\s*(\d{3,4})\s*(?:знак|символ|char)", lower)
    if m:
        mid = (int(m.group(1)) + int(m.group(2))) // 2
        if mid < 700:
            return TELEGRAM_LENGTH_SHORT, "inferred"
        if mid > 1200:
            return TELEGRAM_LENGTH_LONG, "inferred"
        return TELEGRAM_LENGTH_STANDARD, "inferred"
    return None


def _extract_topic_heuristic(blob: str) -> str | None:
    m = re.search(
        r"(?:пост|post).{0,60}?(?:о|about|про)\s+(.+?)(?:\.|$|\n)",
        blob,
        re.I | re.S,
    )
    if m:
        topic = _clean_value(m.group(1))
        # Stop at audience/tone/objective lines if they leaked into the capture.
        topic = re.split(
            r"(?=\n|(?:аудитори|тон|цель|в\s+конце)\b)",
            topic,
            maxsplit=1,
            flags=re.I,
        )[0].strip(" .")
        return topic or None
    return None


def merge_skill_inputs(
    *,
    text: str,
    clarification_answer: str | None,
    structured: dict[str, Any] | None,
    route_category: UserRequestRouteCategory,
) -> dict[str, str]:
    merged: dict[str, str] = {}
    sources: dict[str, str] = {}
    blob = "\n".join(p for p in [text or "", clarification_answer or ""] if p)

    for key, pattern in _FIELD_PATTERNS.items():
        match = pattern.search(blob)
        if match:
            merged[key] = _clean_value(match.group(1))
            sources[key] = "explicit"

    if structured:
        for key, value in structured.items():
            if key.startswith("_"):
                continue
            if value is not None and str(value).strip():
                merged[key] = str(value).strip()
                sources[key] = sources.get(key, "explicit")

    if route_category in {
        UserRequestRouteCategory.CONTENT,
        UserRequestRouteCategory.SOCIAL_MEDIA,
    }:
        if "platform" not in merged:
            merged["platform"] = "Telegram"
            sources["platform"] = "default"

        if "topic" not in merged:
            topic = _extract_topic_heuristic(blob)
            if topic:
                merged["topic"] = topic
                sources["topic"] = "inferred"

        # CTA: semantic inference before requiring a labeled field.
        if "CTA" not in merged:
            inferred = infer_cta_from_text(blob)
            if inferred:
                cta_type, cta_text = inferred
                merged["CTA"] = cta_text
                merged["cta_type"] = cta_type
                sources["CTA"] = "inferred"
                sources["cta_type"] = "inferred"
        else:
            merged.setdefault("cta_type", "custom")
            sources.setdefault("cta_type", "explicit")

        # Length: soft default — do not block.
        if "length" not in merged:
            inferred_len = infer_length_from_text(blob)
            if inferred_len:
                band, src = inferred_len
                merged["length"] = band
                sources["length"] = src
            else:
                merged["length"] = TELEGRAM_LENGTH_STANDARD
                sources["length"] = "default"
            merged["length_source"] = (
                "platform_default" if sources["length"] == "default" else sources["length"]
            )
        else:
            merged.setdefault("length_source", "explicit")

        if "tone" not in merged:
            merged["tone"] = "professional"
            sources["tone"] = "default"

        if "factuality_mode" not in merged:
            merged["factuality_mode"] = "cautious"
            sources["factuality_mode"] = "default"

    # Persist field sources for owner diagnostics only (underscore-prefixed).
    for key, src in sources.items():
        merged[f"_source_{key}"] = src
    return merged


def missing_telegram_inputs(inputs: dict[str, str]) -> list[str]:
    """Only hard-required fields block execution."""
    missing: list[str] = []
    for field in TELEGRAM_POST_HARD_REQUIRED:
        if not (inputs.get(field) or "").strip():
            missing.append(field)
    platform = (inputs.get("platform") or "Telegram").lower()
    if platform not in {"telegram", "tg"} and inputs.get("platform"):
        # Explicit wrong platform — ask once.
        missing.append("platform")
    return missing


def telegram_clarification_prompt(missing: list[str]) -> str:
    labels = {
        "topic": "тема",
        "audience": "аудитория",
        "objective": "цель поста",
        "platform": "площадка",
    }
    pretty = ", ".join(labels.get(m, m) for m in missing)
    if set(missing) <= {"topic", "audience"}:
        return "Уточните, пожалуйста: о чём пост и для какой аудитории?"
    return f"Чтобы подготовить пост, уточните: {pretty}."


def _natural_ready_message(inputs: dict[str, str]) -> str:
    audience = (inputs.get("audience") or "вашей аудитории").strip()
    tone = (inputs.get("tone") or "профессиональный").strip()
    if tone.lower() == "professional":
        tone = "профессиональный"
    objective = (inputs.get("objective") or "").strip()
    cta_type = (inputs.get("cta_type") or "").strip()
    parts = [f"Понял. Подготовлю {tone} пост для Telegram для {audience}."]
    if objective and cta_type == "discussion_question":
        parts.append(f"Цель — {objective}, поэтому в конце добавлю вопрос.")
    elif objective:
        parts.append(f"Цель — {objective}.")
        if cta_type == "discussion_question":
            parts.append("В конце добавлю вопрос для обсуждения.")
    elif cta_type == "discussion_question":
        parts.append("В конце добавлю вопрос для обсуждения.")
    elif inputs.get("CTA"):
        parts.append(f"В конце: {inputs['CTA']}.")
    return " ".join(parts)


def normalize_telegram_owner_request(text: str) -> dict[str, Any]:
    """Deterministic diagnostics for owner Telegram prompts (no LLM, no DB)."""
    inputs = merge_skill_inputs(
        text=text,
        clarification_answer=None,
        structured=None,
        route_category=UserRequestRouteCategory.CONTENT,
    )
    missing = missing_telegram_inputs(inputs)
    readiness = (
        UserRequestExecutionReadiness.READY_FOR_DRAFT
        if not missing
        else UserRequestExecutionReadiness.NEEDS_CLARIFICATION
    )
    return {
        "route": "content",
        "skill": SpecialistSkillCode.CONTENT_TELEGRAM_POST.value,
        "topic": inputs.get("topic"),
        "audience": inputs.get("audience"),
        "tone": inputs.get("tone"),
        "objective": inputs.get("objective"),
        "CTA": inputs.get("CTA"),
        "cta_type": inputs.get("cta_type"),
        "length": inputs.get("length"),
        "length_source": inputs.get("length_source"),
        "missing_inputs": missing,
        "execution_readiness": readiness.value,
        "assistant_message": (
            _natural_ready_message(inputs)
            if not missing
            else telegram_clarification_prompt(missing)
        ),
    }


async def attach_skill_context(
    session: AsyncSession,
    row: UserRequestTable,
    *,
    structured_inputs: dict[str, Any] | None = None,
    locale: str = "ru",
    ensure_pack: bool = True,
) -> SkillContextAttachment:
    """Resolve skill context for a routed/clarified UserRequest. No execution."""
    structured = structured_inputs or dict(row.skill_inputs or {})
    home_agency = bool(structured.get("home_agency_flow"))
    mapping = map_route_to_skill(row.route_category)
    if home_agency and row.route_category in {
        UserRequestRouteCategory.IDEA_VALIDATION,
        UserRequestRouteCategory.MARKET_RESEARCH,
    }:
        mapping = map_route_to_skill(UserRequestRouteCategory.MARKET_RESEARCH)

    if mapping.skill_code is None or (
        mapping.uses_existing_project_path and not home_agency
    ):
        return SkillContextAttachment(
            skill_code=None,
            skill_version=None,
            capability_pack_code=None,
            capability_pack_version=None,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.NOT_APPLICABLE,
            missing_inputs=[],
            quality_profile_code=None,
            skill_inputs={},
            approved_knowledge_count=0,
            status=row.status,
            clarification_question=row.clarification_question,
            assistant_message=None,
        )

    skill = get_skill(mapping.skill_code)
    pack = (
        get_capability_pack(mapping.specialist_role)
        if mapping.specialist_role
        else None
    )
    if skill is None or pack is None:
        return SkillContextAttachment(
            skill_code=None,
            skill_version=None,
            capability_pack_code=None,
            capability_pack_version=None,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.BLOCKED,
            missing_inputs=["skill_or_pack_missing"],
            quality_profile_code=None,
            skill_inputs={},
            approved_knowledge_count=0,
            status=UserRequestStatus.FAILED,
            clarification_question=None,
            assistant_message="Не удалось подобрать специалиста для этого запроса.",
        )

    inputs = merge_skill_inputs(
        text=row.text,
        clarification_answer=row.clarification_answer,
        structured=structured_inputs or dict(row.skill_inputs or {}),
        route_category=row.route_category,
    )

    if mapping.skill_code == SpecialistSkillCode.DESIGN_IMAGE_GENERATION:
        return _attach_image_generation(
            row=row,
            skill=skill,
            pack=pack,
            inputs=inputs,
        )

    if mapping.skill_code != SpecialistSkillCode.CONTENT_TELEGRAM_POST:
        return SkillContextAttachment(
            skill_code=skill.code.value,
            skill_version=skill.version,
            capability_pack_code=pack.specialist_role,
            capability_pack_version=pack.version,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.NEEDS_CLARIFICATION
            if row.route_kind == UserRequestRouteKind.CLARIFY
            else UserRequestExecutionReadiness.AWAITING_KNOWLEDGE,
            missing_inputs=[],
            quality_profile_code="content_quality_v1"
            if skill.code.value.startswith("content.")
            else None,
            skill_inputs=inputs,
            approved_knowledge_count=0,
            status=row.status
            if row.status != UserRequestStatus.SUBMITTED
            else UserRequestStatus.ROUTED,
            clarification_question=row.clarification_question,
            assistant_message=None,
        )

    # content.telegram_post — hard required only; soft fields already defaulted.
    missing = missing_telegram_inputs(inputs)
    if missing:
        prompt = telegram_clarification_prompt(missing)
        return SkillContextAttachment(
            skill_code=skill.code.value,
            skill_version=skill.version,
            capability_pack_code=pack.specialist_role,
            capability_pack_version=pack.version,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.NEEDS_CLARIFICATION,
            missing_inputs=missing,
            quality_profile_code="content_quality_v1",
            skill_inputs=inputs,
            approved_knowledge_count=0,
            status=UserRequestStatus.NEEDS_CLARIFICATION,
            clarification_question=prompt,
            assistant_message=prompt,
        )

    if ensure_pack:
        await ingest_approved_content_pack(session)

    domain = classify_content_domain(row.text)
    inputs["_domain"] = domain.model_dump(mode="json")
    domain_codes = domain_codes_for_retrieval(domain)
    settings = get_settings()
    requires_governed = bool(settings.knowledge_governance_runtime_enforced) and (
        domain.primary in _GOVERNED_REQUIRED_DOMAINS
        or any(c in _GOVERNED_REQUIRED_DOMAINS for c in (domain.secondary or []))
    )

    # Prefer governed published+fresh snapshot when available or required.
    eligible = await list_eligible_published_versions(
        session, tenant_owner_id=row.owner_id
    )
    if requires_governed or eligible:
        try:
            snapshot = await create_governed_snapshot(
                session,
                tenant_owner_id=row.owner_id,
                skill_code=skill.code.value,
                skill_version=skill.version,
                capability_pack_version=pack.version,
                locale=locale,
                require_knowledge=True if requires_governed else bool(eligible),
            )
        except InsufficientGovernedKnowledgeError:
            return SkillContextAttachment(
                skill_code=skill.code.value,
                skill_version=skill.version,
                capability_pack_code=pack.specialist_role,
                capability_pack_version=pack.version,
                knowledge_snapshot_id=None,
                knowledge_snapshot_hash=None,
                execution_readiness=UserRequestExecutionReadiness.BLOCKED,
                missing_inputs=["insufficient_governed_knowledge"],
                quality_profile_code="content_quality_v1",
                skill_inputs=inputs,
                approved_knowledge_count=0,
                status=UserRequestStatus.FAILED,
                clarification_question=None,
                assistant_message=(
                    "Выполнение заблокировано: нет опубликованных актуальных "
                    "управляемых знаний (insufficient_governed_knowledge). "
                    "Опубликуйте Knowledge Object через Knowledge Operator."
                ),
            )
        inputs["_governed_snapshot"] = True
        return SkillContextAttachment(
            skill_code=skill.code.value,
            skill_version=skill.version,
            capability_pack_code=pack.specialist_role,
            capability_pack_version=pack.version,
            knowledge_snapshot_id=snapshot.id,
            knowledge_snapshot_hash=snapshot.snapshot_hash,
            execution_readiness=UserRequestExecutionReadiness.READY_FOR_DRAFT,
            missing_inputs=[],
            quality_profile_code="content_quality_v1",
            skill_inputs=inputs,
            approved_knowledge_count=len(snapshot.item_refs or []),
            status=UserRequestStatus.READY_FOR_DRAFT,
            clarification_question=None,
            assistant_message=_natural_ready_message(inputs),
        )

    retrieval = await KnowledgeRetrievalAdapter(session).retrieve(
        KnowledgeRetrievalRequest(
            skill_code=skill.code.value,
            skill_version=skill.version,
            specialist_role=pack.specialist_role,
            owner_id=row.owner_id,
            project_id=row.project_id,
            locale=locale,
            requested_scopes=list(pack.knowledge_scopes),
            query_terms=["telegram", "content", *domain_codes],
            domain_codes=domain_codes,
            limit=40,
        ),
        include_content=False,
    )
    if not retrieval.items:
        return SkillContextAttachment(
            skill_code=skill.code.value,
            skill_version=skill.version,
            capability_pack_code=pack.specialist_role,
            capability_pack_version=pack.version,
            knowledge_snapshot_id=None,
            knowledge_snapshot_hash=None,
            execution_readiness=UserRequestExecutionReadiness.AWAITING_KNOWLEDGE,
            missing_inputs=[],
            quality_profile_code="content_quality_v1",
            skill_inputs=inputs,
            approved_knowledge_count=0,
            status=UserRequestStatus.ROUTED,
            clarification_question=None,
            assistant_message=(
                "Понял задачу, но пока нет утверждённых материалов для подготовки "
                "черновика. Добавьте знания в раздел «Знания» и повторите запрос."
            ),
        )

    snapshot = await KnowledgeSnapshotService(session).create_from_retrieval(
        owner_id=row.owner_id,
        project_id=row.project_id,
        skill_code=skill.code.value,
        skill_version=skill.version,
        capability_pack_version=pack.version,
        locale=locale,
        retrieval=retrieval,
    )
    return SkillContextAttachment(
        skill_code=skill.code.value,
        skill_version=skill.version,
        capability_pack_code=pack.specialist_role,
        capability_pack_version=pack.version,
        knowledge_snapshot_id=snapshot.id,
        knowledge_snapshot_hash=snapshot.snapshot_hash,
        execution_readiness=UserRequestExecutionReadiness.READY_FOR_DRAFT,
        missing_inputs=[],
        quality_profile_code="content_quality_v1",
        skill_inputs=inputs,
        approved_knowledge_count=len(retrieval.items),
        status=UserRequestStatus.READY_FOR_DRAFT,
        clarification_question=None,
        assistant_message=_natural_ready_message(inputs),
    )


def apply_attachment_to_row(
    row: UserRequestTable,
    attachment: SkillContextAttachment,
) -> None:
    row.skill_code = attachment.skill_code
    row.skill_version = attachment.skill_version
    row.capability_pack_code = attachment.capability_pack_code
    row.capability_pack_version = attachment.capability_pack_version
    row.knowledge_snapshot_id = attachment.knowledge_snapshot_id
    row.knowledge_snapshot_hash = attachment.knowledge_snapshot_hash
    row.execution_readiness = attachment.execution_readiness
    row.missing_inputs = list(attachment.missing_inputs)
    row.quality_profile_code = attachment.quality_profile_code
    preserved = {
        key: value
        for key, value in dict(row.skill_inputs or {}).items()
        if key.startswith("_route") or key.startswith("_llm") or key == "_routing_decision_id"
    }
    inputs = {**preserved, **dict(attachment.skill_inputs)}
    inputs["_approved_knowledge_count"] = attachment.approved_knowledge_count
    row.skill_inputs = inputs
    if attachment.status is not None:
        row.status = attachment.status
    if attachment.clarification_question is not None:
        row.clarification_question = attachment.clarification_question
    if attachment.assistant_message:
        row.assistant_message = attachment.assistant_message[:4000]
    if attachment.execution_readiness == UserRequestExecutionReadiness.READY_FOR_DRAFT:
        row.next_action_label = "Проверить черновик"
        row.route_kind = UserRequestRouteKind.SPECIALIST_TASK
    elif attachment.execution_readiness == UserRequestExecutionReadiness.NEEDS_CLARIFICATION:
        row.route_kind = UserRequestRouteKind.CLARIFY
        row.next_action_label = "Уточнить детали"
