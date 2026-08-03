"""Phase H1 — UserRequest API owner isolation + routing."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_lists_and_isolates_user_requests(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    create = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши 10 постов для Telegram о бурении."},
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["route_category"] == "content"
    # H2.5: content.telegram_post asks for skill clarifications before snapshot
    assert body["status"] == "needs_clarification"
    assert body["skill_code"] == "content.telegram_post"
    assert body["execution_readiness"] == "needs_clarification"
    assert body["avoids_investigation"] is True
    assert body["assigned_specialist"] == "content_specialist"
    request_id = body["id"]

    listed = client.get("/user-requests", headers=auth_headers)
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert request_id in ids

    other_list = client.get("/user-requests", headers=other_auth_headers)
    assert other_list.status_code == 200
    assert request_id not in {row["id"] for row in other_list.json()}

    other_get = client.get(f"/user-requests/{request_id}", headers=other_auth_headers)
    assert other_get.status_code == 404


def test_bot_and_idea_routes(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    bot = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Создай Telegram-бота для записи клиентов."},
    ).json()
    assert bot["route_category"] == "telegram_bot"
    assert bot["assigned_specialist"] == "programmer"

    idea = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Хочу открыть кафе в центре Баку."},
    ).json()
    assert idea["route_category"] == "idea_validation"
    assert idea["route_kind"] == "project_intake"
    assert "projects/new" in (idea["next_href"] or "")


def test_website_clarification_then_re_route(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    first = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Нужен сайт."},
    )
    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "needs_clarification"
    assert body["clarification_question"]

    clarified = client.post(
        f"/user-requests/{body['id']}/clarify",
        headers=auth_headers,
        json={"answer": "Лендинг для продукта"},
    )
    assert clarified.status_code == 200
    out = clarified.json()
    assert out["route_category"] == "website"
    assert out["status"] == "routed"
    assert out["avoids_investigation"] is True


def test_create_does_not_spawn_agent_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Напиши пост для Telegram."},
    )
    runs = client.get("/agent-runs", headers=auth_headers)
    # endpoint may 404 or empty — must not create runs as side effect
    if runs.status_code == 200:
        assert runs.json() == [] or len(runs.json()) == 0
