"""Recovery R3.3 — draft generation from brief via foundation plan-drafts."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web" / "src"


def _read(relative: str) -> str:
    return (WEB_ROOT / relative).read_text(encoding="utf-8")


def test_r33_generate_materials_client_wiring() -> None:
    panel = _read("components/content-factory/content-factory-panel.tsx")
    endpoint = _read("lib/api/endpoints/content-factory.ts")
    generator = _read("lib/content-factory/generate-materials-from-brief.ts")

    assert "generateContentFactoryMaterials" in panel
    assert 'data-testid="content-factory-create-materials"' in panel
    assert "fetchContentFactoryProviderReadiness" in panel
    assert "allowDemoMaterials" in panel
    assert "recovery_r3_demo" in panel
    assert 'contentFactoryPath(projectId, "/generate-materials")' in endpoint
    assert 'contentFactoryPath(projectId, "/provider-readiness")' in endpoint
    # Foundation plan-draft path remains available for legacy/integration flows.
    assert "generateMaterialsFromBrief" in generator
    assert "generateAssetsFromPlanDraft" in generator


def test_r33_demo_only_in_owner_preview() -> None:
    preview = _read("components/workspace/home/recovery-preview-r3-view.tsx")
    assert "allowDemoMaterials" in preview


def test_r33_plan_draft_generate_assets_creates_three_drafts(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "R3.3 generation"}, headers=auth_headers)
    assert project.status_code == 201
    project_id = project.json()["id"]

    campaign = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Контент-завод: тест", "status": "active"},
        headers=auth_headers,
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]

    plan_payload = {
        "goal": "Рост подписчиков",
        "target_audience": "SMB owners",
        "key_message": "Telegram launch",
        "content_items": [
            {
                "title": f"Материал {index}",
                "channel": "telegram",
                "format": "text",
                "notes": f"Слот {index} из брифа",
            }
            for index in range(1, 4)
        ],
    }
    draft = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={"title": "План: Telegram launch", "plan_payload": plan_payload},
        headers=auth_headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    generated = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
        headers=auth_headers,
    )
    assert generated.status_code == 201, generated.text
    body = generated.json()
    assert body["created_count"] == 3
    assert len(body["asset_ids"]) == 3

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers)
    assert assets.status_code == 200
    rows = assets.json()
    created = [row for row in rows if row["id"] in body["asset_ids"]]
    assert len(created) == 3
    for row in created:
        metadata = row.get("metadata") or {}
        assert metadata.get("source_plan_draft_id") == draft_id
        assert metadata.get("plan_item_index") is not None
        assert metadata.get("recovery_r3_demo") is None
        assert row["status"] == "draft"


def test_r33_generate_assets_idempotent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "R3.3 idempotent"},
        headers=auth_headers,
    ).json()["id"]
    campaign_id = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Campaign"},
        headers=auth_headers,
    ).json()["id"]
    draft_id = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={
            "title": "Plan",
            "plan_payload": {
                "content_items": [
                    {"title": "A", "channel": "telegram", "format": "text", "notes": "1"},
                    {"title": "B", "channel": "telegram", "format": "text", "notes": "2"},
                    {"title": "C", "channel": "telegram", "format": "text", "notes": "3"},
                ],
            },
        },
        headers=auth_headers,
    ).json()["id"]

    first = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["already_generated"] is True
    assert second.json()["created_count"] == 0
