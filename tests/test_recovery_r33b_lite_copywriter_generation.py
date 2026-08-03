"""Recovery R3.3B-LITE — copywriter pipeline → ContentAsset generation."""

from __future__ import annotations

from typing import Any
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.content_factory.provider_gate import assess_content_factory_provider_readiness
from app.core.exceptions import InvalidStateError
from app.core.config import get_settings
from app.db.repositories.content_assets import ContentAssetRepository
from app.marketing.copywriter_asset_conversion import (
    build_content_asset_fields_from_copywriter_item,
    extract_content_items,
)
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistPriorOutput,
    MarketingSpecialistType,
)
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "R3.3B Content Factory"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _brief_payload(**overrides: Any) -> dict[str, Any]:
    base = {
        "topic": "Стоматология для семей",
        "goal": "Привлечь первичные записи",
        "audience": "Родители 30–45 в городе",
        "channel": "telegram",
        "period": "Май 2026",
        "frequency": "3 поста в неделю",
        "format": "Короткий пост + CTA",
        "source_materials": "Прайс, отзывы, фото кабинета",
        "idempotency_key": f"r33b-{uuid4()}",
    }
    base.update(overrides)
    return base


def _copywriter_structured(*, mock: bool = False) -> dict[str, Any]:
    bodies = [
        "Пять критериев выбора детской стоматологии для родителей, которые хотят спокойные визиты без слёз и с понятной стоимостью лечения.",
        "Как подготовить ребёнка к первому визиту к стоматологу: короткий чек-лист для родителей 30–45 лет с акцентом на доверие и безопасность.",
        "Истории родителей о том, как сделать поход к стоматологу привычным: практические советы, игры дома и правильный выбор клиники рядом с домом.",
    ]
    items = [
        {
            "title": f"Пост {index}",
            "headline": f"Пост {index}",
            "hook": f"Хук {index} для родителей.",
            "body": bodies[index - 1],
            "cta": "Записаться на консультацию",
            "channel": "telegram",
            "angle": f"Angle {index}",
            "slot_index": index,
            "funnel_stage": "awareness",
            "content_pillar": "Care",
        }
        for index in range(1, 4)
    ]
    data: dict[str, Any] = {
        "content_items": items,
        "brief_channel": "telegram",
        "llm_provider": "openai",
        "model": "gpt-4o-mini",
    }
    if mock:
        data["mock"] = True
    return data


async def _fake_execute(data: MarketingSpecialistExecutionInput) -> MarketingSpecialistExecutionOutput:
    if data.specialist == MarketingSpecialistType.STRATEGIST:
        return MarketingSpecialistExecutionOutput(
            title="Strategy",
            output_type="strategy",
            content="Strategy direction",
            structured_data={"key_message": "Trust the clinic"},
            safe_summary="Strategy ready",
        )
    if data.specialist == MarketingSpecialistType.RESEARCHER:
        return MarketingSpecialistExecutionOutput(
            title="Research",
            output_type="research",
            content="Audience insights",
            structured_data={"insights": ["Parents search evenings"]},
            safe_summary="Research ready",
        )
    if data.specialist == MarketingSpecialistType.CONTENT_PLANNER:
        return MarketingSpecialistExecutionOutput(
            title="Content plan",
            output_type="content_plan",
            content="Plan outline",
            structured_data={
                "content_pillars": ["Care", "Offers", "Stories"],
                "post_ideas": [
                    {"title": "Post 1", "channel": "telegram"},
                    {"title": "Post 2", "channel": "telegram"},
                    {"title": "Post 3", "channel": "telegram"},
                ],
            },
            safe_summary="Plan ready",
        )
    if data.specialist == MarketingSpecialistType.COPYWRITER:
        return MarketingSpecialistExecutionOutput(
            title="Content copy",
            output_type="content_copy",
            content="Copy package",
            structured_data=_copywriter_structured(mock=False),
            safe_summary="Copy ready",
        )
    raise AssertionError(f"Unexpected specialist {data.specialist}")


@pytest.fixture
def live_provider_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    patched = settings.model_copy(
        update={
            "default_llm_provider": "openai",
            "openai_api_key": SecretStr("test-openai-key"),
        },
    )
    monkeypatch.setattr("app.content_factory.provider_gate.get_settings", lambda: patched)
    monkeypatch.setattr("app.agents.marketer.specialists.base.get_settings", lambda: patched)


def test_mock_provider_not_commercial(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    patched = settings.model_copy(update={"default_llm_provider": "mock"})
    monkeypatch.setattr("app.content_factory.provider_gate.get_settings", lambda: patched)
    readiness = assess_content_factory_provider_readiness(settings=patched)
    assert readiness.ready is False
    assert readiness.blocked_reason == "mock_provider_not_commercial"
    assert readiness.mock_provider is True


def test_provider_unavailable_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    patched = settings.model_copy(
        update={"default_llm_provider": "openai", "openai_api_key": None},
    )
    monkeypatch.setattr("app.content_factory.provider_gate.get_settings", lambda: patched)
    monkeypatch.setattr("app.agents.marketer.specialists.base.get_settings", lambda: patched)
    readiness = assess_content_factory_provider_readiness()
    assert readiness.ready is False
    assert readiness.blocked_reason == "llm_provider_not_configured"


def test_specialist_lineage_required_in_asset_fields() -> None:
    item = _copywriter_structured()["content_items"][0]
    fields = build_content_asset_fields_from_copywriter_item(
        item=item,
        slot_index=1,
        fallback_title="Fallback",
        structured_data=_copywriter_structured(),
        content_planner_output_id=str(uuid4()),
        idempotency_key="idem-1",
    )
    assert fields is not None
    assert fields["metadata"]["content_slot"] == 1
    assert fields["metadata"]["source_content_planner_output_id"]
    assert fields["metadata"]["content_factory_generation"] is True
    assert fields["metadata"]["quality_state"] == "draft_ready_for_review"


def test_failed_output_item_skipped() -> None:
    broken = {"headline": "No body item"}
    fields = build_content_asset_fields_from_copywriter_item(
        item=broken,
        slot_index=9,
        fallback_title="Fallback",
        structured_data=None,
    )
    assert fields is None


def test_provider_blocked_does_not_create_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    patched = settings.model_copy(update={"default_llm_provider": "mock"})
    monkeypatch.setattr("app.content_factory.provider_gate.get_settings", lambda: patched)
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json={"brief": _brief_payload(), "step": "all"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "blocked"
    assert body["content_assets"] == []


@pytest.mark.asyncio
async def test_full_pipeline_creates_three_assets_with_lineage(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    live_provider_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.specialist_execution_service.execute_marketing_specialist",
        _fake_execute,
    )
    project_id = _create_project(client, auth_headers)
    idem = f"pipeline-{uuid4()}"
    response = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json={"brief": _brief_payload(idempotency_key=idem), "step": "all"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "completed"
    assert len(body["content_assets"]) >= 3
    for asset in body["content_assets"]:
        assert asset["source_marketing_plan_id"]
        assert asset["source_execution_run_id"]
        assert asset["source_content_planner_output_id"]
        assert asset["source_copywriter_output_id"]
        assert asset["llm_provider"] == "openai"

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    repo = ContentAssetRepository(db_session)
    stored = await repo.list_by_project(UUID(project["owner_id"]), UUID(project_id))
    cf_assets = [
        row
        for row in stored
        if (row.asset_metadata or {}).get("content_factory_idempotency_key") == idem
    ]
    assert len(cf_assets) >= 3
    for row in cf_assets:
        assert row.source_marketing_plan_id is not None
        assert row.source_execution_run_id is not None
        assert row.source_specialist_output_id is not None


def test_retry_idempotency_returns_existing_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    live_provider_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.specialist_execution_service.execute_marketing_specialist",
        _fake_execute,
    )
    project_id = _create_project(client, auth_headers)
    idem = f"idem-{uuid4()}"
    payload = {"brief": _brief_payload(idempotency_key=idem), "step": "all"}
    first = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json=payload,
        headers=auth_headers,
    ).json()
    second = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json=payload,
        headers=auth_headers,
    ).json()
    assert first["stage"] == "completed"
    assert second["stage"] == "completed"
    assert {a["content_asset_id"] for a in first["content_assets"]} == {
        a["content_asset_id"] for a in second["content_assets"]
    }


def test_partial_copywriter_failure_does_not_create_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    live_provider_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _weak_copywriter(data: MarketingSpecialistExecutionInput) -> MarketingSpecialistExecutionOutput:
        if data.specialist == MarketingSpecialistType.COPYWRITER:
            structured = _copywriter_structured()
            structured["content_items"] = structured["content_items"][:1]
            return MarketingSpecialistExecutionOutput(
                title="Content copy",
                output_type="content_copy",
                content="Only one",
                structured_data=structured,
                safe_summary="Copy partial",
            )
        return await _fake_execute(data)

    monkeypatch.setattr(
        "app.services.specialist_execution_service.execute_marketing_specialist",
        _weak_copywriter,
    )
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json={"brief": _brief_payload(idempotency_key=f"fail-{uuid4()}"), "step": "all"},
        headers=auth_headers,
    )
    body = response.json()
    assert body["stage"] == "failed"
    assert body["content_assets"] == []


def test_tenant_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    live_provider_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.specialist_execution_service.execute_marketing_specialist",
        _fake_execute,
    )
    project_id = _create_project(client, auth_headers)
    generated = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json={"brief": _brief_payload(idempotency_key=f"tenant-{uuid4()}"), "step": "all"},
        headers=auth_headers,
    ).json()
    run_id = generated["execution_run_id"]
    denied = client.get(
        f"/projects/{project_id}/content-factory/generation-runs/{run_id}/status",
        headers=other_auth_headers,
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_mock_structured_data_rejected_for_asset_creation(
    client: TestClient,
    auth_headers: dict[str, str],
    live_provider_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_copywriter(data: MarketingSpecialistExecutionInput) -> MarketingSpecialistExecutionOutput:
        if data.specialist == MarketingSpecialistType.COPYWRITER:
            return MarketingSpecialistExecutionOutput(
                title="Content copy",
                output_type="content_copy",
                content="Mock copy",
                structured_data=_copywriter_structured(mock=True),
                safe_summary="Mock copy",
            )
        return await _fake_execute(data)

    monkeypatch.setattr(
        "app.services.specialist_execution_service.execute_marketing_specialist",
        _mock_copywriter,
    )
    project_id = _create_project(client, auth_headers)
    body = client.post(
        f"/projects/{project_id}/content-factory/generate-materials",
        json={"brief": _brief_payload(idempotency_key=f"mock-{uuid4()}"), "step": "all"},
        headers=auth_headers,
    ).json()
    assert body["stage"] == "failed"
    assert "mock" in body["safe_message"].lower()


def test_extract_content_items_requires_headline() -> None:
    items = extract_content_items(
        {"content_items": [{"body": "no headline"}, {"title": "Ok", "body": "text"}]},
    )
    assert len(items) == 1


def test_parser_valid_json() -> None:
    from app.marketing.copywriter_output_parser import parse_copywriter_llm_content

    payload = """
    {"content_items":[
      {"title":"Пост 1","body":"Русский текст достаточной длины для коммерческого материала о стоматологии для детей и родителей.","channel":"telegram","angle":"a1","slot_index":1},
      {"title":"Пост 2","body":"Второй уникальный русский текст про подготовку ребёнка к визиту и выбор клиники рядом с домом для семьи.","channel":"telegram","angle":"a2","slot_index":2},
      {"title":"Пост 3","body":"Третий уникальный русский текст с советами родителям и призывом записаться на консультацию в клинику.","channel":"telegram","angle":"a3","slot_index":3}
    ]}
    """
    parsed = parse_copywriter_llm_content(payload, expected_channel="telegram")
    assert len(parsed) == 3
    assert all(item["channel"] == "telegram" for item in parsed)


def test_parser_markdown_sections_from_smoke_shape() -> None:
    from app.marketing.copywriter_output_parser import parse_copywriter_llm_content

    content = """
#### Content Item 1
- **Headline:** Пять критериев выбора детской стоматологии
- **Body:** """ + ("Русский текст " * 20) + """
- **Channel:** Telegram
#### Content Item 2
- **Headline:** Как подготовить ребёнка к первому визиту
- **Body:** """ + ("Другой текст " * 20) + """
- **Channel:** Telegram
#### Content Item 3
- **Headline:** Истории родителей о детском стоматологе
- **Body:** """ + ("Третий текст " * 20) + """
- **Channel:** Telegram
"""
    parsed = parse_copywriter_llm_content(content, expected_channel="telegram")
    assert len(parsed) == 3
    assert parsed[0]["channel"] == "telegram"


def test_parser_unparseable_raises() -> None:
    from app.marketing.copywriter_output_parser import (
        CopywriterOutputUnparseableError,
        parse_copywriter_llm_content,
    )

    with pytest.raises(CopywriterOutputUnparseableError):
        parse_copywriter_llm_content("plain prose without structure", expected_channel="telegram")


def test_quality_gate_rejects_duplicate_bodies() -> None:
    from app.marketing.copywriter_quality_gate import validate_copywriter_content_items

    duplicate_body = "Одинаковый русский текст достаточной длины для проверки качества материалов контент-завода."
    items = [
        {"title": "A", "body": duplicate_body, "channel": "telegram"},
        {"title": "B", "body": duplicate_body, "channel": "telegram"},
        {"title": "C", "body": duplicate_body, "channel": "telegram"},
    ]
    with pytest.raises(InvalidStateError):
        validate_copywriter_content_items(items, expected_channel="telegram")


def test_quality_gate_rejects_fallback_marker() -> None:
    from app.marketing.copywriter_quality_gate import validate_copywriter_content_items

    items = [
        {
            "title": "A",
            "body": "Quick win for founders building funnels. " + ("x" * 80),
            "channel": "telegram",
        },
        {"title": "B", "body": "Уникальный русский текст " * 8, "channel": "telegram"},
        {"title": "C", "body": "Ещё один уникальный русский текст " * 8, "channel": "telegram"},
    ]
    with pytest.raises(InvalidStateError):
        validate_copywriter_content_items(items, expected_channel="telegram")


def test_channel_telegram_preserved_in_asset_fields() -> None:
    item = _copywriter_structured()["content_items"][0]
    fields = build_content_asset_fields_from_copywriter_item(
        item=item,
        slot_index=1,
        fallback_title="Fallback",
        structured_data=_copywriter_structured(),
    )
    assert fields is not None
    assert fields["metadata"]["channel_adaptation"] == "telegram"


def test_frontend_body_mapper_never_undefined() -> None:
    source = (Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "api" / "mappers" / "content-assets.ts").read_text(
        encoding="utf-8",
    )
    editor = (
        Path(__file__).resolve().parents[1]
        / "web"
        / "src"
        / "components"
        / "content-factory"
        / "content-factory-material-editor.tsx"
    ).read_text(encoding="utf-8")
    assert "normalizeContentAsset" in source
    assert "fetchContentAsset" in editor
    assert "contentAssetBodyUnavailableLabel" in editor
