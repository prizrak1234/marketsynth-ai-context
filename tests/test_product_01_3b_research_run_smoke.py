"""PRODUCT-01.3B — API-level research run smoke (pre-owner visual gate)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.contracts import AnalysisContextCreateDraftRequest, AnalysisContextConfirmRequest
from app.services.business_idea_validation_service import build_research_idempotency_key
from tests.conftest import _create_user_with_api_key


IDEA = (
    "AI-платформа для автоматического создания коммерческих "
    "предложений для строительных компаний"
)


@pytest.mark.asyncio
async def test_product_01_3b_research_run_api_smoke(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenarios 1–2 at API layer: fresh research run + idempotent replay."""
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        project = await client.post(
            "/projects",
            json={"name": "Smoke 01.3B"},
            headers=headers,
        )
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]

        draft = await client.post(
            f"/projects/{project_id}/analysis-contexts",
            json=AnalysisContextCreateDraftRequest(
                idea_description=IDEA,
                product_or_service="SaaS генерации КП для строительного B2B",
                target_customer="Коммерческие директора строительных компаний 50–500 сотрудников",
                geography="Россия, B2B",
                analysis_goal="Проверить спрос и конкуренцию перед запуском",
            ).model_dump(mode="json"),
            headers=headers,
        )
        assert draft.status_code == 201, draft.text
        context = draft.json()
        context_id = context["context_id"]
        snapshot_hash = context["input_snapshot_hash"]
        assert snapshot_hash

        confirmed = await client.post(
            f"/projects/{project_id}/analysis-contexts/{context_id}/confirm",
            json=AnalysisContextConfirmRequest(
                input_snapshot_hash=snapshot_hash,
            ).model_dump(mode="json"),
            headers=headers,
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["confirmed_by_user"] is True

        user_request = await client.post(
            "/user-requests",
            json={
                "text": IDEA,
                "selected_scenario": "idea_validation",
                "skill_inputs": {"home_agency_flow": "v2"},
            },
            headers=headers,
        )
        assert user_request.status_code == 201, user_request.text
        request_id = user_request.json()["id"]

        idem_key = build_research_idempotency_key(context_id, snapshot_hash)
        assert idem_key.startswith("biv-research-")

        run_body = {
            "idempotency_key": idem_key,
            "research_intent": True,
            "analysis_context_id": context_id,
            "input_snapshot_hash": snapshot_hash,
            "idea": IDEA,
            "location": "Россия, B2B",
            "target_audience": "Коммерческие директора строительных компаний",
        }

        first = await client.post(
            f"/user-requests/{request_id}/business-idea-validation/run",
            json=run_body,
            headers=headers,
        )
        assert first.status_code == 200, first.text
        first_json = first.json()
        assert first_json["analysis_context_id"] == context_id
        assert first_json["input_snapshot_hash"] == snapshot_hash
        assert first_json["status"] in {"succeeded", "running", "failed"}
        run_id = first_json["run_id"]

        if first_json.get("output"):
            output = first_json["output"]
            assert output.get("analysis_context_id") == context_id
            assert output.get("input_snapshot_hash") == snapshot_hash
            assert output.get("run_id") == run_id
            assert "research_terminal_state" in output

            garbage_markers = (
                "To main content",
                "skillbox",
                "youtube.com",
                "[Skillbox]",
            )
            blob = " ".join(
                [
                    *(f.get("statement", "") for f in output.get("findings", [])),
                    *(e.get("claim", "") for e in output.get("evidence", [])),
                    *(e.get("observation", "") or "" for e in output.get("evidence", [])),
                ]
            ).lower()
            for marker in garbage_markers:
                assert marker.lower() not in blob, f"garbage marker found: {marker}"

            for ev in output.get("evidence", []):
                claim = (ev.get("observation") or ev.get("claim") or "")
                assert "http://" not in claim and "https://" not in claim

        second_request = await client.post(
            "/user-requests",
            json={"text": IDEA, "selected_scenario": "idea_validation"},
            headers=headers,
        )
        assert second_request.status_code == 201
        second_id = second_request.json()["id"]

        second = await client.post(
            f"/user-requests/{second_id}/business-idea-validation/run",
            json=run_body,
            headers=headers,
        )
        assert second.status_code == 200, second.text
        second_json = second.json()
        assert second_json.get("lineage_reused") is True or second_json["run_id"] == run_id

        hydration = await client.get(
            f"/projects/{project_id}/business-idea-validation/latest"
            f"?analysis_context_id={context_id}&input_snapshot_hash={snapshot_hash}",
            headers=headers,
        )
        if first_json.get("output"):
            assert hydration.status_code == 200, hydration.text
            hydrated = hydration.json()
            assert hydrated["run_id"] == run_id
            assert hydrated["analysis_context_id"] == context_id

        wrong_hash = "b" * 64
        stale = await client.get(
            f"/projects/{project_id}/business-idea-validation/latest"
            f"?analysis_context_id={context_id}&input_snapshot_hash={wrong_hash}",
            headers=headers,
        )
        assert stale.status_code == 404
