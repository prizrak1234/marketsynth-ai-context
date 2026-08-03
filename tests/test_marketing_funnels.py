"""Phase 4.8 — marketing funnel domain skeleton."""

from __future__ import annotations

from app.schemas.contracts import AgentType
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Funnels"},
        headers=headers,
    ).json()["id"]


def _create_funnel(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Launch funnel", "description": "Main funnel"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Email asset", "body": "copy"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_funnel(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel = _create_funnel(client, auth_headers, project_id)
    assert funnel["status"] == "draft"
    assert funnel["title"] == "Launch funnel"


def test_list_funnels_by_project(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    _create_funnel(client, auth_headers, project_id)
    _create_funnel(client, auth_headers, project_id)

    listed = client.get(
        f"/projects/{project_id}/funnels",
        headers=auth_headers,
    ).json()
    assert len(listed) == 2


def test_get_funnel_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]

    response = client.get(
        f"/projects/{project_id}/funnels/{funnel_id}",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_update_funnel(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]

    updated = client.patch(
        f"/projects/{project_id}/funnels/{funnel_id}",
        json={"title": "Renamed funnel", "status": "active"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed funnel"
    assert updated.json()["status"] == "active"


def test_archive_funnel(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]

    archived = client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_create_step(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]

    response = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Top of funnel"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["position"] == 1


def test_unique_position_enforced(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]

    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Step A", "position": 1},
        headers=auth_headers,
    )
    conflict = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "offer", "title": "Step B", "position": 1},
        headers=auth_headers,
    )
    assert conflict.status_code == 409


def test_list_steps_ordered_by_position(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]

    step_a = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "A"},
        headers=auth_headers,
    ).json()
    step_b = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "nurture", "title": "B"},
        headers=auth_headers,
    ).json()

    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/reorder",
        json={"step_ids": [step_b["id"], step_a["id"]]},
        headers=auth_headers,
    )

    listed = client.get(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        headers=auth_headers,
    ).json()
    assert [row["title"] for row in listed] == ["B", "A"]
    assert [row["position"] for row in listed] == [1, 2]


def test_reorder_steps(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_one = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "One"},
        headers=auth_headers,
    ).json()
    step_two = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "offer", "title": "Two"},
        headers=auth_headers,
    ).json()

    reordered = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/reorder",
        json={"step_ids": [step_two["id"], step_one["id"]]},
        headers=auth_headers,
    ).json()
    assert [row["position"] for row in reordered] == [1, 2]
    assert reordered[0]["title"] == "Two"


def test_archive_step(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "checkout", "title": "Checkout"},
        headers=auth_headers,
    ).json()["id"]

    archived = client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_link_asset_to_step(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "offer", "title": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _create_asset(client, auth_headers, project_id)

    linked = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
        json={"asset_id": asset_id, "role": "primary"},
        headers=auth_headers,
    )
    assert linked.status_code == 201
    assert linked.json()["asset_id"] == asset_id


def test_list_step_assets_includes_asset_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "lead_magnet", "title": "Lead magnet"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
        json={"asset_id": asset_id, "role": "supporting"},
        headers=auth_headers,
    )

    listed = client.get(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
        headers=auth_headers,
    ).json()
    assert len(listed) == 1
    row = listed[0]
    assert row["asset_id"] == asset_id
    assert row["asset_title"] == "Email asset"
    assert row["asset_type"] == "email"
    assert row["asset_status"] == "draft"
    assert row["role"] == "supporting"


def test_unlink_asset(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "nurture", "title": "Nurture"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
        json={"asset_id": asset_id},
        headers=auth_headers,
    )

    removed = client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets/{asset_id}",
        headers=auth_headers,
    )
    assert removed.status_code == 204
    assert (
        client.get(
            f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
            headers=auth_headers,
        ).json()
        == []
    )


def test_cannot_link_asset_from_another_project(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    other_project_id = _project_id(client, other_auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "offer", "title": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    foreign_asset = _create_asset(client, other_auth_headers, other_project_id)

    response = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
        json={"asset_id": foreign_asset},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_cannot_link_step_from_another_funnel(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_a = _create_funnel(client, auth_headers, project_id)["id"]
    funnel_b = _create_funnel(client, auth_headers, project_id)["id"]
    step_a = client.post(
        f"/projects/{project_id}/funnels/{funnel_a}/steps",
        json={"step_type": "awareness", "title": "A"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _create_asset(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/funnels/{funnel_b}/steps/{step_a}/assets",
        json={"asset_id": asset_id},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_archived_funnel_cannot_receive_new_steps(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Late step"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_archived_step_cannot_receive_asset_links(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "retention", "title": "Retention"},
        headers=auth_headers,
    ).json()["id"]
    client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}",
        headers=auth_headers,
    )
    asset_id = _create_asset(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}/assets",
        json={"asset_id": asset_id},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_include_archived_for_funnels_and_steps(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    funnel_id = _create_funnel(client, auth_headers, project_id)["id"]
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "onboarding", "title": "Onboarding"},
        headers=auth_headers,
    ).json()["id"]
    client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}/steps/{step_id}",
        headers=auth_headers,
    )
    client.delete(
        f"/projects/{project_id}/funnels/{funnel_id}",
        headers=auth_headers,
    )

    funnels_default = client.get(
        f"/projects/{project_id}/funnels",
        headers=auth_headers,
    ).json()
    assert funnels_default == []

    funnels_archived = client.get(
        f"/projects/{project_id}/funnels",
        params={"include_archived": True},
        headers=auth_headers,
    ).json()
    assert len(funnels_archived) == 1

    steps_default = client.get(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        headers=auth_headers,
    ).json()
    assert steps_default == []

    steps_archived = client.get(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        params={"include_archived": True},
        headers=auth_headers,
    ).json()
    assert len(steps_archived) == 1


def test_phase3_agent_tools_unchanged() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.COPYWRITER)}
    assert "content_asset.get" in tools
    assert "marketing_brief.get" in tools
    assert "marketing_funnel.get" in tools
    assert "marketing_funnel.step_assets" in tools
    assert "marketing_funnel.list" not in tools
    assert "marketing_funnel.gap_analysis" not in tools
