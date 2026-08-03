"""Phase AI.14.2 — chain demo smoke: API response shape + UI contract."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

LAUNCH_MESSAGE = "Запусти новый продукт в Telegram"
FORBIDDEN_RESPONSE_KEYS = frozenset(
    {
        "output_payload",
        "previous_child_output",
        "input_payload",
    },
)
FORBIDDEN_CHAIN_ENTRY_KEYS = frozenset(
    {
        "output_payload",
        "previous_child_output",
        "content",
        "tools",
    },
)
def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.14.2 Demo"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_type: str,
) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": agent_type},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_chain_response_exposes_compact_chain_not_child_payloads(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    for agent_type in ("researcher", "strategist", "copywriter"):
        _create_agent(client, auth_headers, project_id, agent_type=agent_type)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": LAUNCH_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()

    assert "subagent_chain" in body
    chain = body["subagent_chain"]
    assert len(chain) == 3
    assert [entry["subagent"] for entry in chain] == [
        "researcher",
        "strategist",
        "copywriter",
    ]

    for key in FORBIDDEN_RESPONSE_KEYS:
        assert key not in body

    for entry in chain:
        assert set(entry.keys()) <= {"subagent", "agent_run_id", "status"}
        for forbidden in FORBIDDEN_CHAIN_ENTRY_KEYS:
            assert forbidden not in entry
        assert entry.get("status") == "succeeded"

    assert body["subagent_execution"]["subagent"] == "copywriter"

    serialized = json.dumps(body)
    assert "output_payload" not in serialized
    assert "previous_child_output" not in serialized


def test_chain_response_has_no_top_level_write_action_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Перепиши этот пост", "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()

    assert sent.get("subagent_chain")
    assert "generated_assets" not in sent or sent.get("generated_assets") is None
    assert "revised_assets" not in sent or not sent.get("revised_assets")
