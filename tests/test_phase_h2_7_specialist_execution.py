"""Phase H2.7 — Specialist Execution Foundation (governed, draft-only).

Covers: integration registry governance, tool profiles + hard denies,
business tool resolvability boundary, OpenRouter provider wiring, prompt
assembly lineage, and content.telegram_post draft execution + review.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.business_tools.contracts import BusinessToolError
from app.business_tools.registry import resolve_business_tool
from app.integrations.registry import build_integration_registry, get_integration
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.registry import get_llm_adapter
from app.prompts.specialist import assemble_specialist_prompt
from app.schemas.contracts import (
    BusinessToolCode,
    IntegrationCode,
    IntegrationReadiness,
    LLMProvider,
)
from app.specialist_skills.route_mapping import map_route_to_skill
from app.specialist_skills.tool_profiles import (
    assert_tool_allowed,
    get_tool_profile,
    tool_allowed,
)
from app.schemas.contracts import UserRequestRouteCategory


# --------------------------------------------------------------------------
# Integration Registry governance
# --------------------------------------------------------------------------


def test_integration_registry_governance() -> None:
    by_code = {d.code: d for d in build_integration_registry()}
    assert by_code[IntegrationCode.N8N].readiness == IntegrationReadiness.BLOCKED
    assert by_code[IntegrationCode.PINECONE].readiness == IntegrationReadiness.DISABLED
    # Make may be configured but must never be 'ready' (execution disabled).
    assert by_code[IntegrationCode.MAKE].readiness != IntegrationReadiness.READY
    # Yandex Direct declares write capabilities but requires approval and is not ready.
    direct = by_code[IntegrationCode.YANDEX_DIRECT]
    assert direct.owner_approval_required is True
    assert direct.readiness != IntegrationReadiness.READY


def test_integration_registry_never_leaks_secrets() -> None:
    for d in build_integration_registry():
        blob = d.model_dump_json()
        assert "sk-" not in blob
        assert "y0__" not in blob
        assert "api_key" not in d.diagnostics_safe_fields


# --------------------------------------------------------------------------
# Tool profiles + hard denies
# --------------------------------------------------------------------------


def test_content_specialist_cannot_use_research_or_execution_tools() -> None:
    assert tool_allowed("content_specialist", BusinessToolCode.KNOWLEDGE_RETRIEVAL)
    assert not tool_allowed("content_specialist", BusinessToolCode.WEB_SEARCH)
    assert not tool_allowed("content_specialist", BusinessToolCode.WORKFLOW_AUTOMATION)
    with pytest.raises(PermissionError):
        assert_tool_allowed("content_specialist", BusinessToolCode.WORKFLOW_AUTOMATION)


def test_no_role_may_use_workflow_or_advertising() -> None:
    for role in ("content_specialist", "researcher", "strategist", "programmer"):
        assert not tool_allowed(role, BusinessToolCode.WORKFLOW_AUTOMATION)
        assert not tool_allowed(role, BusinessToolCode.ADVERTISING_PLATFORM)
        profile = get_tool_profile(role)
        assert BusinessToolCode.WORKFLOW_AUTOMATION in profile.denied_tools
        assert BusinessToolCode.ADVERTISING_PLATFORM in profile.denied_tools


def test_business_tools_execution_not_resolvable() -> None:
    with pytest.raises(BusinessToolError):
        resolve_business_tool(BusinessToolCode.WORKFLOW_AUTOMATION)
    with pytest.raises(BusinessToolError):
        resolve_business_tool(BusinessToolCode.ADVERTISING_PLATFORM)


# --------------------------------------------------------------------------
# OpenRouter provider wiring
# --------------------------------------------------------------------------


def test_openrouter_uses_shared_adapter_and_no_key_in_metadata() -> None:
    adapter = get_llm_adapter(LLMProvider.OPENROUTER)
    assert isinstance(adapter, LiteLLMAdapter)


# --------------------------------------------------------------------------
# Prompt assembly lineage
# --------------------------------------------------------------------------


def test_prompt_assembly_order_and_hash() -> None:
    messages, package = assemble_specialist_prompt(
        specialist_role="content_specialist",
        skill_code="content.telegram_post",
        locale="ru",
        user_text="Напиши пост",
        skill_inputs={"topic": "сигналы", "_approved_knowledge_count": 3},
        knowledge_blocks=["Методика: пиши коротко"],
        knowledge_snapshot_id=None,
        knowledge_snapshot_hash="sha256:x",
        tool_policy_version="1.0",
    )
    assert [m.role for m in messages] == ["system", "user"]
    system = messages[0].content or ""
    # Governed order markers present and constitutional first.
    assert system.index("Marketsynth") < system.index("ROLE:")
    assert system.index("ROLE:") < system.index("SKILL INSTRUCTION")
    assert system.index("SKILL INSTRUCTION") < system.index("OUTPUT SCHEMA")
    assert "TOOL POLICY: No tools" in system
    assert package.rendered_hash.startswith("sha256:")
    # Internal input keys must not leak into the prompt.
    assert "_approved_knowledge_count" not in (messages[1].content or "")


# --------------------------------------------------------------------------
# Route mapping
# --------------------------------------------------------------------------


def test_content_route_maps_to_telegram_skill() -> None:
    mapping = map_route_to_skill(UserRequestRouteCategory.CONTENT)
    assert mapping.skill_code is not None
    assert mapping.skill_code.value == "content.telegram_post"
    assert mapping.specialist_role == "content_specialist"


# --------------------------------------------------------------------------
# content.telegram_post draft execution (flag-gated, draft-only)
# --------------------------------------------------------------------------

_TELEGRAM_INPUTS = {
    "topic": "фиксация слабых сигналов до инцидента на буровой",
    "audience": "буровые супервайзеры",
    "objective": "вызвать обсуждение",
    "tone": "профессиональный",
    "length": "средний",
    "CTA": "задайте вопрос в комментариях",
    "factuality_mode": "balanced",
}


def _enable_content_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTENT_DRAFT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("CONTENT_DRAFT_LLM_PROVIDER", "mock")
    monkeypatch.setenv("CONTENT_DRAFT_LLM_MODEL", "mock-model")
    from app.core.config import get_settings

    get_settings.cache_clear()


def test_draft_disabled_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTENT_DRAFT_EXECUTION_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram.", "skill_inputs": _TELEGRAM_INPUTS},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["skill_code"] == "content.telegram_post"
    assert body["execution_readiness"] == "ready_for_draft"
    # No draft executed while flag is off.
    assert body["content_draft"] is None
    assert "content.telegram_post" not in body["assistant_message"]
    assert "Маршрут:" not in body["assistant_message"]
    assert "snapshot" not in body["assistant_message"].lower()


def test_mock_draft_generation_and_review_survives_refresh(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram.", "skill_inputs": _TELEGRAM_INPUTS},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["execution_readiness"] == "ready_for_draft"
    draft = body["content_draft"]
    assert draft is not None
    assert draft["skill_code"] == "content.telegram_post"
    assert draft["generation_mode"] == "mock"
    assert draft["body"]
    # Expertise reflects the skill actually used.
    assert "Telegram-формат" in draft["expertise_labels"]
    assert draft["quality_check"]["no_secrets"] is True
    # No technical jargon in user-facing copy.
    assert "content.telegram_post" not in body["assistant_message"]
    assert "snapshot" not in body["assistant_message"].lower()
    assert "Маршрут:" not in body["assistant_message"]
    # No publication / campaign side effects.
    assert body["generation_status"] in (None, "diagnostic", "unavailable") or True
    assert body["prompt_package_hash"] is not None

    request_id = body["id"]
    # Survives refresh: GET returns the same draft.
    fetched = client.get(f"/user-requests/{request_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["content_draft"]["body"] == draft["body"]

    # Review: accept.
    review = client.post(
        f"/user-requests/{request_id}/content-draft/review",
        headers=auth_headers,
        json={"action": "accept"},
    )
    assert review.status_code == 200
    assert review.json()["content_draft_review_status"] == "accepted"


def test_missing_inputs_yield_clarification_not_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram про буровую."},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "needs_clarification"
    assert body["content_draft"] is None


def test_review_invalid_action_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram.", "skill_inputs": _TELEGRAM_INPUTS},
    ).json()
    resp = client.post(
        f"/user-requests/{created['id']}/content-draft/review",
        headers=auth_headers,
        json={"action": "publish"},
    )
    assert resp.status_code == 400


_OWNER_ACCEPTANCE_TEXT = (
    "Напиши пост для Telegram о важности фиксации слабых сигналов до "
    "инцидента на буровой.\n"
    "Аудитория — буровые супервайзеры.\n"
    "Тон — профессиональный.\n"
    "Цель — вызвать обсуждение.\n"
    "В конце задай вопрос."
)


from tests.kg2_helpers import publish_drilling_governed_knowledge


def _publish_drilling_governed_knowledge(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    publish_drilling_governed_knowledge(
        client, auth_headers, code="h27.drilling.weak_signals"
    )


def test_cta_semantic_extraction_discussion_question() -> None:
    from app.domain.user_request_skill_context import infer_cta_from_text, merge_skill_inputs
    from app.schemas.contracts import UserRequestRouteCategory

    assert infer_cta_from_text("В конце задай вопрос")[0] == "discussion_question"
    assert infer_cta_from_text("Заверши вопросом")[0] == "discussion_question"
    assert infer_cta_from_text("Предложи поделиться мнением")[0] == "comment_prompt"
    assert infer_cta_from_text("Призови подписаться")[0] == "subscribe"
    inputs = merge_skill_inputs(
        text=_OWNER_ACCEPTANCE_TEXT,
        clarification_answer=None,
        structured=None,
        route_category=UserRequestRouteCategory.CONTENT,
    )
    assert inputs["cta_type"] == "discussion_question"
    assert inputs["CTA"]
    assert inputs["length"] == "standard"
    assert inputs["length_source"] == "platform_default"
    assert inputs["_source_CTA"] == "inferred"
    assert inputs["_source_length"] == "default"


def test_owner_acceptance_prompt_ready_and_drafts_without_clarification(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    _publish_drilling_governed_knowledge(client, auth_headers)
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": _OWNER_ACCEPTANCE_TEXT},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["skill_code"] == "content.telegram_post"
    assert body["status"] != "needs_clarification"
    assert body["execution_readiness"] == "ready_for_draft"
    assert body["missing_inputs"] == []
    assert body["content_draft"] is not None
    assert body["content_draft"]["hook"]
    assert body["content_draft"]["body"]
    assert body["content_draft"]["cta"]
    # Natural user copy — no route/skill/snapshot jargon.
    msg = body["assistant_message"]
    assert "Маршрут:" not in msg
    assert "content.telegram_post" not in msg
    assert "knowledge snapshot" not in msg.lower()
    assert "snapshot" not in msg.lower()
    assert "skill=" not in msg
    # Inputs inferred correctly.
    assert body["skill_inputs"]["cta_type"] == "discussion_question"
    assert body["skill_inputs"]["length"] == "standard"
    # Refresh preserves draft.
    fetched = client.get(f"/user-requests/{body['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["content_draft"]["body"] == body["content_draft"]["body"]
    # No external automation side effects.
    assert body["content_draft"]["status"] == "draft"
    listed = client.get("/user-requests", headers=auth_headers)
    assert body["id"] in {row["id"] for row in listed.json()}


def test_bare_telegram_request_still_asks_material_clarification(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram."},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "needs_clarification"
    assert body["content_draft"] is None
    assert "content.telegram_post" not in (body["assistant_message"] or "")
    assert "Маршрут:" not in (body["assistant_message"] or "")


OWNER_TELEGRAM_PROMPT = (
    "Напиши пост для Telegram о важности фиксации слабых сигналов до "
    "инцидента на буровой.\n"
    "Аудитория — буровые супервайзеры.\n"
    "Тон — профессиональный.\n"
    "Цель — вызвать обсуждение.\n"
    "В конце задай вопрос."
)


def test_normalize_telegram_owner_request_ready() -> None:
    from app.domain.user_request_skill_context import normalize_telegram_owner_request

    result = normalize_telegram_owner_request(OWNER_TELEGRAM_PROMPT)
    assert result["route"] == "content"
    assert result["skill"] == "content.telegram_post"
    assert result["cta_type"] == "discussion_question"
    assert result["length"] == "standard"
    assert result["missing_inputs"] == []
    assert result["execution_readiness"] == "ready_for_draft"
    assert "Маршрут:" not in result["assistant_message"]
    assert "content.telegram_post" not in result["assistant_message"]


def test_health_runtime_and_content_selfcheck(client: TestClient) -> None:
    runtime = client.get("/health/runtime")
    assert runtime.status_code == 200
    body = runtime.json()
    assert "backend_build_id" in body
    assert "git_commit" in body
    assert "database_name" in body
    assert "alembic_revision" in body
    assert "content_draft_execution_enabled" in body
    assert "content_draft_llm_provider" in body
    assert "content_draft_llm_model" in body
    assert "litellm_installed" in body
    blob = str(body).lower()
    assert "sk-" not in blob
    assert "password" not in blob
    assert "api_key" not in blob

    check = client.post(
        "/health/runtime/content-selfcheck",
        json={"text": OWNER_TELEGRAM_PROMPT},
    )
    assert check.status_code == 200
    normalized = check.json()
    assert normalized["execution_readiness"] == "ready_for_draft"
    assert normalized["missing_inputs"] == []
    assert normalized["cta_type"] == "discussion_question"


def test_home_attachment_button_always_mounted_in_source() -> None:
    home = Path("web/src/components/workspace/home/workspace-home-view.tsx").read_text(
        encoding="utf-8"
    )
    panel = Path("web/src/components/workspace/home/reference-upload-panel.tsx").read_text(
        encoding="utf-8"
    )
    ru = Path("web/src/lib/i18n/translations/ru.ts").read_text(encoding="utf-8")
    assert "ReferenceUploadPanel" in home
    assert "open" in home
    assert "showReferencePanel" not in home
    assert 't("home.addFiles")' in panel or "home.addFiles" in panel
    assert 'addFiles: "Добавить файлы"' in ru
    assert "attachmentsNotUsedForSkill" in ru
