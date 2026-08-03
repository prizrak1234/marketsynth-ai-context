"""Phase AI.224 — Marketing data tools regression."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.domain.marketing_metrica_parser import parse_metrica_input
from app.marketing.data_tools.yandex_regions import resolve_region
from app.schemas.contracts import MetricaToolInput
from app.services.marketing_wordstat_service import MarketingWordstatService
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.helpers.business_operator_helpers import (
    analyze_operator,
    complete_and_confirm_brief,
    create_operator_campaign,
)
from tests.helpers.v2_specialist_execution_helpers import create_project


@pytest.fixture
def enable_marketing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_DATA_TOOLS_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def disable_marketing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MARKETING_DATA_TOOLS_ENABLED", "false")
    monkeypatch.setenv("MARKETING_DATA_TOOLS_MOCK_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_wordstat_query_required() -> None:
    service = MarketingWordstatService()
    with pytest.raises(ValidationError):
        await service.execute({"query": ""})


def test_wordstat_region_name_to_code() -> None:
    region = resolve_region("Moscow")
    assert region["code"] == 213
    assert region["name"] == "Moscow"


def test_wordstat_unknown_region_is_global() -> None:
    region = resolve_region("Unknown City XYZ")
    assert region["code"] == 0
    assert region["name"] == "All regions"


@pytest.mark.asyncio
async def test_wordstat_report_type_defaults_to_one() -> None:
    service = MarketingWordstatService()
    output, metadata = await service.execute({"query": "dental implants"})
    assert output["report_type"] == "one"
    assert len(output["rows"]) == 1
    assert metadata["provider"] == "mock"
    assert metadata["external_call"] is False


def test_metrica_visits_users_pageviews_mapping() -> None:
    parsed = parse_metrica_input(
        MetricaToolInput(metrics=["visits", "users", "pageviews"]),
    )
    assert parsed.metrics == ["ym:s:visits", "ym:s:users", "ym:s:pageviews"]


def test_metrica_traffic_device_content_scenarios() -> None:
    parsed = parse_metrica_input(
        MetricaToolInput(
            natural_language="show visits users traffic and device breakdown",
            dimensions=["traffic", "device"],
        ),
    )
    assert "ym:s:trafficSource" in parsed.dimensions
    assert "ym:s:deviceCategory" in parsed.dimensions


def test_wordstat_mock_call_via_api(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 wordstat")
    response = client.post(
        f"/projects/{project_id}/marketing-tools/wordstat/calls",
        json={"input_payload": {"query": "стоматология", "region": "Moscow"}},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["provider"] == "mock"
    assert body["output_payload"]["region_code"] == 213
    assert body["safe_metadata"]["external_call"] is False
    assert "api_key" not in body["input_payload"]


def test_metrica_mock_call_via_api(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 metrica")
    response = client.post(
        f"/projects/{project_id}/marketing-tools/metrica/calls",
        json={
            "input_payload": {
                "metrics": ["visits", "users"],
                "dimensions": ["traffic", "device"],
                "natural_language": "traffic by device",
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["provider"] == "mock"
    assert body["output_payload"]["data"]
    assert "token" not in str(body["input_payload"]).lower()


def test_image_mock_call_via_api(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 image")
    response = client.post(
        f"/projects/{project_id}/marketing-tools/image_generation/calls",
        json={
            "input_payload": {
                "prompt": "Dental clinic ad banner, clean modern style",
                "aspect_ratio": "16:9",
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    images = body["output_payload"]["images"]
    assert len(images) == 1
    assert images[0]["url"].startswith("mock://image/")
    assert body["safe_metadata"]["image_count"] == 1


def test_rejects_secret_keys_in_input(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 secrets")
    response = client.post(
        f"/projects/{project_id}/marketing-tools/wordstat/calls",
        json={"input_payload": {"query": "test", "api_key": "sk-secret-value"}},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_permissions_block_when_disabled(
    client: TestClient,
    auth_headers: dict[str, str],
    disable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 disabled")
    response = client.post(
        f"/projects/{project_id}/marketing-tools/wordstat/calls",
        json={"input_payload": {"query": "test"}},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_list_and_get_tool_calls(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 list")
    created = client.post(
        f"/projects/{project_id}/marketing-tools/wordstat/calls",
        json={"input_payload": {"query": "leads"}},
        headers=auth_headers,
    )
    call_id = created.json()["id"]

    listed = client.get(
        f"/projects/{project_id}/marketing-tools/calls",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert any(row["id"] == call_id for row in listed.json())

    fetched = client.get(
        f"/projects/{project_id}/marketing-tools/calls/{call_id}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == call_id


def test_tool_suggestions_do_not_execute_tools(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 suggestions")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    suggestions = analyzed.get("tool_suggestions") or []
    assert suggestions
    tool_types = {item["tool_type"] for item in suggestions}
    assert "wordstat" in tool_types

    listed = client.get(
        f"/projects/{project_id}/marketing-tools/calls",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json() == []


def test_control_center_includes_tool_suggestions_without_execution(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 control center tools")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    brief_id = complete_and_confirm_brief(
        client,
        auth_headers,
        project_id,
        analyzed,
        extra_answers={
            "offer": "Dental implants and hygiene packages",
            "target_audience": "Adults 30-55 in the city",
        },
    )
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    campaign_id = created["campaign"]["id"]

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert body.get("tool_suggestions")
    assert body["next_action"]["action_type"]

    listed = client.get(
        f"/projects/{project_id}/marketing-tools/calls",
        headers=auth_headers,
    )
    assert listed.json() == []


def test_get_unknown_call_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_tools: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.224 not found")
    response = client.get(
        f"/projects/{project_id}/marketing-tools/calls/{uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404
