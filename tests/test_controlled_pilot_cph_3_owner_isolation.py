"""CPH.3 — cross-owner isolation (404 non-disclosure) for commercial domains."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from tests.conftest import _create_user_with_api_key


def test_cross_owner_project_isolation_matrix(client: TestClient) -> None:
    key_a, _ = asyncio.run(_create_user_with_api_key(telegram_id=9100401))
    key_b, _ = asyncio.run(_create_user_with_api_key(telegram_id=9100402))
    ha = {"Authorization": f"Bearer {key_a}"}
    hb = {"Authorization": f"Bearer {key_b}"}

    project_b = client.post(
        "/projects",
        json={"name": "Owner B Project", "description": "iso"},
        headers=hb,
    )
    assert project_b.status_code == 201, project_b.text
    pid = project_b.json()["id"]

    assert client.get(f"/projects/{pid}", headers=ha).status_code == 404
    assert client.patch(
        f"/projects/{pid}",
        json={"name": "hijack"},
        headers=ha,
    ).status_code == 404

    for path in (
        f"/projects/{pid}/briefs",
        f"/projects/{pid}/investigations",
        f"/projects/{pid}/sources",
        f"/projects/{pid}/business-verdicts",
        f"/projects/{pid}/marketing-strategies",
        f"/projects/{pid}/implementation-plans",
        f"/projects/{pid}/marketing-plans",
    ):
        res = client.get(path, headers=ha)
        assert res.status_code == 404, f"{path} → {res.status_code} {res.text[:200]}"

    fake = "00000000-0000-4000-8000-000000000001"
    assert (
        client.get(f"/projects/{pid}/implementation-plans/{fake}", headers=ha).status_code
        == 404
    )
    assert client.post(
        f"/projects/{pid}/implementation-plans/{fake}/marketing-plan-handoff/preview",
        headers=ha,
    ).status_code in (404, 409, 422)
