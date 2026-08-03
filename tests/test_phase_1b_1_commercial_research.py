"""Phase 1B.1 — commercial research orchestration foundation."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from app.commercial_research.preflight import build_preflight_result
from app.commercial_research.quote import build_quote
from app.commercial_research.request_hash import compute_commercial_research_request_hash
from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models.commercial_research_run import CommercialResearchRunTable
from app.db.models.investigation import InvestigationTable
from app.db.models.project import ProjectTable
from app.db.models.project_brief import ProjectBriefTable
from app.schemas.contracts import (
    CommercialResearchRunStatus,
    CommercialResearchStageId,
)
from app.services.commercial_research_pipeline_service import CommercialResearchPipelineService
from fastapi.testclient import TestClient
from sqlalchemy import func, select


def _create_user_request(
    client: TestClient,
    headers: dict[str, str],
    text: str = "Проверить идею кофейни в центре города",
) -> str:
    resp = client.post(
        "/user-requests",
        json={"text": text, "source": "home_conversation", "locale": "ru"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _error_code(resp) -> str:
    body = resp.json()
    return str(body.get("error_code") or body.get("detail") or "")


def _research_ready_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    get_settings.cache_clear()


def _research_blocked_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "false")
    get_settings.cache_clear()


@pytest.fixture
def other_auth_headers(database_url: str) -> dict[str, str]:
    from tests.conftest import _create_user_with_api_key

    plain_key, _user = asyncio.run(_create_user_with_api_key())
    return {"Authorization": f"Bearer {plain_key}"}


def test_request_hash_changes_when_brief_fingerprint_changes() -> None:
    base = compute_commercial_research_request_hash(
        user_request_id=uuid4(),
        normalized_text="same text",
        route_category="idea_validation",
        project_brief_fingerprint="fp_v1",
        project_brief_version=1,
    )
    changed = compute_commercial_research_request_hash(
        user_request_id=uuid4(),
        normalized_text="same text",
        route_category="idea_validation",
        project_brief_fingerprint="fp_v2",
        project_brief_version=2,
    )
    assert base != changed


def test_preflight_and_quote_perform_no_provider_billing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _research_ready_env(monkeypatch)

    def _fail_billing(*_args, **_kwargs):
        raise AssertionError("paid provider call must not run in preflight/quote")

    monkeypatch.setattr(
        "app.research_source_collection.readiness.probe_providers",
        _fail_billing,
    )

    settings = get_settings()
    commercial, developer = build_preflight_result(settings=settings, query_text="test idea")
    assert commercial.research_not_executed is True
    assert developer.get("secrets_exposed") is False
    assert "api_key" not in str(developer).lower()

    scope = commercial.estimated_scope
    quote, quote_commercial, quote_dev = build_quote(
        tenant_id=uuid4(),
        request_hash="abc123",
        scope=scope,
        settings=settings,
    )
    assert quote_commercial.research_not_executed is True
    assert "api_key" not in str(quote_dev).lower()


def test_bootstrap_idempotency(client: TestClient, auth_headers: dict[str, str], monkeypatch):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    key = "bootstrap-key-1"

    first = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        json={"idempotency_key": key},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    second = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        json={"idempotency_key": key},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert first.json()["run_id"] == second.json()["run_id"]


def test_bootstrap_creates_real_lineage(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    resp = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    status = client.get(
        f"/user-requests/{req_id}/commercial-research/status?developer=true",
        headers=auth_headers,
    )
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["project_id"]
    assert body["investigation_id"]
    assert body["commercial"]["research_not_executed"] is True

    async def _counts():
        projects = await db_session.scalar(select(func.count()).select_from(ProjectTable))
        briefs = await db_session.scalar(select(func.count()).select_from(ProjectBriefTable))
        investigations = await db_session.scalar(
            select(func.count()).select_from(InvestigationTable)
        )
        runs = await db_session.scalar(
            select(func.count()).select_from(CommercialResearchRunTable)
        )
        return projects, briefs, investigations, runs

    projects, briefs, investigations, runs = asyncio.run(_counts())
    assert projects >= 1
    assert briefs >= 1
    assert investigations >= 1
    assert runs >= 1


def test_changed_brief_creates_new_run_version(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers, text="Идея A: кофейня")
    first = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    assert first.status_code == 200

    async def _change_text():
        from app.db.models.user_request import UserRequestTable

        row = await db_session.get(UserRequestTable, UUID(req_id))
        row.text = "Идея B: пекарня с доставкой"
        row.normalized_text = row.text.lower()
        db_session.add(row)
        await db_session.commit()

    asyncio.run(_change_text())

    second = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert first.json()["run_id"] != second.json()["run_id"]


def test_tenant_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    foreign = client.get(
        f"/user-requests/{req_id}/commercial-research/status",
        headers=other_auth_headers,
    )
    assert foreign.status_code == 404


def test_preflight_blocked_when_research_disabled(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    _research_blocked_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    resp = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["commercial"]["ready"] is False
    assert resp.json()["commercial"]["blocking_reasons"]


def test_preflight_ready_when_mock_enabled(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    resp = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["commercial"]["ready"] is True


def test_quote_without_execution(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    quote = client.post(
        f"/user-requests/{req_id}/commercial-research/quote",
        headers=auth_headers,
    )
    assert quote.status_code == 200, quote.text
    assert quote.json()["commercial"]["research_not_executed"] is True


def test_quote_tied_to_request_hash(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    quote = client.post(
        f"/user-requests/{req_id}/commercial-research/quote",
        headers=auth_headers,
    )
    quote_id = quote.json()["quote_id"]

    status = client.get(
        f"/user-requests/{req_id}/commercial-research/status?developer=true",
        headers=auth_headers,
    )
    request_hash = status.json()["developer"]["request_hash"]

    bad = client.post(
        f"/user-requests/{req_id}/commercial-research/approve",
        json={"quote_id": str(uuid4()), "owner_confirmed": True},
        headers=auth_headers,
    )
    assert bad.status_code == 409
    assert _error_code(bad) == "quote_mismatch"

    good = client.post(
        f"/user-requests/{req_id}/commercial-research/approve",
        json={"quote_id": quote_id, "owner_confirmed": True},
        headers=auth_headers,
    )
    assert good.status_code == 200, good.text

    async def _verify():
        run = await db_session.scalar(
            select(CommercialResearchRunTable).where(
                CommercialResearchRunTable.user_request_id == UUID(req_id)
            )
        )
        assert run.request_hash == request_hash
        assert run.approval_json["request_hash"] == request_hash
        assert run.approval_json["quote_id"] == quote_id

    asyncio.run(_verify())


def test_expired_quote_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    quote = client.post(
        f"/user-requests/{req_id}/commercial-research/quote",
        headers=auth_headers,
    )
    quote_id = quote.json()["quote_id"]

    async def _expire():
        run = await db_session.scalar(
            select(CommercialResearchRunTable).where(
                CommercialResearchRunTable.user_request_id == UUID(req_id)
            )
        )
        q = dict(run.quote_json)
        q["expires_at"] = (utc_now() - timedelta(hours=1)).isoformat()
        run.quote_json = q
        db_session.add(run)
        await db_session.commit()

    asyncio.run(_expire())

    resp = client.post(
        f"/user-requests/{req_id}/commercial-research/approve",
        json={"quote_id": quote_id, "owner_confirmed": True},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert _error_code(resp) == "quote_expired"


def test_execute_unavailable_in_phase_1b_1(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    quote = client.post(
        f"/user-requests/{req_id}/commercial-research/quote",
        headers=auth_headers,
    )
    client.post(
        f"/user-requests/{req_id}/commercial-research/approve",
        json={"quote_id": quote.json()["quote_id"], "owner_confirmed": True},
        headers=auth_headers,
    )
    execute = client.post(
        f"/user-requests/{req_id}/commercial-research/execute",
        json={"idempotency_key": "exec-key-1", "owner_confirmed": True},
        headers=auth_headers,
    )
    assert execute.status_code == 409
    assert _error_code(execute) == "execution_not_enabled_in_phase_1b_1"


def test_execute_without_approval_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    execute = client.post(
        f"/user-requests/{req_id}/commercial-research/execute",
        json={"idempotency_key": "exec-key-2", "owner_confirmed": True},
        headers=auth_headers,
    )
    assert execute.status_code == 409
    assert _error_code(execute) == "approval_required"


def test_outcome_unknown_cannot_blind_retry(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    quote = client.post(
        f"/user-requests/{req_id}/commercial-research/quote",
        headers=auth_headers,
    )
    client.post(
        f"/user-requests/{req_id}/commercial-research/approve",
        json={"quote_id": quote.json()["quote_id"], "owner_confirmed": True},
        headers=auth_headers,
    )

    async def _mark():
        from app.services.auth import AuthService

        token = auth_headers["Authorization"].split(" ", 1)[1]
        auth = await AuthService(db_session).authenticate_api_key(token)
        assert auth is not None
        user, _key = auth
        svc = CommercialResearchPipelineService(db_session, get_settings())
        await svc.mark_outcome_unknown(user.id, UUID(req_id))
        await db_session.commit()

    asyncio.run(_mark())

    execute = client.post(
        f"/user-requests/{req_id}/commercial-research/execute",
        json={"idempotency_key": "exec-key-3", "owner_confirmed": True},
        headers=auth_headers,
    )
    assert execute.status_code == 409
    assert _error_code(execute) == "outcome_unknown_no_blind_retry"

    status = client.get(
        f"/user-requests/{req_id}/commercial-research/status",
        headers=auth_headers,
    )
    assert status.json()["commercial"]["outcome_unknown"] is True
    assert status.json()["commercial"]["retryable"] is False


def test_status_reflects_pipeline_state(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    _research_ready_env(monkeypatch)
    req_id = _create_user_request(client, auth_headers)
    client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    client.post(
        f"/user-requests/{req_id}/commercial-research/quote",
        headers=auth_headers,
    )
    status = client.get(
        f"/user-requests/{req_id}/commercial-research/status",
        headers=auth_headers,
    )
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == CommercialResearchRunStatus.QUOTE_READY.value
    assert body["current_stage"] == CommercialResearchStageId.QUOTE.value
    assert body["commercial"]["quote_summary"]
    assert "xmlriver" not in str(body).lower()
    assert "api_key" not in str(body).lower()


def test_secrets_not_in_developer_status(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "false")
    monkeypatch.setenv("XMLRIVER_USER_ID", "user123")
    monkeypatch.setenv("XMLRIVER_API_KEY", "super-secret-key-value")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "firecrawl-secret")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    req_id = _create_user_request(client, auth_headers)
    resp = client.post(
        f"/user-requests/{req_id}/commercial-research/preflight",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    blob = str(resp.json())
    assert "super-secret" not in blob
    assert "firecrawl-secret" not in blob
