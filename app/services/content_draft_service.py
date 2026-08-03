"""content.telegram_post draft execution (Phase H2.7 slice 1).

Draft-only. One LLM call through the existing adapter. Mandatory knowledge
snapshot. No tools, no publication, no campaign, no external workflow.
Mock provider yields a labeled diagnostic draft, never a real result.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ExecutorError
from app.db.base import utc_now
from app.db.models.knowledge_item import KnowledgeItemTable, KnowledgeSnapshotTable
from app.db.models.knowledge_governance import KnowledgeVersionTable
from app.db.models.user_request import UserRequestTable
from app.knowledge_governance.citation_gate import (
    CitationGateError,
    enforce_and_persist_citations,
)
from app.llm.contracts import LLMGenerateInput
from app.llm.registry import get_llm_adapter
from app.prompts.specialist.assembler import assemble_specialist_prompt
from app.schemas.contracts import (
    ContentDomainClassification,
    ContentDraftQualityCheck,
    ContentDraftResult,
    ContentDraftReviewStatus,
    ContentFactualityMode,
    ContentQualityGateDecision,
    LLMProvider,
    SpecialistSkillCode,
    UserRequestExecutionReadiness,
    UserRequestStatus,
)
from app.services.content_claim_verification import (
    apply_claim_actions,
    verify_content_claims,
)
from app.services.content_editorial_review import (
    build_revision_brief,
    run_editorial_review,
)
from app.services.content_quality_gate import run_strict_quality_gate
from app.specialist_skills.tool_profiles import get_tool_profile

log = logging.getLogger(__name__)

_ROLE = "content_specialist"
_SKILL = SpecialistSkillCode.CONTENT_TELEGRAM_POST.value
_MOCK_WARNING = "mock_diagnostic_draft_not_real"

MSG_DISABLED = (
    "Понял задачу и подготовил контекст, но генерация черновиков текста сейчас "
    "отключена. Запрос сохранён — включите генерацию и повторите."
)
MSG_MOCK = (
    "Подготовил тестовый черновик (служебный контур). Это не финальный "
    "продакшен-текст — проверьте настройки модели для реальной генерации."
)
MSG_SUCCESS = (
    "Готово. Черновик поста подготовлен и ждёт вашей проверки. "
    "Публикация не выполняется."
)
MSG_FAILED = "Не удалось создать черновик. Запрос сохранён — можно повторить."
MSG_NEEDS_WORK = (
    "Черновик сохранён, но не прошёл редакторскую проверку. "
    "Требуется доработка перед использованием."
)


class ContentDraftUnavailableError(RuntimeError):
    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.user_message = message


class ContentDraftService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    def readiness(self) -> dict:
        enabled = bool(self._settings.content_draft_execution_enabled)
        provider = (self._settings.content_draft_llm_provider or "mock").strip().lower()
        return {
            "content_draft_execution_enabled": enabled,
            "configured_provider": provider,
            "is_mock": provider == "mock",
        }

    async def _load_snapshot_knowledge(
        self,
        row: UserRequestTable,
    ) -> tuple[list[str], list[str], KnowledgeSnapshotTable]:
        """Return (knowledge_blocks, knowledge_refs, snapshot) for the attached snapshot."""
        if row.knowledge_snapshot_id is None:
            raise ContentDraftUnavailableError(
                "no_snapshot", "Knowledge snapshot is required before draft."
            )
        snap = await self._session.get(KnowledgeSnapshotTable, row.knowledge_snapshot_id)
        if snap is None or snap.owner_id != row.owner_id:
            raise ContentDraftUnavailableError(
                "no_snapshot", "Knowledge snapshot is required before draft."
            )
        refs = list(snap.item_refs or [])
        meta = snap.governance_meta or {}
        version_ids = list(meta.get("knowledge_version_ids") or [])

        # Governed path: load immutable kg_versions by id
        if version_ids:
            from uuid import UUID as _UUID

            ids = []
            for vid in version_ids:
                try:
                    ids.append(_UUID(str(vid)))
                except Exception:  # noqa: BLE001
                    continue
            blocks: list[str] = []
            knowledge_refs: list[str] = []
            if ids:
                stmt = select(KnowledgeVersionTable).where(
                    KnowledgeVersionTable.id.in_(ids),
                    KnowledgeVersionTable.tenant_owner_id == row.owner_id,
                )
                result = await self._session.execute(stmt)
                by_id = {r.id: r for r in result.scalars().all()}
                for vid in ids:
                    ver = by_id.get(vid)
                    if ver is None:
                        continue
                    blocks.append(f"kg:{ver.version}: {ver.content[:4000]}")
                    knowledge_refs.append(f"kg:{ver.id}@{ver.version}")
            if not blocks:
                raise ContentDraftUnavailableError(
                    "insufficient_governed_knowledge",
                    "Governed snapshot has no loadable published versions.",
                )
            return blocks, knowledge_refs, snap

        ids = []
        for ref in refs:
            try:
                from uuid import UUID as _UUID

                ids.append(_UUID(str(ref["knowledge_item_id"])))
            except Exception:  # noqa: BLE001
                continue
        blocks = []
        knowledge_refs = []
        if ids:
            stmt = select(KnowledgeItemTable).where(KnowledgeItemTable.id.in_(ids))
            result = await self._session.execute(stmt)
            by_id = {r.id: r for r in result.scalars().all()}
            for ref in refs:
                try:
                    from uuid import UUID as _UUID

                    item = by_id.get(_UUID(str(ref["knowledge_item_id"])))
                except Exception:  # noqa: BLE001
                    item = None
                if item is None:
                    continue
                blocks.append(f"{item.title}: {item.content}")
                knowledge_refs.append(f"{item.code}@{item.version}")
        return blocks, knowledge_refs, snap

    def _resolve_provider(self) -> tuple[LLMProvider, str]:
        raw = (self._settings.content_draft_llm_provider or "mock").strip().lower()
        model = (self._settings.content_draft_llm_model or "mock-model").strip()
        try:
            provider = LLMProvider(raw)
        except ValueError as exc:
            raise ExecutorError(f"Unsupported content draft provider: {raw}") from exc
        # Skills never choose arbitrary provider/model; only configured allowlist.
        if provider not in {LLMProvider.MOCK, LLMProvider.OPENAI, LLMProvider.OPENROUTER}:
            raise ExecutorError(f"Provider not allowed for content draft: {raw}")
        return provider, model

    async def execute_for_user_request(
        self,
        row: UserRequestTable,
    ) -> ContentDraftResult:
        if not self._settings.content_draft_execution_enabled:
            raise ContentDraftUnavailableError("disabled", MSG_DISABLED)

        blocks, knowledge_refs, snap = await self._load_snapshot_knowledge(row)
        inputs = dict(row.skill_inputs or {})
        locale = "ru"
        tool_profile = get_tool_profile(_ROLE)
        tool_policy_version = tool_profile.version if tool_profile else "1.0"
        domain = _load_domain_classification(inputs)
        factuality = _resolve_factuality_mode(inputs)
        audience = str(inputs.get("audience") or "").strip()

        provider, model = self._resolve_provider()
        revision_brief: str | None = None
        result: ContentDraftResult | None = None
        package = None

        for attempt in range(2):
            messages, package = assemble_specialist_prompt(
                specialist_role=_ROLE,
                skill_code=_SKILL,
                locale=locale,
                user_text=_compose_user_text(row.text, revision_brief),
                skill_inputs=inputs,
                knowledge_blocks=blocks,
                knowledge_snapshot_id=row.knowledge_snapshot_id,
                knowledge_snapshot_hash=row.knowledge_snapshot_hash,
                tool_policy_version=tool_policy_version,
            )

            if provider == LLMProvider.MOCK:
                result = _build_mock_draft(inputs=inputs, knowledge_refs=knowledge_refs)
            else:
                adapter = get_llm_adapter(provider)
                try:
                    output = await adapter.generate(
                        LLMGenerateInput(
                            provider=provider,
                            model=model,
                            messages=messages,
                            temperature=0.65 if attempt else 0.7,
                            max_tokens=1400,
                            metadata={
                                "skill_code": _SKILL,
                                "prompt_hash": package.rendered_hash,
                                "revision": attempt,
                            },
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "content_draft_llm_failed",
                        extra={"error": type(exc).__name__},
                    )
                    raise ContentDraftUnavailableError("provider_error", MSG_FAILED) from exc
                result = _parse_draft(output.content, knowledge_refs=knowledge_refs)

            result.revision_count = attempt
            result.domain = domain
            result.factuality_mode = factuality
            _enrich_expertise_and_materials(result, domain=domain, knowledge_refs=knowledge_refs)

            claims, foundation, claim_warnings = verify_content_claims(
                result,
                factuality_mode=factuality,
                knowledge_refs=knowledge_refs,
                user_material_refs=_user_material_refs(inputs),
            )
            apply_claim_actions(result, claims)
            result.claims = claims
            result.text_foundation = foundation
            result.warnings = list(dict.fromkeys([*result.warnings, *claim_warnings]))

            editorial_issues, editorial_scores = run_editorial_review(
                result,
                domain=domain,
                audience=audience,
            )
            result.editorial_notes = editorial_issues
            result.quality_check = run_strict_quality_gate(
                result,
                editorial_issues=editorial_issues,
                editorial_scores=editorial_scores,
                claims=claims,
                locale=locale,
            )

            gate = result.quality_check.gate_decision
            if gate == ContentQualityGateDecision.PASS:
                break
            if attempt == 0 and gate == ContentQualityGateDecision.REVISE:
                revision_brief = build_revision_brief(editorial_issues, result.editorial_notes)
                continue
            break

        assert result is not None and package is not None

        # KG.2 citation enforcement when snapshot is governed
        if snap.governance_meta:
            citation_claims = _citation_claims_from_draft(result, snap)
            try:
                await enforce_and_persist_citations(
                    self._session,
                    tenant_owner_id=row.owner_id,
                    user_request_id=row.id,
                    snapshot_id=snap.id,
                    skill_code=_SKILL,
                    claims=citation_claims,
                    citation_required=True,
                )
            except CitationGateError as exc:
                raise ContentDraftUnavailableError(exc.code, exc.message) from exc

        _apply_result_to_row(row, result=result, package=package, provider=provider, model=model)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return result


def _citation_claims_from_draft(
    result: ContentDraftResult, snap: KnowledgeSnapshotTable
) -> list[dict]:
    meta = snap.governance_meta or {}
    version_ids = list(meta.get("knowledge_version_ids") or [])
    source_ids = list(meta.get("source_ids") or [])
    primary_version = version_ids[0] if version_ids else None
    primary_source = source_ids[0] if source_ids else (primary_version or "")
    claims: list[dict] = []
    texts = [c for c in (result.factual_claims or []) if str(c).strip()]
    if not texts and result.body.strip():
        # mock / soft path: bind body as single cited claim to governed source
        texts = [result.body.strip()[:500]]
    for i, text in enumerate(texts):
        claims.append(
            {
                "claim_id": f"claim-{i + 1}",
                "claim_text": text,
                "knowledge_version_id": primary_version,
                "source_id": primary_source,
                "confidence": "medium",
            }
        )
    return claims


def _compose_user_text(base: str, revision_brief: str | None) -> str:
    if not revision_brief:
        return base
    return f"{base}\n\n---\n{revision_brief}"


def _load_domain_classification(inputs: dict) -> ContentDomainClassification | None:
    raw = inputs.get("_domain")
    if isinstance(raw, dict):
        try:
            return ContentDomainClassification.model_validate(raw)
        except Exception:  # noqa: BLE001
            return None
    return None


def _resolve_factuality_mode(inputs: dict) -> ContentFactualityMode:
    raw = str(inputs.get("factuality_mode") or inputs.get("_factuality_mode") or "").strip()
    if raw:
        try:
            return ContentFactualityMode(raw)
        except ValueError:
            pass
    return ContentFactualityMode.GENERAL_EXPERT


def _user_material_refs(inputs: dict) -> list[str]:
    mats = inputs.get("_user_materials")
    if isinstance(mats, list):
        return [str(m) for m in mats if str(m).strip()]
    return []


def _enrich_expertise_and_materials(
    result: ContentDraftResult,
    *,
    domain: ContentDomainClassification | None,
    knowledge_refs: list[str],
) -> None:
    labels: list[str] = ["Контент-специалист"]
    if domain and domain.labels:
        labels.extend(domain.labels[:2])
    labels.extend(
        [
            "Telegram-формат",
            "Проверка утверждений",
            "Профессиональная редактура",
        ]
    )
    result.expertise_labels = list(dict.fromkeys(labels))

    domain_items = [r for r in knowledge_refs if "ms.domain.drilling" in r]
    methodology_count = max(0, len(knowledge_refs) - len(domain_items))
    materials = [
        f"Отраслевые материалы: {len(domain_items)}",
        f"Методология и стандарты: {methodology_count}",
    ]
    if result.generation_mode == "mock":
        materials.append("Тестовый контур генерации")
    result.materials_used = materials
    result.knowledge_refs = knowledge_refs
    if result.text_foundation is None:
        from app.schemas.contracts import ContentTextFoundation

        result.text_foundation = ContentTextFoundation(domain_items=domain_items)
    else:
        result.text_foundation.domain_items = domain_items


def _strip_json_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    # Extract the first {...} block if extra prose slipped in.
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        return match.group(0)
    return cleaned


def _parse_draft(content: str, *, knowledge_refs: list[str]) -> ContentDraftResult:
    raw = _strip_json_fences(content)
    try:
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise ContentDraftUnavailableError("invalid_output", MSG_FAILED) from exc
    if not isinstance(data, dict):
        raise ContentDraftUnavailableError("invalid_output", MSG_FAILED)

    def _str(key: str) -> str:
        val = data.get(key)
        return str(val).strip() if val is not None else ""

    def _list(key: str) -> list[str]:
        val = data.get(key)
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        return []

    return ContentDraftResult(
        skill_code=_SKILL,
        hook=_str("hook"),
        body=_str("body"),
        cta=_str("cta"),
        variants=_list("variants"),
        assumptions=_list("assumptions"),
        factual_claims=_list("factual_claims"),
        warnings=_list("warnings"),
        knowledge_refs=list(knowledge_refs),
        generation_mode="real",
        review_status=ContentDraftReviewStatus.PENDING,
        status="draft",
    )


def _build_mock_draft(*, inputs: dict, knowledge_refs: list[str]) -> ContentDraftResult:
    topic = str(inputs.get("topic") or "заданная тема").strip()
    audience = str(inputs.get("audience") or "целевая аудитория").strip()
    objective = str(inputs.get("objective") or "вовлечение").strip()
    cta_hint = str(inputs.get("CTA") or inputs.get("cta") or "").strip()
    hook = f"[MOCK] {topic}: почему это важно уже сегодня"
    body = (
        f"[Служебный черновик] Пост для аудитории «{audience}». "
        f"Основная мысль раскрывает тему «{topic}» с учётом цели «{objective}». "
        "Это тестовый контур: реальная модель не вызывалась."
    )
    cta = cta_hint or "Поделитесь мнением в комментариях."
    return ContentDraftResult(
        skill_code=_SKILL,
        hook=hook,
        body=body,
        cta=cta,
        variants=[f"[MOCK] {topic}: короткий разбор"],
        assumptions=["mock_run: содержание сгенерировано без реальной модели"],
        factual_claims=[],
        warnings=[_MOCK_WARNING],
        knowledge_refs=list(knowledge_refs),
        generation_mode="mock",
        review_status=ContentDraftReviewStatus.PENDING,
        status="draft",
    )


def run_quality_gate(result: ContentDraftResult, *, locale: str) -> ContentDraftQualityCheck:
    """Deterministic quality gate. No infinite loops, at most advisory."""
    issues: list[str] = []
    schema_valid = bool(result.skill_code)
    required_present = bool(result.hook.strip() and result.body.strip() and result.cta.strip())
    if not required_present:
        issues.append("missing_required_fields")
    # No raw enum leakage / obvious secret patterns.
    blob = " ".join([result.hook, result.body, result.cta] + result.variants)
    no_secrets = not re.search(r"(sk-[A-Za-z0-9]{10,}|api[_-]?key|y0__[A-Za-z0-9])", blob, re.I)
    if not no_secrets:
        issues.append("possible_secret_leak")
    # Unsupported numeric claim heuristic: numbers in body not declared in factual_claims.
    numbers = re.findall(r"\b\d[\d\s.,%]{1,}\b", result.body)
    no_unsupported = True
    if numbers and not result.factual_claims:
        no_unsupported = False
        issues.append("undeclared_numeric_claims")
    locale_ok = True  # single-locale slice; enforced via prompt.
    length_ok = len(result.body) >= 40
    if not length_ok:
        issues.append("body_too_short")

    checks = {
        "schema_valid": schema_valid,
        "required_fields_present": required_present,
        "locale_ok": locale_ok,
        "no_unsupported_claims": no_unsupported,
        "no_secrets": no_secrets,
        "length_ok": length_ok,
    }
    passed = all(checks.values())
    score = round(sum(1 for v in checks.values() if v) / len(checks), 3)
    return ContentDraftQualityCheck(
        passed=passed,
        schema_valid=schema_valid,
        required_fields_present=required_present,
        locale_ok=locale_ok,
        no_unsupported_claims=no_unsupported,
        no_secrets=no_secrets,
        checks=checks,
        issues=issues,
        score=score,
    )


def _apply_result_to_row(
    row: UserRequestTable,
    *,
    result: ContentDraftResult,
    package,
    provider: LLMProvider,
    model: str,
) -> None:
    payload = result.model_dump(mode="json")
    lineage = package.model_dump(mode="json")
    row.content_draft = payload
    row.content_draft_review_status = result.review_status.value
    row.prompt_package_hash = package.rendered_hash
    row.prompt_package_version = package.version
    row.execution_provider = provider.value
    row.execution_model = model if provider != LLMProvider.MOCK else "mock-model"
    row.content_draft_lineage = lineage

    gate = result.quality_check.gate_decision
    inputs = dict(row.skill_inputs or {})
    audience = str(inputs.get("audience") or "").strip()
    ack = f"Подготовил пост для аудитории «{audience}». " if audience else ""

    if result.generation_mode == "mock":
        row.status = UserRequestStatus.COMPLETED
        row.execution_readiness = UserRequestExecutionReadiness.READY_FOR_DRAFT
        row.assistant_message = MSG_MOCK[:4000]
        row.next_action_label = "Проверить черновик (тест)"
        result.status = "draft"
    elif gate == ContentQualityGateDecision.PASS:
        row.status = UserRequestStatus.COMPLETED
        row.execution_readiness = UserRequestExecutionReadiness.READY_FOR_DRAFT
        row.assistant_message = (ack + MSG_SUCCESS)[:4000]
        row.next_action_label = "Проверить черновик"
        result.status = "draft"
    else:
        row.status = UserRequestStatus.COMPLETED
        row.execution_readiness = UserRequestExecutionReadiness.READY_FOR_DRAFT
        row.assistant_message = (ack + MSG_NEEDS_WORK)[:4000]
        row.next_action_label = "Доработать черновик"
        result.status = "blocked"

    row.next_href = "/workspace/tasks"
    row.updated_at = utc_now()


def apply_draft_unavailable(row: UserRequestTable, *, message: str, category: str) -> None:
    row.content_draft_review_status = None
    row.assistant_message = message[:4000]
    row.next_action_label = "Повторить позже"
    row.generation_warnings = [category]
    row.updated_at = utc_now()
